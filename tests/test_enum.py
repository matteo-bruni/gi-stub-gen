import gi

gi.require_version("GstAudio", "1.0")
gi.require_version("Gst", "1.0")
gi.require_version("GstVideo", "1.0")

from gi.repository import GObject, GLib, Gst, GstAudio, GstVideo
from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.enum import parse_enum


def test_parse_enum_glib_user_directory():
    """Test parsing of a standard GEnum (GLib.UserDirectory)."""
    enum_schema = parse_enum(GLib.UserDirectory)

    assert enum_schema is not None
    assert enum_schema.name == "UserDirectory"
    assert enum_schema.super_namespace == "enum"
    assert enum_schema.super_name == "IntEnum"
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
    assert any(m.name == "READABLE" for m in flag_schema.fields)


def test_parse_enum_gstaudio_uses_direct_runtime_base():
    """GI enum schemas should keep GEnum as their single direct base."""
    enum_schema = parse_enum(GstAudio.AudioBaseSrcSlaveMethod)

    assert enum_schema is not None
    assert enum_schema.super_namespace == "GObject"
    assert enum_schema.super_name == "GEnum"


def test_render_enum_uses_only_direct_genum_base():
    """IntEnum is inherited through GEnum and must not be repeated."""
    enum_schema = parse_enum(GstAudio.AudioBaseSrcSlaveMethod)

    assert enum_schema is not None

    TemplateManager.set_module_name("GstAudio")
    rendered = enum_schema.render()

    assert "class AudioBaseSrcSlaveMethod(GObject.GEnum):" in rendered
    assert "GObject.GEnum, enum.IntEnum" not in rendered
    assert "SKEW = 2" in rendered


def test_render_enum_methods():
    resource_error = parse_enum(Gst.ResourceError)
    assert resource_error is not None

    quark = next(method for method in resource_error.methods if method.name == "quark")
    assert quark.complete_return_hint("Gst") == "int"

    TemplateManager.set_module_name("Gst")
    rendered = resource_error.render()
    assert "@staticmethod" in rendered
    assert "def quark() -> int:" in rendered

    video_format = parse_enum(GstVideo.VideoFormat)
    assert video_format is not None

    from_string = next(method for method in video_format.methods if method.name == "from_string")
    assert from_string.complete_return_hint("GstVideo") == "VideoFormat"
    assert from_string.render_args("GstVideo", one_line=True) == "format: str"

    TemplateManager.set_module_name("GstVideo")
    rendered = video_format.render()
    assert "def from_string(format: str) -> VideoFormat:" in rendered
