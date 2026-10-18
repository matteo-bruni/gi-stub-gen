"""PyGObject 3.56.3 accepts a Python payload despite Gio GIR's GValue input.

Verified with Task.return_value(42) / propagate_value(); preserve the GI default.
"""

from gi_stub_gen.overrides.types import MethodSchema
from gi_stub_gen.schema.function import FunctionSchema


def transform_return_value(method: MethodSchema) -> MethodSchema:
    if not isinstance(method, FunctionSchema):
        raise TypeError("Gio.Task.return_value requires a GI callable")
    arguments = [arg for arg in method.args if arg.name == "result"]
    if len(arguments) != 1 or arguments[0].direction != "IN":
        raise ValueError("Gio.Task.return_value requires one IN argument named result")
    argument = arguments[0]
    if not (
        (argument.py_type_name == "Value" and argument.py_type_namespace == "GObject")
        or (argument.py_type_name == "Any" and argument.py_type_namespace == "typing")
    ):
        raise ValueError("Gio.Task.return_value result is no longer a GValue payload")
    argument.py_type_name = "Any"
    argument.py_type_namespace = "typing"
    argument.is_marshaled_gvalue_payload = True
    return method
