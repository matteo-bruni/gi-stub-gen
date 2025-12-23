from gi.repository import GObject, GLib
from gi_stub_gen.parser.enum import parse_enum


def test_parse_enum_glib_user_directory():
    """Test parsing of a standard GEnum (GLib.UserDirectory)."""
    enum_schema = parse_enum(GLib.UserDirectory)

    assert enum_schema is not None
    assert enum_schema.name == "UserDirectory"
    assert len(enum_schema.fields) > 0
    # Verify a known member
    assert any(m.name == "DIRECTORY_DESKTOP" for m in enum_schema.fields)


def test_parse_flags_gobject_param_flags():
    """Test parsing of GFlags (GObject.ParamFlags)."""
    flag_schema = parse_enum(GObject.ParamFlags)

    assert flag_schema is not None
    assert flag_schema.name == "ParamFlags"
    assert any(m.name == "READABLE" for m in flag_schema.fields)
