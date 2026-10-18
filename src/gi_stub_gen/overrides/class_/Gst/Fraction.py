"""Fraction-only additions, verified against initialized gst-python 1.28.3.

num/denom are already annotated upstream; these definitions retain their docs.
The constructor is parsed normally. Explicit operators avoid expanding the
global special-method filter or claiming an unrelated numeric base class.
"""

from gi_stub_gen.schema.class_ import ClassFieldSchema
from gi_stub_gen.schema.function import FunctionArgumentSchema, FunctionSchema


GST_FRACTION_NUM_SCHEMA = ClassFieldSchema(
    name="num",
    type_hint_namespace=None,
    type_hint_name="int",
    is_deprecated=False,
    docstring="Numerator of the fraction.",
    line_comment=None,
    may_be_null=False,
    deprecation_warnings=None,
    is_readable=True,
    is_writable=True,
)
GST_FRACTION_DEN_SCHEMA = ClassFieldSchema(
    name="denom",
    type_hint_namespace=None,
    type_hint_name="int",
    is_deprecated=False,
    docstring="Denominator of the fraction.",
    line_comment=None,
    may_be_null=False,
    deprecation_warnings=None,
    is_readable=True,
    is_writable=True,
)


def _fraction_operator(name: str, operand: str | None, result: str) -> FunctionSchema:
    return FunctionSchema(
        name=name,
        namespace="Gst",
        args=[
            FunctionArgumentSchema(
                namespace="Gst",
                name="other",
                direction="IN",
                is_optional=False,
                is_callback=False,
                may_be_null=False,
                is_deprecated=False,
                is_caller_allocates=False,
                tag_as_string="",
                get_array_length=-1,
                py_type_name=operand,
                py_type_namespace=None,
                line_comment=None,
                default_value=None,
                is_pointer=False,
            )
        ]
        if operand is not None
        else [],
        docstring=None,
        is_callback=False,
        skip_return=False,
        is_deprecated=False,
        can_throw_gerror=False,
        may_return_null=False,
        deprecation_warnings=None,
        return_hint=result,
        return_hint_namespace=None,
        is_method=True,
        is_async=False,
        is_getter=False,
        is_setter=False,
        is_constructor=False,
        wrap_vfunc=False,
        line_comment=None,
        function_type="FunctionInfo",
        is_overload=False,
        is_class_member=True,
    )


GST_FRACTION_METHODS: dict[str, FunctionSchema | None] = {
    name: _fraction_operator(name, operand, result)
    for name, operand, result in (
        ("__mul__", "Fraction | int", "Fraction"),
        ("__rmul__", "Fraction | int", "Fraction"),
        ("__truediv__", "Fraction | int", "Fraction"),
        ("__rtruediv__", "int", "Fraction"),
        ("__float__", None, "float"),
    )
}
