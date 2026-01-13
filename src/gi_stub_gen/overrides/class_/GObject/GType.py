from gi_stub_gen.schema.class_ import ClassFieldSchema
from gi_stub_gen.schema.function import FunctionSchema, FunctionArgumentSchema


# ============================================================================
# GType Fields
# ============================================================================
# GType is implemented in C by pygobject, not via GI introspection.
# All fields are getset_descriptors (read-only properties).

GTYPE_NAME = ClassFieldSchema(
    name="name",
    type_hint_name="str",
    type_hint_namespace=None,
    may_be_null=True,
    line_comment=None,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="The GType name.",
    is_readable=True,
    is_writable=False,
)

GTYPE_PARENT = ClassFieldSchema(
    name="parent",
    type_hint_name="GType",
    type_hint_namespace=None,
    may_be_null=False,
    line_comment=None,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="The parent GType.",
    is_readable=True,
    is_writable=False,
)

GTYPE_CHILDREN = ClassFieldSchema(
    name="children",
    type_hint_name="list[GType]",
    type_hint_namespace=None,
    may_be_null=False,
    line_comment=None,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="List of child GTypes.",
    is_readable=True,
    is_writable=False,
)

GTYPE_DEPTH = ClassFieldSchema(
    name="depth",
    type_hint_name="int",
    type_hint_namespace=None,
    may_be_null=False,
    line_comment=None,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="The depth in the type hierarchy.",
    is_readable=True,
    is_writable=False,
)

GTYPE_FUNDAMENTAL = ClassFieldSchema(
    name="fundamental",
    type_hint_name="GType",
    type_hint_namespace=None,
    may_be_null=False,
    line_comment=None,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="The fundamental type this GType is derived from.",
    is_readable=True,
    is_writable=False,
)

GTYPE_INTERFACES = ClassFieldSchema(
    name="interfaces",
    type_hint_name="list[GType]",
    type_hint_namespace=None,
    may_be_null=False,
    line_comment=None,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="List of interfaces implemented by this GType.",
    is_readable=True,
    is_writable=False,
)

GTYPE_PYTYPE = ClassFieldSchema(
    name="pytype",
    type_hint_name="type",
    type_hint_namespace="builtins",
    may_be_null=True,
    line_comment=None,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="The Python type associated with this GType, or None.",
    is_readable=True,
    is_writable=False,
)


# ============================================================================
# GType Methods
# ============================================================================
# All methods are implemented in C by pygobject.


def _make_gtype_bool_method(name: str, docstring: str) -> FunctionSchema:
    """Helper to create GType methods that return bool with no arguments."""
    return FunctionSchema(
        name=name,
        namespace="GObject",
        is_method=True,
        is_class_member=True,
        is_deprecated=False,
        deprecation_warnings=None,
        docstring=docstring,
        args=[],
        is_callback=False,
        can_throw_gerror=False,
        is_async=False,
        is_constructor=False,
        is_getter=False,
        is_setter=False,
        may_return_null=False,
        return_hint="bool",
        return_hint_namespace=None,
        skip_return=False,
        wrap_vfunc=False,
        line_comment=None,
        function_type="FunctionInfo",
        is_overload=False,
    )


GTYPE_IS_A = FunctionSchema(
    name="is_a",
    namespace="GObject",
    is_method=True,
    is_class_member=True,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring="Check if this GType is derived from another GType.",
    args=[
        FunctionArgumentSchema(
            namespace="GObject",
            name="type",
            direction="IN",
            is_callback=False,
            may_be_null=False,
            is_optional=False,
            is_deprecated=False,
            is_caller_allocates=False,
            tag_as_string="",
            get_array_length=-1,
            py_type_name="GType",
            py_type_namespace=None,
            line_comment=None,
            default_value=None,
            is_pointer=False,
        ),
    ],
    is_callback=False,
    can_throw_gerror=False,
    is_async=False,
    is_constructor=False,
    is_getter=False,
    is_setter=False,
    may_return_null=False,
    return_hint="bool",
    return_hint_namespace=None,
    skip_return=False,
    wrap_vfunc=False,
    line_comment=None,
    function_type="FunctionInfo",
    is_overload=False,
)

GTYPE_IS_ABSTRACT = _make_gtype_bool_method(
    "is_abstract",
    "Check if this GType is abstract.",
)

GTYPE_IS_CLASSED = _make_gtype_bool_method(
    "is_classed",
    "Check if this GType is a classed type.",
)

GTYPE_IS_DEEP_DERIVABLE = _make_gtype_bool_method(
    "is_deep_derivable",
    "Check if this GType can be deeply derived.",
)

GTYPE_IS_DERIVABLE = _make_gtype_bool_method(
    "is_derivable",
    "Check if this GType can be derived.",
)

GTYPE_IS_INSTANTIATABLE = _make_gtype_bool_method(
    "is_instantiatable",
    "Check if this GType can be instantiated.",
)

GTYPE_IS_INTERFACE = _make_gtype_bool_method(
    "is_interface",
    "Check if this GType is an interface.",
)

GTYPE_IS_VALUE_ABSTRACT = _make_gtype_bool_method(
    "is_value_abstract",
    "Check if this GType is an abstract value type.",
)

GTYPE_IS_VALUE_TYPE = _make_gtype_bool_method(
    "is_value_type",
    "Check if this GType is a value type.",
)

GTYPE_HAS_VALUE_TABLE = _make_gtype_bool_method(
    "has_value_table",
    "Check if this GType has a value table.",
)
