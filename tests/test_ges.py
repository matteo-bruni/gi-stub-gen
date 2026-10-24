"""GES initialization is opt-in; native GES objects use the normal parser."""

from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import gi
import pytest

from gi_stub_gen.cli import gi_stub_gen as cli
from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.class_ import create_init_method, parse_class


@pytest.mark.parametrize(
    ("names", "preload", "expected"),
    (
        (["Gio"], None, []),
        (["Gst"], None, ["Gst"]),
        (["GES"], None, ["Gst", "GES"]),
        (["GES", "Gst"], None, ["Gst", "GES", "Gst"]),
        (["Gio"], ["GES"], ["Gst", "GES"]),
    ),
)
def test_cli_initializes_ges_only_when_requested(monkeypatch, tmp_path, names, preload, expected):
    initialized = []
    loaded = []

    def load(module_name, gi_version):
        namespace = module_name.removeprefix("gi.repository.")
        loaded.append(namespace)
        module = ModuleType(module_name)
        if namespace == "Gst":
            setattr(module, "init", lambda args: initialized.append("Gst"))
        elif namespace == "GES":
            assert "Gst" in initialized
            setattr(module, "init", lambda: initialized.append("GES") or True)
        return module

    monkeypatch.setattr(cli, "get_gi_module_from_name", load)
    monkeypatch.setattr(cli, "GIRepo", Mock())
    monkeypatch.setattr("gi_stub_gen.parser.module.parse_module", Mock(return_value=(Mock(render_stub=lambda **kw: ""), {})))
    monkeypatch.setattr("gi_stub_gen.package.create_stub_package", Mock())
    monkeypatch.setattr(cli, "format_stub_with_ruff", lambda **kw: "")
    cli.main(
        name=[f"gi.repository.{name}:1.0" for name in names],
        preload=[f"gi.repository.{name}:1.0" for name in preload] if preload else None,
        pkg_name="init-probe",
        pkg_version="1.0",
        output=tmp_path,
    )
    assert initialized == expected
    if "GES" not in names and not preload:
        assert "GES" not in loaded


def test_cli_reports_ges_initialization_failure(monkeypatch, tmp_path):
    gst, ges = Mock(), Mock()
    ges.init.return_value = False
    monkeypatch.setattr(cli, "get_gi_module_from_name", lambda module_name, gi_version: gst if module_name.endswith("Gst") else ges)
    monkeypatch.setattr(cli, "GIRepo", Mock())
    with pytest.raises(RuntimeError, match="Could not initialize GES"):
        cli.main(name=["gi.repository.GES:1.0"], pkg_name="init-probe", pkg_version="1.0", output=tmp_path)
    gst.init.assert_called_once_with(None)


@pytest.fixture
def ges():
    gi.require_version("Gst", "1.0")
    try:
        gi.require_version("GES", "1.0")
    except ValueError:
        pytest.skip("GES-1.0 typelib is not installed")
    from gi.repository import GES, Gst

    Gst.init(None)
    assert GES.init()
    return GES


def test_ges_timeline_properties_and_inheritance(ges):
    docs = GIRDocs()
    assert docs.load(Path("/usr/share/gir-1.0/GES-1.0.gir"))
    timeline, _ = parse_class("GES", ges.Timeline, docs=docs)
    clip, _ = parse_class("GES", ges.TestClip, docs=docs)
    assert timeline is not None and clip is not None
    assert "Gst.Bin" in timeline.super
    assert {"Extractable", "MetaContainer"} <= set(timeline.super)
    constructor = next(method for method in timeline.methods if method.name == "new_audio_video")
    assert constructor.render_return_annotation("GES") == "Timeline"
    assert constructor.docstring
    TemplateManager.set_module_name("GES")
    rendered = clip.render_stub()
    assert "duration: int" in rendered


def test_ges_timeline_in_memory(ges):
    from gi.repository import Gst

    timeline = ges.Timeline.new_audio_video()
    layer = timeline.append_layer()
    clip = ges.TestClip.new()
    assert clip is not None
    clip.props.duration = Gst.SECOND
    assert layer.add_clip(clip)
    assert clip.props.duration == Gst.SECOND
    assert clip.get_layer() == layer
    assert len(timeline.get_tracks()) == 2
    assert len(clip.get_children(False)) == 2


@pytest.mark.parametrize(("namespace", "expected"), (("GES", "TrackType(1)"), ("Gst", "GES.TrackType(1)")))
def test_ges_flag_default_when_name_is_a_method(ges, namespace, expected):
    assert callable(ges.TrackType.UNKNOWN.name)
    constructor = create_init_method(namespace, ges.AudioSource)
    assert constructor is not None
    argument = next(arg for arg in constructor.args if arg.name == "track_type")
    assert argument.default_value == expected
