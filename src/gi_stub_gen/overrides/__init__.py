# TODO if it happens more than once consider a more generic structure
from gi_stub_gen.adapter import get_callback_schema
from gi_stub_gen.overrides.class_.GIRepository import (
    FUNCTION_INFO_GET_ARGUMENTS,
    TYPE_INFO_GET_TAG_AS_STRING,
)
from gi_stub_gen.schema.function import FunctionSchema

# Import OBJECT_* schemas from class_/GObject.py
from gi_stub_gen.overrides.class_.GObject import (
    OBJECT_EMIT,
    OBJECT_WEAK_REF,
    OBJECT_HANDLER_DEFAULT,
)


CLASS_OVERRIDES = {
    "gi.repository.GIRepository": {
        "TypeInfo": {
            "methods": {
                "get_tag_as_string": TYPE_INFO_GET_TAG_AS_STRING,  # (pygobject 3.54)
            }
        },
        "CallableInfo": {
            "methods": {
                "get_arg_info": FUNCTION_INFO_GET_ARGUMENTS,  # (pygobject 3.54)
                "get_n_args": None,  # present in C api but not in Python (pygobject 3.54)
                "get_arg": None,  # present in C api but not in Python (pygobject 3.54)
            }
        },
    },
    "gi.repository.GObject": {
        "Object": {
            "methods": {
                # "connect": OBJECT_CONNECT,
                "emit": OBJECT_EMIT,
                # "disconnect": OBJECT_DISCONNECT,
                # "handler_block": OBJECT_HANDLER_BLOCK,
                # "handler_unblock": OBJECT_HANDLER_UNBLOCK,
                "weak_ref": OBJECT_WEAK_REF,
                "handler_default": OBJECT_HANDLER_DEFAULT,
            },
        },
    },
}
"""List of manual overrides for classes and their methods.
The structure is as follows:
<namespace>: {<class_name>: { <"methods": { <method_name>: <FunctionSchema | None> } } }
If the value is None, the method is removed from the generated stub.
"""

CALLBACK_OVERRIDES = {
    "gi.repository.GObject": {
        "ClosureMarshal": get_callback_schema("GObject", "ClosureMarshal"),
    },
    "gi.repository.GLib": {
        "EqualFunc": get_callback_schema("GLib", "EqualFunc"),
        "EqualFuncFull": get_callback_schema("GLib", "EqualFuncFull"),
    },
}


def apply_method_overrides(
    current_methods: list[FunctionSchema],
    namespace: str,
    class_name: str,
) -> list[FunctionSchema]:
    overrides = CLASS_OVERRIDES.get(namespace, {}).get(class_name, {}).get("methods", {})

    if not overrides:
        return current_methods

    new_methods = []
    processed_overrides = set()

    # keep / replace / remove existing methods
    for method in current_methods:
        if method.name in overrides:
            replacement = overrides[method.name]

            # if override exist we replace the method
            processed_overrides.add(method.name)
            if replacement is None:
                continue

            # replace
            new_methods.append(replacement)
        else:
            # No override: keep the original method
            new_methods.append(method)

    # add methods that are not present yet
    for name, replacement in overrides.items():
        if name not in processed_overrides and replacement is not None:
            new_methods.append(replacement)

    return new_methods
