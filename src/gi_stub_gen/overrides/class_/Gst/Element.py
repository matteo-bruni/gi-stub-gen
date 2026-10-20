"""PyGObject accepts an element class wherever register expects its native GType."""

from gi_stub_gen.overrides.types import MethodSchema
from gi_stub_gen.schema.function import FunctionSchema


def transform_register(method: MethodSchema) -> MethodSchema:
    if not isinstance(method, FunctionSchema):
        raise TypeError("Gst.Element.register requires a GI callable")
    argument = next(arg for arg in method.args if arg.name == "type")
    if (argument.py_type_namespace, argument.py_type_name) != ("GObject", "GType"):
        raise ValueError("Gst.Element.register has an unexpected type argument")
    argument.input_type_name = "GObject.GType | type[Element]"
    argument.input_type_namespace = None
    return method
