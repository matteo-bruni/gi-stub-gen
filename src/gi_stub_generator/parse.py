from __future__ import annotations

import gi
import gi._gi as GI  # type: ignore
from gi._gi import Repository  # type: ignore
from gi.repository import GObject
import logging
from gi_stub_generator.parser.gir import ClassDocs, FunctionDocs, ModuleDocs
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
    get_py_type_name_repr,
    get_py_type_namespace_repr,
    gi_type_is_callback,
    gi_type_to_py_type,
    is_py_builtin_type,
    sanitize_module_name,
    sanitize_variable_name,
)

logger = logging.getLogger(__name__)
repository = Repository.get_default()


def parse_constant(
    parent: str,
    name: str,  # name of the attribute
    obj: Any,  # actual object to be parsed
    docstring: str | None,
    deprecation_warnings: str | None,  # deprecation warnings if any
):
    """
    Parse values and return a VariableSchema.
    Return None if the object is not a module constant.

    Args:
        parent (str): parent module name
        name (str): name of the attribute
        obj (Any): object to be parsed

    Returns:
        VariableSchema | None
    """

    _gi_type = type(obj)

    if _gi_type in (int, str, float, dict, tuple, list):
        # if is_py_builtin_type(_gi_type):
        return VariableSchema.from_gi_object(
            obj=obj,
            namespace=parent,
            name=name,
            docstring=docstring,
            deprecation_warnings=deprecation_warnings,
        )

    # check if it is a constant from an enum/flag
    if hasattr(obj, "__info__"):
        info = getattr(obj, "__info__")
        # both enums and flags have __info__ attribute of type EnumInfo
        # example, this is a flag:
        # type(getattr(Gst.BUFFER_COPY_METADATA, "__info__")) == GI.EnumInfo
        if type(info) is GI.EnumInfo:
            # if info.is_flags():
            # at this point this can be the "flags" class or an attribute
            # with a value of the flag class
            # if it is an attribute it is an instance of GObject.GFlags
            if isinstance(obj, (GObject.GFlags, GObject.GEnum)):
                # or info.get_g_type().parent.name == "GFlags"
                assert obj.is_integer(), f"{name} is not an enum/flag?"
                return VariableSchema.from_gi_object(
                    obj=obj,
                    namespace=parent,
                    name=name,
                    docstring=docstring,
                    deprecation_warnings=deprecation_warnings,
                )

    # TODO: handle GType elements (which lacks __info__ attribute)
    if isinstance(obj, GObject.GType):
        # GType is a type, not a value
        # so we can not parse it as a constant
        # but we can parse it as an enum/flag
        return VariableSchema.from_gi_object(
            obj=obj,
            namespace=parent,
            name=name,
            docstring=docstring,
            deprecation_warnings=deprecation_warnings,
        )

    return None


def parse_enum(
    attribute: Any,
    docs: dict[str, ClassDocs],
    deprecation_warnings: str | None,  # deprecation warnings if any
) -> EnumSchema | None:
    is_flags = isinstance(attribute, type) and issubclass(attribute, GObject.GFlags)
    is_enum = isinstance(attribute, type) and issubclass(attribute, GObject.GEnum)

    if is_flags or is_enum:
        # GObject.Enum and Gobject.Flags do not have __info__ attribute
        if hasattr(attribute, "__info__"):
            _type_info = attribute.__info__  # type: ignore

            # to retrieve its docstring we need to get the name of the class
            class_name = attribute.__info__.get_name()  # type: ignore
            class_doc_data = docs.get(class_name, None)

            # class docstring
            class_docstring = None
            if class_doc_data:
                class_docstring = class_doc_data.class_docstring

            # parse all possible enum/flag values
            # and retrieve their docstrings
            args: list[EnumFieldSchema] = []
            for v in _type_info.get_values():
                element_docstring = None
                if class_doc_data:
                    element_docstring = class_doc_data.fields.get(v.get_name(), None)
                args.append(
                    EnumFieldSchema.from_gi_value_info(
                        value_info=v,
                        docstring=element_docstring,
                        deprecation_warnings=deprecation_warnings,
                    )
                )
            return EnumSchema.from_gi_object(
                obj=attribute,
                enum_type="flags" if is_flags else "enum",
                fields=args,
                docstring=class_docstring,
            )

    return None


def parse_function(
    attribute: Any,
    docstring: dict[str, FunctionDocs],
    deprecation_warnings: str | None,  # deprecation warnings if any
) -> FunctionSchema | None:
    is_callback = isinstance(attribute, GI.CallbackInfo)
    is_function = isinstance(attribute, GI.FunctionInfo)

    if not is_callback and not is_function:
        # print("not a callback or function skip", type(attribute))
        return None

    return FunctionSchema.from_gi_object(
        obj=attribute,
        docstring=docstring.get(attribute.get_name(), None),
    )


def parse_class(
    namespace: str,
    class_to_parse: Any,
    module_docs: ModuleDocs,
    deprecation_warnings: str | None,  # deprecation warnings if any
) -> tuple[ClassSchema | None, list[GI.TypeInfo]]:
    """
    Parse a class and return a ClassSchema.

    Args:
        namespace (str): namespace of the class
        class_to_parse (Any): class to be parsed
        module_docs (ModuleDocs): module documentation
    Returns:
        ClassSchema | None: parsed class schema or None if the class is not parsable
    """
    ###############
    # Check if it is a class #################
    if type(class_to_parse) not in (gi.types.GObjectMeta, gi.types.StructMeta, type):  # type: ignore
        return None, []

    if (
        namespace.split(".")[-1].lower()
        != str(class_to_parse.__module__).split(".")[-1].lower()
    ):
        # if the class is not in the same namespace as the module, skip it
        # this can happen with classes from gi.repository that are not in the same namespace
        logger.warning(
            f"[SKIP][CLASS_IN_OTHER_NS]{class_to_parse}, {class_to_parse.__name__}, {str(class_to_parse.__module__)}"
        )
        return None, []

    callbacks_found: list[GI.TypeInfo] = []
    """callbacks found during class parsing, saved to be parsed later"""

    class_props: list[ClassPropSchema] = []
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
                # breakpoint()

                prop_type = gi_type_to_py_type(prop.get_type())
                prop_type_repr_namespace = get_py_type_namespace_repr(prop_type)
                prop_type_repr_name = get_py_type_name_repr(prop_type)

                prop_type_repr = prop_type_repr_name
                if (
                    prop_type_repr_namespace
                    and prop_type_repr_namespace != sanitize_module_name(namespace)
                ):
                    prop_type_repr = f"{prop_type_repr_namespace}.{prop_type_repr_name}"

                sanitized_name, comment = sanitize_variable_name(prop.get_name())

                c = ClassPropSchema(
                    name=sanitized_name,
                    type=str(prop_type),
                    is_deprecated=prop.is_deprecated(),
                    readable=bool(prop.get_flags() & GObject.ParamFlags.READABLE),
                    writable=bool(prop.get_flags() & GObject.ParamFlags.WRITABLE),
                    type_repr=prop_type_repr,
                    line_comment=f"#{comment}" if comment else None,
                )
                class_props.append(c)
                class_parsed_elements.append(prop.get_name())
        if hasattr(class_to_parse.__info__, "get_methods"):
            for met in class_to_parse.__info__.get_methods():
                parsed_method = parse_function(met, module_docs.functions, None)
                if parsed_method:
                    # save callbacks to be parsed later
                    callbacks_found.extend(parsed_method._gi_callbacks)
                    class_methods.append(parsed_method)
                    class_parsed_elements.append(met.get_name())

    # do a second pass to get all the attributes not parsed by get_properties/get_methods
    # i.e class not from GI but added in overrides
    for attribute_name in dir(class_to_parse):
        if attribute_name.startswith("__"):
            # skip dunder methods
            continue
        try:
            attribute = getattr(class_to_parse, attribute_name)
        except AttributeError as e:
            logger.warning(
                f"Could not get attribute {attribute_name} from {class_to_parse.__name__}: {e}"
            )
            breakpoint()
            continue
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
                docstring=None,  # TODO: retrieve docstring
                deprecation_warnings=None,  # TODO: retrieve deprecation warnings
                # docstring=module_docs.constants.get(attribute_name, None),
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
            elif f := parse_function(
                attribute,
                module_docs.functions,
                None,  # TODO: retrieve?
            ):
                class_methods.append(f)
                # print("function", f)
                # callbacks can be found as arguments of functions, save them to be parsed later
                callbacks_found.extend(f._gi_callbacks)
            else:
                extra.append(f"unknown: {attribute_name}")

    return ClassSchema.from_gi_object(
        namespace=namespace,
        obj=class_to_parse,
        docstring=module_docs.classes.get(class_to_parse.__name__, None),
        props=class_props,
        attributes=class_attributes,
        methods=class_methods,
        extra=extra,
    ), callbacks_found

    # return ClassSchema(
    #     namespace=namespace,
    #     name=class_to_parse.__name__,
    #     # super=[get_super_class_name(class_to_parse)],
    #     super=[
    #         get_super_class_name(class_to_parse),
    #     ],
    #     attributes=class_attributes,
    #     methods=class_methods,
    #     extra=extra,
    #     props=class_props,
    #     _gi_type=class_to_parse,
    #     _gi_callbacks=callbacks_found,
    #     docstring=module_docs.classes.get(class_to_parse.__name__, None),
    # )
    # print("***** start")
    # print(class_schema)
    # print("***** end")
