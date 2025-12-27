from gi.repository import GIRepository
import gi._gi as GI  # type: ignore


def get_all_signals_flattened(
    info: GIRepository.BaseInfo,
) -> list[GIRepository.SignalInfo]:
    """
    Recursively fetch all signals for a given GI Info.
    Handles both:
    - Objects (traversing parent hierarchy and implemented interfaces)
    - Interfaces (fetching only their own signals, as they don't have parents)
    """
    # Use a dictionary to avoid duplicates (keys are signal names)
    collected_signals: dict[str, GIRepository.SignalInfo] = {}

    current = info

    while current is not None:
        # 1. Collect signals defined directly on the current element (Class or Interface)
        if hasattr(current, "get_signals"):
            for sig in current.get_signals():  # type: ignore
                name = sig.get_name()
                if name not in collected_signals:
                    collected_signals[name] = sig

        # 2. Logic for Classes (ObjectInfo)
        if isinstance(current, (GIRepository.ObjectInfo, GI.ObjectInfo)):
            # A class implements interfaces: we must grab their signals too.
            # (e.g., Gtk.Editable signals for a Gtk.Entry)
            for iface in current.get_interfaces():  # type: ignore
                for sig in iface.get_signals():
                    name = sig.get_name()
                    if name not in collected_signals:
                        collected_signals[name] = sig

            assert hasattr(current, "get_parent"), (
                f"Expected ObjectInfo to have get_parent method, got {type(current).__name__}"
            )
            # Move up the inheritance chain (e.g., Gtk.Button -> Gtk.Bin -> ... -> GObject)
            current = current.get_parent()  # type: ignore

        # 3. Logic for Interfaces (InterfaceInfo)
        elif isinstance(current, (GIRepository.InterfaceInfo, GI.InterfaceInfo)):
            # Interfaces do not inherit from other classes via 'get_parent'.
            # We collected their signals in step 1, now we stop to avoid AttributeError.
            current = None

        # 4. Logic for other types (Structs, etc.)
        else:
            current = None

    return list(collected_signals.values())
