from __future__ import annotations
from types import BuiltinFunctionType, FunctionType, MethodType

from typing import Any
import inspect


from gi_stub_gen.inspect_utils import extract_inspect_params_type_info
from gi_stub_gen.schema.builtin_function import ArgKind, BuiltinFunctionArgumentSchema, FunctionMethodType
from gi_stub_gen.schema.builtin_function import (
    BuiltinFunctionSchema,
)
from gi_stub_gen.utils import get_redacted_stub_value


def classify_method(
    attribute: Any,
    # class_type: type,
    # attr_name: str,
) -> FunctionMethodType:
    # a classmethod looks like a method bound to the class.
    if inspect.ismethod(attribute):
        if isinstance(attribute.__self__, type):
            return FunctionMethodType.CLASS

    # unbound or simple function
    try:
        sig = inspect.signature(attribute)
    except (ValueError, TypeError):
        # if no signature -> static as fallback
        return FunctionMethodType.STATIC

    params = list(sig.parameters.values())
    if not params:
        # instance require at least 'self'
        return FunctionMethodType.STATIC

    # heuristic: first param name
    first_param_name = params[0].name
    if first_param_name == "self":
        return FunctionMethodType.INSTANCE

    # if override is done wrongly and first param is not self
    # we check the type of the first param
    # if params[0].annotation == class_type:
    #     return FunctionMethodType.INSTANCE

    return FunctionMethodType.STATIC


def parse_python_function(
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
        method_type = classify_method(attribute)
        if method_type == FunctionMethodType.INSTANCE:
            if not is_method:
                # this is due to an override, to __init__
                # that is not registered as a method but it is
                is_method = True
                # breakpoint()
            # assert is_method, "Instance method must be a method"
        sig = inspect.signature(attribute)
    except (ValueError, TypeError):
        # Fallback logic for C-extensions/GObject

        params = [
            BuiltinFunctionArgumentSchema(
                name="args",
                type_hint_name="Any",
                type_hint_namespace="typing",
                is_optional=False,
                kind=ArgKind.VAR_POSITIONAL,
                default_value=None,
                line_comment=None,
            ),
            BuiltinFunctionArgumentSchema(
                name="kwargs",
                type_hint_name="Any",
                type_hint_namespace="typing",
                is_optional=False,
                kind=ArgKind.VAR_KEYWORD,
                default_value=None,
                line_comment=None,
            ),
        ]
        if is_method:
            params.insert(
                0,
                BuiltinFunctionArgumentSchema(
                    name="self",
                    type_hint_name="Any",
                    type_hint_namespace="typing",
                    is_optional=False,
                    kind=ArgKind.POSITIONAL_OR_KEYWORD,
                    default_value=None,
                    line_comment=None,
                ),
            )
        return BuiltinFunctionSchema(
            name=name,
            namespace=namespace,
            return_hint_name="Any",
            return_hint_namespace="typing",
            return_is_optional=False,
            docstring=inspect.getdoc(attribute),
            is_method=is_method,
            is_classmethod=False,
            is_staticmethod=False,
            is_async=False,
            params=params,
        )

    args_schema: list[BuiltinFunctionArgumentSchema] = []
    for param_name, param in sig.parameters.items():
        # 1. Parsing del valore di default
        def_val = None
        if param.default is not inspect.Parameter.empty:
            def_val = get_redacted_stub_value(param.default)

        # 2. Estrazione Tipo Robusta
        t_name, t_ns, t_opt = extract_inspect_params_type_info(param.annotation, param.default)
        arg = BuiltinFunctionArgumentSchema(
            name=param_name,
            type_hint_name=t_name,
            type_hint_namespace=t_ns,
            is_optional=t_opt,
            kind=ArgKind.from_inspect(param.kind),
            default_value=def_val,
            line_comment=None,
        )
        args_schema.append(arg)

    # 3. Parsing del Return Type
    ret_name, ret_ns, ret_opt = extract_inspect_params_type_info(sig.return_annotation)

    return BuiltinFunctionSchema(
        name=name,
        namespace=namespace,
        is_method=is_method,
        is_classmethod=(method_type == FunctionMethodType.CLASS),
        is_staticmethod=(method_type == FunctionMethodType.STATIC),
        is_async=inspect.iscoroutinefunction(attribute),
        docstring=inspect.getdoc(attribute),
        return_hint_name=ret_name,
        return_hint_namespace=ret_ns,
        return_is_optional=ret_opt,
        params=args_schema,
    )
