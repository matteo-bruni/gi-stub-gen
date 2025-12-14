from __future__ import annotations
from types import BuiltinFunctionType, FunctionType

import gi._gi as GI  # type: ignore
from typing import Any
import inspect


from gi_stub_gen.schema.function import (
    ArgKind,
    BuiltinFunctionArgumentSchema,
    BuiltinFunctionSchema,
)
from gi_stub_gen.utils import get_redacted_stub_value


def _format_type(t) -> str:
    if t is inspect.Parameter.empty:
        return "typing.Any"
    return getattr(t, "__name__", str(t).replace("typing.", ""))


def parse_builtin_function(
    attribute: Any,
    namespace: str,
    name_override: str | None = None,
) -> BuiltinFunctionSchema | None:
    # pure python function check
    is_function = isinstance(attribute, FunctionType)

    # function check for built-in functions implemented in C
    is_builtin_function = isinstance(attribute, BuiltinFunctionType)

    if not is_function and not is_builtin_function:
        return None

    if name_override is not None:
        name = name_override
    else:
        name = getattr(attribute, "__name__", "unknown")

    try:
        sig = inspect.signature(attribute)
    except (ValueError, TypeError):
        # Fallback logic for C-extensions/GObject
        return BuiltinFunctionSchema(
            name=name,
            namespace=namespace,
            return_hint="typing.Any",
            docstring=inspect.getdoc(attribute) or "No docstring",
            params=[
                BuiltinFunctionArgumentSchema(
                    name="args",
                    type_hint="typing.Any",
                    kind=ArgKind.VAR_POSITIONAL,
                    default_value=None,
                ),
                BuiltinFunctionArgumentSchema(
                    name="kwargs",
                    type_hint="typing.Any",
                    kind=ArgKind.VAR_KEYWORD,
                    default_value=None,
                ),
            ],
        )

    # Main Parsing Loop
    args_schema = []
    for param_name, param in sig.parameters.items():
        # 1. Handle Default Value (using your helper)
        def_val = None
        if param.default is not inspect.Parameter.empty:
            def_val = get_redacted_stub_value(param.default)

        # 2. Create Schema Argument
        # NOTICE: Usage of ArgKind.from_inspect(param.kind)
        arg = BuiltinFunctionArgumentSchema(
            name=param_name,
            type_hint=_format_type(param.annotation),
            kind=ArgKind.from_inspect(param.kind),
            default_value=def_val,
        )
        args_schema.append(arg)

    return BuiltinFunctionSchema(
        name=name,
        namespace=namespace,
        is_async=inspect.iscoroutinefunction(attribute),
        docstring=inspect.getdoc(attribute) or "No docstring",
        return_hint=_format_type(sig.return_annotation),
        params=args_schema,
    )
