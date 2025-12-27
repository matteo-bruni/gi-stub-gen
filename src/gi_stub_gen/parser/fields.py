import gi._gi as GI  # type: ignore
from gi.repository import GIRepository

from gi_stub_gen.adapter import GIRepositoryCallableAdapter
from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.schema.class_ import ClassFieldSchema
from gi_stub_gen.schema.function import CallbackSchema, FunctionSchema
from gi_stub_gen.utils.gi_utils import (
    get_gi_type_info,
    gi_type_is_callback,
    gi_type_to_py_type,
    is_class_field_nullable,
)
from gi_stub_gen.utils.utils import get_py_type_name_repr, get_py_type_namespace_repr, sanitize_variable_name


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
