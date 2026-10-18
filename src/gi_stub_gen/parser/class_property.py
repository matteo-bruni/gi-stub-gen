"""Project GI properties and their accessor metadata into stub declarations."""

import gi._gi as GI
from gi.repository import GObject, GIRepository

from gi_stub_gen.adapter import GIRepositoryCallableAdapter
from gi_stub_gen.schema.class_ import ClassPropSchema
from gi_stub_gen.utils.gi_utils import get_gi_type_info, gi_type_to_py_type, is_class_field_nullable
from gi_stub_gen.utils.inspect_utils import _extract_annotation_type_info
from gi_stub_gen.utils.utils import sanitize_variable_name


def parse_class_property(
    prop: GI.PropertyInfo,
    accessor_info: GIRepository.PropertyInfo | None,
    namespace: str,
    docstring: str | None,
) -> ClassPropSchema:
    name = prop.get_name()
    assert name is not None
    name, comment = sanitize_variable_name(name)
    imports: set[str] = set()

    def annotation(info: GI.TypeInfo | GIRepository.TypeInfo | GIRepositoryCallableAdapter) -> tuple[str, str | None]:
        return _extract_annotation_type_info(
            gi_type_to_py_type(info), current_namespace=namespace, required_imports=imports
        )

    read_name, read_namespace = annotation(get_gi_type_info(prop))
    read_nullable = is_class_field_nullable(prop)
    write_name, write_namespace, write_nullable = read_name, read_namespace, read_nullable
    if accessor_info is not None:
        getter = accessor_info.get_getter()
        setter = accessor_info.get_setter()
        if getter is not None:
            read_name, read_namespace = annotation(GIRepositoryCallableAdapter(getter.get_return_type()))
            read_nullable = getter.may_return_null()
        if setter is not None and setter.get_n_args() == 1:
            argument = setter.get_arg(0)
            write_name, write_namespace = annotation(get_gi_type_info(GIRepositoryCallableAdapter(argument)))
            write_nullable = argument.may_be_null()
    flags = prop.get_flags()
    return ClassPropSchema(
        name=name,
        docstring=docstring,
        line_comment=comment,
        is_deprecated=prop.is_deprecated(),
        readable=bool(flags & GObject.ParamFlags.READABLE),
        writable=bool(flags & GObject.ParamFlags.WRITABLE),
        construct_only=bool(flags & GObject.ParamFlags.CONSTRUCT_ONLY),
        type_hint_name=read_name,
        type_hint_namespace=read_namespace,
        may_be_null=read_nullable,
        write_type_hint_name=write_name,
        write_type_hint_namespace=write_namespace,
        write_may_be_null=write_nullable,
        type_imports=imports,
    )
