import importlib
from typing import Any
import gi
import gi._gi as GI  # type: ignore
from gi._gi import Repository  # pyright: ignore[reportMissingImports]
from gi.repository import GObject, GLib  # pyright: ignore[reportMissingModuleSource]
from gi.repository import GIRepository

from gi_stub_gen.utils import logger


repository = Repository.get_default()


# references
# https://amolenaar.pages.gitlab.gnome.org/pygobject-docs/Gst-1.0/functions.html#gi.repository.Gst.init
# https://gstreamer.freedesktop.org/documentation/gstreamer/gst.html?gi-language=python#gst_init
# https://valadoc.org/gstreamer-1.0/Gst.init.html

map_gi_tag_to_type = {
    # bool
    GI.TypeTag.BOOLEAN: bool,  # 1
    # int
    GI.TypeTag.INT8: int,  # 2
    GI.TypeTag.INT16: int,  # 4
    GI.TypeTag.INT32: int,  # 6
    GI.TypeTag.INT64: int,  # 8
    GI.TypeTag.UINT8: int,  # 3
    GI.TypeTag.UINT16: int,  # 5
    GI.TypeTag.UINT32: int,  # 7
    GI.TypeTag.UINT64: int,  # 9
    # float
    GI.TypeTag.FLOAT: float,  # 10
    GI.TypeTag.DOUBLE: float,  # 11
    # str
    GI.TypeTag.UTF8: str,  # 13
    GI.TypeTag.FILENAME: str,  # 14
    GI.TypeTag.UNICHAR: str,  # 21
    # map
    GI.TypeTag.GHASH: dict,  # 19 or dict?Mapping
    # list
    GI.TypeTag.GLIST: list,  # 17 or list?Sequence
    GI.TypeTag.GSLIST: list,  # 18 or list?Sequence
    GI.TypeTag.ARRAY: list,  # 15 or list? Sequence
    # no match with python?
    GI.TypeTag.VOID: None,  # 0 can be a pointer to an object or None
    GI.TypeTag.INTERFACE: None,  # 16 can be a function/callback/struct
    GI.TypeTag.ERROR: GLib.Error,  # 20
    GI.TypeTag.GTYPE: GObject.GType,  # 12 use string? the resolved type has lowercase gobject
}


# def get_gi_array_length(
#     gi_type_info: GI.TypeInfo,
# ) -> int:
# removed in pygobject 3.54.0?? was present in 3.50.0
# logger.warning(
#     f"Could not get array length for argument {obj.get_name()}: {e}"
# )
# https://valadoc.org/gobject-introspection-1.0/GI.TypeInfo.get_array_length.html
# the array length, or -1 if the type is not an array
# somehow in the newer pygobject this method is missing if not an array

#     if hasattr(gi_type_info, "get_array_length"):
#         return gi_type_info.get_array_length()
#     return -1


def get_safe_gi_array_length(
    gi_type: GI.TypeInfo,
) -> int:
    """
    get_array_length was previously available in all GI.TypeInfo objects
    but seems to have been removed in newer versions of pygobject (3.54.0?)
    when the type is not an array.

    We return -1 if the type is not an array or if the method is not available.
    Args:
        gi_type (GI.TypeInfo): type info object
    Returns:
        int: array length or -1 if not an array
    """
    try:
        tag = gi_type.get_tag()
        if tag != GIRepository.TypeTag.ARRAY:
            return -1
    except AttributeError:
        return -1

    try:
        return gi_type.get_array_length()
    except AttributeError:
        # Fallback per versioni dove il metodo manca su certi oggetti
        return -1
    
def get_safe_gi_destroy_index(
    gi_arg: Any,
) -> int:
    """
    get_destroy_index was previously returning just an int
    but seems to have changed in newer versions of pygobject (3.54.0?)
    to return a tuple (bool, int).

    We return -1 if there is no destroy index.

    Args:
        gi_arg (Any): arg info object
    Returns:
        int: destroy index or -1 if not present
    """
    try:
        result = gi_arg.get_destroy_index()
        if isinstance(result, tuple):
            has_destroy, destroy_idx = result
            if has_destroy:
                return destroy_idx
            return -1
        return result
    except AttributeError:
        return -1


def get_gi_type_info(
    obj: Any,
) -> GI.TypeInfo:
    """
    Recovers safely the TypeInfo.
    Handles the discrepancy between PyGObject versions (get_type vs get_type_info).
    """

    # was present in 3.50.0 ??
    if hasattr(obj, "get_type"):
        return obj.get_type()

    if hasattr(obj, "get_type_info"):
        return obj.get_type_info()

    # if it is already a TypeInfo, return it
    if isinstance(obj, GI.TypeInfo):  # type: ignore
        return obj

    raise AttributeError(f"Could not recover TypeInfo from object: {obj} ({type(obj)})")


def gi_type_is_callback(gi_type_info: GI.TypeInfo) -> bool:
    """
    Check if the gi type is a callback.

    Args:
        gi_type_info (GI.TypeInfo): type info object

    Returns:
        bool: True if the type is a callback

    """
    return gi_type_info.get_tag() == GI.TypeTag.INTERFACE and isinstance(
        gi_type_info.get_interface(), (GI.CallbackInfo, GIRepository.CallbackInfo)
    )


# def gi_callback_to_py_type(gi_type_info: GI.TypeInfo):
#     """
#     Map a gi callback type to a python type

#     A callback is of type gi.CallbackInfo. If trying to access (i.e. Gst.LogFunction)
#     it will raise a NotImplementedError since it is not implemented in pygobject
#     (no direct python equivalent)

#     We can work around this by querying the repository, i.e
#     ```
#     repository = Repository.get_default()
#     repository.find_by_name("Gst", "LogFunction")
#     ```
#     TODO: It should be represented as a Callable Type using Callable from typing
#     or a protocol from PEP 544
#     https://peps.python.org/pep-0544/#callback-protocols

#     Args:
#         gi_type_info (GI.TypeInfo): type info object

#     Returns:
#         python type object

#     """
#     if not gi_type_is_callback(gi_type_info):
#         raise ValueError("Not a callback")
#     return repository.find_by_name(
#         gi_type_info.get_interface().get_namespace(),
#         gi_type_info.get_interface().get_name(),
#     )


# GObject.ClosureMarshal
def gi_type_to_py_type(
    gi_type_info: GI.TypeInfo,
):
    """
    Map a gi type to a python type

    each type is represented by a unique integer and mapped to a type object
    https://docs.gtk.org/GI/enum.TypeTag.html

    Args:
        gi_type_info (GI.TypeInfo): type info object

    Returns:
        python type object

    """
    # retrieve tag from the type info (i.e. an integer)
    tag = gi_type_info.get_tag()
    py_type = map_gi_tag_to_type.get(tag, None)

    # if py_type is None and tag_as_string == "void":
    #     return object
    # if py_type is None and tag_as_string == "interface":
    if py_type is None and tag == GI.TypeTag.INTERFACE:
        # TODO: return parse_struct_info_schema
        # with namespace
        iface = gi_type_info.get_interface()
        ns = iface.get_namespace()
        iface_name = iface.get_name()
        if not iface:
            raise ValueError("Invalid interface")

        if isinstance(iface, (GI.CallbackInfo, GIRepository.CallbackInfo)):
            # cant return the type, will not work since
            # a callback is not implemented in python
            breakpoint()
            raise NotImplementedError(f"CallbackInfo to Python type conversion not possible, found {type(iface)}")
            # return gi_callback_to_py_type(iface)
            # cant return the type, will not work since it is not implemented
            # raise NotImplementedError
            # we can return a Protocol or a Callable..
            # TODO: Protocol of the callback
            return f"{ns}.{iface_name}"

        elif isinstance(iface, GI.UnresolvedInfo):
            raise NotImplementedError("UnresolvedInfo to Python type conversion not possible")
            # TODO: like Callback cannot be resolved, create a Protocol
            return f"{ns}.{iface_name} # TODO: unresolved"

        # elif isinstance(iface, (GI.CallableInfo, GIRepository.CallableInfo)):
        #     # Function/Signal/VFunc ??
        #     return f"{ns}.{iface_name} # TODO: CallableInfo"

        # TODO: make sure it is accessible with try catch
        # if the interface is a callback it will raise a NotImplementedError
        # and we can type it with a protocol

        # should be importable via python
        # from gi.repository import ns
        # return ns.iface_name
        # return f"{ns}.{iface_name}"

        return getattr(importlib.import_module(f"gi.repository.{ns}"), iface_name)

    if py_type is None and tag == GI.TypeTag.VOID:
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

    return py_type


def get_gi_module_from_name(
    module_name: str,
    gi_version: str | None,
) -> Any:
    """
    Get the module from its name.
    This is useful to get the module from a string representation of the module name.
    eg. "gi.repository.Gst", "1.0"

    Args:
        module_name (str): The module name, e.g. "Gst"
        gi_version (str | None): The gi version, e.g. "1.0

    Returns:
        Any: The module object
    """
    if not module_name:
        raise ValueError("get_gi_module_from_name: module_name must be provided")

    if gi_version is not None:
        try:
            logger.debug(f"Requiring gi version {gi_version} for module {module_name}")
            gi.require_version(module_name.removeprefix("gi.repository."), gi_version)
        except ValueError:
            logger.warning(f"Could not require gi version {gi_version} for module {module_name}")

    module_split = module_name.split(".")
    if len(module_split) == 1:
        logger.debug(f"Importing gi module without prefix: {module_name} -> {module_split[0]}")
        return importlib.import_module(f"{module_split[0]}")

    logger.debug(
        f"Importing gi module with prefix: {module_name} -> "
        f"{'.'.join(module_split[:-1])}, {module_split[-1]} "
        f"\n {module_split}"
    )

    try:
        return importlib.import_module(f".{module_split[-1]}", ".".join(module_split[:-1]))
    except ImportError as e:
        logger.debug(f"Could not import module {module_split[-1]} from {'.'.join(module_split[:-1])}.")
        raise e


def catch_gi_deprecation_warnings(
    attribute_module: Any,
    attribute_name: str,
) -> str | None:
    """
    This will catch deprecation warnings for a gi object attribute
    This will re-instantiate the module and try to access the attribute
    to trigger the deprecation warning, if any.
    We need to pass the attribute name as a string because its easier than trying
    to dig through the object to find the attribute name.

    Args:
        obj (Any): The object to check for deprecation warnings.
        attribute_name (str): The name of the attribute to check.
    """
    if not attribute_module:
        return None

    import warnings
    import gi

    # we only catch deprecation warnings from gi.repository
    # if not attribute_module.startswith("gi.repository."):
    #     attribute_module = f"gi.repository.{attribute_module}"

    try:
        # we dont pass version because at this point it was already requested
        module = get_gi_module_from_name(attribute_module, None)
    except ModuleNotFoundError:
        # logger.warning(
        #     f"Could not import module {attribute_module} to check for deprecation warnings."
        # )
        # try with gi.repository prefix
        try:
            module = get_gi_module_from_name(f"gi.repository.{attribute_module}", None)
        except ModuleNotFoundError:
            logger.error(f"Could not import module gi.repository.{attribute_module} to check for deprecation warnings.")
        return None

    attribute_deprecation_warnings: str | None = None
    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always", category=gi.PyGIDeprecationWarning)  # type: ignore

        # actually get the attribute
        # only when doing this we can catch deprecation warnings
        try:
            getattr(module, attribute_name)
        except (AttributeError, NotImplementedError):
            return None

        for warning in captured_warnings:
            if issubclass(warning.category, gi.PyGIDeprecationWarning):  # type: ignore
                attribute_deprecation_warnings = (
                    f"{attribute_deprecation_warnings}. {warning.message}"
                    if attribute_deprecation_warnings
                    else str(warning.message)
                )

    return attribute_deprecation_warnings


def is_class_field_nullable(field_info) -> bool:
    """
    Determine if a struct field can be None.

    """
    try:
        type_info = get_gi_type_info(field_info)
    except AttributeError:
        # worst case assume it is nullable
        return True

    tag = type_info.get_tag()

    # # no match with python?
    # GI.TypeTag.VOID: None,  # 0 can be a pointer to an object or None
    # GI.TypeTag.INTERFACE: None,  # 16 can be a function/callback/struct
    # GI.TypeTag.ERROR: None,  # 20

    # primitives are non-nullable
    NON_NULLABLE_TAGS = {
        GIRepository.TypeTag.BOOLEAN,
        GIRepository.TypeTag.INT8,
        GIRepository.TypeTag.INT16,
        GIRepository.TypeTag.INT32,
        GIRepository.TypeTag.INT64,
        GIRepository.TypeTag.UINT8,
        GIRepository.TypeTag.UINT16,
        GIRepository.TypeTag.UINT32,
        GIRepository.TypeTag.UINT64,
        GIRepository.TypeTag.FLOAT,
        GIRepository.TypeTag.DOUBLE,
        GIRepository.TypeTag.GTYPE,
        GIRepository.TypeTag.UTF8,  # string: can be NULL in c but dont think so in python
        GIRepository.TypeTag.UNICHAR,  # string: can be NULL in c but dont think so in python
        GIRepository.TypeTag.FILENAME,  # string: can be NULL in c but dont think so in python
    }

    if tag in NON_NULLABLE_TAGS:
        return False

    # lists and maps (Array, List, Hash)
    # pointer to structures, can be NULL
    if tag in {
        GIRepository.TypeTag.ARRAY,
        GIRepository.TypeTag.GLIST,
        GIRepository.TypeTag.GSLIST,
        GIRepository.TypeTag.GHASH,
    }:
        return True

    if tag == GIRepository.TypeTag.INTERFACE:  # function/callback/struct
        # we need to check if it is a struct or callback
        iface = type_info.get_interface()
        # we check the class name instead of checking
        # if the type is the "private" one: gi._gi.EnumInfo
        # (should be "safer" this way)
        if iface.__class__.__name__ == "EnumInfo":
            # enums are non-nullable
            return False
        # structs and callbacks can be nullable
        return True

    if tag == GIRepository.TypeTag.VOID:  # can be a pointer to an object or None
        return True

    if type_info.is_pointer():
        return True

    # if not a pointer, and not primitive, assume non-nullable
    return False
