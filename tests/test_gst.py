import gi
import pytest
from gi.repository import GObject, Gst

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.alias import parse_alias
from gi_stub_gen.parser.class_ import create_init_method, parse_class
from gi_stub_gen.parser.constant import parse_constant
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.utils.gst import get_fraction_value


def test_gst_environment():
    assert Gst.version()[0] >= 1


def test_constructor_gst_new_returns_class_type():
    """
    class constructor should return the class type properly.
    """
    constructor_to_test = "new"

    for class_to_test, return_hint in ((Gst.Bin, "Bin"), (Gst.Pipeline, "Pipeline")):
        parsed_class, _ = parse_class("Gst", class_to_test)
        assert parsed_class is not None, f"Failed to parse Gst.{return_hint} class"

        # find the constructor
        constructor = [m for m in parsed_class.methods if m.name == constructor_to_test]
        assert len(constructor) == 1, f"Failed to find Gst.{return_hint}.new constructor method"
        parsed_constructor = constructor[0]

        # check the return hint
        assert parsed_constructor.complete_return_hint(namespace="GObject") == f"Gst.{return_hint}"
        assert parsed_constructor.complete_return_hint(namespace="Gst") == return_hint
        # should have no parameters
        assert parsed_constructor.render_args(namespace="Gst", one_line=True) == "cls, name: str | None = None"

        python_constructor = [m for m in parsed_class.python_methods if m.name == constructor_to_test]
        assert len(python_constructor) == 1, f"Failed to find Gst.{return_hint}.new python override"
        assert python_constructor[0].return_hint(namespace="Gst") == return_hint

        TemplateManager.set_module_name("Gst")
        rendered = parsed_class.render()
        assert f") -> {return_hint}:" in rendered


def test_gst_object_parent_renders_direct_property():
    parsed_class, _ = parse_class("Gst", Gst.Object)
    assert parsed_class is not None

    parent = next(field for field in parsed_class.fields if field.name == "parent")
    assert parent.type_hint("Gst") == "Object | None"
    assert parent.is_property is True

    TemplateManager.set_module_name("Gst")
    rendered = parsed_class.render()
    assert "def parent(self) -> Object | None:" in rendered


def test_gstbadaudio_init_uses_c_prefix_for_enum_properties():
    try:
        gi.require_version("GstBadAudio", "1.0")
        from gi.repository import GstBadAudio
    except (ImportError, ValueError) as exc:
        pytest.skip(f"GstBadAudio typelib not available: {exc}")

    init_method = create_init_method("GstBadAudio", GstBadAudio.NonstreamAudioDecoder)
    assert init_method is not None

    output_mode = next(arg for arg in init_method.args if arg.name == "output_mode")
    assert output_mode.py_type_name == "NonstreamAudioOutputMode"
    assert output_mode.py_type_namespace == "GstBadAudio"
    assert output_mode.default_value == "NonstreamAudioOutputMode.STEADY"


def test_gstvideo_array_fields_keep_item_type():
    try:
        gi.require_version("GstVideo", "1.0")
        from gi.repository import GstVideo
    except (ImportError, ValueError) as exc:
        pytest.skip(f"GstVideo typelib not available: {exc}")

    parsed_class, _ = parse_class("GstVideo", GstVideo.VideoInfo)
    assert parsed_class is not None

    stride = next(field for field in parsed_class.fields if field.name == "stride")
    assert stride.type_hint_name == "list[int]"
    assert stride.type_hint("GstVideo") == "list[int] | None"


def test_gstcuda_invalid_cross_namespace_alias_falls_back_to_constant():
    try:
        gi.require_version("GstCuda", "1.0")
        from gi.repository import GstCuda
    except (ImportError, ValueError) as exc:
        pytest.skip(f"GstCuda typelib not available: {exc}")

    assert parse_alias("gi.repository.GstCuda", "MAP_READ_CUDA", GstCuda.MAP_READ_CUDA) is None

    constant = parse_constant(
        module_name="gi.repository.GstCuda",
        name="MAP_READ_CUDA",
        obj=GstCuda.MAP_READ_CUDA,
        docstring=None,
    )
    assert constant is not None
    assert constant.name == "MAP_READ_CUDA"


def test_named_field_callbacks_keep_public_callback_name():
    parsed_class, callbacks = parse_class("Gst", Gst.Allocator)
    assert parsed_class is not None

    callback_names = {callback.name for callback in callbacks}
    assert "MemoryCopyFunction" in callback_names
    assert "MemoryCopyFunctionAllocatorCB" not in callback_names


def test_nested_callbacks_are_returned_from_class_parsing():
    try:
        gi.require_version("GstPlayer", "1.0")
        from gi.repository import GstPlayer
    except (ImportError, ValueError) as exc:
        pytest.skip(f"GstPlayer typelib not available: {exc}")

    parsed_class, callbacks = parse_class("GstPlayer", GstPlayer.PlayerSignalDispatcherInterface)
    assert parsed_class is not None

    callback_names = {callback.name for callback in callbacks}
    assert "dispatchPlayerSignalDispatcherInterfaceCB" in callback_names
    assert "PlayerSignalDispatcherFunc" in callback_names


def test_gst_structure_get_value_returns_python_values_at_runtime():
    structure = Gst.Structure.new_empty("test")
    structure.set_value("string", "hello")
    structure.set_value("int", 42)
    structure.set_value("bool", True)
    structure.set_value("fraction", Gst.Fraction(1, 2))

    for fieldname, expected_type in (
        ("string", str),
        ("int", int),
        ("bool", bool),
        ("fraction", Gst.Fraction),
    ):
        value = structure.get_value(fieldname)
        assert isinstance(value, expected_type)
        assert not isinstance(value, GObject.Value)

    assert structure.get_value("missing") is None


def test_gst_structure_get_value_override_returns_any():
    parsed_class, _ = parse_class("gi.repository.Gst", Gst.Structure)
    assert parsed_class is not None

    get_value = next(method for method in parsed_class.methods if method.name == "get_value")
    assert get_value.render_args("Gst", one_line=True) == "self, fieldname: str"
    assert get_value.complete_return_hint("Gst") == "typing.Any"

    assert not any(method.name == "get_value" for method in parsed_class.python_methods)

    TemplateManager.set_module_name("Gst")
    rendered = parsed_class.render()
    assert "def get_value(self, fieldname: str) -> typing.Any:" in rendered


def test_function_gst_version():
    function_to_test = Gst.version

    # do the parsing
    parsed_function = parse_function(function_to_test, None)
    assert parsed_function is not None, "Failed to parse Gst.version function"

    # check the return hint
    assert parsed_function.complete_return_hint(namespace="Gst") == "tuple[int, int, int, int]"
    # should have no parameters
    assert parsed_function.render_args(namespace="Gst", one_line=True) == ""


def test_function_gst_version_string():
    function_to_test = Gst.version_string

    # do the parsing
    parsed_function = parse_function(function_to_test, None)
    assert parsed_function is not None, "Failed to parse Gst.version function"

    # check the return hint
    assert parsed_function.complete_return_hint(namespace="Gst") == "str"
    # should have no parameters
    assert parsed_function.render_args(namespace="Gst", one_line=True) == ""


def test_fraction():
    frac = Gst.Fraction(num=3, denom=4)
    assert frac.num == 3
    assert frac.denom == 4


def test_fraction_values():
    frac = Gst.Fraction(num=1, denom=100)

    assert frac.num == 1
    assert frac.denom == 100

    value = get_fraction_value(frac)
    assert value == "Gst.Fraction(num=1, denom=100)"
