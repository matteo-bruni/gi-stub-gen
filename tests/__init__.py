import gi

try:
    gi.require_version("GioUnix", "2.0")
    gi.require_version("GIRepository", "3.0")
    gi.require_version("Gst", "1.0")
except ValueError as e:
    raise RuntimeError(f"Gi library is required: {e}")
