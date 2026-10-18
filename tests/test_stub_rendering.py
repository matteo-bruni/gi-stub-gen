import ast

from gi.repository import GLib, Gst

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.parser.python_function import parse_python_function


def test_callable_out_inout_and_hidden_length_parameters():
    version = parse_function(Gst.version, None)
    assert version is not None
    assert version.render_parameter_list("Gst") == ""
    assert version.render_return_annotation("Gst") == "tuple[int, int, int, int]"
    query = parse_function(Gst.Element.query_position, None)
    assert query is not None
    assert query.render_parameter_list("Gst") == "self, format: Format"
    assert query.render_return_annotation("Gst") == "tuple[bool, int]"
    decode = parse_function(GLib.base64_decode_inplace, None)
    assert decode is not None
    assert [(arg.name, arg.direction) for arg in decode.args] == [("text", "INOUT")]
    assert decode.render_parameter_list("GLib") == "text: collections.abc.Sequence[int]"
    assert decode.render_return_annotation("GLib") == "tuple[int, bytes]"


def test_closure_is_variadic_and_destroy_notifier_is_hidden():
    probe = parse_function(Gst.Pad.add_probe, None)
    assert probe is not None
    assert [arg.name for arg in probe.args] == ["mask", "callback", "user_data"]
    assert probe.args[-1].is_variadic
    assert probe.args[-1].render_parameter("Gst") == "*user_data: *UserData"
    assert "PadProbeCallback" in {callback.name for callback in probe._gi_callbacks}


def test_parameter_rendering_and_python312_syntax():
    def example(value: int, /, label: str = "x", *, enabled: bool = False) -> bool:
        return enabled

    parsed = parse_python_function(example, "Test")
    assert parsed is not None
    assert parsed.render_parameter_list("Test") == [
        "value: int",
        "/",
        "label: str = 'x'",
        "*",
        "enabled: bool = False",
    ]
    TemplateManager.set_module_name("Test")
    ast.parse(parsed.render_stub(), feature_version=(3, 12))
    TemplateManager.set_module_name("Gst")
    function = parse_function(Gst.Element.query_position, None)
    assert function is not None
    ast.parse(function.render_stub(), feature_version=(3, 12))
    ast.parse(function.render_stub_compact(), feature_version=(3, 12))


def test_gi_parameter_defaults_keep_required_argument_order():
    function = parse_function(Gst.Pad.add_probe, None)
    assert function is not None
    optional = function.args[0].model_copy(update={"name": "optional", "is_optional": True, "default_value": "0"})
    required = function.args[0].model_copy(update={"name": "required"})
    function.args = [optional, required]
    assert optional.render_parameter("Gst") == "optional: PadProbeType | None = 0"
    assert function.render_parameter_list("Gst") == "self, optional: PadProbeType | None, required: PadProbeType"


def test_parameter_named_cls_is_not_an_implicit_receiver():
    class Decorator:
        def __call__(self, cls: type[int]) -> type[int]:
            return cls

    parsed = parse_python_function(Decorator.__call__, "Test", from_class=Decorator)
    assert parsed is not None
    assert parsed.render_parameter_list("Test") == ["self", "cls: type[int]"]
