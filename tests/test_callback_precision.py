import ast

from gi import _gi
from gi.repository import Gio, Gst

from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.fields import gi_parse_field


def test_native_self_argument_is_separate_from_protocol_receiver():
    info = getattr(Gio.TlsDatabaseClass, "__info__")
    assert isinstance(info, _gi.StructInfo)
    field = next(field for field in info.get_fields() if field.get_name() == "verify_chain")
    _, callback = gi_parse_field(field, "Gio", "TlsDatabaseClass")
    assert callback is not None
    function = callback.function
    assert function.input_args[0].name == "self"
    TemplateManager.set_module_name("Gio")
    tree = ast.parse(callback.render_stub())
    call = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
    assert not call.args.args
    assert [arg.arg for arg in call.args.posonlyargs] == ["_callback", *[arg.name for arg in function.input_args]]
    assert call.args.posonlyargs[0].annotation is None
    assert call.args.posonlyargs[1].annotation is not None
    assert ast.unparse(call.args.posonlyargs[1].annotation) == "TlsDatabase"

    native = function.input_args[0]
    function.args = [native.model_copy(update={"name": name}) for name in ("self", "_callback", "_callback_")]
    assert function.render_receiver() == "_callback__"
    function.args = [native.model_copy(update={"direction": "OUT"})]
    assert function.render_receiver() == "self"
    function.args = []
    assert function.render_receiver() == "self"


def test_selected_callbacks_link_userdata_and_preserve_original_protocol():
    for runtime, namespace in [
        (Gst.Pad.add_probe, "Gst"),
        (Gst.Bus.set_sync_handler, "Gst"),
        (Gio.File.load_contents_async, "Gio"),
        (Gio.InputStream.read_bytes_async, "Gio"),
    ]:
        schema = parse_function(runtime, None)
        assert schema is not None
        assert schema.type_parameters == ["*UserData"]
        callback = next(arg for arg in schema.args if arg.is_callback)
        assert "WithData[" in callback.py_type_name
        assert "typing.Callable" not in callback.render_type_annotation(namespace)
        original, precise = schema._gi_callbacks
        assert not original.function.positional_only
        assert precise.function.positional_only
        assert precise.function.input_args[-1].type_var_name == "*UserData"
        TemplateManager.set_module_name(namespace)
        text = precise.render_stub()
        assert "/," in text
        assert ": *UserData" in text


def test_unselected_callback_keeps_fallback():
    schema = parse_function(Gst.Pad.set_chain_function_full, None)
    assert schema is not None
    assert not schema.type_parameters
    callback = next(arg for arg in schema.args if arg.is_callback)
    assert "typing.Callable" in callback.render_type_annotation("Gst")


def test_native_callbacks_use_positional_arguments_and_preserve_defaults():
    schema = parse_function(Gst.Pad.set_activatemode_function_full, None)
    assert schema is not None
    callback = next(cb for cb in schema._gi_callbacks if cb.name == "PadActivateModeFunction")
    TemplateManager.set_module_name("Gst")
    tree = ast.parse(callback.render_stub())
    call = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
    assert [arg.arg for arg in call.args.posonlyargs] == ["self", "pad", "parent", "mode", "active"]
    assert not call.args.args

    callback.function.args[-1].default_value = "False"
    assert "active: bool = False," in callback.render_stub()


def test_pad_activation_accepts_different_callback_parameter_names():
    seen: list[tuple[Gst.PadMode, bool]] = []

    def activate(pad: Gst.Pad, parent: Gst.Object, pad_mode: Gst.PadMode, active: bool) -> bool:
        seen.append((pad_mode, active))
        return True

    container = Gst.Bin.new(None)
    pad = Gst.Pad.new("probe", Gst.PadDirection.SRC)
    assert container.add_pad(pad)
    pad.set_activatemode_function_full(activate)
    assert pad.activate_mode(Gst.PadMode.PUSH, True)
    assert pad.activate_mode(Gst.PadMode.PUSH, False)
    assert seen == [(Gst.PadMode.PUSH, True), (Gst.PadMode.PUSH, False)]
