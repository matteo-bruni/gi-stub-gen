import sys
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib  # noqa: E402

# Inizializzazione
Gst.init()


class GstTester:
    def __init__(self):
        # 1. Test Costruttore e Inheritance
        # Se gli stub di Bin sono corretti, questo non deve dare errore
        self.pipeline = Gst.Pipeline.new("test-pipeline")

        # 2. Test Factory (metodi statici/globali)
        self.src = Gst.ElementFactory.make("fakesrc", "source")
        self.sink = Gst.ElementFactory.make("fakesink", "sink")

        if not self.src or not self.sink:
            print("Elementi non creati")
            sys.exit(1)

        # 3. Test metodi di classe mappati (Gst.Bin.add)
        # Se la docstring translation ha funzionato, l'IDE deve suggerire .add()
        self.pipeline.add(self.src)
        self.pipeline.add(self.sink)

        # Link
        self.src.link(self.sink)

    def setup_probes(self):
        assert self.src is not None, "Source element is None"
        pad = self.src.get_static_pad("src")
        if pad is None:
            return

        # --- TEST CRITICO: add_probe e user_data ---

        # CASO A: Nessun user_data
        # Stub atteso: callback(pad, info)
        pad.add_probe(Gst.PadProbeType.BUFFER, self.probe_simple)

        # CASO B: Un user_data (Stringa)
        # Stub atteso: callback(pad, info, user_data)
        pad.add_probe(Gst.PadProbeType.BUFFER, self.probe_with_data, "MyStringData")

        # CASO C: Molteplici user_data (Variadic)
        # Stub atteso: callback(pad, info, *args)
        # Questo funziona solo se hai messo *user_data nello stub!
        pad.add_probe(Gst.PadProbeType.BUFFER, self.probe_multi_data, "Part1", 123, {"key": "val"})

        # CASO D: Explicit None (se hai usato object | None)
        pad.add_probe(Gst.PadProbeType.BUFFER, self.probe_with_none, None)

    # --- CALLBACKS ---

    def probe_simple(self, pad: Gst.Pad, info: Gst.PadProbeInfo) -> Gst.PadProbeReturn:
        print("Probe Simple chiamata")
        return Gst.PadProbeReturn.OK

    def probe_with_data(self, pad: Gst.Pad, info: Gst.PadProbeInfo, user_data: str) -> Gst.PadProbeReturn:
        # Se lo stub è corretto, l'IDE sa che 'data' è str
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
