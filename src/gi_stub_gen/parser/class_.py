from __future__ import annotations

import gi
import gi._gi as GI  # type: ignore
from gi.repository import GObject

from typing import Any
from types import (
    BuiltinFunctionType,
    FunctionType,
    GetSetDescriptorType,
    MethodDescriptorType,
    MethodType,
)

from gi_stub_gen.gi_utils import (
    get_gi_type_info,
    gi_type_is_callback,
    gi_type_to_py_type,
    is_class_field_nullable,
)
from gi_stub_gen.overrides import apply_method_overrides

from gi_stub_gen.parser.builtin_function import parse_builtin_function
from gi_stub_gen.parser.constant import parse_constant
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.parser.gir import ModuleDocs


from gi_stub_gen.schema.class_ import ClassFieldSchema, ClassSchema
from gi_stub_gen.schema.constant import VariableSchema
from gi_stub_gen.schema.function import (
    BuiltinFunctionSchema,
    CallbackSchema,
    FunctionArgumentSchema,
)
from gi_stub_gen.schema.signals import (
    DEFAULT_CONNECT,
    SignalSchema,
    generate_notify_signal,
)
from gi_stub_gen.utils import (
    get_py_type_name_repr,
    get_py_type_namespace_repr,
    sanitize_gi_module_name,
    sanitize_variable_name,
)
from gi.repository import GIRepository

# if TYPE_CHECKING:
#     from gi_stub_gen.schema.function import FunctionSchema
from gi_stub_gen.schema.function import FunctionSchema

import logging

logger = logging.getLogger(__name__)


def is_local(py_class: type, method_name: str) -> bool:
    """
    Determines if a method/attribute is defined in the given class (not inherited)."""
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
    module_name: str,
    class_to_parse: Any,
    module_docs: ModuleDocs,
) -> tuple[ClassSchema | None, list[GI.TypeInfo]]:
    """
    Parse a class and return a ClassSchema and a list of GI.TypeInfo callbacks found during parsing.

    Args:
        module_name (str): module name where we are parsing the class
        class_to_parse (Any): class to be parsed
        module_docs (ModuleDocs): module documentation
    Returns:
        tuple[ClassSchema | None, list[GI.TypeInfo]]: parsed ClassSchema and list of GI.TypeInfo callbacks
    """
    from gi_stub_gen.schema.class_ import ClassPropSchema, ClassSchema

    # Check if it is a class
    if type(class_to_parse) not in (gi.types.GObjectMeta, gi.types.StructMeta, type):  # type: ignore
        return None, []

    # Check if the class is in the same module
    # comparing just the last part of the module name
    # because for overrides the previous part can be different
    # ie from gi.repository.Gio get Gio
    final_module_name_part = module_name.split(".")[-1].lower()
    # do the same for the class module
    class_module_name_part = str(class_to_parse.__module__).split(".")[-1].lower()

    # we make an exception for gi._gi classes
    # we parse them anyway if we are in _gi module
    private_gi_exception = (
        final_module_name_part == "_gi" and class_module_name_part == "gi"
    )
    if private_gi_exception:
        # we fake to be in gi module
        final_module_name_part = "gi"

    # filter out classes not in the same namespace as the module
    if final_module_name_part != class_module_name_part:
        # if the class is not in the same namespace as the module, skip it
        # this can happen with classes from gi.repository that are not in the same namespace
        logger.warning(
            f"[SKIP][CLASS_IN_OTHER_NS]{class_to_parse}, {class_to_parse.__name__}, {str(class_to_parse.__module__)}"
        )
        return None, []

    # callbacks_found: list[GI.TypeInfo] = []
    callbacks_found: list[CallbackSchema] = []
    """callbacks found during class parsing, saved to be parsed later"""

    class_props: list[ClassPropSchema] = []
    class_attributes: list[ClassFieldSchema] = []
    class_getters: list[ClassFieldSchema] = []
    class_methods: list[FunctionSchema] = []
    class_python_methods: list[BuiltinFunctionSchema] = []
    class_signals: list[SignalSchema] = []
    class_parsed_elements: list[str] = []
    extra: list[str] = []

    # there is no __init__ in gi methods
    # but it should be the same as the classmethod new
    # with the same args but self instead of cls
    # if we get the new method, we can manually create the __init__ method
    # class_init: FunctionSchema | None = None

    # if the class is a GObject, it has __info__ attribute
    # do a first pass to get all the attributes with get_properties/get_methods
    if hasattr(class_to_parse, "__info__"):
        # if class_to_parse.__name__ == "Element":
        #     breakpoint()

        if hasattr(class_to_parse.__info__, "get_signals"):
            # notify::<property_name>>
            # signal-name
            signal: GIRepository.SignalInfo
            for signal in class_to_parse.__info__.get_signals():
                signal_name = signal.get_name()
                assert signal_name is not None
                signal_name_unescaped: str = signal.get_name_unescaped()  # type: ignore
                s = SignalSchema(
                    name=signal_name,
                    name_unescaped=signal_name_unescaped,
                    namespace=signal.get_namespace(),
                    handler=FunctionSchema.from_gi_object(signal),
                )
                # if signal_name == "notify":
                #     breakpoint()
                class_signals.append(s)
                class_parsed_elements.append(signal_name)
                # print("Signal:", signal.get_name())
                # breakpoint()

        if hasattr(class_to_parse.__info__, "get_fields"):
            # breakpoint()
            field: GIRepository.FieldInfo
            for field in class_to_parse.__info__.get_fields():
                if not should_expose_class_field(field):
                    continue

                field_name = field.get_name()
                assert field_name is not None
                if not is_local(class_to_parse, field_name):
                    continue

                field_name, line_comment = sanitize_variable_name(field_name)
                field_gi_type_info = get_gi_type_info(field)

                # TODO: ERRORE SE CALLBACK NON TORNA IL TIPO E NON POSSO CAPIRE
                # TODO PORTARE A GIRO SU TUTTI I PARSING
                if gi_type_is_callback(field_gi_type_info):
                    cb_info = field_gi_type_info.get_interface()
                    cb_name = cb_info.get_name() + f"{class_to_parse.__name__}CB"
                    cb_namespace = cb_info.get_namespace()
                    cb_schema = FunctionSchema.from_gi_object(cb_info)
                    found_callback = CallbackSchema(
                        name=cb_name,
                        function=cb_schema,
                        originated_from={f"{class_to_parse.__name__}.{field_name}"},
                    )
                    callbacks_found.append(found_callback)
                    prop_type_hint_namespace = cb_namespace
                    prop_type_hint_name = cb_name
                    may_be_null = found_callback.function.may_return_null
                else:
                    field_py_type = gi_type_to_py_type(field_gi_type_info)
                    prop_type_hint_namespace = get_py_type_namespace_repr(field_py_type)
                    prop_type_hint_name = get_py_type_name_repr(field_py_type)
                    may_be_null = is_class_field_nullable(field)

                f = ClassFieldSchema(
                    name=field_name,
                    type_hint_name=prop_type_hint_name,
                    type_hint_namespace=prop_type_hint_namespace,
                    is_deprecated=field.is_deprecated(),
                    docstring=None,  # TODO: retrieve docstring
                    line_comment=None,
                    deprecation_warnings=None,
                    may_be_null=may_be_null,
                )
                class_attributes.append(f)
                class_parsed_elements.append(field_name)
        # Parse Props (they have a getter/setter depending on the flags)
        if hasattr(class_to_parse.__info__, "get_properties"):
            for prop in class_to_parse.__info__.get_properties():
                # start parsing the actual property
                prop_gi_type_info = get_gi_type_info(prop)

                # TODO: !! PARSING CALLBACK (credo non possa succedere nelle prop)
                prop_type = gi_type_to_py_type(prop_gi_type_info)
                prop_type_hint_namespace = get_py_type_namespace_repr(prop_type)
                prop_type_hint_name = get_py_type_name_repr(prop_type)
                sanitized_name, line_comment = sanitize_variable_name(prop.get_name())

                # may_be_null = is_property_nullable_safe(prop)
                may_be_null = is_class_field_nullable(prop)

                # if sanitized_name == "flags":
                #     breakpoint()
                # if may_be_null:
                #     prop_type_hint_full = f"{prop_type_hint_full} | None"

                c = ClassPropSchema(
                    name=sanitized_name,
                    is_deprecated=prop.is_deprecated(),
                    readable=bool(prop.get_flags() & GObject.ParamFlags.READABLE),
                    writable=bool(prop.get_flags() & GObject.ParamFlags.WRITABLE),
                    type_hint_namespace=prop_type_hint_namespace,
                    type_hint_name=prop_type_hint_name,
                    line_comment=line_comment,
                    docstring=None,  # TODO: retrieve docstring
                    may_be_null=may_be_null,
                )
                class_props.append(c)
                class_parsed_elements.append(prop.get_name())

                # also add the notify signal #########################################
                # notify::<property_name>
                signal_name_unescaped: str = prop.get_name_unescaped()  # type: ignore
                class_signals.append(
                    generate_notify_signal(
                        namespace=prop.get_namespace(),
                        signal_name=sanitized_name,
                        signal_name_unescaped=signal_name_unescaped,
                    )
                )
                # end adding the signal ##############################################

        if hasattr(class_to_parse.__info__, "get_methods"):
            for met in class_to_parse.__info__.get_methods():
                parsed_method = parse_function(
                    met,
                    docstring=module_docs.get_function_docstring(met.get_name()),
                )
                if parsed_method:
                    # save callbacks to be parsed later
                    callbacks_found.extend(parsed_method._gi_callbacks)
                    class_methods.append(parsed_method)
                    class_parsed_elements.append(met.get_name())

    # OVERRIDES AND NATIVE PYTHON CLASS ATTRIBUTES
    #
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

        # do not parse already parsed elements
        # i.e. the gi ones
        if attribute_name in class_parsed_elements:
            continue

        # we only parse local attributes, not inherited ones
        is_attribute_local = is_local(class_to_parse, attribute_name)
        if not is_attribute_local:
            continue

        if c := parse_constant(
            module_name="",
            name=attribute_name,
            obj=attribute,
            docstring=None,  # TODO: retrieve docstring with inspect??
        ):
            extra.append(f"constant: {attribute_name} local={is_attribute_local}")
            # class_attributes.append(c)
        # elif attribute_type is method:
        #     ...
        elif attribute_type is MethodType:
            extra.append(f"method: {attribute_name} local={is_attribute_local}")
        elif attribute_type is GetSetDescriptorType:
            # these are @property
            class_getters.append(
                ClassFieldSchema(
                    name=attribute_name,
                    type_hint_name="Any",
                    type_hint_namespace="typing",
                    is_deprecated=False,
                    docstring=None,
                    line_comment=None,
                    deprecation_warnings=None,
                    may_be_null=True,
                )
            )
            # extra.append(f"getset: {attribute_name} local={is_attribute_local}")

        elif attribute_type is FunctionType or attribute_type is BuiltinFunctionType:
            if f := parse_builtin_function(
                attribute=attribute,
                namespace=module_name.removeprefix("gi.repository."),
                name_override=attribute_name,
            ):
                if f.params:
                    # some overrides use instance as first param, rename to self
                    # dont know why they do that though
                    # if f.params[0].name == "instance":
                    if f.params[0].name != "self":
                        f.params[0].name = "self"
                    # f.is_method = True
                class_python_methods.append(f)

                assert attribute_name not in class_parsed_elements, "was parsed twice?"
                class_parsed_elements.append(attribute_name)

            # if attribute_name == "stop_emission_by_name":
            #     breakpoint()

            # import inspect

            # extra.append(
            #     f"function: {attribute_name} local={is_attribute_local} "
            #     f"isfunction={inspect.isfunction(attribute)} "
            #     f"ismethoddescriptor={inspect.ismethoddescriptor(attribute)}"
            #     f"isbuiltin={inspect.isbuiltin(attribute)}"
            # )
        elif attribute_type is MethodDescriptorType:
            # elif attribute_type is method_descriptor:
            # TODO: how to parse this??
            # cant obtain args/return type
            # inspect does not work on builting
            #     breakpoint()

            # if attribute_name == "connect":
            #     class_signals.append(DEFAULT_CONNECT)

            extra.append(
                f"method_descriptor: {attribute_name} local={is_attribute_local}"
            )
        elif attribute_type is property:
            # TODO: how to parse this??
            # cant obtain args/return type
            # inspect does not work on builting
            # if namespace == "gi.repository.Gst":
            #     breakpoint()

            # import gi
            # gi.require_version("Gst", "1.0")
            # from gi.repository import Gst
            # Gst.init()
            # from gi.repository import GIRepository

            # GIRepository.Repository().find_by_name("Gst.AllocationParams", "align")
            # .find_by_name("Gst", "AllocationParams")
            # repo.find_by_name("Gst.AllocationParams", "align")
            extra.append(f"property: {attribute_name} local={is_attribute_local}")

        else:
            # if attribute_name == "__init__":
            #     breakpoint()
            extra.append(
                f"unknown: {attribute_name}: {attribute_type} local={is_attribute_local}"
            )

    # manual override
    # i.e. in GIRepository.TypeInfo we add get_tag_as_string method
    # which is not present in gi.TypeInfo
    # since it has been injected by pygobject
    class_methods = apply_method_overrides(
        class_methods,
        namespace=module_name,
        class_name=class_to_parse.__name__,
    )

    # sort methods by name
    class_attributes.sort(key=lambda x: x.name)
    class_methods.sort(key=lambda x: x.name)
    class_props.sort(key=lambda x: x.name)

    return ClassSchema.from_gi_object(
        namespace=module_name,
        obj=class_to_parse,
        docstring=module_docs.classes.get(class_to_parse.__name__, None),
        props=class_props,
        fields=class_attributes,
        methods=class_methods,
        getters=class_getters,
        builtin_methods=class_python_methods,
        signals=class_signals,
        extra=sorted(extra),
    ), callbacks_found
