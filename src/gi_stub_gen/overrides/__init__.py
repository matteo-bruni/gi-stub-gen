# TODO if it happens more than once consider a more generic structure
from gi_stub_gen.adapter import get_callback_schema
from gi_stub_gen.overrides.class_.GIRepositoryy.FunctionInfo import FUNCTION_INFO_GET_ARGUMENTS
from gi_stub_gen.overrides.class_.GIRepositoryy.TypeInfo import (
    TYPE_INFO_GET_TAG_AS_STRING,
)
from gi_stub_gen.overrides.class_.GObject.GType import (
    # Fields
    GTYPE_NAME,
    GTYPE_PARENT,
    GTYPE_CHILDREN,
    GTYPE_DEPTH,
    GTYPE_FUNDAMENTAL,
    GTYPE_INTERFACES,
    GTYPE_PYTYPE,
    # Methods
    GTYPE_IS_A,
    GTYPE_IS_ABSTRACT,
    GTYPE_IS_CLASSED,
    GTYPE_IS_DEEP_DERIVABLE,
    GTYPE_IS_DERIVABLE,
    GTYPE_IS_INSTANTIATABLE,
    GTYPE_IS_INTERFACE,
    GTYPE_IS_VALUE_ABSTRACT,
    GTYPE_IS_VALUE_TYPE,
    GTYPE_HAS_VALUE_TABLE,
    GTYPE_FROM_NAME,
)
from gi_stub_gen.overrides.class_.GObject.Object import (
    OBJECT_EMIT,
    OBJECT_GET_PROPERTY,
    OBJECT_HANDLER_DEFAULT,
    OBJECT_WEAK_REF,
    OBJECT_SET_PROPERTY,
)
from gi_stub_gen.overrides.class_.Gst.Fraction import GST_FRACTION_DEN_SCHEMA, GST_FRACTION_NUM_SCHEMA
from gi_stub_gen.schema.class_ import ClassFieldSchema
from gi_stub_gen.schema.function import FunctionSchema


def get_super_override(namespace: str, class_name: str) -> list[str] | None:
    """
    Get the super class override for a given class.
    Returns a list of super class names if an override exists, None otherwise.
    """
    return CLASS_OVERRIDES.get(namespace, {}).get(class_name, {}).get("super")


CLASS_OVERRIDES = {
    "gi.repository.GIRepository": {
        "TypeInfo": {
            "methods": {
                "get_tag_as_string": TYPE_INFO_GET_TAG_AS_STRING,  # (pygobject 3.54)
            }
        },
        "CallableInfo": {
            "methods": {
                "get_arguments": FUNCTION_INFO_GET_ARGUMENTS,  # (pygobject 3.54)
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
                "get_property": OBJECT_GET_PROPERTY,
                "set_property": OBJECT_SET_PROPERTY,
            },
        },
        "GType": {
            "super": ["builtins.type"],
            "fields": {
                "name": GTYPE_NAME,
                "parent": GTYPE_PARENT,
                "children": GTYPE_CHILDREN,
                "depth": GTYPE_DEPTH,
                "fundamental": GTYPE_FUNDAMENTAL,
                "interfaces": GTYPE_INTERFACES,
                "pytype": GTYPE_PYTYPE,
            },
            "methods": {
                "is_a": GTYPE_IS_A,
                "is_abstract": GTYPE_IS_ABSTRACT,
                "is_classed": GTYPE_IS_CLASSED,
                "is_deep_derivable": GTYPE_IS_DEEP_DERIVABLE,
                "is_derivable": GTYPE_IS_DERIVABLE,
                "is_instantiatable": GTYPE_IS_INSTANTIATABLE,
                "is_interface": GTYPE_IS_INTERFACE,
                "is_value_abstract": GTYPE_IS_VALUE_ABSTRACT,
                "is_value_type": GTYPE_IS_VALUE_TYPE,
                "has_value_table": GTYPE_HAS_VALUE_TABLE,
                "from_name": GTYPE_FROM_NAME,
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
