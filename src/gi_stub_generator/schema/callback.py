from pydantic import BaseModel
from typing import Any

from gi_stub_generator.schema import BaseSchema
from gi_stub_generator.schema.function import FunctionSchema


class CallbackSchema(FunctionSchema):
    def render_protocol(self) -> str:
        """
        Renders the Python Protocol definition.
        """
        # Filter arguments for the __call__ method (usually only IN and INOUT matter for input)
        # Note: In Python Protocols for callbacks, you usually define the input signature.
        input_args_str = ", ".join(f"{arg.name}: {arg.type_hint}" for arg in self.args)

        return f"""
class {self.name}(typing.Protocol):
    def __call__(self, {input_args_str}) -> {self.complete_return_hint}:
        ...
"""
