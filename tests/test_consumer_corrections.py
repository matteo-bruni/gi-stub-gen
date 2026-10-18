"""Small runtime-backed corrections; keep guards that notice upstream fixes."""

import ast
import inspect
import os

import gi
import pytest

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Atk", "1.0")
gi.require_version("GioUnix", "2.0")
from gi.repository import Atk, Gdk, GioUnix, GObject, Gtk

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.overrides import CLASS_OVERRIDES
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema
from gi_stub_gen.schema.function import FunctionSchema


def effective_method(namespace, cls, name):
    schema, _ = parse_class(f"gi.repository.{namespace}", cls)
    assert schema is not None
    return next((m for m in schema.python_methods if m.name == name), None) or next(
        m for m in schema.methods if m.name == name
    )


@pytest.mark.parametrize("cls", [GioUnix.InputStream, GioUnix.OutputStream])
def test_get_fd_runtime_and_annotation(cls):
    read_fd, write_fd = os.pipe()
    try:
        fd = read_fd if cls is GioUnix.InputStream else write_fd
        stream = cls.new(fd, False)
        assert stream.get_fd() == GioUnix.FileDescriptorBased.get_fd(stream) == fd
        method = effective_method("GioUnix", cls, "get_fd")
        assert isinstance(method, BuiltinFunctionSchema)
        assert method.render_return_annotation("GioUnix") == "int"
        assert method.is_method and not method.is_staticmethod
        assert [p.name for p in method.params] == ["self"]
    finally:
        os.close(read_fd)
        os.close(write_fd)


@pytest.mark.parametrize("name", ["name", "description"])
def test_atk_unset_text_is_nullable(name):
    obj = Atk.NoOpObject.new(GObject.Object())
    assert getattr(obj, f"get_{name}")() is None
    getattr(obj, f"set_{name}")("probe")
    assert getattr(obj, f"get_{name}")() == "probe"
    method = effective_method("Atk", Atk.Object, f"get_{name}")
    assert isinstance(method, FunctionSchema)
    assert method.render_return_annotation("Atk") == "str | None"


@pytest.mark.parametrize("namespace,cls,name", [
    ("GioUnix", GioUnix.InputStream, "get_fd"),
    ("GioUnix", GioUnix.OutputStream, "get_fd"),
    ("Atk", Atk.Object, "get_name"),
    ("Atk", Atk.Object, "get_description"),
    ("Gtk", Gtk.TreeViewColumn, "set_cell_data_func"),
])
def test_revisit_transforms_when_upstream_recovers_types(monkeypatch, namespace, cls, name):
    config = CLASS_OVERRIDES[f"gi.repository.{namespace}"][cls.__name__]
    monkeypatch.setitem(config, "method_transforms", {})
    method = effective_method(namespace, cls, name)
    message = f"Reevaluate/remove {namespace}.{cls.__name__}.{name} transform: uncorrected parsing changed"
    if isinstance(method, FunctionSchema):
        assert method.render_return_annotation(namespace) == "str", message
    else:
        assert method.render_return_annotation(namespace) == "typing.Any", message
        if name == "set_cell_data_func":
            assert [p.name for p in method.params] == ["self", "cell_renderer", "func", "func_data"], message
            assert all(p.type_hint_name == "Any" for p in method.params[1:]), message
            assert not method.overloads, message


def test_callback_overloads_preserve_wrapper_shape_docs_and_independence():
    method = effective_method("Gtk", Gtk.TreeViewColumn, "set_cell_data_func")
    assert isinstance(method, BuiltinFunctionSchema)
    assert list(inspect.signature(Gtk.TreeViewColumn.set_cell_data_func).parameters) == [
        "self", "cell_renderer", "func", "func_data",
    ]
    assert len(method.overloads) == 3
    assert [v.params[-1].default_value for v in method.overloads] == ["None", None, "None"]
    assert all(not v.overloads for v in method.overloads)
    TemplateManager.set_module_name("Gtk")
    rendered = method.render_stub()
    assert len(ast.parse(rendered).body) == 3
    assert rendered.count("@typing.overload") == 3
    assert rendered.count("[is-override:") == 1
    assert "typing" in method.required_imports
    assert "*func_data" not in rendered
    method.overloads[0].params[1].type_hint_name = "Changed"
    assert method.overloads[1].params[1].type_hint_name == "RendererT"
    fresh = effective_method("Gtk", Gtk.TreeViewColumn, "set_cell_data_func")
    assert isinstance(fresh, BuiltinFunctionSchema)
    assert fresh.overloads[0].params[1].type_hint_name == "RendererT"


def test_callback_runtime_payload_and_reset():
    if Gdk.Display.get_default() is None:
        pytest.skip("TreeViewColumn requires a display; headless construction crashes GTK")
    column = Gtk.TreeViewColumn()
    renderer = Gtk.CellRendererText()
    column.pack_start(renderer, False)
    model = Gtk.ListStore(int)
    row = model.append([1])
    received: list[object] = []

    def draw(_column, _renderer, _model, _row, data):
        received.append(data)

    assert column.set_cell_data_func(renderer, draw) is None
    column.cell_set_cell_data(model, row, False, False)
    assert received == [None]
    payload = {"value": 42}
    assert column.set_cell_data_func(renderer, draw, payload) is None
    column.cell_set_cell_data(model, row, False, False)
    assert received[-1] is payload
    assert column.set_cell_data_func(renderer, None) is None
    column.cell_set_cell_data(model, row, False, False)
    assert len(received) == 2
