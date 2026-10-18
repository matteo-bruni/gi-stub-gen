"""Nominal interfaces, their generic arguments and the runtime's method precedence."""
import ast
import subprocess
import sys
import textwrap
from typing import Generic, TypeVar, cast

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, GObject, Gst, Gtk

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.overrides import CLASS_OVERRIDES
from gi_stub_gen.parser.class_ import parse_class, _render_interface_base
from gi_stub_gen.schema.builtin_function import TypeVarSchema
from gi_stub_gen.utils.utils import get_declared_class_bases


@pytest.mark.parametrize("namespace,name,bases,props", [
    ("Gio", "ListStore", "GObject.Object, ListModel[ObjectItemType]", "GObject.Object.Props, ListModel.Props"),
    ("Gio", "SimpleActionGroup", "GObject.Object, ActionGroup, ActionMap", "GObject.Object.Props, ActionGroup.Props, ActionMap.Props"),
    ("Gst", "Bin", "Element, ChildProxy", "Element.Props, ChildProxy.Props"),
    ("Gtk", "Widget", "GObject.InitiallyUnowned, Accessible, Buildable, ConstraintTarget",
     "GObject.InitiallyUnowned.Props, Accessible.Props, Buildable.Props, ConstraintTarget.Props"),
    ("Gtk", "StringList", "GObject.Object, Gio.ListModel[GObject.Object], Buildable",
     "GObject.Object.Props, Gio.ListModel.Props, Buildable.Props"),
])
def test_direct_interfaces(namespace, name, bases, props):
    module = {"Gio": Gio, "Gst": Gst, "Gtk": Gtk}[namespace]
    schema, _ = parse_class(f"gi.repository.{namespace}", getattr(module, name))
    assert schema is not None
    assert schema.render_bases() == bases
    assert schema.render_props_base() == props
    TemplateManager.set_module_name(namespace)
    rendered = schema.render_stub()
    assert f"class Props({props}):" in rendered
    ast.parse(rendered)
    if name == "StringList":
        assert not schema.type_vars
        assert {"Gio", "GObject"} <= schema.required_imports


def test_overrides_expand_only_their_own_backing_class():
    class Left: ...
    class Root: ...
    class Right: ...

    backing = type("Wrapped", (Root,), {"__module__": "gi.repository.Probe"})
    wrapper = type("Wrapped", (Left, backing, Right), {"__module__": "gi.overrides.Probe"})
    assert get_declared_class_bases(wrapper) == [Left, Root, Right]
    other_namespace = type("Wrapped", (backing,), {"__module__": "gi.repository.Other"})
    assert get_declared_class_bases(other_namespace) == [backing]


def test_inherited_interfaces_and_prerequisites_are_not_direct_bases():
    application, _ = parse_class("gi.repository.Gtk", Gtk.Application)
    selection, _ = parse_class("gi.repository.Gtk", Gtk.SelectionModel)
    assert application is not None and selection is not None
    assert application.render_bases() == "Gio.Application"
    assert selection.render_bases() == "builtins.object"
    assert not issubclass(Gtk.SelectionModel, Gio.ListModel)
    assert not hasattr(Gtk.SelectionModel, "get_item")


def test_explicit_base_override_replaces_interfaces(monkeypatch):
    monkeypatch.setitem(CLASS_OVERRIDES["gi.repository.Gio"], "SimpleActionGroup", {"super": ["GObject.Object"]})
    schema, _ = parse_class("gi.repository.Gio", Gio.SimpleActionGroup)
    assert schema is not None
    assert schema.super == ["GObject.Object"]
    assert schema.props_bases == ["GObject.Object.Props"]


def test_interface_typevars_use_identity_and_explicit_arguments():
    ObjectItemType = TypeVar("ObjectItemType", bound=GObject.Object)

    class Other(Generic[ObjectItemType]): ...

    imports: set[str] = set()
    annotation, props = _render_interface_base(
        Gio.ListModel, Other, "Gio", [TypeVarSchema(name="ObjectItemType")], imports,
    )
    assert annotation == "ListModel[GObject.Object]"
    assert props == "ListModel.Props"
    assert "GObject" in imports
    annotation, _ = _render_interface_base(Gio.ListModel[GObject.Object], Other, "Gtk", [], imports)
    assert annotation == "Gio.ListModel[GObject.Object]"
    assert {"Gio", "GObject"} <= imports


def test_socket_keeps_the_actual_bound_signature():
    schema, _ = parse_class("gi.repository.Gio", Gio.Socket)
    assert schema is not None
    method = next(m for m in schema.methods if m.name == "condition_wait")
    assert [arg.name for arg in method.args] == ["condition", "cancellable"]
    sock = Gio.Socket.new(Gio.SocketFamily.IPV4, Gio.SocketType.DATAGRAM, Gio.SocketProtocol.UDP)
    cancellable = Gio.Cancellable.new()
    cancellable.cancel()
    try:
        with pytest.raises(GLib.Error):
            sock.condition_wait(GLib.IOCondition.IN, cancellable)
        with pytest.raises(GLib.Error):
            Gio.DatagramBased.condition_wait(cast(Gio.DatagramBased, sock), GLib.IOCondition.IN, 0, cancellable)
        # Dynamic invocation deliberately exercises a signature rejected by the checker.
        with pytest.raises(TypeError, match="arguments"):
            getattr(sock, "condition_wait")(GLib.IOCondition.IN, 0, cancellable)
    finally:
        sock.close()


def test_native_interface_is_not_a_python_structural_contract():
    # Registration/vfunc dispatch is tested in a fresh process, independently of
    # introspection performed by earlier tests and of static consumer diagnostics.
    result = subprocess.run([sys.executable, "-c", textwrap.dedent("""
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gio, GObject, Gtk
        class RealModel(GObject.Object, Gio.ListModel):
            def do_get_item_type(self): return GObject.TYPE_OBJECT
            def do_get_n_items(self): return 0
            def do_get_item(self, position): return None
        class Duck:
            def get_item_type(self): return GObject.TYPE_OBJECT
            def get_n_items(self): return 0
            def get_item(self, position): return None
        model = RealModel()
        selection = Gtk.NoSelection.new(model)
        assert selection.get_model() is model
        assert selection.get_n_items() == 0
        try:
            Gtk.NoSelection.new(Duck())
        except TypeError as exc:
            assert "Expected Gio.ListModel" in str(exc)
        else:
            raise AssertionError("An unregistered structural imitation was accepted")
    """)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_bin_exposes_child_proxy_without_copying_its_methods():
    schema, _ = parse_class("Gst", Gst.Bin)
    assert schema is not None
    assert "get_children_count" not in {m.name for m in schema.methods + schema.python_methods}
    bin_ = Gst.Bin.new("interface-test")
    source = Gst.ElementFactory.make("fakesrc", "source")
    assert source is not None
    bin_.add(source)
    assert isinstance(bin_, Gst.ChildProxy)
    assert bin_.get_children_count() == 1
    assert bin_.get_child_by_name("source") is source
