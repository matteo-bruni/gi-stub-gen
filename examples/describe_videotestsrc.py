"""Run in the devcontainer: uv run --group gst --locked python examples/describe_videotestsrc.py."""

import json

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

from gi_stub_gen.parser.gstreamer import describe_catalog  # noqa: E402


def main() -> None:
    Gst.init(None)
    catalog = describe_catalog(["videotestsrc"])
    print(json.dumps(catalog.model_dump(mode="json"), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
