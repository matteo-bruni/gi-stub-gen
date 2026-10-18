import ast

import gi
from gi.repository import Gio
import pytest

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.overrides import CLASS_OVERRIDES, validate_class_override
from gi_stub_gen.overrides.class_.Gio.DBusConnection import build_dbus_connection_init
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.schema.builtin_function import ArgKind
from gi_stub_gen.schema.class_ import ClassSchema


def _assert_dbus_init_still_needs_factory(parsed: ClassSchema) -> None:
    message = (
        "Gio.DBusConnection.__init__ parsing changed; review and possibly remove "
        "init_factory and its necessity test, retaining the constructor/runtime tests"
    )
    assert not any(method.name == "__init__" for method in parsed.methods), message
    initializers = [method for method in parsed.python_methods if method.name == "__init__"]
    assert len(initializers) == 1, message
    assert [(param.name, param.kind) for param in initializers[0].params] == [
        ("self", ArgKind.POSITIONAL_OR_KEYWORD),
        ("args", ArgKind.VAR_POSITIONAL),
        ("kwargs", ArgKind.VAR_KEYWORD),
    ], message


def test_dbus_init_still_needs_property_factory(monkeypatch):
    monkeypatch.delitem(CLASS_OVERRIDES["gi.repository.Gio"]["DBusConnection"], "init_factory")
    parsed, _ = parse_class("gi.repository.Gio", Gio.DBusConnection)
    assert parsed is not None
    _assert_dbus_init_still_needs_factory(parsed)


def test_dbus_necessity_check_detects_an_upstream_signature_fix(monkeypatch):
    def precise_init(self, address: str) -> None:
        pass

    monkeypatch.delitem(CLASS_OVERRIDES["gi.repository.Gio"]["DBusConnection"], "init_factory")
    monkeypatch.setattr(Gio.DBusConnection, "__init__", precise_init)
    parsed, _ = parse_class("gi.repository.Gio", Gio.DBusConnection)
    assert parsed is not None
    with pytest.raises(AssertionError, match="review and possibly remove init_factory"):
        _assert_dbus_init_still_needs_factory(parsed)


def test_dbus_property_constructor_and_other_members(monkeypatch):
    parsed, _ = parse_class("gi.repository.Gio", Gio.DBusConnection)
    assert parsed is not None
    method = next(method for method in parsed.methods if method.name == "__init__")
    assert not any(method.name == "__init__" for method in parsed.python_methods)
    assert {arg.name: (arg.render_type_annotation("Gio"), arg.default_value) for arg in method.args} == {
        "address": ("str | None", "None"),
        "authentication_observer": ("DBusAuthObserver | None", "None"),
        "exit_on_close": ("bool | None", "None"),
        "flags": ("DBusConnectionFlags | None", "DBusConnectionFlags.NONE"),
        "guid": ("str | None", "None"),
        "stream": ("IOStream | None", "None"),
    }
    assert method.docstring and "should not be instantiated directly" in method.docstring
    assert "new_sync" in method.docstring and "new_for_address_sync" in method.docstring
    TemplateManager.set_module_name("Gio")
    cls = ast.parse(parsed.render_stub()).body[0]
    assert isinstance(cls, ast.ClassDef)
    assert sum(isinstance(node, ast.FunctionDef) and node.name == "__init__" for node in cls.body) == 1

    # The override only replaces __init__; other members retain normal parsing.
    monkeypatch.delitem(CLASS_OVERRIDES["gi.repository.Gio"]["DBusConnection"], "init_factory")
    original, _ = parse_class("gi.repository.Gio", Gio.DBusConnection)
    assert original is not None
    for schema in (parsed, original):
        schema.methods = [method for method in schema.methods if method.name != "__init__"]
        schema.python_methods = [method for method in schema.python_methods if method.name != "__init__"]
    assert parsed.model_dump() == original.model_dump()


def test_dbus_factory_results_are_independent_and_reject_non_objects():
    first = build_dbus_connection_init("Gio", Gio.DBusConnection)
    before = first.model_dump()
    first.args[0].name = "changed"
    assert build_dbus_connection_init("Gio", Gio.DBusConnection).model_dump() == before
    with pytest.raises(ValueError, match="Cannot build .* from GObject properties"):
        build_dbus_connection_init("Test", int)


def test_init_factory_conflicts_are_rejected():
    with pytest.raises(ValueError, match="init_factory conflicts"):
        validate_class_override(
            "Gio",
            "DBusConnection",
            {"init_factory": build_dbus_connection_init, "methods": {"__init__": None}},
        )
    with pytest.raises(ValueError, match="init_factory conflicts"):
        validate_class_override(
            "Gio",
            "DBusConnection",
            {"init_factory": build_dbus_connection_init, "method_transforms": {"__init__": lambda method: method}},
        )


def test_init_factory_runs_once_and_validates_its_result(monkeypatch):
    calls = []

    def factory(namespace: str, cls: type):
        calls.append((namespace, cls))
        return build_dbus_connection_init(namespace, cls)

    config = CLASS_OVERRIDES["gi.repository.Gio"]["DBusConnection"]
    monkeypatch.setitem(config, "init_factory", factory)
    assert parse_class("gi.repository.Gio", Gio.DBusConnection)[0] is not None
    assert calls == [("Gio", Gio.DBusConnection)]

    wrong_name = build_dbus_connection_init("Gio", Gio.DBusConnection)
    wrong_name.name = "not_init"
    monkeypatch.setitem(config, "init_factory", lambda namespace, cls: wrong_name)
    with pytest.raises(TypeError, match="init_factory must return an __init__ FunctionSchema"):
        parse_class("gi.repository.Gio", Gio.DBusConnection)


def test_dbus_runtime_constructor_properties_and_warning():
    # Direct construction sets properties but does not initialize a DBus connection.
    with pytest.warns(gi.PyGIWarning, match="shouldn't be instantiated directly"):
        connection = Gio.DBusConnection(
            address="unix:path=/tmp/gi-stub-gen-unused-dbus",
            exit_on_close=False,
        )
    assert connection.get_property("exit-on-close") is False
