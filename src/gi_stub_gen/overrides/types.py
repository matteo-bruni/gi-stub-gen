"""Internal override configuration; declarations do not inspect runtime objects."""

from collections.abc import Callable
from typing import TypedDict

from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema
from gi_stub_gen.schema.class_ import ClassFieldSchema
from gi_stub_gen.schema.function import FunctionSchema

type MethodSchema = FunctionSchema | BuiltinFunctionSchema
type MethodTransform = Callable[[MethodSchema], MethodSchema]
type InitFactory = Callable[[str, type], FunctionSchema]


class ClassOverride(TypedDict, total=False):
    init_factory: InitFactory
    super: list[str]
    methods: dict[str, FunctionSchema | None]
    fields: dict[str, ClassFieldSchema | None]
    property_comments: dict[str, str]
    """Inline comments on selected Props declarations; property types and flags stay parsed."""
    method_transforms: dict[str, MethodTransform]
