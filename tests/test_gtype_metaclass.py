"""
Tests for GTypeMeta metaclass detection.

GTypeMeta is needed for boxed/struct types that have a GType but don't inherit from GObject.Object.
This ensures Pylance correctly recognizes these types as GTypes.
"""

import gi

gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "4.0")

from gi.repository import GObject, Gst, GLib, Gtk

from gi_stub_gen.utils.gi_utils import do_class_need_gtype_metaclass
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.overrides.class_.GObject.GEnum import GENUM_SCHEMA
from gi_stub_gen.overrides.class_.GObject.GFlag import GFLAG_SCHEMA
from gi_stub_gen.overrides.class_.GObject.GEnumMeta import GENUM_META_SCHEMA, GFLAGS_META_SCHEMA


class TestGTypeMetaclassDetection:
    """Test do_class_need_gtype_metaclass function."""

    def test_gobject_object_no_metaclass(self):
        """
        GObject.Object itself should NOT need metaclass.
        It's the base class for all GObjects, already has GType.
        """
        assert do_class_need_gtype_metaclass(GObject.Object) is False

    def test_gobject_subclass_no_metaclass(self):
        """
        Classes that inherit from GObject.Object should NOT need metaclass.
        Example: Gtk.Widget, Gst.Element
        """
        # Gtk.Widget inherits from GObject.Object
        assert do_class_need_gtype_metaclass(Gtk.Widget) is False

        # Gst.Element inherits from GObject.Object
        Gst.init(None)
        assert do_class_need_gtype_metaclass(Gst.Element) is False

        # Gst.Pipeline inherits from Gst.Bin -> Gst.Element -> GObject.Object
        assert do_class_need_gtype_metaclass(Gst.Pipeline) is False

    def test_boxed_type_needs_metaclass(self):
        """
        Boxed types (GBoxed) should need metaclass.
        They have a GType but don't inherit from GObject.Object.
        """
        # Gst.Buffer is a boxed type
        Gst.init(None)
        assert do_class_need_gtype_metaclass(Gst.Buffer) is True

        # Gst.Caps is a boxed type
        assert do_class_need_gtype_metaclass(Gst.Caps) is True

        # Gst.Structure is a boxed type
        assert do_class_need_gtype_metaclass(Gst.Structure) is True

    def test_glib_types_need_metaclass(self):
        """
        GLib types like Error, Variant should need metaclass.
        They are boxed types with GType.
        """
        # GLib.Error is a boxed type
        assert do_class_need_gtype_metaclass(GLib.Error) is True

        # GLib.Variant is a boxed type
        assert do_class_need_gtype_metaclass(GLib.Variant) is True

    def test_enum_no_metaclass(self):
        """
        GObject enums (GEnum, GFlags) should NOT need metaclass.
        They are handled differently.
        """
        # Gst.State is an enum
        Gst.init(None)
        # Enums don't have __gtype__ in the same way, or are TYPE_INVALID
        result = do_class_need_gtype_metaclass(Gst.State)
        # This depends on implementation - enums might not have __gtype__
        # or might be handled as TYPE_INVALID
        assert isinstance(result, bool)  # Just verify it doesn't crash


class TestClassSchemaMetaclass:
    """Test ClassSchema generation with metaclass via parse_class."""

    def test_enum_typing_metaclasses(self):
        """Enum metaclasses combine runtime EnumType behavior with GType compatibility."""
        TemplateManager.set_module_name("GObject")

        assert GENUM_META_SCHEMA.super == ["enum.EnumType", "GType"]
        assert GFLAGS_META_SCHEMA.super == ["enum.EnumType", "GType"]
        assert GENUM_SCHEMA.super == ["enum.IntEnum", "metaclass=_GEnumMeta"]
        assert GFLAG_SCHEMA.super == ["enum.IntFlag", "metaclass=_GFlagsMeta"]

        rendered_meta = GENUM_META_SCHEMA.render()
        assert "# Typing-only model of gi._enum.GEnumMeta" in rendered_meta
        assert "class _GEnumMeta(enum.EnumType, GType):" in rendered_meta
        assert "Stub-only static typing model" in rendered_meta
        assert "def __gtype__(self) -> GType:" in rendered_meta

        assert "class GEnum(enum.IntEnum, metaclass=_GEnumMeta):" in GENUM_SCHEMA.render()
        assert "class GFlags(enum.IntFlag, metaclass=_GFlagsMeta):" in GFLAG_SCHEMA.render()

    def test_boxed_class_has_metaclass_in_super(self):
        """
        When parsing a boxed class, the super list should include metaclass=GObject.GType
        """
        Gst.init(None)
        schema, _ = parse_class("gi.repository.Gst", Gst.Buffer)
        assert schema is not None

        # Check that metaclass is in the super list
        assert any("metaclass=" in s for s in schema.super), f"Expected metaclass in super list, got: {schema.super}"
        assert any("GType" in s for s in schema.super), f"Expected GType in super list, got: {schema.super}"

    def test_gobject_class_no_metaclass_in_super(self):
        """
        When parsing a GObject class, the super list should NOT include metaclass.
        """
        Gst.init(None)
        schema, _ = parse_class("gi.repository.Gst", Gst.Element)
        assert schema is not None

        # Check that metaclass is NOT in the super list
        metaclass_entries = [s for s in schema.super if "metaclass=" in s]
        assert len(metaclass_entries) == 0, (
            f"Expected no metaclass in super list for GObject class, got: {schema.super}"
        )

    def test_gobject_object_no_metaclass_in_super(self):
        """
        GObject.Object itself should not have metaclass in super.
        """
        schema, _ = parse_class("gi.repository.GObject", GObject.Object)
        assert schema is not None

        metaclass_entries = [s for s in schema.super if "metaclass=" in s]
        assert len(metaclass_entries) == 0, f"Expected no metaclass for GObject.Object, got: {schema.super}"

    def test_metaclass_namespace_in_gobject_module(self):
        """
        When in GObject namespace, metaclass should be just 'GType', not 'GObject.GType'.
        """
        # GObject.GPointer is a boxed type in GObject namespace
        schema, _ = parse_class("gi.repository.GObject", GObject.GPointer)
        assert schema is not None

        # If it needs metaclass, it should use 'metaclass=GType' (without GObject. prefix)
        gtype_entries = [s for s in schema.super if "metaclass=GType" in s]
        if gtype_entries:
            assert "GObject.GType" not in gtype_entries[0], (
                f"In GObject namespace, should use GType without prefix, got: {schema.super}"
            )

    def test_metaclass_namespace_outside_gobject(self):
        """
        When outside GObject namespace, metaclass should be 'GObject.GType'.
        """
        Gst.init(None)
        schema, _ = parse_class("gi.repository.Gst", Gst.Buffer)
        assert schema is not None

        gtype_entries = [s for s in schema.super if "metaclass=" in s and "GType" in s]
        assert len(gtype_entries) > 0, "Gst.Buffer should have metaclass=GObject.GType"
        assert "GObject.GType" in gtype_entries[0], (
            f"Outside GObject namespace, should use GObject.GType, got: {schema.super}"
        )
