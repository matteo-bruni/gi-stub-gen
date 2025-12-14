from __future__ import annotations
from types import BuiltinFunctionType, FunctionType, MethodDescriptorType, MethodType

import gi._gi as GI  # type: ignore
from typing import Any
import inspect


from gi_stub_gen.schema.function import (
    ArgKind,
    BuiltinFunctionArgumentSchema,
    BuiltinFunctionSchema,
)
from gi_stub_gen.utils import get_redacted_stub_value, sanitize_gi_module_name


def _format_type(t) -> str:
    if t is inspect.Parameter.empty:
        return "Any"
    return getattr(t, "__name__", str(t).replace("typing.", ""))


def _format_type_namespace(t) -> str | None:
    if t is inspect.Parameter.empty:
        return "typing"
    ns = getattr(t, "__module__", None)
    if ns == "builtins":
        return None
    if ns:
        ns = sanitize_gi_module_name(ns)
    return ns


def parse_builtin_function(
    attribute: Any,
    namespace: str,
    name_override: str | None = None,
) -> BuiltinFunctionSchema | None:
    """
    Parse a pure Python function into a BuiltinFunctionSchema using inspect.

    """

    # pure python function check
    is_function = isinstance(attribute, FunctionType)

    # function check for built-in functions implemented in C
    is_builtin_function = isinstance(attribute, BuiltinFunctionType)
    is_method = isinstance(attribute, MethodType)

    if not is_function and not is_builtin_function and not is_method:
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
            return_hint_name="Any",
            return_hint_namespace="typing",
            docstring=inspect.getdoc(attribute),
            is_method=is_method,
            is_async=False,
            params=[
                BuiltinFunctionArgumentSchema(
                    name="args",
                    type_hint_name="Any",
                    type_hint_namespace="typing",
                    kind=ArgKind.VAR_POSITIONAL,
                    default_value=None,
                ),
                BuiltinFunctionArgumentSchema(
                    name="kwargs",
                    type_hint_name="Any",
                    type_hint_namespace="typing",
                    kind=ArgKind.VAR_KEYWORD,
                    default_value=None,
                ),
            ],
        )

    # Main Parsing Loop
    args_schema = []
    for param_name, param in sig.parameters.items():
        def_val = None
        if param.default is not inspect.Parameter.empty:
            def_val = get_redacted_stub_value(param.default)

        arg = BuiltinFunctionArgumentSchema(
            name=param_name,
            type_hint_name=_format_type(param.annotation),
            type_hint_namespace=_format_type_namespace(param.annotation),
            kind=ArgKind.from_inspect(param.kind),
            default_value=def_val,
        )
        args_schema.append(arg)

    return BuiltinFunctionSchema(
        name=name,
        namespace=namespace,
        is_method=is_method,
        is_async=inspect.iscoroutinefunction(attribute),
        docstring=inspect.getdoc(attribute),
        return_hint_name=_format_type(sig.return_annotation),
        return_hint_namespace=_format_type_namespace(sig.return_annotation),
        params=args_schema,
    )
