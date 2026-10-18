import subprocess
import sys

from gi.repository import GObject
import pytest

from gi_stub_gen.parser.gobject import describe_signals, describe_type
from gi_stub_gen.parser.gstreamer import describe_catalog
from gi_stub_gen.schema.gstreamer import ElementCatalog


@pytest.fixture(scope="module")
def catalog():
    return describe_catalog(["videotestsrc", "appsrc", "fakesrc", "identity", "tee", "decodebin", "playbin"])


def test_shared_enum_types_and_reference_integrity(catalog):
    elements = {element.name: element for element in catalog.elements}
    for name in ("appsrc", "fakesrc"):
        element = elements[name]
        assert "GstFormat" in element.enum_types
        assert next(prop for prop in element.properties if prop.name == "format").value_type == "GstFormat"
    assert catalog.types["GstFormat"].fundamental == "GEnum"
    assert any(value.nick == "time" for value in catalog.types["GstFormat"].values)
    flags = next(prop for prop in elements["playbin"].properties if prop.name == "flags")
    assert catalog.types[flags.value_type].fundamental == "GFlags"
    assert catalog.types[flags.value_type].values
    assert set(catalog.types) == {name for element in catalog.elements for name in element.enum_types}
    assert not {"guint", "void", "GEnum", "GFlags", "GObject", "GstBuffer"} & catalog.types.keys()
    for element in catalog.elements:
        assert set(element.enum_types) <= catalog.types.keys()
        for prop in element.properties:
            assert "values" not in prop.model_dump()
    for descriptor in catalog.types.values():
        assert descriptor.fundamental in ("GEnum", "GFlags")
    assert ElementCatalog.model_validate_json(catalog.model_dump_json()) == catalog


def test_pad_templates_metadata_and_enum_values(catalog):
    elements = {element.name: element for element in catalog.elements}
    video = elements["videotestsrc"]
    assert video.plugin_name == "videotestsrc"
    assert "Source/Video" in video.metadata["klass"]
    assert video.type_name == "GstVideoTestSrc"
    pad = next(pad for pad in video.pad_templates if pad.name_template == "src")
    assert (pad.direction, pad.presence) == ("src", "always")
    assert pad.caps is not None and "video/x-raw" in pad.caps
    pattern = catalog.types["GstVideoTestSrcPattern"]
    assert pattern.values is not None and any(value.nick == "smpte" for value in pattern.values)
    assert any(pad.presence == "request" and pad.name_template == "src_%u" for pad in elements["tee"].pad_templates)
    assert any(pad.presence == "sometimes" for pad in elements["decodebin"].pad_templates)


def test_own_inherited_interface_and_action_signals(catalog):
    elements = {element.name: element for element in catalog.elements}
    signals = {signal.name: signal for signal in elements["identity"].signals}
    assert signals["handoff"].owner_type == "GstIdentity"
    assert signals["handoff"].parameter_types == ["GstBuffer"]
    assert signals["handoff"].return_type == "void"
    assert signals["notify"].owner_type == "GObject" and signals["notify"].detailed
    assert signals["pad-added"].owner_type == "GstElement"
    assert any(signal.action and signal.name == "push-buffer" for signal in elements["appsrc"].signals)
    assert any(signal.owner_type == "GstChildProxy" for signal in elements["decodebin"].signals)
    select_result = catalog.types["GstAutoplugSelectResult"]
    assert select_result.values is not None
    assert {value.nick for value in select_result.values} >= {"try", "expose", "skip"}


def test_selected_catalog_is_order_independent_and_missing_factory_is_explicit():
    assert describe_catalog(["identity", "videotestsrc", "identity"]) == describe_catalog(["videotestsrc", "identity"])
    with pytest.raises(ValueError, match="not installed"):
        describe_catalog(["gi-stub-gen-nonexistent-element"])
    with pytest.raises(ValueError, match="invalid GType"):
        describe_type(GObject.TYPE_INVALID)
    with pytest.raises(TypeError, match="GObject type"):
        describe_signals(GObject.TYPE_INT)


def test_generic_runtime_parser_does_not_import_gstreamer():
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import gi
from gi_stub_gen.parser.gobject import describe_type
from gi_stub_gen.parser.property import describe_property
assert gi.get_required_version('Gst') is None
""",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_signal_collection_initializes_the_class_without_an_instance():
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
from gi_stub_gen.parser.gobject import describe_signals, describe_type
Gst.init(None)
factory = Gst.ElementFactory.find('identity').load()
signals = describe_signals(factory.get_element_type())
assert any(signal.name == 'handoff' for signal in signals)
from gi.repository import GObject
factory = Gst.ElementFactory.find('decodebin').load()
describe_signals(factory.get_element_type())
gtype = GObject.type_from_name('GstAutoplugSelectResult')
assert gtype.pytype is None
assert {value.nick for value in describe_type(gtype).values} >= {'try', 'expose', 'skip'}
""",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
