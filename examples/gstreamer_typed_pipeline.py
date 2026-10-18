"""Run a typed appsrc → appsink pipeline entirely in memory."""

from typing import assert_type

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
from gi.repository import Gst, GstApp


def main() -> None:
    Gst.init(None)
    pipeline = Gst.Pipeline.new("typed-pipeline")
    source = GstApp.AppSrc()
    sink = GstApp.AppSink()
    source.props.format = Gst.Format.TIME
    source.props.is_live = True
    source.props.caps = Gst.Caps.from_string("application/octet-stream")
    sink.props.sync = False
    assert_type(source.props.caps, Gst.Caps | None)
    assert_type(sink.props.current_level_buffers, int)
    pipeline.add(source, sink)
    assert source.link(sink)
    pad = source.get_static_pad("src")
    assert pad is not None
    observed: list[str] = []

    def on_buffer(renamed_pad: Gst.Pad, info: Gst.PadProbeInfo, label: str) -> Gst.PadProbeReturn:
        assert_type(info.get_buffer(), Gst.Buffer | None)
        assert renamed_pad == pad
        observed.append(label)
        return Gst.PadProbeReturn.OK

    pad.add_probe(Gst.PadProbeType.BUFFER, on_buffer, "payload")
    payload = b"typed GStreamer pipeline"
    try:
        assert pipeline.set_state(Gst.State.PLAYING) != Gst.StateChangeReturn.FAILURE
        buffer = Gst.Buffer.new_wrapped(payload)
        assert_type(source.push_buffer(buffer), Gst.FlowReturn)
        assert source.end_of_stream() == Gst.FlowReturn.OK
        sample = sink.try_pull_sample(5 * Gst.SECOND)
        assert sample is not None, "No sample received within five seconds"
        result = sample.get_buffer()
        assert result is not None
        assert result.extract_dup(0, result.get_size()) == payload
        assert observed == ["payload"]
        bus = pipeline.get_bus()
        assert bus is not None
        message = bus.timed_pop_filtered(5 * Gst.SECOND, Gst.MessageType.ERROR | Gst.MessageType.EOS)
        assert message is not None and message.type == Gst.MessageType.EOS
    finally:
        pipeline.set_state(Gst.State.NULL)
    print("GStreamer pipeline: buffer, probe, properties and EOS verified")


if __name__ == "__main__":
    main()
