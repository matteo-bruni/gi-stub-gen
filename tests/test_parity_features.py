"""Small runtime contracts for the public Python API and native marshalling."""
import ast
import gi

gi.require_version("GstBase", "1.0")
gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gst, GstBase

from gi_stub_gen.manager.gi_repo import GIRepo
from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.parser.python_function import parse_python_function


def test_selected_gst_operators_are_parsed_not_redeclared():
    GIRepo().require("Gst", "1.0")
    for cls, names in ((Gst.Caps, {"__getitem__", "__len__"}),
                       (Gst.Structure, {"__getitem__", "__setitem__", "__len__"})):
        schema, _ = parse_class("gi.repository.Gst", cls)
        assert schema is not None
        methods = {method.name: method for method in schema.python_methods}
        assert names <= methods.keys()
        for name in names:
            expected = parse_python_function(getattr(cls, name), "Gst", name, cls)
            assert expected is not None
            assert methods[name].render_return_annotation("Gst") == expected.render_return_annotation("Gst")
            assert methods[name].render_parameter_list("Gst") == expected.render_parameter_list("Gst")
        assert "__eq__" not in methods
        TemplateManager.set_module_name("Gst")
        ast.parse(schema.render_stub(), feature_version=(3, 12))
    caps = Gst.Caps.from_string("video/x-raw,width=640,height=480")
    assert caps is not None and len(caps) == 1
    assert caps[0].get_name() == "video/x-raw"
    structure = Gst.Structure.new_empty("example")
    structure["width"] = 640
    assert structure["width"] == 640 and len(structure) == 1


def test_only_native_virtual_methods_become_positional():
    parsed = parse_python_function(GstBase.Aggregator.do_aggregate, "GstBase", from_class=GstBase.Aggregator)
    assert parsed is not None
    assert parsed.render_parameter_list("GstBase") == ["self", "timeout: bool", "/"]

    class Ordinary:
        def do_work(self, value: int) -> None:
            pass

    normal = parse_python_function(Ordinary.do_work, "Test", from_class=Ordinary)
    assert normal is not None
    assert normal.render_parameter_list("Test") == ["self", "value: int"]


def test_input_arrays_keep_concrete_outputs_and_callback_values():
    from gi_stub_gen.parser.function import parse_function, parse_callable
    join = parse_function(GLib.strjoinv, None)
    assert join is not None
    assert "str_array: collections.abc.Sequence[str]" in join.render_parameter_list("GLib")
    assert GLib.strjoinv(",", ("a", "b")) == "a,b"
    wrapped = parse_python_function(Gst.Buffer.new_wrapped, "Gst", from_class=Gst.Buffer)
    assert wrapped is not None
    assert "data: collections.abc.Sequence[int]" in wrapped.render_parameter_list("Gst")
    assert Gst.Buffer.new_wrapped((65, 66)).extract_dup(0, 2) == b"AB"
    decode = parse_function(GLib.base64_decode_inplace, None)
    assert decode is not None
    assert "Sequence[int]" in decode.render_parameter_list("GLib")
    assert decode.render_return_annotation("GLib") == "tuple[int, bytes]"
    from gi.repository import Gio
    signal = next(info for info in getattr(Gio.Application, "__info__").get_signals() if info.get_name() == "open")
    parsed = parse_callable(signal)
    assert parsed.args[0].py_type_name == "list[File]"
    assert parsed.args[0].input_type_name is None


def test_input_mapping_and_nested_containers():
    from collections import UserDict
    from collections.abc import Mapping, Sequence
    from unittest.mock import Mock
    import gi._gi as GI
    from gi_stub_gen.parser.function import parse_function
    from gi_stub_gen.utils.gi_utils import gi_type_to_py_type

    integer = Mock()
    integer.get_tag.return_value = GI.TypeTag.INT32
    array = Mock()
    array.get_tag.return_value = GI.TypeTag.ARRAY
    array.get_param_type.return_value = integer
    mapping = Mock()
    mapping.get_tag.return_value = GI.TypeTag.GHASH
    mapping.get_param_type.side_effect = lambda index: integer if index == 0 else array
    assert gi_type_to_py_type(mapping) == dict[int, list[int]]
    assert gi_type_to_py_type(mapping, for_input=True) == Mapping[int, Sequence[int]]
    uri = Gst.Uri.from_string("https://example.com")
    assert uri is not None
    assert uri.set_query_table(UserDict({"a": "b"}))
    assert uri.get_query_table() == {"a": "b"}
    parsed = parse_function(Gst.Uri.set_query_table, None)
    assert parsed is not None
    assert "Mapping[str, str]" in parsed.render_parameter_list("Gst")


def test_helpers_render_through_the_existing_models():
    import importlib
    from gi_stub_gen.parser.module import parse_module

    for name in ("gi", "gi._signalhelper", "gi._gtktemplate", "gi.events"):
        module = importlib.import_module(name)
        schema, _ = parse_module(module)
        text = schema.render_stub([], {})
        ast.parse(text, feature_version=(3, 12))
        if name == "gi":
            assert "namespace: str" in text and "requires: dict[str, str]" in text
        else:
            assert "class Props" not in text
            assert "__getattr__" not in text
            if name == "gi._signalhelper":
                assert "class BoundSignal(str)" in text
            if name == "gi._gtktemplate":
                assert "class Callback" in text and "type[T]" in text
            if name == "gi.events":
                assert "class GLibTask[T](asyncio.Task[T])" in text
        original = schema.model_dump()
        schema.classes.clear()
        assert parse_module(module)[0].model_dump() == original


def test_python_helpers_runtime_contracts():
    import inspect
    import gi.events as events
    from gi.repository import GObject

    class Emitter(GObject.Object):
        @GObject.Signal
        def changed(self, value: int) -> None:
            pass

    values = []
    emitter = Emitter()
    handler = emitter.changed.connect(lambda _obj, value: values.append(value))
    emitter.changed.emit(7)
    emitter.changed.disconnect(handler)
    assert values == [7]
    assert isinstance(Emitter.changed, GObject.Signal)
    gi.check_version((3, 58, 1))
    assert gi.get_required_version("Gst") == "1.0"

    # Deliberately fail when upstream removes the unused argument: update its stub then.
    assert str(inspect.signature(events.GLibTask.get_priority)) == "(self, priority)", "Recheck GLibTask.get_priority declaration"
    loop = events.GLibEventLoop()

    async def answer() -> int:
        return 42

    try:
        task = events.GLibTask(answer(), loop=loop)
        task.set_priority(GLib.PRIORITY_DEFAULT)
        assert task.get_priority(None) == GLib.PRIORITY_DEFAULT
        with loop.paused():
            pass
        assert loop.run_until_complete(task) == 42
    finally:
        loop.close()


def test_virtual_dispatch_with_a_renamed_argument_in_a_real_pipeline():
    received: list[int] = []
    template = Gst.PadTemplate.new("sink", Gst.PadDirection.SINK, Gst.PadPresence.ALWAYS, Gst.Caps.new_any())
    assert template is not None

    class RecordingSink(GstBase.BaseSink):
        __gstmetadata__ = ("Parity test sink", "Sink", "Checks virtual dispatch", "gi-stub-gen")
        __gsttemplates__ = (template,)

        def do_render(self, renamed_buffer: Gst.Buffer) -> Gst.FlowReturn:
            received.append(renamed_buffer.get_size())
            return Gst.FlowReturn.OK

    pipeline = Gst.Pipeline.new("parity-test")
    source = Gst.ElementFactory.make("fakesrc")
    assert pipeline is not None and source is not None
    source.set_property("num-buffers", 2)
    sink = RecordingSink()
    pipeline.add(source)
    pipeline.add(sink)
    assert source.link(sink)
    bus = pipeline.get_bus()
    assert bus is not None
    try:
        assert pipeline.set_state(Gst.State.PLAYING) != Gst.StateChangeReturn.FAILURE
        message = bus.timed_pop_filtered(5 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
        assert message is not None and message.type == Gst.MessageType.EOS
        assert len(received) == 2
    finally:
        pipeline.set_state(Gst.State.NULL)
