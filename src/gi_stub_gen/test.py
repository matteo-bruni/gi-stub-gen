# import gi

from gi_stub_gen.gi_repo import GIRepo

# from gi_stub_gen.gi_utils import gi_type_is_callback
import gi

# gi.require_version("GIRepository", "3.0")
gi.require_version("Gst", "1.0")
from gi.repository import GIRepository
from gi.repository import Gst

Gst.init(None)


repo = GIRepo()


ti_info = repo.find_by_name(
    "Gst",
    "Element",
    namespace_version="1.0",
    target_type=GIRepository.ObjectInfo,
)
assert ti_info is not None
for i in range(ti_info.get_n_signals()):
    signal_info = ti_info.get_signal(i)
    print("Signal:", signal_info.get_name())

for i in range(ti_info.get_n_fields()):
    field_info = ti_info.get_field(i)
    print("Field:", field_info.get_name())

class_to_parse.__info__, "get_fields"


# m_info = ti_info.find_method("set_use_ssl3")
# assert m_info is not None


# breakpoint()

# iterator = GIRepository.AttributeIter()
# for a in m_info.iterate_attributes(iterator):
#     if a is None:
#         break
#     if a:
#         print("Attribute:", a)


# print("Is deprecated:", m_info.is_deprecated)
# print(repo.find_by_name("Gst", "AllocationParams.align"))
# print(repo.find_by_name("Gst", "AllocationParams.align"))

# repo.find_by_gtype(GI.Boxed.__gtype__)

# GIRepository.Repository.new().find_by_gtype(GI.Boxed.__gtype__)


import importlib
import inspect


def find_gi_namespace_for_internal_class(cls):
    """
    Find the GI namespace (e.g. 'GLib') for a gi._gi internal class (e.g. OptionGroup).
    Works by identity comparison.

    TODO: add test for gi._gi.OptionGroup -> GLib.OptionGroup
    """

    # 1. If it has the correct __module__ (e.g. 'gi.repository.GLib'), use it!
    # Many overrides fix the module name.
    if cls.__module__.startswith("gi.repository."):
        return cls.__module__.split(".")[-1]

    # 2. Reverse search in Core modules
    for ns in ["GLib", "GObject", "Gio"]:
        try:
            # Import the public module (e.g. gi.repository.GLib)
            module = importlib.import_module(f"gi.repository.{ns}")

            # Check if our class 'cls' exists within this module
            # Use getattr for safety
            candidate = getattr(module, cls.__name__, None)
            if candidate is cls:
                return ns

        except (ImportError, AttributeError):
            continue

    return None


# a = find_gi_namespace_for_internal_class(gi._gi.OptionGroup)  # should return "GLib"
# print("Found namespace:", a)
# b = find_gi_namespace_for_internal_class(gi._gi.TypeInfo)  # should return "Gio"
# print("Found namespace:", b)
# breakpoint()
