from __future__ import annotations
from types import BuiltinFunctionType, FunctionType, MethodType

from typing import Any
import inspect


from gi_stub_gen.utils.inspect_utils import extract_inspect_params_type_info
from gi_stub_gen.schema.builtin_function import ArgKind, BuiltinFunctionArgumentSchema
from gi_stub_gen.schema.builtin_function import (
    BuiltinFunctionSchema,
)
from gi_stub_gen.utils.utils import get_redacted_stub_value


def _detect_method_type(func: Any, name: str, parent_class: type) -> tuple[bool, bool]:
    """
    Detect if a function is a classmethod or staticmethod.

    Args:
        func: The function/method to check
        name: The name of the method
        parent_class: The class containing this method

    Returns:
        Tuple of (is_classmethod, is_staticmethod).

    Detection strategy:
    1. classmethod: check if __self__ exists and is a type (bound to the class)
    2. staticmethod: use getattr_static on the parent class
    """
    # Check for classmethod: when accessed from class, classmethod has __self__ bound to the class
    if hasattr(func, "__self__") and isinstance(func.__self__, type):
        return True, False

    # Check for staticmethod: need to use getattr_static on parent class
    try:
        raw_attr = inspect.getattr_static(parent_class, name, None)
        if isinstance(raw_attr, staticmethod):
            return False, True
    except Exception:
        pass

    return False, False


def parse_python_function(
    attribute: Any,
    namespace: str,
    name_override: str | None = None,
    from_class: type | None = None,
) -> BuiltinFunctionSchema | None:
    """
    Parse a pure Python function into a BuiltinFunctionSchema using inspect.

    Args:
        attribute: The function/method to parse
        namespace: The namespace for the function
        name_override: Optional name override
        from_class: The class containing this method (required for class methods).
                   Used to properly detect @staticmethod and @classmethod.
                   If None, the function is treated as a module-level function.
    """

    # pure python function check
    is_function = isinstance(attribute, FunctionType)

    # function check for built-in functions implemented in C
    is_builtin_function = isinstance(attribute, BuiltinFunctionType)
    is_method_type = isinstance(attribute, MethodType)

    if not is_function and not is_builtin_function and not is_method_type:
        return None

    if name_override is not None:
        name = name_override
    else:
        name = getattr(attribute, "__name__", "unknown")

    # Determine if this function is from a class based on from_class parameter
    is_from_class = from_class is not None

    # Detect classmethod and staticmethod only if we have a parent class
    if from_class is not None:
        is_classmethod, is_staticmethod = _detect_method_type(attribute, name, from_class)
    else:
        is_classmethod, is_staticmethod = False, False

    try:
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
        # Add self for instance methods
        if is_from_class and not is_staticmethod and not is_classmethod:
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
            is_from_class=is_from_class,
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod,
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
        is_from_class=is_from_class,
        is_classmethod=is_classmethod,
        is_staticmethod=is_staticmethod,
        is_async=inspect.iscoroutinefunction(attribute),
        docstring=inspect.getdoc(attribute),
        return_hint_name=ret_name,
        return_hint_namespace=ret_ns,
        return_is_optional=ret_opt,
        params=args_schema,
    )
