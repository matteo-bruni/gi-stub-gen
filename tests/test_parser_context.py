import logging
from pathlib import Path
import subprocess
import sys
from types import ModuleType

from gi.repository import Gst, Gio

from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.parser.module import parse_module


def test_module_parser_without_logging_handlers(monkeypatch):
    monkeypatch.setattr(logging.root, "handlers", [])
    module = ModuleType("gi.repository.Gst")
    setattr(module, "version", Gst.version)
    updates = []
    parsed, unknown = parse_module(module, on_progress=lambda *update: updates.append(update))
    assert not unknown
    assert [function.name for function in parsed.function] == ["version"]
    assert len(updates) == len(dir(module))
    assert updates[-1][1:] == (len(dir(module)), len(dir(module)))
    assert parse_module(module)[0] == parsed


def test_documentation_is_explicit_and_survives_namespace_reset():
    def value_hint(docs=None):
        parsed = parse_function(Gst.Structure.get_value, None, docs=docs)
        assert parsed is not None
        return parsed.return_hint

    gst_docs = GIRDocs()
    assert gst_docs.load(Path("/usr/share/gir-1.0/Gst-1.0.gir"))
    assert value_hint(gst_docs) == "Any"
    assert value_hint() == "Value"

    GIRDocs.reset()
    gio_docs = GIRDocs()
    assert gio_docs.load(Path("/usr/share/gir-1.0/Gio-2.0.gir"))
    propagate = parse_function(Gio.Task.propagate_value, None, docs=gio_docs)
    assert propagate is not None
    value = next(arg for arg in propagate.args if arg.name == "value")
    assert value.is_marshaled_gvalue_payload
    assert value_hint(gst_docs) == "Any"
    assert value_hint(None) == "Value"


def test_parser_imports_in_fresh_processes():
    for first in ("adapter", "parser.function", "parser.class_", "parser.module", "overrides"):
        subprocess.run(
            [sys.executable, "-c", f"import gi_stub_gen.{first}; import gi_stub_gen.parser.module"],
            check=True,
            capture_output=True,
            text=True,
        )
