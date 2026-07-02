from gi_stub_gen.schema.function import FunctionArgumentSchema, FunctionSchema


GST_STRUCTURE_GET_VALUE = FunctionSchema(
    name="get_value",
    namespace="Gst",
    is_method=True,
    is_class_member=True,
    is_deprecated=False,
    deprecation_warnings=None,
    docstring=(
        "Return the Python value for a structure field. PyGObject unwraps "
        "the underlying GObject.Value at runtime."
    ),
    args=[
        FunctionArgumentSchema(
            namespace="Gst",
            name="fieldname",
            direction="IN",
            is_callback=False,
            may_be_null=False,
            is_optional=False,
            is_deprecated=False,
            is_caller_allocates=False,
            tag_as_string="",
            get_array_length=-1,
            py_type_name="str",
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
    return_hint="Any",
    return_hint_namespace="typing",
    skip_return=False,
    wrap_vfunc=False,
    line_comment=None,
    function_type="FunctionInfo",
    is_overload=False,
)
