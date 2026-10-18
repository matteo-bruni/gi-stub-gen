from typing import Callable

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GObject, Gst, Gtk  # noqa: E402

from gi_stub_gen.manager.gi_repo import GIRepo
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.parser.function import parse_callable, parse_function
from gi_stub_gen.schema.module import ModuleSchema
from gi_stub_gen.utils.inspect_utils import _extract_annotation_type_info


def test_inherited_signal_uses_destination_namespace_without_changing_origin():
    for namespace, cls, expected in (
        ("Gio", Gio.Application, "list[File]"),
        ("Gtk", Gtk.Application, "list[Gio.File]"),
    ):
        GIRepo().require(namespace, "2.0" if namespace == "Gio" else "4.0")
        parsed, _ = parse_class(namespace, cls)
        assert parsed is not None
        signal = next(signal for signal in parsed.signals if signal.name == "open")
        assert signal.namespace == signal.handler.namespace == "Gio"
        assert signal.render_handler_parameters(namespace) == f"[typing_extensions.Self, {expected}, str, *UserData]"
        assert signal.handler.args[0].namespace == "Gio"
        assert ("Gio" in signal.required_gi_imports) == (namespace == "Gtk")


def test_signal_import_is_collected_without_other_gio_declarations():
    info = getattr(Gio.Application, "__info__")
    signal = next(signal for signal in info.get_signals() if signal.get_name() == "open")
    handler = parse_callable(signal, render_namespace="Gtk")
    module = ModuleSchema(
        name="gi.repository.Gtk",
        classes=[],
        constant=[],
        enum=[],
        function=[handler],
        builtin_function=[],
        callbacks=[],
        aliases=[],
    )
    gi_imports, _ = module.collect_imports()
    assert "Gio" in gi_imports


@pytest.mark.parametrize(
    "annotation, local, foreign, outer",
    [
        (list[Gio.File], "list[File]", "list[Gio.File]", None),
        (dict[str, list[Gio.File | None]], "dict[str, list[File | None]]", "dict[str, list[Gio.File | None]]", None),
        (
            Callable[[Gio.File], list[Gio.File]],
            "Callable[[File], list[File]]",
            "Callable[[Gio.File], list[Gio.File]]",
            "collections.abc",
        ),
    ],
)
def test_nested_annotations_keep_namespaces_and_imports(annotation, local, foreign, outer):
    for namespace, expected, dependencies in (("Gio", local, set()), ("Gtk", foreign, {"Gio"})):
        imports: set[str] = set()
        assert _extract_annotation_type_info(annotation, namespace, imports) == (expected, outer)
        assert imports == dependencies


def test_nested_return_imports_survive_callable_construction(monkeypatch):
    monkeypatch.setattr(
        "gi_stub_gen.parser.function.gi_type_to_py_type",
        lambda _: Callable[[Gio.File], list[Gio.File]],
    )
    parsed = parse_function(Gst.version_string, docstring=None, render_namespace="Gst")
    assert parsed is not None
    assert parsed.render_return_annotation("Gst") == "collections.abc.Callable[[Gio.File], list[Gio.File]]"
    assert {"Gio", "collections.abc"} <= parsed.required_imports


def test_nested_types_with_same_name_from_different_namespaces():
    imports: set[str] = set()
    annotation, namespace = _extract_annotation_type_info(
        tuple[Gst.Object, GObject.Object], current_namespace="Gst", required_imports=imports
    )
    assert annotation == "tuple[Object, GObject.Object]"
    assert namespace is None
    assert imports == {"GObject"}
