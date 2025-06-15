import importlib
import keyword
from typing import Any
import ast
import logging
import gi
import gi._gi as GI  # type: ignore
from gi._gi import Repository  # pyright: ignore[reportMissingImports]
from gi.repository import GObject  # pyright: ignore[reportMissingModuleSource]
# from typing import Sequence, Mapping

logger = logging.getLogger(__name__)
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
    GI.TypeTag.ERROR: None,  # 20
    GI.TypeTag.GTYPE: GObject.GType,  # 12 use string? the resolved type has lowercase gobject
}
# TODO: should use Mapping/Sequence for args and dict/list for return type


def is_py_builtin_type(py_type):
    return py_type in (int, str, float, dict, tuple, list)
    # return py_type.__name__ in dir(builtins)


def is_genum(attribute):
    return isinstance(attribute, type) and issubclass(attribute, GObject.GEnum)


def is_gflags(attribute):
    return isinstance(attribute, type) and issubclass(attribute, GObject.GFlags)


def gi_type_is_callback(gi_type_info: GI.TypeInfo) -> bool:
    """
    Check if the gi type is a callback.

    Args:
        gi_type_info (GI.TypeInfo): type info object

    Returns:
        bool: True if the type is a callback

    """
    return gi_type_info.get_tag() == GI.TypeTag.INTERFACE and isinstance(
        gi_type_info.get_interface(), GI.CallbackInfo
    )


def gi_callback_to_py_type(gi_type_info: GI.TypeInfo):
    """
    Map a gi callback type to a python type

    A callback is of type gi.CallbackInfo. If trying to access (i.e. Gst.LogFunction)
    it will raise a NotImplementedError since it is not implemented in pygobject
    (no direct python equivalent)

    We can work around this by querying the repository, i.e
    ```
    repository = Repository.get_default()
    repository.find_by_name("Gst", "LogFunction")
    ```

    TODO: It should be represented as a Callable Type using Callable from typing
    or a protocol from PEP 544
    https://peps.python.org/pep-0544/#callback-protocols

    Args:
        gi_type_info (GI.TypeInfo): type info object

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
    # tag_as_string = gi_type_info.get_tag_as_string()
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

        # TODO: decide whether to return the interface name or the interface itself
        if isinstance(iface, GI.CallbackInfo):
            # return gi_callback_to_py_type(iface)
            # cant return the type, will not work since it is not implemented
            # raise NotImplementedError
            # we can return a Protocol or a Callable..
            # TODO: Protocol of the callback
            return f"{ns}.{iface_name}"

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

    # TODO: how to handle map key value?

    return py_type


def get_super_class_name(obj, current_namespace: str | None = None):
    """
    Get the super class name of an object
    If current namespace is the same as the super class namespace
    it will return the class name only
    """
    # usually the first class in the mro is the object class
    # the second class is the super class
    # but if there is an override, the first class is the override
    # so the super class is the second class in the mro
    # loop all mro until we find a class with __name__ different from obj.__name__
    # TODO: should we skip gi._gi module?
    super_class = next(
        (
            cls
            for cls in obj.__mro__
            # for cls in obj.mro()
            if cls.__name__ != obj.__name__ and str(cls.__module__) != "gi._gi"
        ),
        object,
    )

    super_module = super_class.__module__
    super_module_name = sanitize_module_name(str(super_module))

    if super_module_name == "gi":
        super_module_name = "GI"
    # elif super_module_name == "module":
    #     super_module_name = "types.ModuleType"
    elif super_module_name == "builtins":
        if super_class.__name__ == "module":
            # if the super class is a module, return types.ModuleType
            return "types.ModuleType"
        return super_class.__name__

    # if the super class is in the same namespace as the current class
    # return only the class name
    if super_module_name == sanitize_module_name(current_namespace):
        return super_class.__name__
    # in typing it is uppercase
    # super_module_name = super_module_name.replace("gobject", "GObject")
    return f"{super_module_name}.{super_class.__name__}"


def get_py_type_namespace_repr(py_type: Any) -> str | None:
    """
    Get the namespace repr of a python type or object
    """

    # if the type has a __info__ attribute, it is a GObject type
    # and we can get the namespace from it
    if hasattr(py_type, "__info__"):
        return f"{py_type.__info__.get_namespace()}"  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]

    from inspect import getmodule

    # we can use getmodule to get the module of the type
    if module_namespace := getmodule(py_type):
        name = module_namespace.__name__
        # manual fix for some modules, how to get the correct namespace?
        name = name.replace("gobject", "GObject")
        if name == "builtins":
            return None
        return name

    return None


def get_py_type_name_repr(py_type: Any) -> str:
    """
    Get the string representation of a python type or object
    """
    # if gi_type_is_callback(self._gi_type):
    #     # TODO: registrare protocollo
    #     return f"TODOProtocol({py_type})"

    # if it is a GObject
    if hasattr(py_type, "__info__"):
        # assert False, f"which type is this? {py_type}: {py_type.__info__.get_name()}"
        return f"{py_type.__info__.get_name()}"

    if hasattr(py_type, "__name__"):
        # assert False, f"which type is this? {py_type}: {py_type.__name__}"
        return py_type.__name__

    return str(py_type)


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
    import importlib
    import warnings
    import gi

    # if not hasattr(obj, "__info__"):
    #     return None

    # we dont pass version because at this point it was already requested
    module = get_module_from_name(attribute_module, None)

    attribute_deprecation_warnings: str | None = None
    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always", category=gi.PyGIDeprecationWarning)  # type: ignore

        # actually get the attribute
        # only when doing this we can catch deprecation warnings
        # getattr(module, attribute_name)
        # getattr(module, get_name(obj))
        getattr(module, attribute_name)

        for warning in captured_warnings:
            if issubclass(warning.category, gi.PyGIDeprecationWarning):  # type: ignore
                attribute_deprecation_warnings = (
                    f"{attribute_deprecation_warnings}. {warning.message}"
                    if attribute_deprecation_warnings
                    else str(warning.message)
                )

    return attribute_deprecation_warnings


def get_symbol_name(obj):
    """
    retrieve the variable name of the object
    """
    frame = inspect.currentframe().f_back  # type: ignore
    call_line = inspect.getframeinfo(frame).code_context[0].strip()  # type: ignore
    tree = ast.parse(call_line)

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.symbol = None

        def visit_Call(self, node):
            if hasattr(node, "args") and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Attribute):
                    self.symbol = arg.attr  # <--- Qui ottieni "IO_ERR"
            self.generic_visit(node)

    visitor = Visitor()
    visitor.visit(tree)
    return visitor.symbol


def get_module_from_name(
    module_name: str,
    version: str | None,
) -> Any:
    """
    Get the module from its name.
    This is useful to get the module from a string representation of the module name.
    """

    if version:
        gi.require_version(module_name, version)

    if module_name.startswith("gi"):
        return importlib.import_module(f"{module_name}")

    # we got only the final part of the module name
    return importlib.import_module(f".{module_name}", "gi.repository")


def sanitize_module_name(module_name: Any) -> str:
    """
    Sanitize the module name to be used in the gi.repository namespace.
    This will remove the gi.repository prefix and return the module name.
    """
    return (
        str(module_name)
        .removeprefix("gi.repository.")
        .removeprefix("gi.overrides.")
        .replace("gobject", "GObject")
        .replace("glib", "GLib")
    )


def sanitize_variable_name(name: str) -> tuple[str, str | None]:
    """
    Sanitize a variable name to be a valid Python identifier.
    This will replace hyphens with underscores, check if the name is a keyword,
    and ensure it is a valid identifier.
    If the name is a keyword, it will prepend an underscore to it.
    If the name is not a valid identifier, it will prepend an underscore to it.
    Args:
        name (str): The name to sanitize.
    Returns:
        tuple[str, bool]: A tuple containing the sanitized name and a boolean indicating
                          if the name was modified to be valid.
    """
    name = name.replace("-", "_")
    if keyword.iskeyword(name):
        return f"_{name}", "changed due to name is a python keyword"

    if name.isidentifier():
        return name, None

    return f"_{name}", "changed due to not a valid identifier"  