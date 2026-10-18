import json
import subprocess
import sys
from types import SimpleNamespace
from typing import ClassVar, cast

from gi.repository import GObject, Gst
from pydantic import ValidationError
import pytest

from gi_stub_gen.parser.property import describe_properties, describe_property
from gi_stub_gen.schema.property import PropertyDefault, PropertyDescriptor
from gi_stub_gen.schema.gstreamer import ElementCatalog


class PropertyBase(GObject.Object):
    __gtype__: ClassVar[GObject.GType]
    count = GObject.Property(type=int, minimum=-2, maximum=12, default=3)
    label = GObject.Property(type=GObject.Object, default=None)


class PropertyChild(PropertyBase):
    mode = GObject.Property(type=Gst.BufferFlags, default=Gst.BufferFlags.LIVE | Gst.BufferFlags.DISCONT)
    readonly = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    initial = GObject.Property(
        type=int,
        default=0,
        flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY,
    )
    constructed = GObject.Property(
        type=int, default=0, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT
    )


def test_inherited_properties_flags_defaults_and_roundtrip():
    descriptions = describe_properties(PropertyChild.__gtype__)
    props = {prop.name: prop for prop in descriptions}
    count = props["count"]
    assert count.owner_type == PropertyBase.__gtype__.name
    assert count.value_type == "gint"
    assert (count.minimum, count.maximum, count.default.value, count.nullable) == (-2, 12, 3, False)
    assert props["label"].default == PropertyDefault(status="available", value=None)
    assert props["label"].nullable is True
    assert props["readonly"].is_readable and not props["readonly"].is_writable
    assert props["initial"].is_construct_only
    assert props["constructed"].is_construct and not props["constructed"].is_construct_only
    assert props["mode"].default.value == int(Gst.BufferFlags.LIVE | Gst.BufferFlags.DISCONT)
    live = next(value for value in props["mode"].values if value.value == int(Gst.BufferFlags.LIVE))
    assert (live.name, live.nick) == ("GST_BUFFER_FLAG_LIVE", "live")
    for description in descriptions:
        assert PropertyDescriptor.model_validate_json(description.model_dump_json()) == description
        json.dumps(description.model_dump(mode="json"), allow_nan=False)


def _spec(get_default, value_type=GObject.TYPE_STRING, flags=GObject.ParamFlags.READWRITE) -> GObject.ParamSpec:
    # Test double for defaults that cannot be constructed through the native binding.
    return cast(
        GObject.ParamSpec,
        SimpleNamespace(
            name="some-value",
            flags=int(flags),
            value_type=value_type,
            owner_type=PropertyBase.__gtype__,
            get_blurb=lambda: "Description",
            get_default_value=get_default,
        ),
    )


def test_default_states_do_not_conflate_null_with_missing_or_native_values():
    def unavailable():
        raise TypeError("Binding cannot expose the default")

    class NativeValue:
        def __repr__(self):
            raise AssertionError("Native values must not be serialized through repr")

    deprecated_spec = _spec(lambda: None, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.DEPRECATED)
    assert describe_property(deprecated_spec).is_deprecated
    missing = describe_property(_spec(unavailable))
    assert missing.default.status == "unavailable" and missing.nullable is None
    unsupported = describe_property(_spec(lambda: NativeValue()))
    assert unsupported.default.status == "unsupported" and unsupported.nullable is None
    known = describe_property(_spec(lambda: "hello"))
    assert known.default.value == "hello" and known.nullable is None
    assert known.python_name == "some_value" and known.description == "Description"
    assert describe_property(_spec(lambda: float("nan"), GObject.TYPE_DOUBLE)).default.status == "unsupported"
    with pytest.raises(ValidationError):
        PropertyDefault(status="unavailable", value=3)
    with pytest.raises(ValidationError):
        PropertyDefault.model_validate({"status": "available", "value": NativeValue()})
    with pytest.raises(ValidationError):
        PropertyDefault(status="available", value=float("inf"))


def test_base_interface_is_rejected_before_native_introspection():
    with pytest.raises(TypeError, match="GInterface"):
        describe_properties(GObject.TYPE_INTERFACE)


def test_models_import_without_gi_or_rendering_dependencies():
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from importlib.abc import MetaPathFinder
class BlockRuntime(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'gi', 'rich', 'jinja2'}:
            raise ImportError(fullname)
sys.meta_path.insert(0, BlockRuntime())
from gi_stub_gen.schema.property import PropertyDescriptor, PropertyDefault
from gi_stub_gen.schema.gstreamer import ElementCatalog
assert PropertyDefault(status='available', value=None).model_dump_json()
assert PropertyDescriptor.model_json_schema()
assert ElementCatalog.model_json_schema()
""",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_videotestsrc_runtime_catalog_and_example():
    factory = Gst.ElementFactory.find("videotestsrc")
    assert factory is not None
    loaded = factory.load()
    assert isinstance(loaded, Gst.ElementFactory)
    props = {prop.name: prop for prop in describe_properties(loaded.get_element_type())}
    count = props["num-buffers"]
    assert count.python_name == "num_buffers" and count.owner_type == "GstBaseSrc"
    assert count.maximum is not None
    assert count.default.value == -1 and count.minimum == -1 and count.maximum >= 1
    assert count.is_readable and count.is_writable and not count.is_construct_only
    pattern = props["pattern"]
    assert pattern.value_type == "GstVideoTestSrcPattern" and pattern.owner_type == "GstVideoTestSrc"
    assert pattern.default.value == 0
    assert next(value for value in pattern.values if value.value == 0).nick == "smpte"
    assert props["is-live"].default.value is False and props["is-live"].nullable is False
    assert props["name"].owner_type == "GstObject"
    result = subprocess.run(
        [sys.executable, "examples/describe_videotestsrc.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    catalog = ElementCatalog.model_validate_json(result.stdout)
    serialized = catalog.elements[0].properties
    assert {prop.name: prop.model_dump() for prop in serialized} == {
        name: prop.model_dump(exclude={"values"}) for name, prop in props.items()
    }
    assert catalog.types[pattern.value_type].values == pattern.values
