from __future__ import annotations

import gi
import gi._gi as GI  # type: ignore
from gi.repository import GObject

from typing import Any, TYPE_CHECKING
from types import MethodDescriptorType

from gi_stub_gen.gi_utils import get_gi_type_info, is_property_nullable_safe
from gi_stub_gen.parser.constant import parse_constant
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.parser.gir import ModuleDocs


from gi_stub_gen.schema.class_ import ClassAttributeSchema, ClassSchema
from gi_stub_gen.utils import (
    get_py_type_name_repr,
    get_py_type_namespace_repr,
    gi_type_is_callback,
    gi_type_to_py_type,
    sanitize_gi_module_name,
    sanitize_variable_name,
)
from gi.repository import GIRepository

if TYPE_CHECKING:
    from gi_stub_gen.schema.function import FunctionSchema

import logging

logger = logging.getLogger(__name__)


def is_method_local(py_class: type, method_name: str) -> bool:
    return method_name in py_class.__dict__


def should_expose_class_field(
    field_info: GIRepository.FieldInfo,
) -> bool:
    """
    Determines if a class field should be exposed in the generated stub.
    """
    name = field_info.get_name()

    if not name:
        return False

    flags = field_info.get_flags()

    if name.startswith("_"):
        return False

    if name in ("parent", "parent_instance", "g_type_instance", "priv"):
        return False

    if not (flags & GIRepository.FieldInfoFlags.READABLE):
        return False

    type_info = get_gi_type_info(field_info)
    tag = type_info.get_tag()

    if tag == GIRepository.TypeTag.INTERFACE:
        interface_info = type_info.get_interface()

        # do not expose callback interfaces as simple fields
        if isinstance(interface_info, GIRepository.CallbackInfo):
            return False

        # do not expose CallableInfo generic (Function/Signal/VFunc)
        if isinstance(interface_info, GIRepository.CallableInfo):
            return False

    # discard void fields ??
    if tag == GIRepository.TypeTag.VOID:
        return False
    return True


def parse_class(
    namespace: str,
    class_to_parse: Any,
    module_docs: ModuleDocs,
) -> tuple[ClassSchema | None, list[GI.TypeInfo]]:
    """
    Parse a class and return a ClassSchema and a list of GI.TypeInfo callbacks found during parsing.

    Args:
        namespace (str): namespace of the class
        class_to_parse (Any): class to be parsed
        module_docs (ModuleDocs): module documentation
    Returns:
        tuple[ClassSchema | None, list[GI.TypeInfo]]: parsed ClassSchema and list of GI.TypeInfo callbacks
    """
    from gi_stub_gen.schema.class_ import ClassPropSchema, ClassSchema

    # Check if it is a class
    if type(class_to_parse) not in (gi.types.GObjectMeta, gi.types.StructMeta, type):  # type: ignore
        return None, []

    # filter out classes not in the same namespace as the module
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
    class_attributes: list[ClassAttributeSchema] = []
    class_methods: list[FunctionSchema] = []
    class_parsed_elements: list[str] = []
    extra: list[str] = []

    # there is no __init__ in gi methods
    # but it should be the same as the classmethod new
    # with the same args but self instead of cls
    # if we get the new method, we can manually create the __init__ method
    class_init: FunctionSchema | None = None

    # if the class is a GObject, it has __info__ attribute
    # do a first pass to get all the attributes with get_properties/get_methods
    if hasattr(class_to_parse, "__info__"):
        if hasattr(class_to_parse.__info__, "get_fields"):
            ...
        # Parse Props (they have a getter/setter depending on the flags)
        if hasattr(class_to_parse.__info__, "get_properties"):
            for prop in class_to_parse.__info__.get_properties():
                # start from type info
                prop_gi_type_info = get_gi_type_info(prop)
                prop_type = gi_type_to_py_type(prop_gi_type_info)

                prop_type_hint_namespace = get_py_type_namespace_repr(prop_type)
                prop_type_hint_name = get_py_type_name_repr(prop_type)

                sanitized_name, line_comment = sanitize_variable_name(prop.get_name())

                prop_type_hint_full = prop_type_hint_name
                if (
                    prop_type_hint_namespace
                    and prop_type_hint_namespace != sanitize_gi_module_name(namespace)
                ):
                    prop_type_hint_full = (
                        f"{prop_type_hint_namespace}.{prop_type_hint_name}"
                    )

                may_be_null = is_property_nullable_safe(prop)

                # if sanitized_name == "source_property":
                #     breakpoint()
                if may_be_null:
                    prop_type_hint_full = f"{prop_type_hint_full} | None"
                    if line_comment:
                        line_comment += "maybe null since not primitive?? (TODO: check better way to determine this)"
                    else:
                        line_comment = "maybe null since not primitive?? (TODO: check better way to determine this)"

                c = ClassPropSchema(
                    name=sanitized_name,
                    # type=str(prop_type),
                    is_deprecated=prop.is_deprecated(),
                    readable=bool(prop.get_flags() & GObject.ParamFlags.READABLE),
                    writable=bool(prop.get_flags() & GObject.ParamFlags.WRITABLE),
                    type_hint_namespace=prop_type_hint_namespace,
                    type_hint_name=prop_type_hint_name,
                    type_hint_full=prop_type_hint_full,
                    line_comment=line_comment,
                    docstring=None,  # TODO: retrieve docstring
                    may_be_null=may_be_null,
                )
                class_props.append(c)
                class_parsed_elements.append(prop.get_name())
        if hasattr(class_to_parse.__info__, "get_methods"):
            for met in class_to_parse.__info__.get_methods():
                parsed_method = parse_function(
                    met,
                    docstring=module_docs.get_function_docstring(met.get_name()),
                )
                if parsed_method:
                    if parsed_method.name == "new":
                        # create __init__ method from new
                        class_init = parsed_method.model_copy(
                            update={
                                "name": "__init__",
                                "is_method": True,  # so it will use self in template
                                "is_constructor": False,
                                "return_hint": None,
                                "return_hint_namespace": None,
                            },
                            deep=True,
                        )
                        class_methods.append(class_init)

                    # save callbacks to be parsed later
                    callbacks_found.extend(parsed_method._gi_callbacks)
                    class_methods.append(parsed_method)
                    class_parsed_elements.append(met.get_name())

    # do a second pass to get all the attributes not parsed by get_properties/get_methods
    # i.e class not from GI but added in overrides
    for attribute_name in dir(class_to_parse):
        if attribute_name.startswith("_") and attribute_name != "__init__":
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

        # if not attribute_name.startswith("_"):
        # do not parse already parsed elements
        if attribute_name in class_parsed_elements:
            continue

        # we only parse local attributes, not inherited ones
        is_attribute_local = is_method_local(class_to_parse, attribute_name)
        if not is_attribute_local:
            continue

        if c := parse_constant(
            parent="",
            name=attribute_name,
            obj=attribute,
            docstring=None,  # TODO: retrieve docstring with inspect??
        ):
            extra.append(f"constant: {attribute_name} local={is_attribute_local}")
            # class_attributes.append(c)
        # elif attribute_type is method:
        #     ...
        elif attribute_type is MethodDescriptorType:
            # TODO: how to parse this??
            # cant obtain args/return type
            # inspect does not work on builting

            extra.append(f"method: {attribute_name} local={is_attribute_local}")
        elif attribute_type is property:
            # TODO: how to parse this??
            # cant obtain args/return type
            # inspect does not work on builting
            if namespace == "gi.repository.Gst":
                breakpoint()

            # import gi
            # gi.require_version("Gst", "1.0")
            # from gi.repository import Gst
            # Gst.init()
            # from gi.repository import GIRepository

            # GIRepository.Repository().find_by_name("Gst.AllocationParams", "align")
            # .find_by_name("Gst", "AllocationParams")
            # repo.find_by_name("Gst.AllocationParams", "align")
            extra.append(f"property: {attribute_name} local={is_attribute_local}")

        elif f := parse_function(
            attribute,
            module_docs.get_function_docstring(attribute_name),
        ):
            class_methods.append(f)
            # callbacks can be found as arguments of functions, save them to be parsed later
            callbacks_found.extend(f._gi_callbacks)
        else:
            extra.append(
                f"unknown: {attribute_name}: {attribute_type} local={is_attribute_local}"
            )

    # sort methods by name
    class_methods.sort(key=lambda x: x.name)

    return ClassSchema.from_gi_object(
        namespace=namespace,
        obj=class_to_parse,
        docstring=module_docs.classes.get(class_to_parse.__name__, None),
        props=class_props,
        attributes=class_attributes,
        methods=class_methods,
        extra=sorted(extra),
    ), callbacks_found
