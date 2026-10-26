"""Represent gst-python 1.28.8's native Mtd sentinel without a class-body reference."""

from gi_stub_gen.overrides.types import MethodSchema
from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema


def transform_iter_direct_related(method: MethodSchema) -> MethodSchema:
    """Correct only the known default; leave changed upstream signatures untouched."""
    if not isinstance(method, BuiltinFunctionSchema):
        return method
    param = next((param for param in method.params if param.name == "mtd_type"), None)
    if param is None or param.default_value != "Mtd":
        return method

    # The native class is a sentinel, distinct from the public Python override.
    param.default_value = "..."
    note = (
        "Stub note: the default is gst-python's internal native Mtd sentinel "
        "(all metadata types), represented here as ellipsis. Omit mtd_type to use it. "
        "With gst-python 1.28.8, explicitly passing the public GstAnalytics.Mtd class "
        "raises TypeError; concrete types such as GstAnalytics.ODMtd work."
    )
    method.docstring = f"{method.docstring}\n\n{note}" if method.docstring else note
    return method
