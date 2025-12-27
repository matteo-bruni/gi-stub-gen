import gi
from gi.repository import GObject
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.utils.utils import get_super_class_name


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


def test_super_class():
    """Test getting the super class name of a class."""
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    obj = Gtk.Builder
    super_module, super_name = get_super_class_name(obj, current_namespace="Gtk")
    assert super_name == "Object"
    assert super_module == "gi.repository.GObject"


def test_gtk_application_inheritance_fix():
    """
    CRITICAL TEST: Gtk.Application (Namespace 'Gtk') inherits from Gio.Application (Namespace 'Gio').
    Both have the name 'Application'.

    The parser MUST verify that despite having the same name, they are different classes
    because the namespace differs.
    """
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    # Gtk.Application MRO usually:
    # [Gtk.Application, Gio.Application, GObject.Object, ...]
    cls = Gtk.Application

    module, name = get_super_class_name(cls, current_namespace="Gtk")

    # We expect it to point to Gio.Application
    assert module == "gi.repository.Gio"
    assert name == "Application"


def test_gtk_builder_shadowing_fix():
    """
    CRITICAL TEST: Gtk.Builder.
    This class usually has a Python Override.
    MRO: [gi.overrides.Gtk.Builder, gi.repository.Gtk.Builder, GObject.Object...]

    The parser MUST skip 'gi.repository.Gtk.Builder' because it has:
    1. Same Name ('Builder')
    2. Same Namespace ('Gtk')

    So the parent must be GObject.
    """

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    cls = Gtk.Builder

    module, name = get_super_class_name(cls, current_namespace="Gtk")

    # We expect it to SKIP the Gtk.Builder repo shadow and go to GObject
    assert module == "gi.repository.GObject"
    assert name == "Object"


def test_standard_widget_inheritance():
    """
    Standard Case: Gtk.Box inherits from Gtk.Widget.
    Different names, easy case.
    """
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    cls = Gtk.Box

    module, name = get_super_class_name(cls, current_namespace="Gtk")

    assert module == "gi.repository.Gtk"
    assert name == "Widget"


def test_gobject_inheritance():
    """
    Case: GObject.Object inherits from builtins.object.
    """

    cls = GObject.Object

    module, name = get_super_class_name(cls, current_namespace="GObject")

    assert module == "builtins"
    assert name == "object"


def test_ginitially_unowned():
    """
    Some GTK widgets inherit from GObject.InitiallyUnowned.
    E.g., Gtk.Widget -> GObject.InitiallyUnowned -> GObject.Object"""
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    # Gtk.Widget -> GObject.InitiallyUnowned -> GObject.Object
    cls = Gtk.Widget
    module, name = get_super_class_name(cls, current_namespace="Gtk")
    # It should point to InitiallyUnowned
    assert module == "gi.repository.GObject"
    assert name == "InitiallyUnowned"


def test_gio_file_interface():
    """
    Gio.File is an Interface, but in Python it appears as a class.
    We want to ensure we don't crash or return WeirdCThings.
    """
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio

    cls = Gio.File

    # Gio.File inherits from GObject.GInterface in MRO, but we treat it as a class base
    # or it might be a root interface.
    # Actually, Gio.File is a GInterface. In PyGObject it inherits from GObject.GInterface.

    module, name = get_super_class_name(cls, current_namespace="Gio")

    # We explicitly skip GInterface in the function, so it should fall back to object
    # OR if PyGObject exposes a prerequisite (like GObject), return that.

    # For interfaces, usually returning GObject.GInterface is what we filtered OUT.
    # So it should probably return 'object' or 'None, object'.
    assert name == "object"


def test_namespace_inference():
    """
    Test that the function can guess 'Gtk' from the object module
    if current_namespace is not provided.
    """
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    cls = Gtk.Button
    module, name = get_super_class_name(cls)  # No namespace provided

    assert module == "gi.repository.Gtk"
    assert name == "Widget"
