"""GObject runtime metadata, independent of GStreamer and stub rendering."""

from collections.abc import Callable
from importlib import import_module

from gi.repository import GObject

from gi_stub_gen.schema.gobject import GTypeDescriptor, SignalDescriptor
from gi_stub_gen.schema.property import PropertyValue


def describe_enum_values(enum_class: type[GObject.GEnum] | type[GObject.GFlags]) -> list[PropertyValue]:
    """Read the members exposed by the Python enum/flags wrapper."""
    if issubclass(enum_class, GObject.GEnum):
        return [
            PropertyValue(value=int(member), name=member.value_name, nick=member.value_nick)
            for member in enum_class.__members__.values()
        ]
    values = []
    for member in enum_class.__members__.values():
        names, nicks = member.value_names, member.value_nicks
        # A composite mask can expose only its constituents, not its registered name.
        values.append(
            PropertyValue(
                value=int(member),
                name=names[0] if len(names) == 1 else None,
                nick=nicks[0] if len(nicks) == 1 else None,
            )
        )
    return values


def describe_type(gtype: GObject.GType) -> GTypeDescriptor:
    """Describe a registered type using names, never process-local numeric IDs."""
    if gtype == GObject.TYPE_INVALID:
        raise ValueError("Cannot describe an invalid GType")
    pytype = gtype.pytype
    # Same fallback used by PyGObject's ParamSpecEnum/Flags overrides (3.56+).
    fundamental = gtype.fundamental
    if pytype is None and gtype != fundamental and fundamental in (GObject.TYPE_ENUM, GObject.TYPE_FLAGS):
        # The compiled extension has no stubs; type its constructor at this native boundary.
        constructor: Callable[[None, str, GObject.GType, None], type[GObject.GEnum] | type[GObject.GFlags]] = getattr(
            import_module("gi._gi"), "enum_add" if fundamental == GObject.TYPE_ENUM else "flags_add"
        )
        pytype = constructor(None, gtype.name, gtype, None)
    values = None
    if pytype is not None and issubclass(pytype, (GObject.GEnum, GObject.GFlags)):
        values = describe_enum_values(pytype)
    return GTypeDescriptor(
        name=gtype.name,
        fundamental=gtype.fundamental.name,
        parent=gtype.parent.name if gtype.parent != GObject.TYPE_INVALID else None,
        interfaces=sorted(interface.name for interface in gtype.interfaces),
        values=values,
    )


def describe_signals(gtype: GObject.GType) -> list[SignalDescriptor]:
    """Describe an object's own, inherited and interface signals without instantiation."""
    if not gtype.is_a(GObject.TYPE_OBJECT):
        raise TypeError("Signal collection requires a GObject type")
    # Class initialization registers signals, even when no instance has ever existed.
    type_class = GObject.type_class_ref(gtype)
    try:
        pending = [gtype]
        seen_types: set[str] = set()
        signals: dict[int, SignalDescriptor] = {}
        while pending:
            current = pending.pop()
            if current.name in seen_types:
                continue
            seen_types.add(current.name)
            pending.extend(current.interfaces)
            if current.parent != GObject.TYPE_INVALID:
                pending.append(current.parent)
            for signal_id in GObject.signal_list_ids(current):
                query = GObject.signal_query(signal_id)
                if query is None:
                    continue
                signals[signal_id] = SignalDescriptor(
                    name=query.signal_name,
                    owner_type=query.itype.name,
                    flags=int(query.signal_flags),
                    detailed=bool(query.signal_flags & GObject.SignalFlags.DETAILED),
                    action=bool(query.signal_flags & GObject.SignalFlags.ACTION),
                    return_type=query.return_type.name,
                    parameter_types=[parameter.name for parameter in query.param_types or ()],
                )
        return sorted(signals.values(), key=lambda signal: (signal.name, signal.owner_type))
    finally:
        type_class.unref()
