from gi.repository import GObject
from gi_stub_gen.parser.class_ import parse_class


def test_parse_class_gobject_object():
    """Test parsing of GObject.Object."""
    class_schema, callbacks = parse_class("gi.repository.GObject", GObject.Object)

    assert class_schema is not None
    assert class_schema.name == "Object"
    assert class_schema.namespace == "gi.repository.GObject"

    # Check for some known methods
    method_names = [m.name for m in class_schema.methods]
    assert "bind_property" in method_names
    assert "emit" in method_names, (
        f"Expected 'emit' method to be present in GObject.Object \n Methods found: {method_names}"
    )

    # Check for properties (GObject.Object doesn't have many props, but let's check attributes/props lists exist)
    # assert isinstance(class_schema.props, list)
    # assert isinstance(class_schema.attributes, list)


def test_parse_class_gobject_initially_unowned():
    """Test parsing of GObject.InitiallyUnowned."""
    class_schema, callbacks = parse_class("gi.repository.GObject", GObject.InitiallyUnowned)

    assert class_schema is not None
    assert class_schema.name == "InitiallyUnowned"
    assert "Object" == class_schema.super_class


def test_runtime_fields():
    """
    In some cases, certain fields are only discoverable at runtime.
    eg: GLib.Error.message, GLib.Error.code, GLib.Error.domain
    This test ensures we can parse such classes and find these fields.

    We discover them using GIRepository directly.
    """
    from gi.repository import GLib

    class_schema, callbacks = parse_class("gi.repository.GLib", GLib.Error)

    assert class_schema is not None
    assert class_schema.name == "Error"
    field_names = [f.name for f in class_schema.fields]
    assert "message" in field_names
    assert "code" in field_names
    assert "domain" in field_names
