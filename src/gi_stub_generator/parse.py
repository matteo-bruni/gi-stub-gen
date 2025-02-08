from gi.repository import GObject
from gi_stub_generator.schema import Constant, FunctionArgumentSchema, FunctionSchema
import gi._gi as GIRepository  # type: ignore
from gi._gi import Repository
from typing import Any, Literal

from gi_stub_generator.utils import gi_type_is_callback


repository = Repository.get_default()


def parse_constant(
    parent: str,
    name: str,  # name of the attribute
    obj: Any,  # actual object to be parsed
    obj_type: Any,  # the actual type object
):
    """
    Parse values and return an Attribute.
    Return None if the object is not a module constant.

    Args:
        parent (str): parent module name
        name (str): name of the attribute
        obj (Any): object to be parsed
        obj_type (Any): the actual type object

    Returns:
        Attribute | None
    """

    if obj_type in (int, str, float):
        return Constant(
            _type=obj_type,
            parent=parent,
            name=name,
            value=obj,
        )

    # check if it is a constant from an enum/flag
    if hasattr(obj, "__info__"):
        info = getattr(obj, "__info__")
        # both enums and flags have __info__ attribute of type EnumInfo
        if type(info) is GIRepository.EnumInfo:
            # if info.is_flags():
            # at this point this can be the "flags" class or an atribute
            # with a value of the flag class
            # if it is an attribute it is an instance of GObject.GFlags
            if isinstance(obj, (GObject.GFlags, GObject.GEnum)):
                # or info.get_g_type().parent.name == "GFlags"
                assert obj.is_integer(), f"{name} is not an enum/flag?"
                return Constant(
                    _type=obj_type,
                    parent=parent,
                    name=name,
                    value=obj.real,
                )
    return None


def parse_function(
    attribute: Any,
) -> FunctionSchema | None:
    is_callback = isinstance(attribute, GIRepository.CallbackInfo)
    is_function = isinstance(attribute, GIRepository.FunctionInfo)

    if not is_callback and not is_function:
        # print("not a callback or function skip", type(attribute))
        return None

    # GIFunctionInfo
    # represents a function, method or constructor.
    # To find out what kind of entity a GIFunctionInfo represents,
    # call gi_function_info_get_flags().
    # See also GICallableInfo for information on how to retrieve arguments
    # and other metadata.

    # check whether the function is a method (i.e. has a self argument)
    function_args: list[FunctionArgumentSchema] = []

    callback_found: list[GIRepository.TypeInfo] = []
    """callbacks found during function argument parsing"""

    # function_return_type = []
    # function_in_out = []
    for arg in attribute.get_arguments():
        direction: Literal["IN", "OUT", "INOUT"]
        if arg.get_direction() == GIRepository.Direction.OUT:
            direction = "OUT"
        elif arg.get_direction() == GIRepository.Direction.IN:
            direction = "IN"
        elif arg.get_direction() == GIRepository.Direction.INOUT:
            direction = "INOUT"
        else:
            raise ValueError("Invalid direction")

        # in Gst.debug_log_default,
        # user_data args is void but
        # https://gstreamer.freedesktop.org/documentation/gstreamer/gstinfo.html?gi-language=python#gst_debug_log_default
        # says it is a object
        # Gst.debug_log_default.get_arguments()[7]

        function_args.append(
            FunctionArgumentSchema(
                namespace=arg.get_namespace(),
                name=arg.get_name(),
                is_optional=arg.is_optional(),
                _gi_type=arg.get_type(),
                direction=direction,
                maybe_null=arg.may_be_null(),
            )
        )

        if gi_type_is_callback(arg.get_type()):
            callback_found.append(arg.get_type())

    return FunctionSchema(
        namespace=attribute.get_namespace(),
        name=attribute.get_name(),
        args=function_args,
        _gi_type=attribute,
        _gi_callbacks=callback_found,
        is_callback=is_callback,
    )
