from pathlib import Path
import xml.etree.ElementTree as ET


def gir_docs(
    path: Path,
):
    if not path.exists():
        return {}

    tree = ET.parse(path)
    root = tree.getroot()

    ns = {
        "core": "http://www.gtk.org/introspection/core/1.0",
        "c": "http://www.gtk.org/introspection/c/1.0",
        "glib": "http://www.gtk.org/introspection/glib/1.0",
    }

    docs = {
        "functions": {},
        "enums": {},
    }
    # find the functions
    for f in root.findall("core:namespace/core:function", ns):
        name = f.attrib.get("name", None)
        if name:
            doc = f.find("core:doc", ns)
            if doc is not None:
                docs["functions"][name] = f.find("core:doc", ns).text

    # flags have docs for class and for each bitfield
    for f in root.findall("core:namespace/core:bitfield", ns):
        name = f.attrib.get("name", None)
        if name:
            doc = f.find("core:doc", ns)
            if doc is not None:
                docs["enums"][name] = {"class": f.find("core:doc", ns).text}

            # get member docs
            for field in f.findall("core:member", ns):
                field_name = field.attrib.get("name", None)
                if field_name:
                    field_doc = field.find("core:doc", ns)
                    if field_doc is not None:
                        if name not in docs["enums"]:
                            docs["enums"][name] = {}
                        docs["enums"][name][field_name] = field.find(
                            "core:doc", ns
                        ).text

    return docs
