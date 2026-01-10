from __future__ import annotations
from types import BuiltinFunctionType, FunctionType, MethodType

from typing import Any
import inspect
import sys


from gi_stub_gen.utils.inspect_utils import extract_inspect_params_type_info
from gi_stub_gen.schema.builtin_function import ArgKind, BuiltinFunctionArgumentSchema
from gi_stub_gen.schema.builtin_function import (
    BuiltinFunctionSchema,
)
from gi_stub_gen.utils.utils import get_redacted_stub_value


def _is_from_class(func: Any) -> bool:
    """
    Determine if a function is defined inside a class by checking __qualname__.

    Note: This is a heuristic and may fail for dynamically created methods
    like PyGObject's signal wrappers.

    Examples:
        - "top_level_func" -> False
        - "MyClass.method" -> True
        - "outer.<locals>.inner" -> False (nested function, not a class method)
    """
    qualname = getattr(func, "__qualname__", "") or ""
    return "." in qualname and "<locals>" not in qualname


def _get_parent_class(func: Any) -> type | None:
    """
    Extract the parent class of a method from __qualname__ and __module__.

    Returns the class object if found, None otherwise.
    """
    qualname = getattr(func, "__qualname__", "") or ""
    module_name = getattr(func, "__module__", "") or ""

    if "." not in qualname or "<locals>" in qualname:
        return None

    class_name = qualname.rsplit(".", 1)[0]

    # Get the module
    module = sys.modules.get(module_name)
    if module is None:
        return None

    # Get the class from the module
    parent = getattr(module, class_name, None)
    return parent if isinstance(parent, type) else None


def _detect_method_type(func: Any, name: str, parent_class: type | None = None) -> tuple[bool, bool]:
    """
    Detect if a function is a classmethod or staticmethod.

    Returns (is_classmethod, is_staticmethod).

    Detection strategy:
    1. classmethod: check if __self__ exists and is a type (bound to the class)
    2. staticmethod: use getattr_static on the parent class
    """
    # Check for classmethod: when accessed from class, classmethod has __self__ bound to the class
    if hasattr(func, "__self__") and isinstance(func.__self__, type):
        return True, False

    # Check for staticmethod: need to use getattr_static on parent class
    if parent_class is None:
        parent_class = _get_parent_class(func)

    if parent_class is not None:
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
        from_class: If provided, the class containing this method.
                   Used to properly detect @staticmethod and @classmethod,
                   and to mark as is_from_class for methods with unusual __qualname__.
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

    # Determine if this function is from a class
    # If from_class is provided, use it; otherwise try to detect via __qualname__
    if from_class is not None:
        is_from_class = True
    else:
        is_from_class = _is_from_class(attribute)

    # Detect classmethod and staticmethod using proper introspection
    is_classmethod, is_staticmethod = _detect_method_type(attribute, name, from_class)

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
