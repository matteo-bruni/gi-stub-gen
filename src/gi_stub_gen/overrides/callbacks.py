"""Limit precise callbacks to verified call sites; signatures still come from GI.

The source-object specialization is verified per call site: AsyncReadyCallback
itself only describes a generic object, not necessarily the caller's class.
"""

PRECISE_CALLBACKS = {
    ("Gst", "Pad", "add_probe"): ("PadProbeCallback", None),
    ("Gio", "File", "load_contents_async"): ("AsyncReadyCallback", "File"),
    ("Gio", "InputStream", "read_bytes_async"): ("AsyncReadyCallback", "InputStream"),
}
