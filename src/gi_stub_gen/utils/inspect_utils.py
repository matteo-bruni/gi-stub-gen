import inspect
from types import UnionType
import typing
from typing import Any, get_args, get_origin

from gi_stub_gen.utils.utils import get_py_type_name_repr, get_py_type_namespace_repr
from gi_stub_gen.utils.utils import sanitize_gi_module_name

_TypeVarType = type(typing.TypeVar("_TypeVar"))


def _normalize_namespace(namespace: str | None) -> str | None:
    if namespace is None:
        return None
    return sanitize_gi_module_name(namespace)


def _is_none_type(annotation: Any) -> bool:
    return annotation is None or annotation is type(None)


def _is_type_var(annotation: Any) -> bool:
    return isinstance(annotation, _TypeVarType)


def _format_annotation_expr(
    annotation: Any,
    relative_namespace: str | None = None,
    current_namespace: str | None = None,
) -> str:
    normalized_relative_namespace = _normalize_namespace(relative_namespace)
    normalized_current_namespace = _normalize_namespace(current_namespace)

    type_name, type_namespace = _extract_annotation_type_info(
        annotation,
        current_namespace=normalized_current_namespace,
    )

    if type_namespace and type_namespace not in {
        normalized_relative_namespace,
        normalized_current_namespace,
    }:
        return f"{type_namespace}.{type_name}"

    return type_name


def _format_union_args(
    args: tuple[Any, ...],
    current_namespace: str | None = None,
) -> str:
    return " | ".join(
        "None"
        if _is_none_type(arg)
        else _format_annotation_expr(
            arg,
            current_namespace=current_namespace,
        )
        for arg in args
    )


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

    if _is_none_type(annotation):
        return "None", None

    if isinstance(annotation, str):
        return annotation, None

    if _is_type_var(annotation):
        return annotation.__name__, None

    origin = get_origin(annotation)

    if origin in (typing.Union, UnionType):
        args = get_args(annotation)
        return _format_union_args(args, current_namespace=current_namespace), None

    if origin is not None:
        origin_name = get_py_type_name_repr(origin)
        origin_namespace = _normalize_namespace(get_py_type_namespace_repr(origin))

        arg_reprs = [
            _format_annotation_expr(
                arg,
                relative_namespace=origin_namespace,
                current_namespace=current_namespace,
            )
            for arg in get_args(annotation)
        ]

        return f"{origin_name}[{', '.join(arg_reprs)}]", origin_namespace

    return (
        get_py_type_name_repr(annotation),
        _normalize_namespace(get_py_type_namespace_repr(annotation)),
    )


def extract_inspect_params_type_info(
    annotation: Any,
    default_value: Any = inspect.Parameter.empty,
    current_namespace: str | None = None,
) -> tuple[str, str | None, bool]:
    # no annotation -> Any
    if annotation is inspect.Parameter.empty:
        return "Any", "typing", False

    is_optional = default_value is None
    origin = get_origin(annotation)
    real_type = annotation

    if origin in (typing.Union, UnionType):
        args = get_args(annotation)

        if any(_is_none_type(arg) for arg in args):
            is_optional = True

            # Remove None from args to find the real type.
            non_none_args = [arg for arg in args if not _is_none_type(arg)]

            if len(non_none_args) == 1:
                real_type = non_none_args[0]

            elif non_none_args:
                return (
                    " | ".join(
                        _format_annotation_expr(
                            arg,
                            current_namespace=current_namespace,
                        )
                        for arg in non_none_args
                    ),
                    None,
                    is_optional,
                )

            else:
                return "Any", "typing", is_optional

    base_name, namespace = _extract_annotation_type_info(
        real_type,
        current_namespace=current_namespace,
    )

    return base_name, namespace, is_optional


def extract_inspect_type_vars(
    annotation: Any,
    current_namespace: str | None = None,
) -> list[tuple[str, str | None, str | None]]:
    """
    Extract TypeVars referenced by an annotation.

    Returns tuples of (type_var_name, bound_name, bound_namespace). The bound
    entries are None when the TypeVar is unconstrained or unbound.
    """
    found: dict[str, tuple[str, str | None, str | None]] = {}

    def visit(value: Any) -> None:
        if value is inspect.Parameter.empty or value is inspect.Signature.empty:
            return

        if isinstance(value, list):
            for item in value:
                visit(item)
            return

        if _is_type_var(value):
            bound = getattr(value, "__bound__", None)
            if bound is None:
                found[value.__name__] = (value.__name__, None, None)
                return

            bound_name, bound_namespace = _extract_annotation_type_info(
                bound,
                current_namespace=current_namespace,
            )
            found[value.__name__] = (value.__name__, bound_name, bound_namespace)
            return

        for arg in get_args(value):
            visit(arg)

    visit(annotation)
    return list(found.values())
