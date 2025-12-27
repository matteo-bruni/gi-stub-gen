# TODO if it happens more than once consider a more generic structure
from gi_stub_gen.adapter import get_callback_schema
from gi_stub_gen.overrides.class_.GIRepository import (
    FUNCTION_INFO_GET_ARGUMENTS,
    TYPE_INFO_GET_TAG_AS_STRING,
)
from gi_stub_gen.overrides.class_.Gst import GST_FRACTION_DEN_SCHEMA, GST_FRACTION_NUM_SCHEMA
from gi_stub_gen.schema.class_ import ClassFieldSchema
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
    "gi.repository.Gst": {
        "Fraction": {
            "fields": {
                "num": GST_FRACTION_NUM_SCHEMA,
                "denom": GST_FRACTION_DEN_SCHEMA,
            },
        }
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
"""List of manual overrides for callback functions. 
These are usually discovered while parsing other elements. If we never encounter them,
we can add them here to ensure they are present in the stubs."""


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


def apply_field_overrides(
    current_fields: list[ClassFieldSchema],
    namespace: str,
    class_name: str,
) -> list[ClassFieldSchema]:
    """
    Applies manual overrides to class fields.
    It can replace existing fields, remove them (if mapped to None),
    or add new fields that are not present in the GIR (e.g. Python-only attributes).
    """
    # Retrieve the specific field overrides for this class from the global config
    overrides = CLASS_OVERRIDES.get(namespace, {}).get(class_name, {}).get("fields", {})

    if not overrides:
        return current_fields

    new_fields = []
    processed_overrides = set()

    # 1. Iterate over existing fields found in the GIR
    #    We check if an override exists for each field.
    for field in current_fields:
        if field.name in overrides:
            replacement = overrides[field.name]
            processed_overrides.add(field.name)

            # If the replacement is None, it means we want to hide/remove this field
            if replacement is None:
                continue

            # Otherwise, replace the original field with the override schema
            new_fields.append(replacement)
        else:
            # No override defined, keep the original field
            new_fields.append(field)

    # 2. Add strictly new fields
    #    These are fields present in the overrides but not in the original GIR list
    #    (e.g., 'num' and 'denom' for Gst.Fraction)
    for name, replacement in overrides.items():
        if name not in processed_overrides and replacement is not None:
            new_fields.append(replacement)

    return new_fields
