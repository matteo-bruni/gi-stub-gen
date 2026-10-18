"""Native signal arguments and Python user data must remain separate."""

import ast

import pytest
from gi.repository import Gio, GLib, GObject, Gst

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.schema.signals import generate_notify_signal


@pytest.mark.parametrize("payload", [(), ("label",), (42, "label")])
def test_bus_sync_handler_marshalling_and_removal(payload):
    bus = Gst.Bus.new()
    received = []

    def handler(sender, event, *data):
        assert sender == bus and event.type == Gst.MessageType.APPLICATION
        received.append(data)
        return Gst.BusSyncReply.PASS

    bus.set_sync_handler(handler, *payload)
    assert bus.post(Gst.Message.new_application(None, Gst.Structure.new_empty("probe")))
    assert received == [payload]
    assert bus.pop() is not None
    bus.set_sync_handler(None)
    assert bus.post(Gst.Message.new_application(None, Gst.Structure.new_empty("probe")))
    assert bus.pop() is not None
    assert received == [payload]


@pytest.mark.parametrize("payload", [(), ("label",), (42, "label")])
def test_bus_message_and_notify_marshalling(payload):
    bus = Gst.Bus.new()
    received = []

    def handler(sender, event, *data):
        assert sender == bus and event.type == Gst.MessageType.APPLICATION
        received.append(data)

    bus.add_signal_watch()
    connection = bus.connect("message", handler, *payload)
    try:
        assert bus.post(Gst.Message.new_application(None, Gst.Structure.new_empty("probe")))
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(False)
        assert received == [payload]
    finally:
        bus.disconnect(connection)
        bus.remove_signal_watch()

    action = Gio.SimpleAction.new("probe", None)
    notified = []
    action.connect("notify::enabled", lambda sender, spec, *data: notified.append((spec.name, data)), *payload)
    action.set_enabled(False)
    assert notified == [("enabled", payload)]


def test_zero_argument_signal_still_receives_emitter_and_userdata():
    class Emitter(GObject.Object):
        __gsignals__ = {"ping": (GObject.SignalFlags.RUN_LAST, None, ())}

    emitter = Emitter()
    received = []
    emitter.connect("ping", lambda sender, *data: received.append((sender, data)), 42, "label")
    emitter.emit("ping")
    assert received == [(emitter, (42, "label"))]


def test_signal_rendering_has_one_userdata_pack_and_preserves_fallback():
    parsed, _ = parse_class("Gio", Gio.Application)
    assert parsed is not None
    startup = next(s for s in parsed.signals if s.name == "startup")
    assert startup.render_handler_parameters("Gio") == "[typing_extensions.Self, *UserData]"
    notify = generate_notify_signal("Gio", "enabled", "enabled", "Property documentation")
    assert notify.render_handler_parameters("Gio") == "[typing_extensions.Self, GObject.ParamSpec, *UserData]"
    TemplateManager.set_module_name("Gio")
    rendered = TemplateManager.render_master("class_signals.jinja", signals=[startup, notify])
    methods = ast.parse(rendered, feature_version=(3, 12)).body
    assert len(methods) == 3
    assert all(isinstance(m, ast.FunctionDef) and len(m.type_params) == 1 for m in methods[:2])
    fallback = methods[-1]
    assert isinstance(fallback, ast.FunctionDef) and not fallback.type_params
    assert "handler: typing.Callable[..., typing.Any]" in rendered
    assert "Property documentation" in rendered
