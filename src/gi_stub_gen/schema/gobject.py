"""JSON-safe runtime type and signal descriptions; no GI imports."""

from pydantic import BaseModel

from gi_stub_gen.schema.property import PropertyValue


class GTypeDescriptor(BaseModel):
    name: str
    fundamental: str
    parent: str | None
    interfaces: list[str]
    values: list[PropertyValue] | None = None
    """Enum/flags members when available; None means unavailable or not applicable."""


class SignalDescriptor(BaseModel):
    name: str
    owner_type: str
    flags: int
    detailed: bool
    action: bool
    return_type: str
    parameter_types: list[str]
    """Explicit native parameters, excluding the instance and callback user data."""
