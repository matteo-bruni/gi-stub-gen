import pytest


# from gi.repository import GIRepository  # noqa: E402
from gi.repository import Gst


@pytest.fixture(scope="session", autouse=True)
def init_gst():
    """
    Initialize GStreamer for tests that need it.
    """
    print("Initializing GStreamer...")
    Gst.init(None)
    return
