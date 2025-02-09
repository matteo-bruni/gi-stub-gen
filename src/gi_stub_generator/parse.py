import gi
import gi._gi as GI  # type: ignore
from gi._gi import Repository
from gi.repository import GObject

from gi_stub_generator.schema import (
    ClassPropSchema,
    ClassSchema,
    EnumFieldSchema,
    EnumSchema,
    VariableSchema,
    FunctionArgumentSchema,
    FunctionSchema,
)
from types import (
    FunctionType,
    ModuleType,
    BuiltinFunctionType,
    MethodDescriptorType,
    MethodType,
)
from typing import Any, Literal
from gi_stub_generator.utils import (
    gi_type_is_callback,
    gi_type_to_py_type,
    is_py_builtin_type,
)


repository = Repository.get_default()


def parse_constant(
    parent: str,
    name: str,  # name of the attribute
    obj: Any,  # actual object to be parsed
    # _gi_type: Any,  # the actual type object
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

    _gi_type = type(obj)

    if _gi_type in (int, str, float, dict, tuple, list):
        # if is_py_builtin_type(_gi_type):
        return VariableSchema(
            _gi_type=_gi_type,
            namespace=parent,
            name=name,
            value=obj,
        )

    # check if it is a constant from an enum/flag
    if hasattr(obj, "__info__"):
        info = getattr(obj, "__info__")
        # both enums and flags have __info__ attribute of type EnumInfo
        if type(info) is GI.EnumInfo:
            # if info.is_flags():
            # at this point this can be the "flags" class or an atribute
            # with a value of the flag class
            # if it is an attribute it is an instance of GObject.GFlags
            if isinstance(obj, (GObject.GFlags, GObject.GEnum)):
                # or info.get_g_type().parent.name == "GFlags"
                assert obj.is_integer(), f"{name} is not an enum/flag?"
                return VariableSchema(
                    _gi_type=_gi_type,
                    namespace=parent,
                    name=name,
                    value=obj.real,
                )
    return None


def parse_enum(attribute: Any) -> EnumSchema | None:
    is_flags = isinstance(attribute, type) and issubclass(attribute, GObject.GFlags)
    is_enum = isinstance(attribute, type) and issubclass(attribute, GObject.GEnum)
    if is_flags or is_enum:
        # GObject.Enum and Gobject.Flags do not have __info__ attribute
        if hasattr(attribute, "__info__"):
            _type_info = attribute.__info__
            args: list[FunctionArgumentSchema] = []
            for v in _type_info.get_values():
                args.append(
                    EnumFieldSchema(
                        # name=v.get_name(),
                        # value=v.get_value(),
                        _gi_info=v,
                    )
                )
            return EnumSchema(
                # _gi_info=_type_info,
                _gi_type=attribute,
                enum_type="flags" if is_flags else "enum",
                values=args,
            )

    return None


def parse_function(
    attribute: Any,
) -> FunctionSchema | None:
    is_callback = isinstance(attribute, GI.CallbackInfo)
    is_function = isinstance(attribute, GI.FunctionInfo)

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

    callback_found: list[GI.TypeInfo] = []
    """callbacks found during function argument parsing"""

    # function_return_type = []
    # function_in_out = []
    for arg in attribute.get_arguments():
        direction: Literal["IN", "OUT", "INOUT"]
        if arg.get_direction() == GI.Direction.OUT:
            direction = "OUT"
        elif arg.get_direction() == GI.Direction.IN:
            direction = "IN"
        elif arg.get_direction() == GI.Direction.INOUT:
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
        # if any of the arguments is a callback, store it to be later parsed
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


def get_super_class_name(obj, start_pos=1):
    """
    The first element in mro is the class itself, so to get the super class
    we need to start from the second element.
    If the super class is from gi, we need to skip it and get the next one.

    Get as super class the first class that is not from gi
    (gi.Something are not importable)
    """
    mro = obj.mro()
    mro_pos = start_pos
    if mro[mro_pos].__module__ == "gi":
        return get_super_class_name(obj, mro_pos + 1)
    return f"{mro[mro_pos].__module__}.{mro[mro_pos].__name__}"


def parse_class(
    namespace: str,
    class_to_parse: Any,
) -> ClassSchema | None:
    # Check if it is a class #################
    if type(class_to_parse) not in (gi.types.GObjectMeta, gi.types.StructMeta, type):
        return None

    callbacks_found: list[GI.TypeInfo] = []
    """callbacks found during class parsing, saved to be parsed later"""

    class_props: list[VariableSchema] = []
    class_attributes: list[VariableSchema] = []
    class_methods: list[FunctionSchema] = []
    class_parsed_elements: list[str] = []
    extra: list[str] = []

    # if the class is a GObject, it has __info__ attribute
    # do a first pass to get all the attributes with get_properties/get_methods
    if hasattr(class_to_parse, "__info__"):
        # Parse Props (they have a getter/setter depending on the flags)
        if hasattr(class_to_parse.__info__, "get_properties"):
            for prop in class_to_parse.__info__.get_properties():
                c = ClassPropSchema(
                    name=prop.get_name(),
                    type=str(gi_type_to_py_type(prop.get_type())),
                    is_deprecated=prop.is_deprecated(),
                    readable=bool(prop.get_flags() & GObject.ParamFlags.READABLE),
                    writable=bool(prop.get_flags() & GObject.ParamFlags.WRITABLE),
                )
                class_props.append(c)
                class_parsed_elements.append(prop.get_name())
        if hasattr(class_to_parse.__info__, "get_methods"):
            for met in class_to_parse.__info__.get_methods():
                parsed_method = parse_function(met)
                if parsed_method:
                    # save callbacks to be parsed later
                    callbacks_found.extend(parsed_method._gi_callbacks)
                    class_methods.append(parsed_method)
                    class_parsed_elements.append(met.get_name())

    # do a second pass to get all the attributes not parsed by get_properties/get_methods
    # i.e class not from GI but added in overrides
    for attribute_name in dir(class_to_parse):
        attribute = getattr(class_to_parse, attribute_name)
        attribute_type = type(attribute)

        # could not find any example of this but should work like this if present
        # class variables with no default are in attribute.__annotations__
        # if hasattr(obj, "__annotations__"):
        #     if len(attribute.__annotations__) > 0:
        #         print("annotations", attribute.__annotations__)

        if not attribute_name.startswith("__"):
            # do not parse already parsed elements
            if attribute_name in class_parsed_elements:
                continue

            if c := parse_constant(
                parent="",
                name=attribute_name,
                obj=attribute,
            ):
                class_attributes.append(c)
            elif attribute_type is MethodDescriptorType:
                # TODO: how to parse this??
                # cant obtain args/return type
                # inspect does not work on builting
                extra.append(f"method: {attribute_name}")
            elif attribute_type is property:
                # TODO: how to parse this??
                # cant obtain args/return type
                # inspect does not work on builting
                extra.append(f"property: {attribute_name}")
            elif f := parse_function(attribute):
                class_methods.append(f)
                # print("function", f)
                # callbacks can be found as arguments of functions, save them to be parsed later
                callbacks_found.extend(f._gi_callbacks)
            else:
                extra.append(f"unknown: {attribute_name}")

    return ClassSchema(
        namespace=namespace,
        name=class_to_parse.__name__,
        super=[get_super_class_name(class_to_parse)],
        attributes=class_attributes,
        methods=class_methods,
        extra=extra,
        props=class_props,
        _gi_type=class_to_parse,
        _gi_callbacks=callbacks_found,
    )
    # print("***** start")
    # print(class_schema)
    # print("***** end")
