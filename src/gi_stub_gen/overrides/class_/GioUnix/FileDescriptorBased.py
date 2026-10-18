"""PyGObject 3.58.1 get_fd wrappers lose the native integer return annotation."""

from gi_stub_gen.overrides.types import MethodSchema
from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema


def transform_get_fd(method: MethodSchema) -> MethodSchema:
    if not isinstance(method, BuiltinFunctionSchema) or [p.name for p in method.params] != ["self"]:
        raise TypeError("GioUnix stream get_fd requires the bound Python wrapper")
    # FileDescriptorBased.get_fd remains static; do not change the bound wrapper to hide that collision.
    method.return_hint_name = "int"
    method.return_hint_namespace = None
    method.return_is_optional = False
    return method
