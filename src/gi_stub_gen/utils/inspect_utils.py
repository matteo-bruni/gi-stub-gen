import inspect
from types import UnionType
import typing
from typing import Any, get_origin, get_args

from gi_stub_gen.utils.utils import get_py_type_name_repr, get_py_type_namespace_repr
from gi_stub_gen.utils.utils import sanitize_gi_module_name


def _normalize_namespace(namespace: str | None) -> str | None:
    if namespace is None:
        return None
    return sanitize_gi_module_name(namespace)


def _format_annotation_expr(
    annotation: Any,
    relative_namespace: str | None = None,
    current_namespace: str | None = None,
) -> str:
    normalized_relative_namespace = _normalize_namespace(relative_namespace)
    normalized_current_namespace = _normalize_namespace(current_namespace)
    type_name, type_namespace = _extract_annotation_type_info(
        annotation, current_namespace=normalized_current_namespace
    )
    if type_namespace and type_namespace not in {normalized_relative_namespace, normalized_current_namespace}:
        return f"{type_namespace}.{type_name}"
    return type_name


def _extract_annotation_type_info(
    annotation: Any,
    current_namespace: str | None = None,
) -> tuple[str, str | None]:
    if isinstance(annotation, list):
        return (
            f"[{', '.join(_format_annotation_expr(item, current_namespace=current_namespace) for item in annotation)}]",
            None,
        )

    if annotation is Ellipsis:
        return "...", None

    origin = get_origin(annotation)
    if origin is not None:
        origin_name = get_py_type_name_repr(origin)
        origin_namespace = get_py_type_namespace_repr(origin)
        arg_reprs = [
            _format_annotation_expr(
                arg,
                relative_namespace=origin_namespace,
                current_namespace=current_namespace,
            )
            for arg in get_args(annotation)
        ]
        return f"{origin_name}[{', '.join(arg_reprs)}]", _normalize_namespace(origin_namespace)

    if isinstance(annotation, str):
        return annotation, None

    return get_py_type_name_repr(annotation), _normalize_namespace(get_py_type_namespace_repr(annotation))


def extract_inspect_params_type_info(
    annotation: Any,
    default_value: Any = inspect.Parameter.empty,
    current_namespace: str | None = None,
) -> tuple[str, str | None, bool]:
    # no annotation -> Any
    if annotation is inspect.Parameter.empty:
        return "Any", "typing", False

    is_optional = False
    if default_value is None:
        is_optional = True

    origin = get_origin(annotation)
    real_type = annotation

    if origin in (typing.Union, UnionType):
        args = get_args(annotation)
        if type(None) in args:
            is_optional = True
            #  Remove NoneType from args to find the real type
            non_none_args = [a for a in args if a is not type(None)]
            if len(non_none_args) == 1:
                real_type = non_none_args[0]
            elif non_none_args:
                return (
                    " | ".join(
                        _format_annotation_expr(arg, current_namespace=current_namespace) for arg in non_none_args
                    ),
                    None,
                    is_optional,
                )
            else:
                return "Any", "typing", is_optional

    base_name, namespace = _extract_annotation_type_info(real_type, current_namespace=current_namespace)

    return base_name, namespace, is_optional
