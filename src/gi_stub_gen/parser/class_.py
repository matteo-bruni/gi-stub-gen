from __future__ import annotations

import gi
import gi._gi as GI  # type: ignore
from gi.repository import GObject

from typing import Any, TYPE_CHECKING
from types import MethodDescriptorType

from gi_stub_gen.parser.constant import parse_constant
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.parser.gir import ModuleDocs


from gi_stub_gen.utils import (
    get_py_type_name_repr,
    get_py_type_namespace_repr,
    gi_type_to_py_type,
    sanitize_module_name,
    sanitize_variable_name,
)

if TYPE_CHECKING:
    from gi_stub_gen.schema.class_ import ClassSchema
    from gi_stub_gen.schema.constant import VariableSchema
    from gi_stub_gen.schema.function import FunctionSchema

import logging

logger = logging.getLogger(__name__)


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
    from gi_stub_gen.schema.class_ import ClassPropSchema, ClassSchema

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
                try:
                    prop_type = gi_type_to_py_type(prop.get_type())
                except AttributeError as e:
                    # removed in pygobject 3.54.0?? was present in 3.50.0
                    # logger.warning(
                    #     f"Could not get type for property {prop.get_name()} of class {class_to_parse.__name__}: {e}"
                    #     "\nfalling back to type_info"
                    # )
                    prop_type = gi_type_to_py_type(prop.get_type_info())

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
                # if f.is_callback:
                #     print(f"!!!!!!!!!!!!!!!!!!! callback: {attribute_name}")
                # if len(f._gi_callbacks) > 0:
                #     print(
                #         f"@@@@@@@@@@@@@@@@@@@ callbacks found in method {attribute_name}: {[cb.get_name() for cb in f._gi_callbacks]}"
                #     )
            else:
                extra.append(f"unknown: {attribute_name}")

    from gi_stub_gen.schema.class_ import ClassSchema

    return ClassSchema.from_gi_object(
        namespace=namespace,
        obj=class_to_parse,
        docstring=module_docs.classes.get(class_to_parse.__name__, None),
        props=class_props,
        attributes=class_attributes,
        methods=class_methods,
        extra=extra,
    ), callbacks_found
