"""Describe runtime ParamSpecs, not GI PropertyInfo declarations."""

import math

from gi.repository import GObject

from gi_stub_gen.parser.gobject import describe_enum_values
from gi_stub_gen.schema.property import PropertyDefault, PropertyDescriptor, PropertyValue
from gi_stub_gen.utils.utils import sanitize_variable_name


def _describe_default(param_spec: GObject.ParamSpec) -> PropertyDefault:
    try:
        value = param_spec.get_default_value()
    except (AttributeError, TypeError, ValueError, NotImplementedError):
        return PropertyDefault(status="unavailable")
    if value is None or type(value) in (bool, int, str):
        return PropertyDefault(status="available", value=value)
    if type(value) is float and math.isfinite(value):
        return PropertyDefault(status="available", value=value)
    if isinstance(value, int) and param_spec.value_type.fundamental in (GObject.TYPE_ENUM, GObject.TYPE_FLAGS):
        return PropertyDefault(status="available", value=int(value))
    return PropertyDefault(status="unsupported")


def _numeric_limit(param_spec: GObject.ParamSpec, name: str) -> int | float | None:
    value = getattr(param_spec, name, None)
    if type(value) is int or (type(value) is float and math.isfinite(value)):
        return value
    return None


def _describe_values(param_spec: GObject.ParamSpec) -> list[PropertyValue]:
    fundamental = param_spec.value_type.fundamental
    # PyGObject exposes Python enum classes dynamically, unlike the native GI fields.
    if fundamental == GObject.TYPE_ENUM:
        enum_class: type[GObject.GEnum] = getattr(param_spec, "enum_class")
        return describe_enum_values(enum_class)
    if fundamental == GObject.TYPE_FLAGS:
        flags_class: type[GObject.GFlags] = getattr(param_spec, "flags_class")
        return describe_enum_values(flags_class)
    return []


def describe_property(param_spec: GObject.ParamSpec) -> PropertyDescriptor:
    """Read a ParamSpec into JSON-safe metadata, without importing its namespace."""
    name, _ = sanitize_variable_name(param_spec.name)
    flags = int(param_spec.flags)
    default = _describe_default(param_spec)
    fundamental = param_spec.value_type.fundamental
    numeric_types = {
        GObject.TYPE_BOOLEAN,
        GObject.TYPE_CHAR,
        GObject.TYPE_UCHAR,
        GObject.TYPE_INT,
        GObject.TYPE_UINT,
        GObject.TYPE_LONG,
        GObject.TYPE_ULONG,
        GObject.TYPE_INT64,
        GObject.TYPE_UINT64,
        GObject.TYPE_FLOAT,
        GObject.TYPE_DOUBLE,
        GObject.TYPE_ENUM,
        GObject.TYPE_FLAGS,
    }
    nullable = False if fundamental in numeric_types else None
    if nullable is None and default.status == "available" and default.value is None:
        nullable = True
    return PropertyDescriptor(
        name=param_spec.name,
        python_name=name,
        description=param_spec.get_blurb() or None,
        value_type=param_spec.value_type.name,
        owner_type=param_spec.owner_type.name,
        flags=flags,
        is_readable=bool(flags & GObject.ParamFlags.READABLE),
        is_writable=bool(flags & GObject.ParamFlags.WRITABLE),
        is_construct=bool(flags & GObject.ParamFlags.CONSTRUCT),
        is_construct_only=bool(flags & GObject.ParamFlags.CONSTRUCT_ONLY),
        is_deprecated=bool(flags & GObject.ParamFlags.DEPRECATED),
        default=default,
        minimum=_numeric_limit(param_spec, "minimum"),
        maximum=_numeric_limit(param_spec, "maximum"),
        values=_describe_values(param_spec),
        nullable=nullable,
    )


def describe_properties(gtype: GObject.GType) -> list[PropertyDescriptor]:
    """Return own and inherited type properties, without creating an instance."""
    if gtype == GObject.TYPE_INTERFACE:
        # PyGObject can segfault when asked for properties of GInterface itself.
        raise TypeError("The base GInterface type cannot be inspected for properties")
    return [describe_property(spec) for spec in sorted(GObject.list_properties(gtype), key=lambda spec: spec.name)]
