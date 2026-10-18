"""Internal override configuration; declarations do not inspect runtime objects."""

from collections.abc import Callable
from typing import TypedDict

from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema
from gi_stub_gen.schema.class_ import ClassFieldSchema
from gi_stub_gen.schema.function import FunctionSchema

type MethodSchema = FunctionSchema | BuiltinFunctionSchema
type MethodTransform = Callable[[MethodSchema], MethodSchema]


class ClassOverride(TypedDict, total=False):
    super: list[str]
    methods: dict[str, FunctionSchema | None]
    fields: dict[str, ClassFieldSchema | None]
    method_transforms: dict[str, MethodTransform]
