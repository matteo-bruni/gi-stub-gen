import inspect
import typing
from typing import Any, get_origin, get_args

from gi_stub_gen.utils.utils import sanitize_gi_module_name


def extract_inspect_params_type_info(
    annotation: Any,
    default_value: Any = inspect.Parameter.empty,
) -> tuple[str, str | None, bool]:
    # no annotation -> Any
    if annotation is inspect.Parameter.empty:
        return "Any", "typing", False

    is_optional = False
    if default_value is None:
        is_optional = True

    origin = get_origin(annotation)
    real_type = annotation

    if origin is typing.Union:
        args = get_args(annotation)
        if type(None) in args:
            is_optional = True
            #  Remove NoneType from args to find the real type
            non_none_args = [a for a in args if a is not type(None)]
            if len(non_none_args) == 1:
                real_type = non_none_args[0]
            else:
                # TODO: Handle multiple types excluding None
                real_type = non_none_args[0]

    if isinstance(real_type, str):
        base_name = real_type
        namespace = None
    else:
        base_name = getattr(real_type, "__name__", str(real_type).replace("typing.", ""))
        module_name = getattr(real_type, "__module__", "")
        namespace = None

        if module_name == "builtins":
            namespace = None
        elif module_name:
            namespace = sanitize_gi_module_name(module_name)

    return base_name, namespace, is_optional
