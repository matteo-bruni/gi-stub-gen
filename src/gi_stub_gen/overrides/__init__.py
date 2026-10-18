"""Manual Python API corrections. Rationale and runtime evidence: README.md here."""

from gi_stub_gen.overrides.types import ClassOverride, InitFactory
from gi_stub_gen.overrides.class_.Gio.DBusConnection import build_dbus_connection_init
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
    OBJECT_CHAIN,
    OBJECT_CONNECT_AFTER,
    OBJECT_CONNECT_OBJECT,
    OBJECT_CONNECT_OBJECT_AFTER,
    OBJECT_DISCONNECT_BY_FUNC,
    OBJECT_EMIT,
    OBJECT_GET_PROPERTIES,
    OBJECT_GET_PROPERTY,
    OBJECT_HANDLER_BLOCK_BY_FUNC,
    OBJECT_HANDLER_UNBLOCK_BY_FUNC,
    OBJECT_SET_PROPERTIES,
    OBJECT_SET_PROPERTY,
    OBJECT_WEAK_REF,
)
from gi_stub_gen.overrides.class_.GObject.GBoxed import GBOXED_COPY
from gi_stub_gen.overrides.class_.Gst.Fraction import (
    GST_FRACTION_DEN_SCHEMA,
    GST_FRACTION_NUM_SCHEMA,
    GST_FRACTION_METHODS,
)
from gi_stub_gen.overrides.class_.Gio.Task import transform_return_value
from gi_stub_gen.overrides.class_.Gst.Structure import transform_set_value
from gi_stub_gen.overrides.class_.GioUnix.FileDescriptorBased import transform_get_fd
from gi_stub_gen.overrides.class_.Atk.Object import transform_nullable_text
from gi_stub_gen.overrides.class_.Gtk.TreeViewColumn import transform_set_cell_data_func
from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema
from gi_stub_gen.schema.class_ import ClassFieldSchema
from gi_stub_gen.schema.function import FunctionSchema


def get_super_override(namespace: str, class_name: str) -> list[str] | None:
    """
    Get the super class override for a given class.
    Returns a list of super class names if an override exists, None otherwise.
    """
    bases = CLASS_OVERRIDES.get(namespace, {}).get(class_name, {}).get("super")
    return bases.copy() if bases is not None else None


CLASS_OVERRIDES: dict[str, dict[str, ClassOverride]] = {
    "gi.repository.GioUnix": {
        "InputStream": {"method_transforms": {"get_fd": transform_get_fd}},
        "OutputStream": {"method_transforms": {"get_fd": transform_get_fd}},
    },
    "gi.repository.Atk": {
        "Object": {"method_transforms": {
            "get_name": transform_nullable_text,
            "get_description": transform_nullable_text,
        }},
    },
    "gi.repository.Gtk": {
        "TreeViewColumn": {"method_transforms": {"set_cell_data_func": transform_set_cell_data_func}},
    },
    "gi.repository.GObject": {
        "Object": {
            "methods": {
                # "connect": OBJECT_CONNECT,
                "chain": OBJECT_CHAIN,
                "connect_after": OBJECT_CONNECT_AFTER,
                "connect_object": OBJECT_CONNECT_OBJECT,
                "connect_object_after": OBJECT_CONNECT_OBJECT_AFTER,
                "disconnect_by_func": OBJECT_DISCONNECT_BY_FUNC,
                "emit": OBJECT_EMIT,
                # "disconnect": OBJECT_DISCONNECT,
                # "handler_block": OBJECT_HANDLER_BLOCK,
                # "handler_unblock": OBJECT_HANDLER_UNBLOCK,
                "get_properties": OBJECT_GET_PROPERTIES,
                "get_property": OBJECT_GET_PROPERTY,
                "handler_block_by_func": OBJECT_HANDLER_BLOCK_BY_FUNC,
                "handler_unblock_by_func": OBJECT_HANDLER_UNBLOCK_BY_FUNC,
                "set_properties": OBJECT_SET_PROPERTIES,
                "set_property": OBJECT_SET_PROPERTY,
                "weak_ref": OBJECT_WEAK_REF,
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
        "GBoxed": {
            "methods": {
                "copy": GBOXED_COPY,
            },
        },
    },
    "gi.repository.Gio": {
        "DBusConnection": {"init_factory": build_dbus_connection_init},
        "Task": {
            "method_transforms": {
                "return_value": transform_return_value,
            },
        },
    },
    "gi.repository.Gst": {
        "Caps": {"include_methods": ("__getitem__", "__len__")},
        "ControlBinding": {
            "property_comments": {
                "name": (
                    "pyright: ignore[reportIncompatibleVariableOverride]  "
                    "# ty: ignore[invalid-property-type-override]  "
                    "# pyrefly: ignore[bad-override]  "
                    "# Native construct-only property restricts its mutable parent."
                ),
            },
        },
        "Fraction": {
            "methods": GST_FRACTION_METHODS,
            "fields": {
                "num": GST_FRACTION_NUM_SCHEMA,
                "denom": GST_FRACTION_DEN_SCHEMA,
            },
        },
        "Structure": {
            "include_methods": ("__getitem__", "__setitem__", "__len__"),
            "method_transforms": {
                "set_value": transform_set_value,
            },
        },
    },
}
"""List of manual overrides for classes and their methods.
The structure is as follows:
<namespace>: {<class_name>: { <"methods": { <method_name>: <FunctionSchema | None> } } }
If the value is None, the method is removed from the generated stub.
"""

REQUIRED_CALLBACKS: dict[str, tuple[str, ...]] = {
    "gi.repository.GObject": ("ClosureMarshal",),
    "gi.repository.GLib": ("EqualFunc", "EqualFuncFull"),
}
"""Callbacks to discover explicitly if normal parsing has not encountered them."""


def validate_class_override(namespace: str, class_name: str, config: ClassOverride) -> None:
    """Reject inconsistent declarations without loading GI or checking runtime APIs."""
    methods = config.get("methods", {})
    if "init_factory" in config and ("__init__" in methods or "__init__" in config.get("method_transforms", {})):
        raise ValueError(f"{namespace}.{class_name}: init_factory conflicts with an __init__ override")
    conflicts = methods.keys() & config.get("method_transforms", {}).keys()
    if conflicts:
        raise ValueError(f"{namespace}.{class_name}: replacement and transform overlap: {sorted(conflicts)}")
    for name, model in [*methods.items(), *config.get("fields", {}).items()]:
        if model is not None and model.name != name:
            raise ValueError(f"{namespace}.{class_name}.{name}: override model is named {model.name}")


for _namespace, _classes in CLASS_OVERRIDES.items():
    for _class_name, _config in _classes.items():
        validate_class_override(_namespace, _class_name, _config)


def get_init_factory(namespace: str, class_name: str) -> InitFactory | None:
    """Return the constructor factory after checking registry conflicts."""
    config = CLASS_OVERRIDES.get(namespace, {}).get(class_name, {})
    validate_class_override(namespace, class_name, config)
    return config.get("init_factory")


def has_method_override(namespace: str, class_name: str, method_name: str) -> bool:
    """
    Check if a method has a manual override defined.

    This is used to skip generating fallback stubs for method_descriptors
    that already have a proper override.
    """
    return method_name in CLASS_OVERRIDES.get(namespace, {}).get(class_name, {}).get("methods", {})


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
            new_methods.append(replacement.model_copy(deep=True))
        else:
            # No override: keep the original method
            new_methods.append(method)

    # add methods that are not present yet
    for name, replacement in overrides.items():
        if name not in processed_overrides and replacement is not None:
            new_methods.append(replacement.model_copy(deep=True))

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
            new_fields.append(replacement.model_copy(deep=True))
        else:
            # No override defined, keep the original field
            new_fields.append(field)

    # 2. Add strictly new fields
    #    These are fields present in the overrides but not in the original GIR list
    #    (e.g., 'num' and 'denom' for Gst.Fraction)
    for name, replacement in overrides.items():
        if name not in processed_overrides and replacement is not None:
            new_fields.append(replacement.model_copy(deep=True))

    return new_fields


def apply_method_transforms(
    methods: list[FunctionSchema],
    python_methods: list[BuiltinFunctionSchema],
    namespace: str,
    class_name: str,
) -> tuple[list[FunctionSchema], list[BuiltinFunctionSchema]]:
    """Transform an independent copy of the effective method, preferring Python.

    Transforms preserve the model kind and name. Missing or ambiguous targets
    fail explicitly rather than silently leaving an incorrect signature.
    """
    config = CLASS_OVERRIDES.get(namespace, {}).get(class_name, {})
    validate_class_override(namespace, class_name, config)
    methods, python_methods = methods.copy(), python_methods.copy()
    for name, transform in config.get("method_transforms", {}).items():
        python_indices = [i for i, method in enumerate(python_methods) if method.name == name]
        gi_indices = [i for i, method in enumerate(methods) if method.name == name]
        target = f"{namespace}.{class_name}.{name}"
        if len(python_indices or gi_indices) != 1:
            raise ValueError(f"{target}: transform requires exactly one effective method")
        if python_indices:
            index = python_indices[0]
            transformed = transform(python_methods[index].model_copy(deep=True))
            if not isinstance(transformed, BuiltinFunctionSchema) or transformed.name != name:
                raise TypeError(f"{target}: transform must preserve the Python model kind and name")
            python_methods[index] = transformed
            for gi_index in gi_indices:
                hidden = methods[gi_index].model_copy(deep=True)
                hidden.is_overridden = True
                methods[gi_index] = hidden
        else:
            index = gi_indices[0]
            transformed = transform(methods[index].model_copy(deep=True))
            if not isinstance(transformed, FunctionSchema) or transformed.name != name:
                raise TypeError(f"{target}: transform must preserve the GI model kind and name")
            methods[index] = transformed
    return methods, python_methods
