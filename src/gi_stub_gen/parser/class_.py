from __future__ import annotations
import importlib

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

from gi_stub_gen.adapter import GIRepositoryCallableAdapter
from gi_stub_gen.manager.gi_repo import GIRepo
from gi_stub_gen.utils.gi_utils import (
    MAP_GI_GTYPE_TO_TYPE,
    get_gi_type_info,
    gi_type_is_callback,
    gi_type_to_py_type,
    is_class_field_nullable,
)
from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.overrides import apply_field_overrides, apply_method_overrides

from gi_stub_gen.parser.python_function import parse_python_function
from gi_stub_gen.parser.constant import parse_constant
from gi_stub_gen.parser.function import parse_function


from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema
from gi_stub_gen.schema.class_ import ClassFieldSchema, ClassSchema
from gi_stub_gen.schema.function import (
    CallbackSchema,
    FunctionArgumentSchema,
)
from gi_stub_gen.schema.signals import (
    SignalSchema,
    generate_notify_signal,
)
from gi_stub_gen.utils.gst import get_fraction_value
from gi_stub_gen.utils.utils import (
    get_py_type_name_repr,
    get_py_type_namespace_repr,
    sanitize_variable_name,
)
from gi.repository import GIRepository

from gi_stub_gen.schema.function import FunctionSchema

import logging

logger = logging.getLogger(__name__)


def is_local(py_class: type, method_name: str) -> bool:
    """
    Determines if a method/attribute is defined in the given class (not inherited)."""
    return method_name in py_class.__dict__


def gi_parse_field(
    field: GIRepository.FieldInfo | GI.FieldInfo,
    module_name: str,
    class_name: str,
) -> tuple[ClassFieldSchema, CallbackSchema | None]:
    """
    Parse a struct/class field.
    A class field can be a callback, in that case a CallbackSchema is also returned.

    Args:
        field (GIRepository.FieldInfo | GI.FieldInfo): field info object
        module_name (str): module name where the class is defined
        class_name (str): class name where the field is defined

    Returns:
        tuple: parsed ClassFieldSchema and found CallbackSchema (if any)
    """

    field_name = field.get_name()
    assert field_name is not None

    found_callback: CallbackSchema | None = None
    """callbacks found during field parsing, saved to be parsed later"""

    flags = field.get_flags()
    is_readable = bool(flags & GIRepository.FieldInfoFlags.READABLE)
    is_writable = bool(flags & GIRepository.FieldInfoFlags.WRITABLE)

    field_name, line_comment = sanitize_variable_name(field_name)
    field_gi_type_info = get_gi_type_info(field)

    if gi_type_is_callback(field_gi_type_info):
        cb_info = field_gi_type_info.get_interface()
        cb_namespace = cb_info.get_namespace()

        # if callback is from another namespace, keep original name
        # otherwise append class name to avoid name clashes
        if cb_namespace != module_name.removeprefix("gi.repository."):
            cb_name = cb_info.get_name()
        else:
            cb_name = cb_info.get_name() + f"{class_name}CB"

        if isinstance(cb_info, GIRepository.CallbackInfo):
            # wrap in adapter to make GIRepository.CallbackInfo compatible
            # with GI.CallbackInfo used in FunctionSchema.from_gi_object
            cb_info = GIRepositoryCallableAdapter(cb_info)

        cb_schema = FunctionSchema.from_gi_object(cb_info)
        # TODO: callback can have callback as param? handle that case
        # cb_schema._gi_callbacks <- extend with found_callback and return list?
        found_callback = CallbackSchema(
            name=cb_name,
            function=cb_schema,
            originated_from={f"{class_name}.{field_name}"},
        )
        prop_type_hint_namespace = cb_namespace
        prop_type_hint_name = cb_name
        may_be_null = found_callback.function.may_return_null
    else:
        field_py_type = gi_type_to_py_type(field_gi_type_info)
        prop_type_hint_namespace = get_py_type_namespace_repr(field_py_type)
        prop_type_hint_name = get_py_type_name_repr(field_py_type)
        may_be_null = is_class_field_nullable(field)

    return ClassFieldSchema(
        name=field_name,
        type_hint_name=prop_type_hint_name,
        type_hint_namespace=prop_type_hint_namespace,
        is_deprecated=field.is_deprecated(),
        docstring=GIRDocs().get_class_field_docstring(
            class_name=class_name,
            field_name=field_name,
        ),
        line_comment=line_comment,
        deprecation_warnings=None,
        may_be_null=may_be_null,
        is_readable=is_readable,
        is_writable=is_writable,
    ), found_callback


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


def create_init_method(namespace: str, real_cls: Any) -> FunctionSchema | None:
    """
    Create an __init__ stub by inspecting the real Python class via PyGObject.
    This captures all properties (parents + interfaces) exactly as Python sees them.

    Args:
        real_cls: The actual Python class object (e.g. Gtk.Box, not the GI info).
    """

    # BEWARE!: if looping through GObject.list_properties(real_cls)
    # GObject.GInterface will segfault (pygobject version 3.54.0)
    # when doing list_properties on it.
    if real_cls is GObject.GInterface:
        return None

    # retrieve all properties of the class including parents and interfaces.
    try:
        props = GObject.list_properties(real_cls)
    except TypeError:
        # this happens if real_cls is not a GObject (eg. simple structs or enums)
        return None

    args: list[FunctionArgumentSchema] = []

    seen_props = set()
    prop_spec: GObject.ParamSpec
    for prop_spec in sorted(props, key=lambda x: x.name):
        name = prop_spec.name  # Es: "secondary-icon-name"
        logger.debug(f"# Property: {name}")

        if name in seen_props:
            logger.debug(f"  - {name} skipping duplicate property")
            continue
        seen_props.add(name)

        # Controlliamo i Flags: ci interessano WRITABLE o CONSTRUCT
        flags = prop_spec.flags
        assert flags is not None, "ParamSpec flags is None"
        # GObject.ParamFlags.WRITABLE = 2, CONSTRUCT = 4, CONSTRUCT_ONLY = 8
        is_writable = (
            (flags & GObject.ParamFlags.WRITABLE)
            or (flags & GObject.ParamFlags.CONSTRUCT)
            or (flags & GObject.ParamFlags.CONSTRUCT_ONLY)
        )
        is_deprecated = bool(flags & GObject.ParamFlags.DEPRECATED)
        if not is_writable:
            logger.debug(f"  - {name} skipping non-writable/non-construct property")
            continue

        sane_arg_name, line_comment = sanitize_variable_name(name)
        blurb = prop_spec.get_blurb()
        if blurb:
            if line_comment:
                line_comment += f" {blurb}"
            else:
                line_comment = blurb

        # 5. Risoluzione Tipo Python
        gtype = prop_spec.value_type
        pytype = gtype.pytype

        if pytype is None:
            # TODO: find by name?
            # Gtk.PrintBackend non viene trovato
            # maybe it does not work beacuse it is not loaded yet?
            info = GIRepo().raw.find_by_gtype(gtype)
            if info:
                gi_ns = info.get_namespace()  # es. "Gtk"
                gi_name = info.get_name()  # es. "Application"
                assert gi_ns is not None and gi_name is not None
                try:
                    module = importlib.import_module(f"gi.repository.{gi_ns}")

                    # this works and let pygobject register the wrapper and set gtype.pytype
                    pytype = getattr(module, gi_name)
                    # now gtype.pytype should be set
                    # pytype = gtype.pytype

                except (ImportError, AttributeError):
                    pass
            else:
                # we try  via find_by_name guessing the name
                # eg. Gtk.PrintBackend has no gtype registered but it exists in the GIR
                c_name = gtype.name  # Es: "GtkPrintBackend"
                if c_name and c_name.startswith(namespace):
                    guessed_name = c_name[len(namespace) :]
                    info_by_name = GIRepo().find_by_name(namespace, guessed_name)
                    if info_by_name:
                        gi_ns = info_by_name.get_namespace()  # es. "Gtk"
                        gi_name = info_by_name.get_name()  # es. "Application"
                        assert gi_ns is not None and gi_name is not None
                        try:
                            module = importlib.import_module(f"gi.repository.{gi_ns}")
                            pytype = getattr(module, gi_name)
                        except (ImportError, AttributeError):
                            pass

        if pytype is None:
            # pass from here only if we fail to load the type
            default_value_repr = "None"
            if gtype not in MAP_GI_GTYPE_TO_TYPE:
                breakpoint()
                assert False, f"Unknown gtype with no pytype in ParamSpec: {gtype}: {gtype.name}"
            pytype = MAP_GI_GTYPE_TO_TYPE.get(gtype, None)
            py_type_hint_name = get_py_type_name_repr(pytype)
            py_type_hint_namespace = get_py_type_namespace_repr(pytype)

        else:
            if pytype is GObject.ValueArray:
                # it is deprecated move to list
                pytype = list
                default_value_repr = "None"
                py_type_hint_name = pytype.__name__
                py_type_hint_namespace = get_py_type_namespace_repr(pytype)

            elif issubclass(pytype, (GObject.GEnum, GObject.GFlags)):
                # Enum/Flag type
                py_type_hint_name = pytype.__name__
                py_type_hint_namespace = get_py_type_namespace_repr(pytype)

                default_value = prop_spec.get_default_value()
                default_value_repr = repr(prop_spec.get_default_value())
                # Enums/Flags: usiamo il nome dell'enum/flag come default
                # default_value = f"{py_type_hint_namespace}.{py_type_hint_name}({default_value})"
                try:
                    actual_default = pytype(default_value)
                    if actual_default.name is None:
                        # this can happen in flags when default is 0 and no flag has value 0
                        default_value_repr = "None"
                    elif "|" in actual_default.name:
                        # multiple flags combined
                        ns = (
                            f"{py_type_hint_namespace}."
                            if py_type_hint_namespace and py_type_hint_namespace != namespace
                            else ""
                        )
                        default_value_repr = " | ".join(
                            f"{ns}{py_type_hint_name}.{part.strip()}" for part in actual_default.name.split("|")
                        )

                    else:
                        default_value_repr = f"{py_type_hint_name}.{actual_default.name}"
                        if py_type_hint_namespace != namespace:
                            default_value_repr = f"{py_type_hint_namespace}.{default_value_repr}"
                except Exception:
                    # fallback: usiamo il valore numerico
                    default_value_repr = repr(prop_spec.get_default_value())
            else:
                # regular type
                py_type_hint_name = get_py_type_name_repr(pytype)
                py_type_hint_namespace = get_py_type_namespace_repr(pytype)
                try:
                    # check if its a fraction
                    default_value_repr = get_fraction_value(prop_spec.get_default_value())
                    if not default_value_repr:
                        default_value_repr = repr(prop_spec.get_default_value())
                except TypeError:
                    default_value_repr = "None" if is_class_field_nullable(prop_spec) else "..."
                    # breakpoint()

        args.append(
            FunctionArgumentSchema(
                direction="IN",
                name=sane_arg_name,
                namespace=namespace,
                may_be_null=is_class_field_nullable(prop_spec),
                is_optional=True,
                is_callback=False,
                get_array_length=-1,
                is_deprecated=is_deprecated,
                is_caller_allocates=False,
                tag_as_string="",
                line_comment=line_comment,
                py_type_name=py_type_hint_name,
                py_type_namespace=py_type_hint_namespace,  # Gestito nella stringa sopra
                default_value=default_value_repr,  # Default standard per kwarg opzionale
                is_pointer=False,
            )
        )

    # create __init__ method schema
    class_init = FunctionSchema(
        name="__init__",
        namespace=namespace,
        is_method=True,
        is_deprecated=False,
        deprecation_warnings=None,
        docstring=f"Initialize {real_cls.__name__} object with properties.",
        args=args,
        is_callback=False,
        can_throw_gerror=False,
        is_async=False,
        is_constructor=False,  # <- it is not a constructor in Python
        is_getter=False,
        is_setter=False,
        may_return_null=False,
        return_hint="None",
        return_hint_namespace=None,
        skip_return=False,
        wrap_vfunc=False,
        line_comment=None,
        function_type="FunctionInfo",
        is_overload=False,
    )
    return class_init


def parse_class(
    module_name: str,
    class_to_parse: Any,
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
    private_gi_exception = final_module_name_part == "_gi" and class_module_name_part == "gi"
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
    class_fields: list[ClassFieldSchema] = []
    # class_getters: list[ClassFieldSchema] = []
    class_methods: list[FunctionSchema] = []
    class_python_methods: list[BuiltinFunctionSchema] = []
    class_signals: list[SignalSchema] = []
    class_parsed_elements: list[str] = []
    extra: list[str] = []

    # retrieve GI info object and parse its properties/methods/signals
    class_info = class_to_parse.__info__ if hasattr(class_to_parse, "__info__") else None
    class_signals_to_parse: list[GIRepository.SignalInfo] = (
        class_info.get_signals() if class_info and hasattr(class_info, "get_signals") else []
    )
    class_fields_to_parse: list[GIRepository.FieldInfo] = (
        class_info.get_fields() if class_info and hasattr(class_info, "get_fields") else []
    )
    class_properties_to_parse: list[GIRepository.PropertyInfo] = (
        class_info.get_properties() if class_info and hasattr(class_info, "get_properties") else []
    )
    class_methods_to_parse: list[GIRepository.CallableInfo] = (
        class_info.get_methods() if class_info and hasattr(class_info, "get_methods") else []
    )

    #######################################################################################
    # parse fields
    #######################################################################################
    for field in class_fields_to_parse:
        # it is possible to have a both a field and a method
        # with the same name, due to how in C structs are defined
        # in python we keep only the method so we need to check
        # if there is a method with the same name and skip it if so
        if any(m.get_name() == field.get_name() for m in class_methods_to_parse):
            logger.debug(
                f"skipping field {field.get_name()} of class {class_to_parse.__name__} because there is a method with the same name"
            )
            continue

        if not should_expose_class_field(field):
            logger.debug(f"not exposing field {field.get_name()} of class {class_to_parse.__name__}")
            continue

        field_name = field.get_name()
        assert field_name is not None
        if not is_local(class_to_parse, field_name):
            continue

        f, cb = gi_parse_field(
            field=field,
            module_name=module_name,
            class_name=class_to_parse.__name__,
        )
        if cb is not None:
            callbacks_found.append(cb)
        class_fields.append(f)
        class_parsed_elements.append(field_name)

    #######################################################################################
    # parse methods
    #######################################################################################
    for met in class_methods_to_parse:
        m_name = met.get_name()
        assert m_name is not None, "Method name is None"
        parsed_method = parse_function(
            met,
            docstring=GIRDocs().get_class_method_docstring(
                class_name=class_to_parse.__name__,
                method_name=m_name,
            ),
        )
        if parsed_method:
            # save callbacks to be parsed later
            callbacks_found.extend(parsed_method._gi_callbacks)
            class_methods.append(parsed_method)
            class_parsed_elements.append(m_name)

            if parsed_method.name == "connect":
                msg = f"[note from gi-stub-gen] {class_to_parse.__name__} has a connect() method which shadows the signal connect() method to add handlers to GObject.Signals. You can still connect to signals using: GObject.Object.connect(object, 'signal-name', handler)"
                if parsed_method.docstring is None:
                    parsed_method.docstring = msg
                else:
                    parsed_method.docstring += "\n\n" + msg

    #######################################################################################
    # parse signals
    #######################################################################################
    # if there is already a method named "connect()" we cant add the signal
    # because they are shadowd by the method
    # for example this happens in Gio.SocketClient where its connect() method
    # shadows the connect() method added by GObject.Signals
    if "connect" not in class_parsed_elements:
        # notify::<property_name>> -> will be added when parsing properties
        # signal-name
        for signal in class_signals_to_parse:
            signal_name = signal.get_name()
            assert signal_name is not None
            signal_name_unescaped: str = signal.get_name_unescaped()  # type: ignore
            flags = signal.get_flags()

            s = SignalSchema(
                name=signal_name,
                name_unescaped=signal_name_unescaped,
                namespace=signal.get_namespace(),
                handler=FunctionSchema.from_gi_object(signal),
                docstring=GIRDocs().get_class_signal_docstring(
                    class_name=class_to_parse.__name__,
                    signal_name=signal_name,
                ),
                run_first=bool(flags & GObject.SignalFlags.RUN_FIRST),
                run_last=bool(flags & GObject.SignalFlags.RUN_LAST),
                run_cleanup=bool(flags & GObject.SignalFlags.RUN_CLEANUP),
                no_recurse=bool(flags & GObject.SignalFlags.NO_RECURSE),
                detailed=bool(flags & GObject.SignalFlags.DETAILED),
                action=bool(flags & GObject.SignalFlags.ACTION),
                no_hooks=bool(flags & GObject.SignalFlags.NO_HOOKS),
                must_collect=bool(flags & GObject.SignalFlags.MUST_COLLECT),
                is_deprecated=bool(flags & GObject.SignalFlags.DEPRECATED),
            )
            # if signal_name == "notify":
            #     breakpoint()
            class_signals.append(s)
            class_parsed_elements.append(signal_name)

    #######################################################################################
    # parse properties
    #######################################################################################
    # Parse Props (they have a getter/setter depending on the flags)
    for prop in class_properties_to_parse:
        # start parsing the actual property
        prop_gi_type_info = get_gi_type_info(prop)

        # TODO: !! PARSING CALLBACK (credo non possa succedere nelle prop)
        prop_type = gi_type_to_py_type(prop_gi_type_info)
        prop_type_hint_namespace = get_py_type_namespace_repr(prop_type)
        prop_type_hint_name = get_py_type_name_repr(prop_type)
        p_name = prop.get_name()
        assert p_name is not None, "Property name is None"
        sanitized_name, line_comment = sanitize_variable_name(p_name)

        # may_be_null = is_property_nullable_safe(prop)
        may_be_null = is_class_field_nullable(prop)

        c = ClassPropSchema(
            name=sanitized_name,
            is_deprecated=prop.is_deprecated(),
            readable=bool(prop.get_flags() & GObject.ParamFlags.READABLE),
            writable=bool(prop.get_flags() & GObject.ParamFlags.WRITABLE),
            type_hint_namespace=prop_type_hint_namespace,
            type_hint_name=prop_type_hint_name,
            line_comment=line_comment,
            docstring=GIRDocs().get_class_property_docstring(
                class_name=class_to_parse.__name__,
                property_name=p_name,
            ),
            may_be_null=may_be_null,
        )
        class_props.append(c)
        class_parsed_elements.append(p_name)

        # also add the notify signal #########################################
        # notify::<property_name>

        # if there is already a method named "connect()" we cant add the signal
        # because they are shadowed by the method
        # for example this happens in Gio.SocketClient where its connect() method
        # shadows the connect() method added by GObject.Signals
        if "connect" not in class_parsed_elements:
            signal_name_unescaped: str = prop.get_name_unescaped()  # type: ignore
            class_signals.append(
                generate_notify_signal(
                    namespace=prop.get_namespace(),
                    signal_name=sanitized_name,
                    signal_name_unescaped=signal_name_unescaped,
                    docstring=None,  # no docstring for notify signals
                )
            )
        # end adding the signal ##############################################

    #######################################################################################
    # SEARCH FOR ADDITIONAL FIELDS VIA GIRepo
    #######################################################################################
    # some classes like GLib.Error have no __info__ so we cant parse from gi info
    # we rely on GIRepository to get them
    type_info = GIRepo().find_by_name(
        module_name.removeprefix("gi.repository."),
        class_to_parse.__name__,
        target_type=GIRepository.BaseInfo,
    )
    if type_info is not None and isinstance(type_info, (GIRepository.ObjectInfo, GIRepository.StructInfo)):
        for i in range(type_info.get_n_fields()):
            field = type_info.get_field(i)
            field_name = field.get_name()
            assert field_name is not None
            if field_name not in class_parsed_elements:
                f, cb = gi_parse_field(
                    field=field,
                    module_name=module_name,
                    class_name=class_to_parse.__name__,
                )
                if cb is not None:
                    callbacks_found.append(cb)
                class_fields.append(f)
                class_parsed_elements.append(field_name)

    #######################################################################################
    # OVERRIDES AND NATIVE PYTHON CLASS ATTRIBUTES
    #######################################################################################
    # do a second pass to get all the attributes not parsed by get_properties/get_methods
    # i.e class not from GI but added in overrides
    for attribute_name in dir(class_to_parse):
        if attribute_name.startswith("_") and attribute_name != "__init__":
            # skip dunder methods
            continue
        try:
            attribute = getattr(class_to_parse, attribute_name)
        except AttributeError as e:
            logger.warning(f"Could not get attribute {attribute_name} from {class_to_parse.__name__}: {e}")
            breakpoint()
            continue

        attribute_type = type(attribute)

        # do not parse already parsed elements
        # i.e. the gi ones
        # if attribute_name in class_parsed_elements:
        #     # set the previously parsed element as overridden
        #     if attribute_name in [m.name for m in class_methods]:
        #         for m in class_methods:
        #             if m.name == attribute_name:
        #                 m.is_overridden = True
        #                 break
        #     else:
        #         breakpoint()
        #     continue

        # we only parse local attributes, not inherited ones
        is_attribute_local = is_local(class_to_parse, attribute_name)
        if not is_attribute_local:
            continue

        if c := parse_constant(
            module_name="",
            name=attribute_name,
            obj=attribute,
            docstring=GIRDocs().get_class_field_docstring(
                class_name=class_to_parse.__name__,
                field_name=attribute_name,
            ),
        ):
            extra.append(f"constant: {attribute_name} local={is_attribute_local}")

        elif attribute_type is GetSetDescriptorType:
            if attribute_name in class_parsed_elements:
                breakpoint()
            # these are @property
            # in classfield will be considered a property
            # when is_readable but not is_writable
            class_fields.append(
                ClassFieldSchema(
                    name=attribute_name,
                    type_hint_name="Any",
                    type_hint_namespace="typing",
                    is_deprecated=False,
                    docstring=None,
                    line_comment=None,
                    deprecation_warnings=None,
                    may_be_null=True,
                    is_readable=True,
                    is_writable=False,
                )
            )

        elif attribute_type in {MethodType, FunctionType, BuiltinFunctionType}:
            if f := parse_python_function(
                attribute=attribute,
                namespace=module_name.removeprefix("gi.repository."),
                name_override=attribute_name,
            ):
                if f.name == "__init__":
                    # some zelous overrides define __init__ with return type Any..
                    # we fix that here
                    if f.return_hint_name == "Any":
                        f.return_hint_name = "None"
                        f.return_hint_namespace = None

                class_python_methods.append(f)
                if attribute_name in class_parsed_elements:
                    # set the previously parsed element as overridden
                    for m in class_methods:
                        if m.name == attribute_name:
                            m.is_overridden = True
                            if f.docstring:
                                f.docstring = f"[is-override: Note this method is an override in Python of the original gi implementation.]\n\n{f.docstring}"
                            else:
                                f.docstring = "[is-override: Note this method is an override in Python of the original gi implementation.]"
                            break
                    # assert attribute_name not in class_parsed_elements, "was parsed twice?"
                class_parsed_elements.append(attribute_name)

        elif attribute_type is MethodDescriptorType:
            extra.append(f"method_descriptor: {attribute_name} local={is_attribute_local}")
        elif attribute_type is property:
            extra.append(f"property: {attribute_name} local={is_attribute_local}")
        else:
            extra.append(f"unknown: {attribute_name}: {attribute_type} local={is_attribute_local}")

    # manual override
    # i.e. in GIRepository.TypeInfo we add get_tag_as_string method
    # which is not present in gi.TypeInfo
    # since it has been injected by pygobject
    class_methods = apply_method_overrides(
        class_methods,
        namespace=module_name,
        class_name=class_to_parse.__name__,
    )
    class_fields = apply_field_overrides(
        class_fields,
        namespace=module_name,
        class_name=class_to_parse.__name__,
    )

    # add __init__ method
    is_init_present_in_methods = any(method.name == "__init__" for method in class_methods)
    is_init_present_in_python_methods = any(method.name == "__init__" for method in class_python_methods)
    if not (is_init_present_in_methods or is_init_present_in_python_methods):
        if init_method := create_init_method(
            namespace=module_name.removeprefix("gi.repository."),
            real_cls=class_to_parse,
        ):
            class_methods.insert(0, init_method)

    # sort methods by name
    class_fields.sort(key=lambda x: x.name)
    class_methods.sort(key=lambda x: x.name)
    class_props.sort(key=lambda x: x.name)

    return ClassSchema.from_gi_object(
        namespace=module_name,
        obj=class_to_parse,
        props=class_props,
        fields=class_fields,
        methods=class_methods,
        builtin_methods=class_python_methods,
        signals=class_signals,
        extra=sorted(extra),
    ), callbacks_found
