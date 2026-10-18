"""Atk returns NULL for an unset object name/description despite GI's str return."""

from gi_stub_gen.overrides.types import MethodSchema
from gi_stub_gen.schema.function import FunctionSchema


def transform_nullable_text(method: MethodSchema) -> MethodSchema:
    if not isinstance(method, FunctionSchema) or method.return_hint != "str":
        raise TypeError("Atk.Object name/description getters require a GI string return")
    method.may_return_null = True
    return method
