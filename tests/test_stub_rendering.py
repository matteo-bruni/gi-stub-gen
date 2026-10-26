import ast

import pytest

from gi.repository import GLib, Gst

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.parser.python_function import parse_python_function
from gi_stub_gen.schema.class_ import ClassFieldSchema


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


@pytest.mark.parametrize("docstring", [None, "Documentation retained for IDE hover."])
@pytest.mark.parametrize("debug", [False, True])
def test_callable_body_has_only_docstring_or_ellipsis(monkeypatch, docstring, debug):
    monkeypatch.setattr(TemplateManager, "MODULE_NAME", "Gst")
    monkeypatch.setattr(TemplateManager, "DEBUG", debug)
    gi_function = parse_function(Gst.version, None)
    assert gi_function is not None

    def example() -> int:
        return 1

    python_function = parse_python_function(example, "Gst")
    assert python_function is not None
    gi_function.docstring = python_function.docstring = docstring
    for render in (gi_function.render_stub, gi_function.render_stub_compact, python_function.render_stub):
        function = ast.parse(render(), feature_version=(3, 12)).body[0]
        assert isinstance(function, ast.FunctionDef)
        assert len(function.body) == 1
        if docstring:
            assert docstring in (ast.get_docstring(function) or "")
        elif ast.get_docstring(function) is None:
            assert isinstance(function.body[0], ast.Expr)
            assert isinstance(function.body[0].value, ast.Constant)
            assert function.body[0].value.value is Ellipsis


@pytest.mark.parametrize("docstring", [None, "Readonly field documentation."])
@pytest.mark.parametrize("deprecated", [False, True])
def test_readonly_field_body_has_only_docstring_or_ellipsis(monkeypatch, docstring, deprecated):
    monkeypatch.setattr(TemplateManager, "MODULE_NAME", "Test")
    field = ClassFieldSchema(
        name="value", type_hint_name="int", type_hint_namespace=None,
        is_deprecated=deprecated, deprecation_warnings=None, docstring=docstring,
        line_comment=None, may_be_null=False, is_readable=True, is_writable=False,
    )
    text = TemplateManager.render_master("class_fields.jinja", fields=[field])
    getter = ast.parse(text, feature_version=(3, 12)).body[0]
    assert isinstance(getter, ast.FunctionDef)
    assert len(getter.body) == 1
