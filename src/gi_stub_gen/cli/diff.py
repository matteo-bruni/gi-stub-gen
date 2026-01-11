#!/usr/bin/env python3
"""
Compare two Python stub files (.pyi) and generate a markdown diff report.

Usage:
    gi-stub-diff <file1.pyi> <file2.pyi> [-o output.md]
    gi-stub-diff https://example.com/file1.pyi local_file.pyi -o output.md
    gi-stub-diff file1.pyi file2.pyi --name1 "My Stubs" --name2 "pygobject-stubs"
"""

import ast
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Optional, Any
from urllib.error import URLError

import typer


def get_version() -> str:
    """Get the package version from metadata."""
    try:
        return version("gi-stub-gen")
    except Exception:
        return "unknown"


@dataclass
class Element:
    """Represents a parsed element from a stub file."""

    name: str
    kind: str  # 'function', 'class', 'constant', 'method', 'attribute'
    signature: str  # The full signature or value
    parent: str = ""  # Parent class name if applicable

    @property
    def full_name(self) -> str:
        if self.parent:
            return f"{self.parent}.{self.name}"
        return self.name


@dataclass
class ParsedStub:
    """Contains all parsed elements from a stub file."""

    functions: dict[str, Element] = field(default_factory=dict)
    classes: dict[str, Element] = field(default_factory=dict)
    constants: dict[str, Element] = field(default_factory=dict)
    class_members: dict[str, dict[str, Element]] = field(default_factory=dict)  # class_name -> {member_name: Element}


def remove_docstring(node: ast.AST) -> None:
    """Remove docstring from a function or class node."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            node.body = node.body[1:] if len(node.body) > 1 else [ast.Pass()]


def normalize_optional_types(signature: str) -> str:
    """Normalize Optional[X] and typing.Optional[X] to X | None for consistent comparison.

    This treats Optional[X], typing.Optional[X], and X | None as equivalent.
    """
    result = signature

    # Handle both Optional[X] and typing.Optional[X]
    for optional_prefix in ["typing.Optional[", "Optional["]:
        while optional_prefix in result:
            start = result.find(optional_prefix)
            if start == -1:
                break

            # Find the matching closing bracket
            bracket_count = 0
            end = start + len(optional_prefix)
            for i, char in enumerate(result[start + len(optional_prefix) :], start=start + len(optional_prefix)):
                if char == "[":
                    bracket_count += 1
                elif char == "]":
                    if bracket_count == 0:
                        end = i
                        break
                    bracket_count -= 1

            # Extract the inner type
            inner = result[start + len(optional_prefix) : end]
            # Replace with X | None
            result = result[:start] + inner + " | None" + result[end + 1 :]

    return result


def get_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Extract function signature as a string, including decorators."""
    lines = []

    # Add decorators
    for decorator in node.decorator_list:
        lines.append(f"@{ast.unparse(decorator)}")

    args = node.args
    params = []

    # Positional only args
    for arg in args.posonlyargs:
        param = arg.arg
        if arg.annotation:
            param += f": {ast.unparse(arg.annotation)}"
        params.append(param)

    if args.posonlyargs:
        params.append("/")

    # Regular args
    defaults_offset = len(args.args) - len(args.defaults)
    for i, arg in enumerate(args.args):
        param = arg.arg
        if arg.annotation:
            param += f": {ast.unparse(arg.annotation)}"
        default_idx = i - defaults_offset
        if default_idx >= 0 and args.defaults[default_idx]:
            param += f" = {ast.unparse(args.defaults[default_idx])}"
        params.append(param)

    # *args
    if args.vararg:
        param = f"*{args.vararg.arg}"
        if args.vararg.annotation:
            param += f": {ast.unparse(args.vararg.annotation)}"
        params.append(param)
    elif args.kwonlyargs:
        params.append("*")

    # Keyword only args
    for i, arg in enumerate(args.kwonlyargs):
        param = arg.arg
        if arg.annotation:
            param += f": {ast.unparse(arg.annotation)}"
        if args.kw_defaults[i]:
            param += f" = {ast.unparse(args.kw_defaults[i])}"  # type: ignore
        params.append(param)

    # **kwargs
    if args.kwarg:
        param = f"**{args.kwarg.arg}"
        if args.kwarg.annotation:
            param += f": {ast.unparse(args.kwarg.annotation)}"
        params.append(param)

    # Format with one parameter per line for readability
    if len(params) > 1:
        params_str = ",\n    ".join(params)
        signature = f"def {node.name}(\n    {params_str},\n)"
    elif params:
        signature = f"def {node.name}({params[0]})"
    else:
        signature = f"def {node.name}()"

    if node.returns:
        signature += f" -> {ast.unparse(node.returns)}"

    # Prepend decorators
    if lines:
        lines.append(signature)
        return "\n".join(lines)
    return signature


def get_class_signature(node: ast.ClassDef) -> str:
    """Extract class signature (with bases)."""
    bases = []
    for base in node.bases:
        bases.append(ast.unparse(base))
    for keyword in node.keywords:
        bases.append(f"{keyword.arg}={ast.unparse(keyword.value)}")

    if bases:
        return f"class {node.name}({', '.join(bases)})"
    return f"class {node.name}"


def get_constant_value(node: ast.AnnAssign | ast.Assign) -> str:
    """Extract constant value/annotation as string."""
    if isinstance(node, ast.AnnAssign):
        result = f": {ast.unparse(node.annotation)}"
        if node.value:
            result += f" = {ast.unparse(node.value)}"
        return result
    elif isinstance(node, ast.Assign):
        if node.value:
            return f" = {ast.unparse(node.value)}"
    return ""


def is_url(path: str) -> bool:
    """Check if a path is a URL."""
    return path.startswith(("http://", "https://"))


def convert_github_url_to_raw(url: str) -> str:
    """Convert a GitHub blob URL to raw content URL."""
    # Convert github.com/user/repo/blob/branch/path to raw.githubusercontent.com/user/repo/branch/path
    pattern = r"https?://github\.com/([^/]+)/([^/]+)/blob/(.+)"
    match = re.match(pattern, url)
    if match:
        owner, repo, path = match.groups()
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{path}"
    return url


def fetch_url_content(url: str) -> str:
    """Fetch content from a URL."""
    # Convert GitHub URLs to raw URLs
    url = convert_github_url_to_raw(url)

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (diff.py stub comparator)"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def parse_stub_content(content: str) -> ParsedStub:
    """Parse stub content string and extract all elements."""
    tree = ast.parse(content)

    result = ParsedStub()

    for node in ast.walk(tree):
        remove_docstring(node)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sig = get_function_signature(node)
            result.functions[node.name] = Element(name=node.name, kind="function", signature=sig)

        elif isinstance(node, ast.ClassDef):
            sig = get_class_signature(node)
            result.classes[node.name] = Element(name=node.name, kind="class", signature=sig)

            # Parse class members
            result.class_members[node.name] = {}
            for class_node in node.body:
                if isinstance(class_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    member_sig = get_function_signature(class_node)
                    result.class_members[node.name][class_node.name] = Element(
                        name=class_node.name, kind="method", signature=member_sig, parent=node.name
                    )
                elif isinstance(class_node, ast.AnnAssign) and isinstance(class_node.target, ast.Name):
                    attr_name = class_node.target.id
                    attr_sig = get_constant_value(class_node)
                    result.class_members[node.name][attr_name] = Element(
                        name=attr_name, kind="attribute", signature=f"{attr_name}{attr_sig}", parent=node.name
                    )
                elif isinstance(class_node, ast.Assign):
                    for target in class_node.targets:
                        if isinstance(target, ast.Name):
                            attr_name = target.id
                            attr_sig = get_constant_value(class_node)
                            result.class_members[node.name][attr_name] = Element(
                                name=attr_name, kind="attribute", signature=f"{attr_name}{attr_sig}", parent=node.name
                            )

        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            sig = get_constant_value(node)
            result.constants[name] = Element(name=name, kind="constant", signature=f"{name}{sig}")

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    sig = get_constant_value(node)
                    result.constants[name] = Element(name=name, kind="constant", signature=f"{name}{sig}")

    return result


def parse_stub_file(filepath: Path) -> ParsedStub:
    """Parse a stub file and extract all elements."""
    content = filepath.read_text(encoding="utf-8")
    return parse_stub_content(content)


def parse_stub_source(source: str) -> ParsedStub:
    """Parse a stub from either a file path or URL."""
    if is_url(source):
        content = fetch_url_content(source)
        return parse_stub_content(content)
    else:
        filepath = Path(source)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        return parse_stub_file(filepath)


# Indent style options
INDENT_NBSP = "nbsp"  # Use &nbsp; for indentation (default)
INDENT_SPACES = "spaces"  # Use regular spaces
INDENT_PRE = "pre"  # Use <pre> tags instead of <code>


def escape_markdown(text: str, indent_style: str = INDENT_NBSP) -> str:
    """Escape special markdown characters and format for table."""
    text = text.replace("|", "\\|")
    # Escape underscores to prevent markdown bold/italic interpretation
    text = text.replace("_", "\\_")

    if indent_style == INDENT_PRE:
        # Use <pre> tags which preserve whitespace natively
        text = text.replace("\n", "<br>")
        return f"<pre>{text}</pre>"

    # Process lines for <code> formatting
    lines = text.split("\n")
    result_lines = []
    for line in lines:
        if indent_style == INDENT_NBSP:
            # Count leading spaces and convert to &nbsp;
            stripped = line.lstrip(" ")
            indent_count = len(line) - len(stripped)
            if indent_count > 0:
                line = "&nbsp;" * indent_count + stripped
        # INDENT_SPACES: keep spaces as-is (may not render correctly in all viewers)
        result_lines.append(line)
    text = "<br>".join(result_lines)
    return f"<code>{text}</code>"


def check_runtime_existence(name: str, kind: str, namespace_module: Any | None, signature: str = "") -> str:
    """
    Check if an element actually exists at runtime in the given namespace module.
    
    Returns:
        '✅' if exists, '❌' if not exists, 'n/a' for Protocols/callbacks, '-' if no module provided
    """
    if namespace_module is None:
        return "-"
    
    # Protocol classes are type hints generated by the stub generator, they don't exist at runtime
    if "typing.Protocol" in signature or "(typing.Protocol)" in signature:
        return "n/a"
    
    try:
        # Handle class members like "ClassName.method_name" or "ClassName.attribute"
        parts = name.split(".")
        obj = namespace_module
        
        for i, part in enumerate(parts):
            try:
                has_attr = hasattr(obj, part)
            except NotImplementedError:
                # GI raises NotImplementedError for callbacks and some other types
                return "n/a"
            
            if not has_attr:
                # For attributes, they might only exist on instances, not the class itself
                # Try to instantiate and check on the instance
                if kind == "attribute" and i == len(parts) - 1:
                    try:
                        # Try to create an instance with no args
                        instance = obj()
                        if hasattr(instance, part):
                            return "✅"
                    except Exception:
                        # Can't instantiate, check if it's in __annotations__ or dir()
                        if hasattr(obj, "__annotations__") and part in obj.__annotations__:
                            return "✅"
                        # Some GI structs have fields accessible via dir() but not hasattr on class
                        if part in dir(obj):
                            return "✅"
                return "❌"
            obj = getattr(obj, part)
        
        # If we got here, it exists
        return "✅"
    except Exception:
        return "n/a"


def get_all_toplevel_names(stub: ParsedStub) -> set[str]:
    """Get all top-level element names (functions, classes, constants)."""
    return set(stub.functions.keys()) | set(stub.classes.keys()) | set(stub.constants.keys())


def get_element_by_name(stub: ParsedStub, name: str) -> Element | None:
    """Get an element by name, checking all categories."""
    if name in stub.functions:
        return stub.functions[name]
    if name in stub.classes:
        return stub.classes[name]
    if name in stub.constants:
        return stub.constants[name]
    return None


def generate_markdown_report(
    source1: str,
    source2: str,
    stub1: ParsedStub,
    stub2: ParsedStub,
    name1: str | None = None,
    name2: str | None = None,
    indent_style: str = INDENT_NBSP,
    normalize_optional: bool = True,
    namespace: str | None = None,
) -> str:
    """Generate a markdown comparison report."""
    display_name1 = name1 or "File 1"
    display_name2 = name2 or "File 2"
    
    # Load namespace module for runtime existence check
    namespace_module: Any | None = None
    if namespace:
        try:
            import gi
            import importlib
            gi.require_version(namespace, gi.Repository.get_default().enumerate_versions(namespace)[0])
            namespace_module = importlib.import_module(f"gi.repository.{namespace}")
            # Some namespaces require initialization (e.g., Gst)
            if hasattr(namespace_module, "init"):
                namespace_module.init(None)
        except Exception:
            # Will show "-" for all existence checks
            namespace_module = None

    # Get all top-level names from both stubs
    names1 = get_all_toplevel_names(stub1)
    names2 = get_all_toplevel_names(stub2)

    # Names only in file 1 (not present in any form in file 2)
    only_in_1_names = names1 - names2
    # Names only in file 2 (not present in any form in file 1)
    only_in_2_names = names2 - names1
    # Names present in both (may have different types or signatures)
    common_names = names1 & names2

    # ========== COLLECT ALL DATA FIRST ==========
    
    only_in_1: list[tuple[str, str, str, str]] = []  # (kind, name, signature, exists)

    # Top-level elements only in file 1
    for name in sorted(only_in_1_names):
        elem = get_element_by_name(stub1, name)
        if elem:
            exists = check_runtime_existence(name, elem.kind, namespace_module, elem.signature)
            only_in_1.append((elem.kind, name, elem.signature, exists))

    # Class members (for classes present in both)
    for class_name in sorted(set(stub1.class_members.keys()) & set(stub2.class_members.keys())):
        members1 = stub1.class_members[class_name]
        members2 = stub2.class_members[class_name]
        for member_name in sorted(set(members1.keys()) - set(members2.keys())):
            elem = members1[member_name]
            full_name = f"{class_name}.{member_name}"
            exists = check_runtime_existence(full_name, elem.kind, namespace_module, elem.signature)
            only_in_1.append((elem.kind, full_name, elem.signature, exists))

    only_in_2: list[tuple[str, str, str, str]] = []  # (kind, name, signature, exists)

    # Top-level elements only in file 2
    for name in sorted(only_in_2_names):
        elem = get_element_by_name(stub2, name)
        if elem:
            exists = check_runtime_existence(name, elem.kind, namespace_module, elem.signature)
            only_in_2.append((elem.kind, name, elem.signature, exists))

    # Class members (for classes present in both)
    for class_name in sorted(set(stub1.class_members.keys()) & set(stub2.class_members.keys())):
        members1 = stub1.class_members[class_name]
        members2 = stub2.class_members[class_name]
        for member_name in sorted(set(members2.keys()) - set(members1.keys())):
            elem = members2[member_name]
            full_name = f"{class_name}.{member_name}"
            exists = check_runtime_existence(full_name, elem.kind, namespace_module, elem.signature)
            only_in_2.append((elem.kind, full_name, elem.signature, exists))

    differences: list[tuple[str, str, str, str, str]] = []  # (kind1, kind2, name, sig1, sig2)

    # Compare common top-level names (may have different types)
    for name in sorted(common_names):
        elem1 = get_element_by_name(stub1, name)
        elem2 = get_element_by_name(stub2, name)
        if elem1 and elem2:
            sig1 = elem1.signature
            sig2 = elem2.signature
            if normalize_optional:
                sig1_cmp = normalize_optional_types(sig1)
                sig2_cmp = normalize_optional_types(sig2)
            else:
                sig1_cmp = sig1
                sig2_cmp = sig2
            if elem1.kind != elem2.kind or sig1_cmp != sig2_cmp:
                differences.append((elem1.kind, elem2.kind, name, elem1.signature, elem2.signature))

    # Class members differences
    for class_name in sorted(set(stub1.class_members.keys()) & set(stub2.class_members.keys())):
        members1 = stub1.class_members[class_name]
        members2 = stub2.class_members[class_name]
        for member_name in sorted(set(members1.keys()) & set(members2.keys())):
            elem1 = members1[member_name]
            elem2 = members2[member_name]
            sig1 = elem1.signature
            sig2 = elem2.signature
            if normalize_optional:
                sig1_cmp = normalize_optional_types(sig1)
                sig2_cmp = normalize_optional_types(sig2)
            else:
                sig1_cmp = sig1
                sig2_cmp = sig2
            if elem1.kind != elem2.kind or sig1_cmp != sig2_cmp:
                differences.append(
                    (elem1.kind, elem2.kind, f"{class_name}.{member_name}", elem1.signature, elem2.signature)
                )

    # ========== COMPUTE STATISTICS ==========
    
    def count_by_kind(items: list[tuple[str, str, str, str]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for kind, _, _, _ in items:
            counts[kind] = counts.get(kind, 0) + 1
        return counts

    def count_by_exists(items: list[tuple[str, str, str, str]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for _, _, _, exists in items:
            counts[exists] = counts.get(exists, 0) + 1
        return counts

    only_in_1_by_kind = count_by_kind(only_in_1)
    only_in_2_by_kind = count_by_kind(only_in_2)
    only_in_1_by_exists = count_by_exists(only_in_1)
    only_in_2_by_exists = count_by_exists(only_in_2)

    # ========== GENERATE REPORT ==========

    # Generate current date
    current_date = datetime.now().strftime("%Y-%m-%d")

    lines = [
        "# Stub Comparison Report",
        "",
        f"**Generated by:** gi-stub-diff v{get_version()}",
        f"**Date:** {current_date}",
        "",
    ]

    # Summary at top
    lines.extend([
        "## Summary",
        "",
        f"| Metric | {display_name1} | {display_name2} |",
        "|--------|-----------------|-----------------|",
        f"| **Total unique elements** | {len(only_in_1)} | {len(only_in_2)} |",
    ])
    
    # Add breakdown by type
    all_kinds = sorted(set(only_in_1_by_kind.keys()) | set(only_in_2_by_kind.keys()))
    for kind in all_kinds:
        count1 = only_in_1_by_kind.get(kind, 0)
        count2 = only_in_2_by_kind.get(kind, 0)
        # Pluralize correctly (class -> classes, not classs)
        plural = "es" if kind.endswith("s") else "s"
        lines.append(f"| └ {kind}{plural} | {count1} | {count2} |")
    
    lines.append(f"| **Elements with differences** | {len(differences)} | |")
    lines.append("")

    # Existence stats if namespace provided
    if namespace:
        lines.extend([
            "### Runtime Existence Check",
            "",
            f"Checked against `gi.repository.{namespace}` at runtime:",
            "",
            f"| Status | {display_name1} | {display_name2} |",
            "|--------|-----------------|-----------------|",
            f"| ✅ Exists | {only_in_1_by_exists.get('✅', 0)} | {only_in_2_by_exists.get('✅', 0)} |",
            f"| ❌ Does not exist | {only_in_1_by_exists.get('❌', 0)} | {only_in_2_by_exists.get('❌', 0)} |",
            f"| n/a Protocol/Callback | {only_in_1_by_exists.get('n/a', 0)} | {only_in_2_by_exists.get('n/a', 0)} |",
            "",
        ])

    lines.append("---")
    lines.append("")

    # Description
    lines.extend([
        "## Description",
        "",
        "This report compares two Python stub files (.pyi) and identifies differences between them.",
        "The comparison is organized into three sections:",
        "",
        f"1. **Elements present only in {display_name1}**: Functions, classes, and constants that exist in the first file but not in the second.",
        f"2. **Elements present only in {display_name2}**: Functions, classes, and constants that exist in the second file but not in the first.",
        "3. **Differences between common elements**: Elements that exist in both files but have different signatures or types.",
        "",
    ])

    # Exists column explanation
    if namespace:
        lines.extend([
            "### Exists Column",
            "",
            "The **Exists** column indicates whether the element actually exists at runtime in the GI namespace:",
            "",
            "| Symbol | Meaning |",
            "|:------:|---------|",
            "| ✅ | Element exists at runtime in the namespace |",
            "| ❌ | Element does NOT exist at runtime (may be incorrect or obsolete in the stub) |",
            "| n/a | Cannot be verified - Protocol classes are type hints for callbacks and don't exist as real classes at runtime |",
            "",
        ])

    # Parameters
    lines.extend([
        "### Parameters",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| Source 1 | `{source1}` |",
        f"| Source 2 | `{source2}` |",
        f"| Display name 1 | {display_name1} |",
        f"| Display name 2 | {display_name2} |",
        f"| Indent style | {indent_style} |",
        f"| Normalize Optional | {normalize_optional} |",
        f"| Namespace | {namespace or 'None (runtime check disabled)'} |",
        "",
        "---",
        "",
        "## Table of Contents",
        "",
        f"- [Summary](#summary)",
        f"- [1. Elements present only in {display_name1}](#1-elements-present-only-in-{display_name1.lower().replace(' ', '-')})",
        f"- [2. Elements present only in {display_name2}](#2-elements-present-only-in-{display_name2.lower().replace(' ', '-')})",
        "- [3. Differences between common elements](#3-differences-between-common-elements)",
        "",
    ])

    # Add note about Optional normalization if enabled
    if normalize_optional:
        lines.extend([
            "> **Note:** `Optional[X]` and `X | None` are treated as equivalent in this comparison.",
            "",
        ])

    # Section 1: Elements only in file 1
    lines.extend([
        "---",
        "",
        f"# 1. Elements present only in {display_name1}",
        "",
    ])

    if only_in_1:
        lines.extend(
            [
                "| Type | Name | Exists | Signature |",
                "|------|------|:------:|-----------|",
            ]
        )
        for kind, name, sig, exists in only_in_1:
            lines.append(f"| {kind} | `{name}` | {exists} | {escape_markdown(sig, indent_style)} |")
    else:
        lines.append(f"*No elements found only in {display_name1}.*")

    lines.append("")

    # Section 2: Elements only in file 2
    lines.extend(
        [
            "---",
            "",
            f"# 2. Elements present only in {display_name2}",
            "",
        ]
    )

    if only_in_2:
        lines.extend(
            [
                "| Type | Name | Exists | Signature |",
                "|------|------|:------:|-----------|",
            ]
        )
        for kind, name, sig, exists in only_in_2:
            lines.append(f"| {kind} | `{name}` | {exists} | {escape_markdown(sig, indent_style)} |")
    else:
        lines.append(f"*No elements found only in {display_name2}.*")

    lines.append("")

    # Section 3: Differences between common elements
    lines.extend(
        [
            "---",
            "",
            "# 3. Differences between common elements",
            "",
        ]
    )

    if differences:
        lines.extend(
            [
                f"| Type ({display_name1}) | Type ({display_name2}) | Name | {display_name1} | {display_name2} |",
                "|------|------|------|--------|--------|",
            ]
        )
        for kind1, kind2, name, sig1, sig2 in differences:
            lines.append(
                f"| {kind1} | {kind2} | `{name}` | {escape_markdown(sig1, indent_style)} | {escape_markdown(sig2, indent_style)} |"
            )
    else:
        lines.append("*No differences found between common elements.*")

    lines.append("")

    # Summary
    # (Summary is now generated at the top of the report)

    return "\n".join(lines)


class IndentStyle(str, Enum):
    """Enum for indent style choices."""

    nbsp = INDENT_NBSP
    spaces = INDENT_SPACES
    pre = INDENT_PRE


app = typer.Typer(help="Compare two Python stub files and generate a markdown diff report.")


@app.command()
def main(
    source1: Annotated[
        str,
        typer.Argument(help="First stub file (.pyi) - can be a local path or URL"),
    ],
    source2: Annotated[
        str,
        typer.Argument(help="Second stub file (.pyi) - can be a local path or URL"),
    ],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output markdown file (default: stdout)"),
    ] = None,
    name1: Annotated[
        Optional[str],
        typer.Option(help="Display name for the first file in the report (default: 'File 1')"),
    ] = None,
    name2: Annotated[
        Optional[str],
        typer.Option(help="Display name for the second file in the report (default: 'File 2')"),
    ] = None,
    indent_style: Annotated[
        IndentStyle,
        typer.Option(
            "--indent-style",
            help=f"How to format indentation in code blocks: '{INDENT_NBSP}' (default, uses &nbsp;), "
            f"'{INDENT_SPACES}' (plain spaces), '{INDENT_PRE}' (use <pre> tags)",
        ),
    ] = IndentStyle.nbsp,
    normalize_optional: Annotated[
        bool,
        typer.Option(
            "--normalize-optional/--no-normalize-optional",
            help="Treat Optional[X] and X | None as equivalent (default: True)",
        ),
    ] = True,
    namespace: Annotated[
        Optional[str],
        typer.Option(
            "--namespace", "-n",
            help="GI namespace to check runtime existence (e.g., 'Gst', 'Gtk'). If provided, adds 'Exists' column.",
        ),
    ] = None,
) -> None:
    """Compare two Python stub files and generate a markdown diff report."""
    try:
        stub1 = parse_stub_source(source1)
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except URLError as e:
        typer.echo(f"Error fetching URL {source1}: {e}", err=True)
        raise typer.Exit(1)
    except SyntaxError as e:
        typer.echo(f"Error parsing first file: {e}", err=True)
        raise typer.Exit(1)

    try:
        stub2 = parse_stub_source(source2)
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except URLError as e:
        typer.echo(f"Error fetching URL {source2}: {e}", err=True)
        raise typer.Exit(1)
    except SyntaxError as e:
        typer.echo(f"Error parsing second file: {e}", err=True)
        raise typer.Exit(1)

    report = generate_markdown_report(
        source1,
        source2,
        stub1,
        stub2,
        name1=name1,
        name2=name2,
        indent_style=indent_style.value,
        normalize_optional=normalize_optional,
        namespace=namespace,
    )

    if output:
        output.write_text(report, encoding="utf-8")
        typer.echo(f"Report written to: {output}")
    else:
        typer.echo(report)


if __name__ == "__main__":
    app()
