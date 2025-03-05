from pathlib import Path
from typing_extensions import TypedDict
import xml.etree.ElementTree as ET

from pydantic import BaseModel


class FunctionDocs(BaseModel):
    docstring: str
    params: dict[str, str]
    return_doc: str


class ClassDocs(BaseModel):
    class_docstring: str
    fields: dict[str, str]


class ModuleDocs(BaseModel):
    functions: dict[str, FunctionDocs]
    enums: dict[str, ClassDocs]
    classes: dict[str, ClassDocs]


def parse_function(path: str, root: ET.Element, namespace: dict[str, str]):
    function_docs: dict[str, FunctionDocs] = {}

    # find the functions
    for f in root.findall(path, namespace):
        name = f.attrib.get("name", None)
        if name:
            doc = f.find("core:doc", namespace)
            function_docstring = ""
            if doc is not None:
                function_docstring = str(doc.text)

            # get params docs
            class_params_docs: dict[str, str] = {}
            for param in f.findall("core:parameters/core:parameter", namespace):
                param_name = param.attrib.get("name", None)
                if param_name:
                    param_doc = param.find("core:doc", namespace)
                    if param_doc is not None:
                        class_params_docs[str(param_name)] = str(param_doc.text)

            # get return docs
            return_doc = f.find("core:return-value/core:doc", namespace)
            return_docstring = ""
            if return_doc is not None:
                return_docstring = str(return_doc.text)

            function_docs[str(name)] = FunctionDocs(
                docstring=function_docstring,
                params=class_params_docs,
                return_doc=return_docstring,
            )

            # get params docs

    return function_docs


def parse_class(path: str, root: ET.Element, namespace: dict[str, str]):
    docs: dict[str, ClassDocs] = {}
    for f in root.findall(path, namespace):
        name = f.attrib.get("name", None)
        if name:
            doc = f.find("core:doc", namespace)
            class_docstring: str = ""
            if doc is not None:
                class_docstring = str(doc.text)

            # get member docs
            class_fields_docs: dict[str, str] = {}
            for field in f.findall("core:member", namespace):
                field_name = field.attrib.get("name", None)
                if field_name:
                    field_doc = field.find("core:doc", namespace)
                    if field_doc is not None:
                        class_fields_docs[str(field_name)] = str(field_doc.text)

            docs[name] = ClassDocs(
                class_docstring=class_docstring,
                fields=class_fields_docs,
            )
    return docs


def gir_docs(
    path: Path,
):
    if not path.exists():
        return ModuleDocs(
            functions={},
            enums={},
            classes={},
        )

    tree = ET.parse(path)
    root = tree.getroot()

    ns = {
        "core": "http://www.gtk.org/introspection/core/1.0",
        "c": "http://www.gtk.org/introspection/c/1.0",
        "glib": "http://www.gtk.org/introspection/glib/1.0",
    }

    function_docs = parse_function("core:namespace/core:function", root, ns)
    # these are enum flags
    # flags have docs for class and for each bitfield
    bifield_docs = parse_class("core:namespace/core:bitfield", root, ns)
    enumeration_docs = parse_class("core:namespace/core:enumeration", root, ns)
    class_docs = parse_class("core:namespace/core:class", root, ns)

    return ModuleDocs(
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
