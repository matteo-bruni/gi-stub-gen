"""
Parser for GIR files to extract documentation.
"""

from __future__ import annotations

from pathlib import Path

# import xml.etree.ElementTree as ET
from lxml import etree
from pydantic import BaseModel
import logging

from gi_stub_gen.manager import TemplateManager

logger = logging.getLogger(__name__)


class GirFunctionDocs(BaseModel):
    """Function documentation extracted from GIR."""

    docstring: str
    params: dict[str, str]
    return_doc: str

    def full_docstring(self) -> str:
        """
        Construct the full docstring including parameters and return value.
        """
        return TemplateManager.render_master("function_docstring.jinja", docs=self)
        doc = self.docstring
        if self.params:
            doc += "\n\nParameters:\n"
            for param_name, param_doc in self.params.items():
                doc += f"    {param_name}: {param_doc}\n"
        if self.return_doc:
            doc += f"\n\nReturns:\n    {self.return_doc}\n"
        return doc


class GirClassDocs(BaseModel):
    """Class documentation extracted from GIR."""

    class_docstring: str
    fields: dict[str, str]


class ModuleDocs(BaseModel):
    constants: dict[str, str]
    functions: dict[str, GirFunctionDocs]
    enums: dict[str, GirClassDocs]
    classes: dict[str, GirClassDocs]

    def get_function_docstring(self, function_name: str) -> str | None:
        """
        Get the docstring for a function by name.
        """
        func_docs = self.functions.get(function_name, None)
        if func_docs:
            return func_docs.full_docstring()
        return None

    # def get_class_docstring(self, class_name: str) -> str | None:


def parse_constant(path: str, root: etree._ElementTree, namespace: dict[str, str]):
    constant_docs: dict[str, str] = {}
    for f in root.xpath(path, namespaces=namespace):  # type: ignore
        name = f.attrib.get("name", None)
        if name:
            doc = f.find("core:doc", namespace)
            constant_docstring = ""
            if doc is not None:
                constant_docstring = str(doc.text)
            constant_docs[str(name)] = constant_docstring
    return constant_docs


def parse_function(path: str, root: etree._ElementTree, namespace: dict[str, str]):
    function_docs: dict[str, GirFunctionDocs] = {}

    # find the functions
    for f in root.xpath(path, namespaces=namespace):  # type: ignore
        name = f.attrib.get("name", None)
        if name:
            doc = f.find("core:doc", namespace)
            function_docstring = ""
            if doc is not None:
                function_docstring = str(doc.text)

            # get params docs
            class_params_docs: dict[str, str] = {}
            for param in f.xpath(
                "core:parameters/core:parameter", namespaces=namespace
            ):
                param_name = param.attrib.get("name", None)
                if param_name:
                    param_doc = param.xpath("core:doc", namespaces=namespace)
                    assert len(param_doc) <= 1, f"more than one param doc {name}"
                    if len(param_doc) == 1:
                        class_params_docs[str(param_name)] = str(param_doc[0].text)

            # get return docs
            return_doc = f.xpath("core:return-value/core:doc", namespaces=namespace)
            return_docstring = ""
            assert len(return_doc) <= 1, f"more than one return doc {name}"
            if len(return_doc) == 1:
                return_docstring = str(return_doc[0].text)

            function_docs[str(name)] = GirFunctionDocs(
                docstring=function_docstring,
                params=class_params_docs,
                return_doc=return_docstring,
            )

            # get params docs

    return function_docs


def parse_class(path: str, root: etree._ElementTree, namespace: dict[str, str]):
    docs: dict[str, GirClassDocs] = {}
    for f in root.xpath(path, namespaces=namespace):  # type: ignore
        name = f.attrib.get("name", None)
        if name:
            doc = f.xpath("core:doc", namespaces=namespace)
            class_docstring: str = ""
            assert len(doc) <= 1, f"more than one class doc {name}"
            if len(doc) == 1:
                class_docstring = str(doc[0].text)

            # get member docs
            class_fields_docs: dict[str, str] = {}
            for field in f.xpath("core:member", namespaces=namespace):
                field_name = field.attrib.get("name", None)
                if field_name:
                    field_doc = field.xpath("core:doc", namespaces=namespace)
                    assert len(field_doc) <= 1, f"more than one field_doc {name}"
                    if len(field_doc) == 1:
                        class_fields_docs[str(field_name)] = str(field_doc[0].text)

            docs[name] = GirClassDocs(
                class_docstring=class_docstring,
                fields=class_fields_docs,
            )
    return docs


def gir_docs(
    path: Path,
):
    if not path.exists():
        logger.warning(f"Path {path} does not exist, returning empty docs.")
        return ModuleDocs(
            constants={},
            functions={},
            enums={},
            classes={},
        )

    root = etree.parse(path, parser=etree.XMLParser(recover=True))

    ns = {
        "core": "http://www.gtk.org/introspection/core/1.0",
        "c": "http://www.gtk.org/introspection/c/1.0",
        "glib": "http://www.gtk.org/introspection/glib/1.0",
    }

    constant_docs = parse_constant("core:namespace/core:constant", root, ns)
    function_docs = parse_function("core:namespace/core:function", root, ns)
    # these are enum flags
    # flags have docs for class and for each bitfield
    bifield_docs = parse_class("core:namespace/core:bitfield", root, ns)
    enumeration_docs = parse_class("core:namespace/core:enumeration", root, ns)
    class_docs = parse_class("core:namespace/core:class", root, ns)

    return ModuleDocs(
        constants=constant_docs,
        functions=function_docs,
        enums={**bifield_docs, **enumeration_docs},
        classes=class_docs,
    )


if __name__ == "__main__":
    path = Path("/usr/share/gir-1.0/GObject-2.0.gir")
    docs = gir_docs(path)
    print(docs)
    print("done")
    # {http://www.gtk.org/introspection/core/1.0}alias
    # {http://www.gtk.org/introspection/core/1.0}bitfield
    # {http://www.gtk.org/introspection/core/1.0}callback
    # {http://www.gtk.org/introspection/core/1.0}class
    # {http://www.gtk.org/introspection/core/1.0}constant
    # {http://www.gtk.org/introspection/core/1.0}docsection
    # {http://www.gtk.org/introspection/core/1.0}enumeration
    # {http://www.gtk.org/introspection/core/1.0}function
    # {http://www.gtk.org/introspection/core/1.0}function-inline
    # {http://www.gtk.org/introspection/core/1.0}function-macro
    # {http://www.gtk.org/introspection/core/1.0}interface
    # {http://www.gtk.org/introspection/core/1.0}record
    # {http://www.gtk.org/introspection/core/1.0}alias
    # {http://www.gtk.org/introspection/core/1.0}bitfield
    # {http://www.gtk.org/introspection/core/1.0}callback
    # {http://www.gtk.org/introspection/core/1.0}class
    # {http://www.gtk.org/introspection/core/1.0}constant
    # {http://www.gtk.org/introspection/core/1.0}function
    # {http://www.gtk.org/introspection/core/1.0}function-macro
    # {http://www.gtk.org/introspection/core/1.0}interface
    # {http://www.gtk.org/introspection/core/1.0}record
    # {http://www.gtk.org/introspection/core/1.0}union
    # {http://www.gtk.org/introspection/glib/1.0}boxed


# from lxml import etree

# ns = {
#     "core": "http://www.gtk.org/introspection/core/1.0",
#     "c": "http://www.gtk.org/introspection/c/1.0",
#     "glib": "http://www.gtk.org/introspection/glib/1.0",
# }
# path = Path("/usr/share/gir-1.0/GObject-2.0.gir")
# root = etree.parse(path, parser=etree.XMLParser(recover=True))
# g = root.xpath("core:namespace/core:class/core:doc", namespaces=ns)
