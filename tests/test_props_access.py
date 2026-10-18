import ast

import gi
import pytest

gi.require_version("GstController", "1.0")
from gi.repository import Gio, GObject, Gst, GstController

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.class_ import parse_class


def test_dbus_props_access_and_constructor_are_separate():
    schema, _ = parse_class("gi.repository.Gio", Gio.DBusConnection)
    assert schema is not None
    props = {prop.name: prop for prop in schema.props}
    assert props["closed"].readable and not props["closed"].can_write
    assert props["flags"].construct_only and not props["flags"].can_write
    assert props["exit_on_close"].can_write
    initializer = next(method for method in schema.methods if method.name == "__init__")
    assert "flags" in {arg.name for arg in initializer.args}
    assert "closed" not in {arg.name for arg in initializer.args}
    TemplateManager.set_module_name("Gio")
    text = schema.render_props()
    ast.parse(text, feature_version=(3, 12))
    assert "@typing.type_check_only" in text
    assert "def closed(self) -> bool:" in text
    assert "def flags(self) -> DBusConnectionFlags:" in text
    assert "exit_on_close: bool" in text
    assert "@flags.setter" not in text


def test_props_separate_accessor_types_and_inaccessible_properties():
    schema, _ = parse_class("gi.repository.Gio", Gio.DBusConnection)
    assert schema is not None
    prop = next(prop for prop in schema.props if prop.name == "exit_on_close")
    schema.props = [
        prop.model_copy(update={"name": "different", "write_may_be_null": True}),
        prop.model_copy(update={"name": "write_only", "readable": False}),
        prop.model_copy(update={"name": "inaccessible", "readable": False, "writable": False}),
    ]
    TemplateManager.set_module_name("Gio")
    text = schema.render_props()
    ast.parse(text, feature_version=(3, 12))
    assert "def different(self) -> bool:" in text
    assert "def different(self, value: bool | None) -> None:" in text
    assert "def write_only(self) -> typing.Never:" in text
    assert "def write_only(self, value: bool) -> None:" in text
    assert "inaccessible" not in text


def test_getter_metadata_supplies_nullability():
    schema, _ = parse_class("gi.repository.Gio", Gio.Application)
    assert schema is not None
    prop = next(prop for prop in schema.props if prop.name == "application_id")
    assert prop.render_type_annotation("Gio") == "str | None"
    assert prop.render_write_annotation("Gio") == "str | None"

    readonly = next(prop for prop in schema.props if prop.name == "is_registered")
    assert readonly.line_comment is not None
    assert readonly.declaration_comment is None
    TemplateManager.set_module_name("Gio")
    assert "changed because contained invalid characters" not in next(
        line for line in schema.render_props().splitlines() if "def is_registered(" in line
    )


def test_control_binding_name_restricts_mutable_parent_property():
    parent = Gst.Object.find_property("name")
    child = Gst.ControlBinding.find_property("name")
    assert parent is not None and child is not None
    assert parent.flags & GObject.ParamFlags.WRITABLE
    assert not parent.flags & GObject.ParamFlags.CONSTRUCT_ONLY
    assert child.flags & GObject.ParamFlags.CONSTRUCT_ONLY

    element = Gst.ElementFactory.make("videotestsrc")
    assert element is not None
    control = GstController.InterpolationControlSource.new()
    binding = GstController.DirectControlBinding.new(element, "pattern", control)
    assert binding is not None
    element.props.name = "renamed"
    assert element.props.name == "renamed"
    assert binding.props.name == "pattern"
    with pytest.raises(TypeError, match="can only be set in constructor"):
        setattr(binding.props, "name", "other")

    schema, _ = parse_class("gi.repository.Gst", Gst.ControlBinding)
    assert schema is not None
    prop = next(prop for prop in schema.props if prop.name == "name")
    assert prop.readable and not prop.can_write
    TemplateManager.set_module_name("Gst")
    text = schema.render_props()
    assert "class Props(Object.Props)" in text
    assert "def name(self) -> str:" in text
    assert "@name.setter" not in text
    name_line = next(line for line in text.splitlines() if "def name(" in line)
    assert "pyright: ignore[reportIncompatibleVariableOverride]" in name_line
    assert "ty: ignore[invalid-property-type-override]" in name_line
    assert "pyrefly: ignore[bad-override]" in name_line
    assert "Native construct-only property" in name_line
    assert text.count("pyright: ignore") == text.count("ty: ignore") == 1

    parent_schema, _ = parse_class("gi.repository.Gst", Gst.Object)
    assert parent_schema is not None
    assert next(prop for prop in parent_schema.props if prop.name == "name").can_write
    assert "ignore[" not in parent_schema.render_props()
