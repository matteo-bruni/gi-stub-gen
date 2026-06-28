import gi

gi.require_version("GstAudio", "1.0")

from gi.repository import GObject, GLib, GstAudio
from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.enum import parse_enum


def test_parse_enum_glib_user_directory():
    """Test parsing of a standard GEnum (GLib.UserDirectory)."""
    enum_schema = parse_enum(GLib.UserDirectory)

    assert enum_schema is not None
    assert enum_schema.name == "UserDirectory"
    assert enum_schema.super_namespace == "enum"
    assert enum_schema.super_name == "IntEnum"
    assert enum_schema.extra_super_namespace is None
    assert enum_schema.extra_super_name is None
    assert len(enum_schema.fields) > 0
    # Verify a known member
    assert any(m.name == "DIRECTORY_DESKTOP" for m in enum_schema.fields)


def test_parse_flags_gobject_param_flags():
    """Test parsing of GFlags (GObject.ParamFlags)."""
    flag_schema = parse_enum(GObject.ParamFlags)

    assert flag_schema is not None
    assert flag_schema.name == "ParamFlags"
    assert flag_schema.super_namespace == "enum"
    assert flag_schema.super_name == "IntFlag"
    assert flag_schema.extra_super_namespace is None
    assert flag_schema.extra_super_name is None
    assert any(m.name == "READABLE" for m in flag_schema.fields)


def test_parse_enum_gstaudio_uses_double_inheritance_when_available():
    """PyGObject enums that expose both GEnum and IntEnum should keep both bases."""
    enum_schema = parse_enum(GstAudio.AudioBaseSrcSlaveMethod)

    assert enum_schema is not None
    assert enum_schema.super_namespace == "GObject"
    assert enum_schema.super_name == "GEnum"
    assert enum_schema.extra_super_namespace == "enum"
    assert enum_schema.extra_super_name == "IntEnum"


def test_render_enum_uses_genum_and_intenum_bases_when_available():
    """Rendered GI enums should expose both GObject.GEnum and enum.IntEnum bases when runtime MRO does."""
    enum_schema = parse_enum(GstAudio.AudioBaseSrcSlaveMethod)

    assert enum_schema is not None

    TemplateManager.set_module_name("GstAudio")
    rendered = enum_schema.render()

    assert "class AudioBaseSrcSlaveMethod(GObject.GEnum, enum.IntEnum):" in rendered
    assert "SKEW = 2" in rendered
