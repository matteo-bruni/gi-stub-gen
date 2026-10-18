"""Serializable GStreamer catalog models, with no runtime imports."""

from pydantic import BaseModel

from gi_stub_gen.schema.gobject import GTypeDescriptor, SignalDescriptor
from gi_stub_gen.schema.property import PropertyMetadata


class PadTemplateDescriptor(BaseModel):
    name_template: str
    direction: str
    presence: str
    caps: str | None
    """GStreamer caps syntax, not negotiated caps or a JSON media-format schema."""


class ElementDescriptor(BaseModel):
    name: str
    type_name: str
    plugin_name: str | None
    rank: int
    metadata: dict[str, str]
    properties: list[PropertyMetadata]
    enum_types: list[str]
    """Referenced enum/flags types; this does not imply ownership by the element."""
    pad_templates: list[PadTemplateDescriptor]
    signals: list[SignalDescriptor]


class ElementCatalog(BaseModel):
    gstreamer_version: str
    elements: list[ElementDescriptor]
    types: dict[str, GTypeDescriptor]
    """Only referenced enum/flags definitions, keyed by registered GType name."""
