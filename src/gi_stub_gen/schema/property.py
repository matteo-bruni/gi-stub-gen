"""Serializable property metadata, independent of GI and stub rendering."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PropertyDefault(BaseModel):
    model_config = ConfigDict(strict=True, allow_inf_nan=False)

    status: Literal["available", "unavailable", "unsupported"]
    value: bool | int | float | str | None = None

    @model_validator(mode="after")
    def check_unavailable_value(self) -> Self:
        if self.status != "available" and self.value is not None:
            raise ValueError("Only an available default can contain a value")
        return self


class PropertyValue(BaseModel):
    """One registered enum/flags value; absent native names remain unknown."""

    value: int
    name: str | None
    nick: str | None


class PropertyMetadata(BaseModel):
    """Property constraints; value_type is the registered GType name."""

    model_config = ConfigDict(strict=True, allow_inf_nan=False)

    name: str
    python_name: str
    description: str | None
    value_type: str
    owner_type: str
    flags: int
    is_readable: bool
    is_writable: bool
    is_construct: bool
    is_construct_only: bool
    is_deprecated: bool
    default: PropertyDefault
    minimum: int | float | None = None
    maximum: int | float | None = None
    nullable: bool | None = None
    """True/False when known; None means ParamSpec does not establish it."""


class PropertyDescriptor(PropertyMetadata):
    """Standalone property description, including its enum/flags values."""

    values: list[PropertyValue] = Field(default_factory=list)
