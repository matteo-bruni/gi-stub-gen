"""Restore callback types hidden by PyGObject 3.58.1's unannotated Python wrapper."""

from gi_stub_gen.overrides.types import MethodSchema
from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema, TypeVarSchema


def transform_set_cell_data_func(method: MethodSchema) -> MethodSchema:
    if not isinstance(method, BuiltinFunctionSchema) or [p.name for p in method.params] != [
        "self", "cell_renderer", "func", "func_data",
    ]:
        raise TypeError("Gtk.TreeViewColumn.set_cell_data_func requires the Python wrapper")
    # Unlike CellLayout's marshaller, this wrapper accepts one func_data, not arbitrary *args.
    method.return_hint_name = "None"
    method.return_hint_namespace = None
    method.return_is_optional = False
    variants: list[BuiltinFunctionSchema] = []
    for payload in ("None", "DataT", "reset"):
        variant = method.model_copy(deep=True)
        variant.overloads = []
        variant.method_type_vars = [] if payload == "reset" else [
            TypeVarSchema(name="RendererT", bound_hint_name="CellRenderer", bound_hint_namespace="Gtk"),
        ]
        if payload == "DataT":
            variant.method_type_vars.append(TypeVarSchema(name="DataT"))
        renderer, callback, data = variant.params[1:]
        renderer.type_hint_name = "CellRenderer" if payload == "reset" else "RendererT"
        callback.type_hint_name = "None" if payload == "reset" else (
            f"typing.Callable[[TreeViewColumn, RendererT, TreeModel, TreeIter, {payload}], None]"
        )
        data.type_hint_name = "object | None" if payload == "reset" else payload
        data.default_value = None if payload == "DataT" else "None"
        for param in (renderer, callback, data):
            param.type_hint_namespace = None
            param.is_optional = False
        variant.type_imports.add("typing")
        variants.append(variant)
    method.overloads = variants
    return method
