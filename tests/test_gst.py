from pathlib import Path
from typing import Any, cast

import gi
import pytest
from gi.repository import GObject, Gst

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.manager.gi_repo import GIRepo
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


def test_gst_mini_object_mixin_inheritance_and_properties():
    parsed_mixin, _ = parse_class("Gst", Gst.MiniObjectMixin)
    assert parsed_mixin is not None

    mixin_fields = {field.name: field for field in parsed_mixin.fields}
    assert parsed_mixin.type_parameters == "FlagsType: GObject.GFlags"
    assert mixin_fields["flags"].type_hint("Gst") == "FlagsType"
    assert mixin_fields["flags"].is_readable is True
    assert mixin_fields["flags"].is_writable is True
    assert {"is_writable", "make_writable"} <= {method.name for method in parsed_mixin.python_methods}

    TemplateManager.set_module_name("Gst")
    rendered_mixin = parsed_mixin.render()
    assert "class MiniObjectMixin[FlagsType: GObject.GFlags]:" in rendered_mixin
    assert "class Props" not in rendered_mixin
    assert "flags: FlagsType = ..." in rendered_mixin

    for concrete_class in (Gst.Buffer, Gst.Caps, Gst.Context, Gst.Event, Gst.Query):
        parsed_class, _ = parse_class("Gst", concrete_class)
        assert parsed_class is not None
        expected_flags = "BufferFlags" if concrete_class is Gst.Buffer else "MiniObjectFlags"
        assert parsed_class.super[0] == f"MiniObjectMixin[{expected_flags}]"
        assert parsed_class.props_super_class == "GObject.GBoxed.Props"
        assert "is_writable" not in {method.name for method in parsed_class.methods}
        assert "make_writable" not in {method.name for method in parsed_class.methods}
        assert "is_writable" not in {method.name for method in parsed_class.python_methods}
        assert "make_writable" not in {method.name for method in parsed_class.python_methods}


def test_gst_override_properties_keep_the_most_informative_types():
    parsed_buffer, _ = parse_class("Gst", Gst.Buffer)
    assert parsed_buffer is not None
    buffer_fields = {field.name: field for field in parsed_buffer.fields}

    assert buffer_fields["flags"].type_hint("Gst") == "BufferFlags"
    for field_name in ("dts", "pts", "duration", "offset", "offset_end"):
        field = buffer_fields[field_name]
        assert field.type_hint("Gst") == "int"
        assert field.is_readable is True
        assert field.is_writable is True

    parsed_probe_info, _ = parse_class("Gst", Gst.PadProbeInfo)
    assert parsed_probe_info is not None
    probe_fields = {field.name: field for field in parsed_probe_info.fields}
    assert probe_fields["data"].type_hint("Gst") == "typing.Any"
    assert probe_fields["type"].type_hint("Gst") == "PadProbeType"
    assert probe_fields["id"].type_hint("Gst") == "int"
    assert probe_fields["offset"].type_hint("Gst") == "int"
    assert probe_fields["size"].type_hint("Gst") == "int"


def test_gst_override_class_annotations_refine_fields_and_add_python_only_attributes():
    assert GIRDocs().load(Path("/usr/share/gir-1.0/Gst-1.0.gir"))
    GIRepo().require("Gst", "1.0")
    parsed_map_info, _ = parse_class("Gst", Gst.MapInfo)
    assert parsed_map_info is not None
    map_info_fields = {field.name: field for field in parsed_map_info.fields}

    assert map_info_fields["data"].type_hint("Gst") == "memoryview | None"
    assert map_info_fields["flags"].type_hint("Gst") == "MapFlags"
    assert map_info_fields["maxsize"].type_hint("Gst") == "int"
    assert map_info_fields["memory"].type_hint("Gst") == "Memory | None"
    assert map_info_fields["size"].type_hint("Gst") == "int"
    assert map_info_fields["data"].docstring == "a pointer to the mapped data"
    assert map_info_fields["data"].is_readable is True
    assert map_info_fields["data"].is_writable is True

    for cls, expected_fields in (
        (Gst.Bitmask, {"v": "int"}),
        (Gst.DoubleRange, {"start": "float", "stop": "float"}),
        (Gst.FractionRange, {"start": "Fraction", "stop": "Fraction"}),
    ):
        parsed_class, _ = parse_class("Gst", cls)
        assert parsed_class is not None
        fields = {field.name: field.type_hint("Gst") for field in parsed_class.fields}
        assert expected_fields.items() <= fields.items()


@pytest.mark.parametrize(
    ("flags", "readonly"),
    (
        (Gst.MapFlags.READ, True),
        (Gst.MapFlags.WRITE, False),
        (Gst.MapFlags.READ | Gst.MapFlags.WRITE, False),
    ),
)
def test_gst_map_info_data_runtime_mutability(flags: Gst.MapFlags, readonly: bool):
    buffer = Gst.Buffer.new_allocate(None, 4, None)
    assert buffer is not None
    map_info = buffer.map(flags)
    try:
        assert isinstance(map_info.data, memoryview)
        assert map_info.data.readonly is readonly
        if readonly:
            with pytest.raises(TypeError):
                map_info.data[:] = b"test"
        else:
            map_info.data[:] = b"test"
            assert bytes(map_info.data) == b"test"
    finally:
        buffer.unmap(map_info)


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


def test_gst_gvalue_inputs_and_callbacks_use_python_payloads_at_runtime():
    caps = Gst.Caps.new_empty_simple("audio/x-raw")
    assert cast(Any, caps).set_value("rate", 48_000) is None
    assert caps.get_structure(0).get_value("rate") == 48_000

    structure = Gst.Structure.new_empty("test")
    assert structure.set_value("answer", 42) is None
    received: list[Any] = []

    def collect_value(field_id: int, value: Any, *user_data: object | None) -> bool:
        del field_id, user_data
        received.append(value)
        return True

    assert structure.foreach(collect_value)
    assert received == [42]
    assert not isinstance(received[0], GObject.Value)

    value = GObject.Value()
    value.init(Gst.Caps)
    native_caps = Gst.Caps.from_string("video/x-raw")
    assert native_caps is not None
    assert Gst.value_set_caps(value, native_caps) is None
    assert value.get_value() == native_caps


def test_gst_gvalue_marshalling_signatures():
    assert GIRDocs().load(Path("/usr/share/gir-1.0/Gst-1.0.gir"))
    parsed_class, _ = parse_class("gi.repository.Gst", Gst.Structure)
    assert parsed_class is not None

    get_value = next(method for method in parsed_class.methods if method.name == "get_value")
    assert get_value.render_args("Gst", one_line=True) == "self, fieldname: str"
    assert get_value.complete_return_hint("Gst") == "typing.Any"

    assert not any(method.name == "get_value" for method in parsed_class.python_methods)

    TemplateManager.set_module_name("Gst")
    rendered = parsed_class.render()
    assert "def get_value(self, fieldname: str) -> typing.Any:" in rendered

    set_value = next(method for method in parsed_class.methods if method.name == "set_value")
    assert set_value.render_args("Gst", one_line=True) == "self, key: str, value: typing.Any"
    assert set_value.complete_return_hint("Gst") == "None"

    caps, _ = parse_class("gi.repository.Gst", Gst.Caps)
    assert caps is not None
    caps_set_value = next(method for method in caps.methods if method.name == "set_value")
    assert caps_set_value.render_args("Gst") == "self, field: str, value: typing.Any"

    compare = parse_function(Gst.value_compare, None)
    fixate = parse_function(Gst.value_fixate, None)
    assert compare is not None and fixate is not None
    assert compare.render_args("Gst") == "value1: typing.Any, value2: typing.Any"
    assert fixate.render_args("Gst") == "dest: GObject.Value, src: typing.Any"

    element_factory, _ = parse_class("gi.repository.Gst", Gst.ElementFactory)
    assert element_factory is not None
    make = next(method for method in element_factory.methods if method.name == "make_with_properties")
    values = next(arg for arg in make.args if arg.name == "values")
    assert values.type_hint("Gst") == "list[typing.Any] | None"

    callbacks = {callback.name: callback for callback in parse_class("gi.repository.Gst", Gst.Structure)[1]}
    for callback_name in ("StructureForeachFunc", "StructureMapFunc"):
        value = next(arg for arg in callbacks[callback_name].function.args if arg.name == "value")
        assert value.type_hint("Gst") == "typing.Any"

    value_list, _ = parse_class("gi.repository.Gst", Gst.ValueList)
    assert value_list is not None
    init = next(method for method in value_list.methods if method.name == "init")
    assert next(arg for arg in init.args if arg.name == "value").type_hint("Gst") == "GObject.Value"


def test_gvalue_without_gir_metadata_is_kept_conservatively():
    compare = parse_function(Gst.value_compare, None)
    assert compare is not None
    assert compare.render_args("Gst") == "value1: GObject.Value, value2: GObject.Value"


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
