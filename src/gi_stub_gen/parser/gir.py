"""
Parser for GIR files to extract documentation.
"""

from __future__ import annotations

from pathlib import Path
import re
import logging

from lxml import etree
from pydantic import BaseModel


logger = logging.getLogger(__name__)


def make_safe_docstring(text: str | None) -> str:
    """
    Cleans up the raw docstring from GIR to make it safe for Python.
    Escapes backslashes and handles quotes.
    """
    if not text:
        return ""

    # Find a backslash not followed by a letter, number or another backslash
    # Transform "function\()" -> "function()"
    # Transform "set_\*"    -> "set_*"
    # Ignore    "C:\User"
    text = re.sub(r"\\(?=[^a-zA-Z0-9\\])", "", text)

    # "C:\user" -> "C:\\user"
    text = text.replace("\\", "\\\\")

    # '''triple quotes''' -> '\"\"\"triple quotes\"\"\"'
    text = text.replace('"""', r"\"\"\"")

    return text


class GirFunctionDocs(BaseModel):
    """
    Documentation for any callable entity (Function, Method, Signal, Constructor).
    """

    docstring: str
    params: dict[str, str]
    return_doc: str


class GirClassDocs(BaseModel):
    """Class documentation extracted from GIR."""

    class_docstring: str
    fields: dict[str, str]  # Data fields
    methods: dict[str, GirFunctionDocs]  # Instance methods, static methods, and constructors
    signals: dict[str, GirFunctionDocs]  # Signals <glib:signal>
    properties: dict[str, str]  # GObject Properties <property>


class ModuleDocs(BaseModel):
    """Top-level container for all documentation in a GIR module."""

    constants: dict[str, str]
    functions: dict[str, GirFunctionDocs]  # Global functions
    enums: dict[str, GirClassDocs]  # Enums and Bitfields
    classes: dict[str, GirClassDocs]  # Classes, Records, Interfaces


def _get_first_doc_text(
    element: etree._Element,
    namespace: dict[str, str],
) -> str:
    """
    Helper to safely extract and clean the text of the first <doc> child tag.
    """
    docs = element.findall("core:doc", namespaces=namespace)
    if docs and docs[0].text:
        return make_safe_docstring(docs[0].text)
    return ""


def _extract_function_docs(
    element: etree._Element,
    namespace: dict[str, str],
) -> GirFunctionDocs:
    """
    Extracts documentation for any function-like node (method, function, constructor, signal).
    """
    docstring = _get_first_doc_text(element, namespace)

    # Extract parameters
    params_docs: dict[str, str] = {}
    parameters = element.find("core:parameters", namespaces=namespace)
    if parameters is not None:
        # We iterate over <parameter> and <instance-parameter> (for methods)
        # We use findall for direct children to avoid traversing too deep or wrong nodes
        for param in parameters.findall("core:parameter", namespaces=namespace):
            param_name = param.attrib.get("name")
            if param_name:
                params_docs[param_name] = _get_first_doc_text(param, namespace)

        # Optionally handle instance-parameter if needed (usually 'self', often ignored)
        for param in parameters.findall("core:instance-parameter", namespaces=namespace):
            param_name = param.attrib.get("name")
            if param_name and param_name != "self":  # Skip self usually
                params_docs[param_name] = _get_first_doc_text(param, namespace)

    # Extract return value documentation
    return_docstring = ""
    return_val = element.find("core:return-value", namespaces=namespace)
    if return_val is not None:
        return_docstring = _get_first_doc_text(return_val, namespace)

    return GirFunctionDocs(
        docstring=docstring,
        params=params_docs,
        return_doc=return_docstring,
    )


def parse_constants(
    path: str,
    root: etree._ElementTree,
    namespace: dict[str, str],
) -> dict[str, str]:
    """Parses global constants documentation."""
    constant_docs: dict[str, str] = {}
    for f in root.xpath(path, namespaces=namespace):  # type: ignore
        name = f.attrib.get("name")
        if name:
            constant_docs[name] = _get_first_doc_text(f, namespace)  # type: ignore
    return constant_docs


def parse_global_functions(
    path: str, root: etree._ElementTree, namespace: dict[str, str]
) -> dict[str, GirFunctionDocs]:
    """Parses global module functions."""
    function_docs: dict[str, GirFunctionDocs] = {}

    for f in root.xpath(path, namespaces=namespace):  # type: ignore
        name = f.attrib.get("name")
        if not name:
            continue
        function_docs[name] = _extract_function_docs(f, namespace)  # type: ignore

    return function_docs


def _parse_simple_container(
    path: str,
    root: etree._ElementTree,
    namespace: dict[str, str],
    member_tag: str,
) -> dict[str, GirClassDocs]:
    """
    Parses simple containers like Enumerations and Bitfields.
    """
    docs: dict[str, GirClassDocs] = {}

    for container in root.xpath(path, namespaces=namespace):  # type: ignore
        name = container.attrib.get("name")
        if not name:
            continue

        class_docstring = _get_first_doc_text(container, namespace)  # type: ignore
        members_docs: dict[str, str] = {}

        # Use findall for performance and type safety on direct children
        for member in container.findall(member_tag, namespaces=namespace):
            member_name = member.attrib.get("name")
            if member_name:
                members_docs[member_name] = _get_first_doc_text(member, namespace)

        docs[name] = GirClassDocs(
            class_docstring=class_docstring,
            fields=members_docs,
            methods={},
            signals={},
            properties={},
        )
    return docs


def parse_classes(path: str, root: etree._ElementTree, namespace: dict[str, str]) -> dict[str, GirClassDocs]:
    """
    Parses complex types: Classes, Interfaces, and Records.
    Extracts fields, methods, constructors, static methods, and signals.
    """
    docs: dict[str, GirClassDocs] = {}

    for container in root.xpath(path, namespaces=namespace):  # type: ignore
        name = container.attrib.get("name")
        if not name:
            continue

        class_docstring = _get_first_doc_text(container, namespace)  # type: ignore

        # 1. Parse Fields (core:field)
        fields_docs: dict[str, str] = {}
        for field in container.findall("core:field", namespaces=namespace):
            field_name = field.attrib.get("name")
            if field_name:
                fields_docs[field_name] = _get_first_doc_text(field, namespace)

        # 2. Parse Properties (core:property)
        properties_docs: dict[str, str] = {}
        for prop in container.findall("core:property", namespaces=namespace):
            prop_name = prop.attrib.get("name")
            if prop_name:
                properties_docs[prop_name] = _get_first_doc_text(prop, namespace)

        # 3. Parse Instance Methods (core:method)
        methods_docs: dict[str, GirFunctionDocs] = {}
        for method in container.findall("core:method", namespaces=namespace):
            method_name = method.attrib.get("name")
            if method_name:
                methods_docs[method_name] = _extract_function_docs(method, namespace)

        # 4. Parse Static Methods (core:function inside the class)
        static_methods_docs: dict[str, GirFunctionDocs] = {}
        for func in container.findall("core:function", namespaces=namespace):
            func_name = func.attrib.get("name")
            if func_name:
                static_methods_docs[func_name] = _extract_function_docs(func, namespace)

        # 5. Parse Constructors (core:constructor)
        constructors_docs: dict[str, GirFunctionDocs] = {}
        for ctor in container.findall("core:constructor", namespaces=namespace):
            ctor_name = ctor.attrib.get("name")
            if ctor_name:
                constructors_docs[ctor_name] = _extract_function_docs(ctor, namespace)

        # 6. Parse Signals (glib:signal)
        # Note: Signals use the 'glib' namespace, not 'core'
        signals_docs: dict[str, GirFunctionDocs] = {}
        for signal in container.findall("glib:signal", namespaces=namespace):
            sig_name = signal.attrib.get("name")
            if sig_name:
                signals_docs[sig_name] = _extract_function_docs(signal, namespace)

        docs[name] = GirClassDocs(
            class_docstring=class_docstring,
            fields=fields_docs,
            methods={**methods_docs, **static_methods_docs, **constructors_docs},
            signals=signals_docs,
            properties=properties_docs,
        )
    return docs


def parse_gir_docs(path: Path) -> ModuleDocs | None:
    """
    Main entry point to parse a GIR file and extract all documentation.
    """
    if not path.exists():
        logger.warning(f"Path {path} does not exist, not parsing.")
        return None

    root = etree.parse(path, parser=etree.XMLParser(recover=True))

    ns = {
        "core": "http://www.gtk.org/introspection/core/1.0",
        "c": "http://www.gtk.org/introspection/c/1.0",
        "glib": "http://www.gtk.org/introspection/glib/1.0",
    }

    # Parse different sections of the GIR file
    constant_docs = parse_constants("core:namespace/core:constant", root, ns)
    function_docs = parse_global_functions("core:namespace/core:function", root, ns)

    # Parse Enums and Bitfields (simple key-value members)
    bitfield_docs = _parse_simple_container("core:namespace/core:bitfield", root, ns, "core:member")
    enumeration_docs = _parse_simple_container("core:namespace/core:enumeration", root, ns, "core:member")

    # Parse Classes, Records, and Interfaces (complex structures)
    # Note: Records (structs) and Interfaces share a similar structure to Classes in GIR
    class_docs = parse_classes("core:namespace/core:class", root, ns)
    record_docs = parse_classes("core:namespace/core:record", root, ns)
    interface_docs = parse_classes("core:namespace/core:interface", root, ns)

    # Combine all complex types into the 'classes' dictionary
    all_classes = {**class_docs, **record_docs, **interface_docs}

    return ModuleDocs(
        constants=constant_docs,
        functions=function_docs,
        enums={**bitfield_docs, **enumeration_docs},
        classes=all_classes,
    )
