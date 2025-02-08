import gi._gi as GIRepository  # type: ignore
from gi._gi import Repository
from gi.repository import GObject
from typing import Sequence, Mapping

repository = Repository.get_default()

# references
# https://amolenaar.pages.gitlab.gnome.org/pygobject-docs/Gst-1.0/functions.html#gi.repository.Gst.init
# https://gstreamer.freedesktop.org/documentation/gstreamer/gst.html?gi-language=python#gst_init
# https://valadoc.org/gstreamer-1.0/Gst.init.html

map_gi_tag_to_type = {
    # bool
    GIRepository.TypeTag.BOOLEAN: bool,
    # int
    GIRepository.TypeTag.INT8: int,
    GIRepository.TypeTag.INT16: int,
    GIRepository.TypeTag.INT32: int,
    GIRepository.TypeTag.INT64: int,  # 8
    GIRepository.TypeTag.UINT8: int,
    GIRepository.TypeTag.UINT16: int,
    GIRepository.TypeTag.UINT32: int,
    GIRepository.TypeTag.UINT64: int,  # 9
    # float
    GIRepository.TypeTag.FLOAT: float,  # 10
    GIRepository.TypeTag.DOUBLE: float,  # 11
    # str
    GIRepository.TypeTag.UTF8: str,  # 13
    GIRepository.TypeTag.FILENAME: str,  # 14
    GIRepository.TypeTag.UNICHAR: str,  # 21
    # map
    GIRepository.TypeTag.GHASH: dict,  # 19 or dict?Mapping
    # list
    GIRepository.TypeTag.GLIST: list,  # 17 or list?Sequence
    GIRepository.TypeTag.GSLIST: list,  # 18 or list?Sequence
    GIRepository.TypeTag.ARRAY: list,  # 15 or list? Sequence
    # no match with python?
    GIRepository.TypeTag.VOID: None,  # 0 can be a pointer to an object or None
    GIRepository.TypeTag.INTERFACE: None,  # 16 can be a function/callback/struct
    GIRepository.TypeTag.ERROR: None,  # 20
    GIRepository.TypeTag.GTYPE: GObject.GType,  # 12 use string? the resolved type has lowercase gobject
}
# NDR: should use Mapping/Sequence for args and dict/list for return type


def gi_type_is_callback(gi_type_info: GIRepository.TypeInfo):
    """
    Check if the gi type is a callback.

    Args:
        gi_type_info (GIRepository.TypeInfo): type info object

    Returns:
        bool: True if the type is a callback

    """
    return gi_type_info.get_tag() == GIRepository.TypeTag.INTERFACE and isinstance(
        gi_type_info.get_interface(), GIRepository.CallbackInfo
    )


def gi_callback_to_py_type(gi_type_info: GIRepository.TypeInfo):
    """
    Map a gi callback type to a python type

    A callback is of type gi.CallbackInfo. If trying to access (i.e. Gst.LogFunction)
    it will raise a NotImplementedError since it is not implemented in pygobject
    (no direct python equivalent)

    We can work around this by querying the repository, i.e
    repository = Repository.get_default()
    repository.find_by_name("Gst", "LogFunction")

    It should be represented as a Callable Type using Callable from typing
    or a protocol from PEP 544
    https://peps.python.org/pep-0544/#callback-protocols

    Args:
        gi_type_info (GIRepository.TypeInfo): type info object

    Returns:
        python type object

    """
    if not gi_type_is_callback(gi_type_info):
        raise ValueError("Not a callback")
    return repository.find_by_name(
        gi_type_info.get_interface().get_namespace(),
        gi_type_info.get_interface().get_name(),
    )


def gi_type_to_py_type(
    gi_type_info: GIRepository.TypeInfo,
):
    """
    Map a gi type to a python type

    each type is represented by a unique integer and mapped to a type object
    https://docs.gtk.org/girepository/enum.TypeTag.html

    Args:
        gi_type_info (GIRepository.TypeInfo): type info object

    Returns:
        python type object

    """
    # retrieve tag from the type info (i.e. an integer)
    tag = gi_type_info.get_tag()
    # tag_as_string = gi_type_info.get_tag_as_string()
    py_type = map_gi_tag_to_type.get(tag, None)

    # if py_type is None and tag_as_string == "void":
    #     return object
    # if py_type is None and tag_as_string == "interface":
    if py_type is None and tag == GIRepository.TypeTag.INTERFACE:
        # TODO: return parse_struct_info_schema
        # with namespace
        iface = gi_type_info.get_interface()
        ns = iface.get_namespace()
        iface_name = iface.get_name()
        if not iface:
            raise ValueError("Invalid interface")

        # TODO: decide whether to return the interface name or the interface itself
        # if isinstance(iface, GIRepository.CallbackInfo):
        #     return iface

        # TODO: make sure it is accessible with try catch
        # if the interface is a callback it will raise a NotImplementedError
        # and we can type it with a protocol
        return f"{ns}.{iface_name}"

    if py_type is None and tag == GIRepository.TypeTag.VOID:
        # TODO: how to handle void?
        # in Gst.is_caps_features.get_arguments()[0].get_type() it is an object
        # in Gst.init.get_return_type().get_tag_as_string() it is None ??
        # VOID = 0
        # Gst.is_caps_features.get_arguments()[0].get_type() -> object
        # see https://gstreamer.freedesktop.org/documentation/gstreamer/gstcapsfeatures.html?gi-language=python#gst_is_caps_features

        if gi_type_info.is_pointer():
            return object
        return None

    if py_type is list:
        # TODO: how to handle list?
        # what is the type of the sequence?
        # i.e
        # Gst.meta_register_custom
        # Gst.meta_register_custom.get_arguments()[1].get_type().get_tag_as_string()
        return list[gi_type_to_py_type(gi_type_info.get_param_type(0))]

    if py_type is dict:
        key_type = gi_type_to_py_type(gi_type_info.get_param_type(0))
        value_type = gi_type_to_py_type(gi_type_info.get_param_type(1))
        return dict[key_type, value_type]

    # TODO: how to handle map key value?

    return py_type
