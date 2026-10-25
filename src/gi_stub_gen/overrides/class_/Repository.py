"""Verified internal Repository signature, also exposed through gi.Repository."""

from gi_stub_gen.overrides.types import MethodSchema
from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema


def transform_get_default(method: MethodSchema) -> MethodSchema:
    if not isinstance(method, BuiltinFunctionSchema) or [p.name for p in method.params] not in ([], ["args", "kwargs"]):
        raise TypeError("PyGObject Repository.get_default signature changed")
    method.params = []
    method.is_staticmethod = True
    method.is_classmethod = False
    method.return_hint_name = "Repository"
    method.return_hint_namespace = None
    method.return_is_optional = False
    return method
