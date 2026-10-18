from gi.repository import Gio, Gst

from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.manager.template import TemplateManager


def test_selected_callbacks_link_userdata_and_preserve_original_protocol():
    for runtime, namespace in [
        (Gst.Pad.add_probe, "Gst"),
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
