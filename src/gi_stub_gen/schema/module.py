from __future__ import annotations

import logging

from gi_stub_gen.utils import sanitize_module_name

from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.schema.alias import AliasSchema
from gi_stub_gen.schema.constant import VariableSchema
from gi_stub_gen.schema.function import (
    BuiltinFunctionSchema,
    FunctionSchema,
    CallbackSchema,
)
from gi_stub_gen.schema.class_ import ClassSchema
from gi_stub_gen.schema.enum import EnumSchema

import gi._gi as GI  # pyright: ignore[reportMissingImports]
from gi.repository import GObject

# GObject.remove_emission_hook
logger = logging.getLogger(__name__)


class ModuleSchema(BaseSchema):
    name: str
    version: int = 1
    # attributes: list[Attribute]
    classes: list[ClassSchema]
    constant: list[VariableSchema]
    enum: list[EnumSchema]
    function: list[FunctionSchema]
    builtin_function: list[BuiltinFunctionSchema]
    callbacks: list[CallbackSchema]
    aliases: list[AliasSchema]

    def to_pyi(self, debug=False) -> str:
        """
        Return the module as a pyi file
        """
        import jinja2
        from gi_stub_gen.template import TEMPLATE

        environment = jinja2.Environment()
        output_template = environment.from_string(TEMPLATE)
        sanitized_module_name = sanitize_module_name(self.name)

        # print(self.callbacks)
        return output_template.render(
            module=sanitized_module_name,
            # module=module.__name__.split(".")[-1],
            constants=self.constant,
            enums=self.enum,
            functions=self.function,
            builtin_function=self.builtin_function,
            classes=self.classes,
            debug=debug,
            aliases=self.aliases,
            callbacks=self.callbacks,
        )
