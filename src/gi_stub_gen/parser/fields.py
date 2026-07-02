import gi._gi as GI  # type: ignore
import gi
from gi.repository import GIRepository

from gi_stub_gen.adapter import GIRepositoryCallableAdapter
from gi_stub_gen.manager.gi_repo import GIRepo
from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.schema.class_ import ClassFieldSchema
from gi_stub_gen.schema.function import CallbackSchema, FunctionSchema
from gi_stub_gen.utils.inspect_utils import _extract_annotation_type_info
from gi_stub_gen.utils.gi_utils import (
    get_gi_type_info,
    gi_type_is_callback,
    gi_type_to_py_type,
    is_class_field_nullable,
)
from gi_stub_gen.utils.utils import sanitize_variable_name


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

    try:
        # in newer library version is is_* on older is without the is
        is_readable = bool(flags & GIRepository.FieldInfoFlags.IS_READABLE)  # type: ignore
        is_writable = bool(flags & GIRepository.FieldInfoFlags.IS_WRITABLE)  # type: ignore
    except Exception:
        try:
            is_readable = bool(flags & GIRepository.FieldInfoFlags.READABLE)  # type: ignore
            is_writable = bool(flags & GIRepository.FieldInfoFlags.WRITABLE)  # type: ignore
        except Exception:
            raise RuntimeError(
                f"Failed to determine field readability/writability for field {field_name} in class {class_name}"
            )

    field_name, line_comment = sanitize_variable_name(field_name)
    field_gi_type_info = get_gi_type_info(field)

    if gi_type_is_callback(field_gi_type_info):
        cb_info = field_gi_type_info.get_interface()
        cb_namespace = cb_info.get_namespace()
        cb_info_name = cb_info.get_name()
        assert cb_info_name is not None

        try:
            named_cb_info = GIRepo().find_by_name(cb_namespace, cb_info_name, gi.get_required_version(cb_namespace))
        except ValueError:
            named_cb_info = GIRepo().find_by_name(cb_namespace, cb_info_name)

        current_namespace = module_name.removeprefix("gi.repository.")
        if cb_namespace != current_namespace or isinstance(named_cb_info, GIRepository.CallbackInfo):
            cb_name = cb_info_name
        else:
            cb_name = cb_info_name + f"{class_name}CB"

        if isinstance(cb_info, GIRepository.CallbackInfo):
            # wrap in adapter to make GIRepository.CallbackInfo compatible
            # with GI.CallbackInfo used in FunctionSchema.from_gi_object
            cb_info = GIRepositoryCallableAdapter(cb_info)

        cb_schema = FunctionSchema.from_gi_object(cb_info)
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
        prop_type_hint_name, prop_type_hint_namespace = _extract_annotation_type_info(
            field_py_type,
            current_namespace=module_name.removeprefix("gi.repository."),
        )
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

    # this is different in depending on glib version,
    # in newer library version is is_* on older is without the is
    # but we can check both to be safe
    try:
        is_readable = bool(flags & GIRepository.FieldInfoFlags.IS_READABLE)  # type: ignore
    except Exception:
        try:
            is_readable = bool(flags & GIRepository.FieldInfoFlags.READABLE)  # type: ignore
        except Exception:
            raise RuntimeError(f"Failed to determine field readability for field {name}")

    if not is_readable:
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
