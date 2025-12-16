from __future__ import annotations

import logging
from enum import Enum, Flag
from typing import Any
from gi.repository import GObject

from gi_stub_gen.gir_manager import GIRDocs
from gi_stub_gen.schema.enum import EnumFieldSchema, EnumSchema

logger = logging.getLogger(__name__)


def parse_enum(
    attribute: Any,
) -> EnumSchema | None:
    """
    Parse a GI enum/flag class.
    """
    if not isinstance(attribute, type):
        return None

    is_flags = issubclass(attribute, GObject.GFlags) or issubclass(attribute, Flag)  # due to new pygobject Enum support
    is_enum = issubclass(attribute, GObject.GEnum) or issubclass(attribute, Enum)  # due to new pygobject Enum support

    if is_flags or is_enum:
        # GObject.Enum and Gobject.Flags do not have __info__ attribute
        if hasattr(attribute, "__info__"):
            _type_info = attribute.__info__  # type: ignore

            # to retrieve its docstring we need to get the name of the class
            class_name = attribute.__info__.get_name()  # type: ignore

            # DOCSTRING HANDLING

            class_docstring = GIRDocs().get_enum_docstring(class_name)
            ##############################

            # parse all possible enum/flag values
            # and retrieve their docstrings
            args: dict[str, EnumFieldSchema] = {}
            for v in _type_info.get_values():
                field_docstring = GIRDocs().get_enum_field_docstring(class_name, v.get_name())
                parsed_field = EnumFieldSchema.from_gi_value_info(
                    value_info=v,
                    docstring=field_docstring,
                    deprecation_warnings=None,
                    # deprecation_warnings=deprecation_warnings,
                )

                if parsed_field.name in args:
                    logger.warning(
                        f"Enum/Flag {class_name} has duplicate field name {parsed_field.name}. Skipping duplicate."
                    )
                    continue
                args[parsed_field.name] = parsed_field

            return EnumSchema.from_gi_object(
                obj=attribute,
                enum_type="flags" if is_flags else "enum",
                fields=[a for a in args.values()],
                docstring=class_docstring,
            )
        else:
            logger.warning(f"Attribute {attribute} is an enum/flag but has no __info__ attribute. Skipping.")

    return None
