import sys
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

Gst.init()


class GstTester:
    def __init__(self):
        # 1. Test Constructor and Inheritance
        # If the stubs for Bin are correct, this should not give an error
        self.pipeline = Gst.Pipeline.new("test-pipeline")

        # 2. Test Factory (static/global methods)
        self.src = Gst.ElementFactory.make("fakesrc", "source")
        self.sink = Gst.ElementFactory.make("fakesink", "sink")

        if not self.src or not self.sink:
            print("Elements not created properly")
            sys.exit(1)

        # 3. Test mapped class methods (Gst.Bin.add)
        # If the docstring translation worked, the IDE should suggest .add()
        self.pipeline.add(self.src)
        self.pipeline.add(self.sink)

        # Link
        self.src.link(self.sink)

    def setup_probes(self):
        assert self.src is not None, "Source element is None"
        pad = self.src.get_static_pad("src")
        if pad is None:
            return

        # --- CRITICAL TEST: add_probe and user_data ---

        # CASE A: No user_data
        # Expected stub: callback(pad, info)
        pad.add_probe(Gst.PadProbeType.BUFFER, self.probe_simple)

        # CASE B: One user_data (String)
        # Expected stub: callback(pad, info, user_data)
        pad.add_probe(Gst.PadProbeType.BUFFER, self.probe_with_data, "MyStringData")

        # CASE C: Multiple user_data (Variadic)
        # Expected stub: callback(pad, info, *args)
        # This only works if you put *user_data in the stub!
        pad.add_probe(Gst.PadProbeType.BUFFER, self.probe_multi_data, "Part1", 123, {"key": "val"})

        # CASE D: Explicit None (if you used object | None)
        pad.add_probe(Gst.PadProbeType.BUFFER, self.probe_with_none, None)

    # --- CALLBACKS ---

    def probe_simple(self, pad: Gst.Pad, info: Gst.PadProbeInfo) -> Gst.PadProbeReturn:
        print("Probe Simple called")
        return Gst.PadProbeReturn.OK

    def probe_with_data(self, pad: Gst.Pad, info: Gst.PadProbeInfo, user_data: str) -> Gst.PadProbeReturn:
        # If the stub is correct, the IDE knows that 'user_data' is str
        print(f"Probe Data: {user_data.upper()}")
        return Gst.PadProbeReturn.OK

    def probe_multi_data(
        self, pad: Gst.Pad, info: Gst.PadProbeInfo, arg1: str, arg2: int, arg3: dict
    ) -> Gst.PadProbeReturn:
        print(f"Probe Multi: {arg1}, {arg2}, {arg3}")
        return Gst.PadProbeReturn.OK

    def probe_with_none(self, pad: Gst.Pad, info: Gst.PadProbeInfo, user_data: object | None) -> Gst.PadProbeReturn:
        print("Probe None")
        return Gst.PadProbeReturn.OK


if __name__ == "__main__":
    t = GstTester()
    t.setup_probes()
    print("GStreamer Test Syntax OK")
