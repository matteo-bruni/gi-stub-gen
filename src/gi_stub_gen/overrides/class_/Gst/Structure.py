"""gst-python 1.28.3 annotates set_value as bool, but runtime returns None.

Preserve the installed Python signature and the GIR documentation merged by the parser.
"""

from gi_stub_gen.overrides.types import MethodSchema
from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema


def transform_set_value(method: MethodSchema) -> MethodSchema:
    if not isinstance(method, BuiltinFunctionSchema):
        raise TypeError("Gst.Structure.set_value requires a Python callable")
    if method.return_hint_name not in {"bool", "None"}:
        raise ValueError("Gst.Structure.set_value has an unexpected return annotation")
    method.return_hint_name = "None"
    method.return_hint_namespace = None
    method.return_is_optional = False
    return method
