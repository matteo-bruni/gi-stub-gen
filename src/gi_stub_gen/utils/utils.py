import typing
import keyword
import logging

import re

from typing import Any, TypeVar
from pathlib import Path
from gi.repository import GObject


logger = logging.getLogger(__name__)

T = TypeVar("T")


class SingletonMeta(type):
    """
    Metaclasse Singleton 'Type-Aware'.
    """

    _instances: dict[type, Any] = {}

    def __call__(cls: type[T], *args: Any, **kwargs: Any) -> T:
        if cls not in SingletonMeta._instances:
            instance = super().__call__(*args, **kwargs)  # type: ignore
            SingletonMeta._instances[cls] = instance
        return SingletonMeta._instances[cls]


def is_py_builtin_type(py_type):
    return py_type in (int, str, float, dict, tuple, list, bool)
    # return py_type.__name__ in dir(builtins)


def is_genum(attribute):
    return isinstance(attribute, type) and issubclass(attribute, GObject.GEnum)


def is_gflags(attribute):
    return isinstance(attribute, type) and issubclass(attribute, GObject.GFlags)


def get_super_class_name(
    obj,
    current_namespace: str | None = None,
) -> tuple[str | None, str]:
    """
    Get the super class name of an object
    If current namespace is the same as the super class namespace
    it will return namespace, classname of the super class

    Args:
        obj (Any): object to get the super class name from
        current_namespace (str | None): current namespace of the object
    Returns:
        tuple:
            - str | None: super class module
            - str class name
    """

    # If namespace is not provided, try to extract it from the object's module.
    # e.g., "gi.repository.Gtk" -> "Gtk"
    if current_namespace is None:
        parts = obj.__module__.split(".")
        current_namespace = parts[-1] if parts else ""
    else:
        current_namespace = sanitize_gi_module_name(current_namespace)

    super_class = object

    # Iterate over the MRO, skipping the first element (the class itself).
    for cls in obj.__mro__[1:]:
        mod_name = str(cls.__module__)
        cls_name = cls.__name__

        # 1. Skip internal C modules
        # 'gi._gi' contains the raw C pointers/structs, not valid for inheritance stubs.
        if mod_name == "gi._gi":
            continue

        # 2. Skip PyGObject Overrides
        # We want to link to the static repository types (gi.repository.X),
        # not the dynamic python overrides (gi.overrides.X).
        if "gi.overrides" in mod_name:
            continue

        # 3. Handle classes with the SAME NAME as the object
        if cls_name == obj.__name__:
            # Extract the namespace of the candidate super class
            # e.g., "gi.repository.Gio" -> "Gio"
            candidate_ns = mod_name.split(".")[-1]

            # CASE A: Shadowing (Same Name, Same Namespace)
            # e.g., obj is Gtk.Builder (override), candidate is Gtk.Builder (repo).
            # We must SKIP this because a class cannot inherit from itself in the stub.
            if candidate_ns == current_namespace:
                continue

            # CASE B: Valid Inheritance (Same Name, Different Namespace)
            # e.g., obj is Gtk.Application, candidate is Gio.Application.
            # This is valid. We found the parent. Stop here.
            # (Implicitly handled by falling through to the break below)

        # 4. Skip GInterface
        # GInterface often appears in the MRO but cannot be used as a direct
        # base class in the generated stub definition if a concrete GObject base exists.
        if cls_name == "GInterface" and cls.__module__ == "gobject":
            continue

        # If we passed all checks, this is the valid super class.
        super_class = cls
        break

    super_module = str(super_class.__module__)

    # --- Formatting Output ---

    # Handle built-in types (e.g. object, int, etc.)
    if super_module == "builtins":
        if super_class.__name__ == "module":
            return None, "type"
        return super_module, super_class.__name__

    return super_module, super_class.__name__


def get_py_type_namespace_repr(py_type: Any) -> str | None:
    """
    Get the namespace repr of a python type or object
    """

    # if the type has a __info__ attribute, it is a GObject type
    # and we can get the namespace from it
    if hasattr(py_type, "__info__"):
        return f"{py_type.__info__.get_namespace()}"  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]

    # py_type.__module__

    from inspect import getmodule

    # we can use getmodule to get the module of the type
    if module_namespace := getmodule(py_type):
        name = module_namespace.__name__

        # assert "gobject" not in name, f"module name not sanitized: {name}: {py_type}"
        # manual fix for some modules, how to get the correct namespace?
        name = sanitize_gi_module_name(name)
        if name == "builtins":
            return None

        # we search for alternatives
        if name == "gi._gi":
            from gi_stub_gen.utils.gi_utils import get_gi_module_from_name

            # ie gi._gi.OptionGroup is also in GLib.OptionGroup
            target = get_py_type_name_repr(py_type)
            # search if we can import from GLib or GObject
            for alt_namespace in ("GLib", "GObject"):
                try:
                    # the version should already be required at this point
                    module = get_gi_module_from_name(f"gi.repository.{alt_namespace}", None)
                    if hasattr(module, target):
                        return alt_namespace
                except (ImportError, AttributeError):
                    pass

        return name

    return None


def get_py_type_name_repr(py_type: Any) -> str:
    """
    Get the string representation of a python type or object
    """
    # if it is a GObject
    if hasattr(py_type, "__info__"):
        # assert False, f"which type is this? {py_type}: {py_type.__info__.get_name()}"
        return f"{py_type.__info__.get_name()}"

    if hasattr(py_type, "__name__"):
        # assert False, f"which type is this? {py_type}: {py_type.__name__}"
        return py_type.__name__

    return str(py_type)


def split_gi_name_version(name_version: str) -> tuple[str, str | None]:
    """
    Split a name:version string into a tuple of name and version.
    If the version is not present, return None for the version.

    e.g. "gi.repository.Gio:2.0" -> ("gi.repository.Gio", "2.0")
    """
    if ":" in name_version:
        module_name, gi_version = name_version.split(":", maxsplit=1)
        return module_name, gi_version
    return name_version, None


def sanitize_gi_module_name(module_name: str) -> str:
    """
    Sanitize the module name to be used in the gi.repository namespace.
    This will remove the gi.repository prefix and return the module name.
    """
    if not isinstance(module_name, str):
        raise ValueError("module_name must be a string")
    return (
        str(module_name)
        .removeprefix("gi.repository.")
        .removeprefix("gi.overrides.")
        .replace("gobject", "GObject")
        .replace("glib", "GLib")
        # .replace("gi", "GI")
    )


def sanitize_variable_name(
    name: str,
    keyword_check=True,
) -> tuple[str, str | None]:
    """
    Sanitizes a variable name to be a valid Python identifier.

    It checks for keywords, invalid characters, and leading numbers.
    It returns distinct reasons for the modification.

    Args:
        name (str): The candidate variable name.
        keyword_check (bool): Whether to check for Python keywords.

    Returns:
        tuple:
            - The sanitized valid identifier.
            - A reason string if changed, or None if valid.
    """
    original_name = name

    if not name:
        raise ValueError("Variable name cannot be empty")

    if keyword_check:
        # check if the name is a keyword first
        if keyword.iskeyword(name):
            return f"{name}_", f"[{original_name}]: changed, name is a reserved keyword"

    # If it is already perfect, return immediately.
    if name.isidentifier():
        return name, None

    # If we are here, .isidentifier() returned False.
    # We need to find out why.

    reasons = []
    # Fix Invalid Characters (anything not a-z, A-Z, 0-9, _)
    # We strip invalid chars first to see if that fixes it.
    clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if clean_name != name:
        reasons.append("contained invalid characters")
        name = clean_name

    # Fix Leading Numbers (Identifiers cannot start with a digit)
    # We check the NEW name (after char sanitization)
    if name[0].isdigit():
        name = f"_{name}"
        reasons.append("started with a number")

    # Handle edge case: String became empty or just underscores after regex
    # (e.g., input "..." -> "___") - technically "___" is a valid identifier,
    # but if it became empty string "" we must fix it.
    if not name:
        name = "_"
        reasons.append("result was empty")

    # Re-check keyword (Rare case: e.g. input "class@" -> "class" -> "class_")
    if keyword.iskeyword(name):
        name = f"{name}_"
        reasons.append("result conflicted with keyword")

    # Format the final reason message
    full_reason = f"[{original_name}]: changed because {', '.join(reasons)}"

    return name, full_reason


def _get_union_str(type_list: list[str]) -> str:
    """
    Helper to create a sorted, deduplicated Union string using modern syntax (|).
    Example: ['int', 'str', 'int'] -> 'int | str'
    """
    unique_types = sorted(list(set(type_list)))
    return " | ".join(unique_types)


def get_type_hint(obj) -> str:
    """
    Recursively infers the type hint of a runtime object,
    generating a string suitable for .pyi stubs.
    Uses modern syntax (dict, list, tuple, |).
    """
    # 1. Handle None
    if obj is None:
        return "None"

    # 2. Handle Dictionaries: dict[KeyType, ValueType]
    if isinstance(obj, dict):
        if not obj:
            return "dict[typing.Any, typing.Any]"

        # Recursively get types for all keys and values
        key_hint = _get_union_str([get_type_hint(k) for k in obj.keys()])
        val_hint = _get_union_str([get_type_hint(v) for v in obj.values()])

        return f"dict[{key_hint}, {val_hint}]"

    # 3. Handle Lists: list[Type] (treated as homogenous or Union)
    elif isinstance(obj, list):
        if not obj:
            return "list[typing.Any]"

        elem_hint = _get_union_str([get_type_hint(e) for e in obj])
        return f"list[{elem_hint}]"

    # 4. Handle Tuples: tuple[Type1, Type2, ...] (treated as fixed structure)
    elif isinstance(obj, tuple):
        if not obj:
            return "tuple[()]"

        # Tuples preserve order and allow duplicates (e.g. tuple[int, int])
        elem_hints = [get_type_hint(e) for e in obj]
        return f"tuple[{', '.join(elem_hints)}]"

    # 5. Handle Primitives and Instances
    return type(obj).__name__


def get_redacted_stub_value(obj: typing.Any) -> str:
    """
    Recursively redacts sensitive or overly specific values in stub representations.
    This includes:
    - Absolute file paths (replaced with "...")
    - Primitive values (int, float, bool, None) are kept as-is
    - Collections (list, tuple, set, dict) are recursively redacted
    Args:
        obj (typing.Any): The object to redact.
    Returns:
        str: The redacted string representation.
    """
    # 1. Strings: Censor existing absolute paths
    if isinstance(obj, str):
        try:
            if Path(obj).is_absolute() and Path(obj).exists():
                return "..."
        except (OSError, ValueError):
            pass
        return repr(obj)

    # 2. Primitives & Ellipsis
    if obj is Ellipsis:
        return "..."
    if isinstance(obj, (int, float, bool, type(None))):
        return repr(obj)

    # 3. Collections (Recursive)
    fmt = get_redacted_stub_value  # Short alias for recursion

    if isinstance(obj, (list, tuple, set)):
        # Sort sets for deterministic output, keep others ordered
        items = sorted(obj, key=str) if isinstance(obj, set) else obj
        # Map all items recursively
        parts = [fmt(x) for x in items]
        body = ", ".join(parts)

        if isinstance(obj, list):
            return f"[{body}]"
        if isinstance(obj, set):
            return f"{{{body}}}" if body else "set()"
        # Tuple: needs trailing comma if singleton
        return f"({body}{',' if len(parts) == 1 else ''})"

    if isinstance(obj, dict):
        body = ", ".join(f"{fmt(k)}: {fmt(v)}" for k, v in obj.items())
        return f"{{{body}}}"

    return repr(obj)


def format_stub_with_ruff(
    code_content: str,
    virtual_filename: str = "generated.pyi",
) -> str:
    """
    Formats a string of code using 'ruff format' via stdin.

    It uses pathlib to construct a virtual absolute path. This ensures that Ruff
    can correctly resolve the project configuration (pyproject.toml) by walking
    up the directory tree from the current working directory.

    Args:
        code_content: The raw source code string to format.
        virtual_filename: A filename to simulate. Important for applying
                          file-specific rules (e.g., .pyi vs .py).

    Returns:
        The formatted code string, or the original content if Ruff fails or is missing.
    """
    import subprocess
    import shutil

    ruff_path = shutil.which("ruff")
    if not ruff_path:
        logger.warning("⚠️ Warning: Ruff not found. Skipping formatting.")
        return code_content

    # We assume the script is running from the project root (where pyproject.toml usually is).
    # Passing this full path via --stdin-filename allows Ruff to find the config file.
    # i.e. config inside pyproject.toml will be applied.
    virtual_path = Path.cwd() / virtual_filename

    try:
        # '-' tells ruff to read from standard input (stdin)
        # '--stdin-filename' gives context for config resolution and file type rules
        process = subprocess.run(
            [ruff_path, "format", "-", f"--stdin-filename={virtual_path}"],
            input=code_content.encode("utf-8"),  # Send string as bytes
            capture_output=True,  # Capture stdout and stderr
            check=True,  # Raise CalledProcessError on failure
        )
        return process.stdout.decode("utf-8")

    except subprocess.CalledProcessError as e:
        # If Ruff fails (e.g., syntax error in the generated code), print the error
        # but return the unformatted code to avoid losing data.
        error_msg = e.stderr.decode("utf-8")
        logger.error(f"❌ Ruff formatting failed on {virtual_filename}:\n{error_msg}")
        return code_content
