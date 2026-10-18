"""GStreamer-specific factory and pad introspection; never used by the stub pipeline."""

from collections.abc import Iterable

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GObject, Gst  # noqa: E402

from gi_stub_gen.parser.gobject import describe_signals, describe_type  # noqa: E402
from gi_stub_gen.parser.property import describe_properties  # noqa: E402
from gi_stub_gen.schema.gobject import GTypeDescriptor  # noqa: E402
from gi_stub_gen.schema.gstreamer import ElementCatalog, ElementDescriptor, PadTemplateDescriptor  # noqa: E402
from gi_stub_gen.schema.property import PropertyMetadata  # noqa: E402


def describe_element(factory: Gst.ElementFactory) -> ElementDescriptor:
    """Load a factory and inspect its class, without creating an element instance."""
    loaded = factory.load()
    if not isinstance(loaded, Gst.ElementFactory):
        raise RuntimeError(f"Cannot load element factory {factory.get_name()}")
    gtype = loaded.get_element_type()
    if gtype == GObject.TYPE_INVALID or not gtype.is_a(GObject.type_from_name("GstElement")):
        raise ValueError(f"Factory {factory.get_name()} has no usable element GType")
    properties = describe_properties(gtype)
    signals = describe_signals(gtype)
    referenced_types = {prop.value_type for prop in properties}
    for signal in signals:
        referenced_types.add(signal.return_type)
        referenced_types.update(signal.parameter_types)
    metadata = {}
    for key in sorted(loaded.get_metadata_keys() or []):
        value = loaded.get_metadata(key)
        if value is not None:
            metadata[key] = value
    pads = []
    for template in loaded.get_static_pad_templates():
        caps = template.get_caps()
        pads.append(
            PadTemplateDescriptor(
                name_template=template.name_template,
                direction=template.direction.value_nick,
                presence=template.presence.value_nick,
                caps=caps.to_string() if caps is not None else None,
            )
        )
    name = loaded.get_name()
    if name is None:
        raise ValueError("Loaded element factory has no name")
    return ElementDescriptor(
        name=name,
        type_name=gtype.name,
        plugin_name=loaded.get_plugin_name(),
        rank=loaded.get_rank(),
        metadata=metadata,
        properties=[PropertyMetadata.model_validate(prop.model_dump(exclude={"values"})) for prop in properties],
        enum_types=sorted(
            name
            for name in referenced_types
            if GObject.type_from_name(name).fundamental in (GObject.TYPE_ENUM, GObject.TYPE_FLAGS)
        ),
        pad_templates=sorted(pads, key=lambda pad: (pad.name_template, pad.direction)),
        signals=signals,
    )


def describe_catalog(element_names: Iterable[str]) -> ElementCatalog:
    """Describe selected installed factories and deduplicate referenced enum/flags types.

    Call Gst.init first. This does not scan the registry for additional elements.
    """
    elements = []
    types: dict[str, GTypeDescriptor] = {}

    for name in sorted(set(element_names)):
        factory = Gst.ElementFactory.find(name)
        if factory is None:
            raise ValueError(f"Element factory {name!r} is not installed")
        element = describe_element(factory)
        elements.append(element)
        for type_name in element.enum_types:
            if type_name not in types:
                types[type_name] = describe_type(GObject.type_from_name(type_name))
    return ElementCatalog(
        gstreamer_version=Gst.version_string(),
        elements=elements,
        types=dict(sorted(types.items())),
    )
