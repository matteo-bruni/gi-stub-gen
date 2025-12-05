from __future__ import annotations

import logging
from enum import Enum
from typing import Any
from venv import logger
from gi.repository import GObject

from gi_stub_generator.parser.gir import ClassDocs
from gi_stub_generator.schema.enum import EnumFieldSchema, EnumSchema

logger = logging.getLogger(__name__)


def parse_enum(
    attribute: Any,
    docs: dict[str, ClassDocs],
    deprecation_warnings: str | None,  # deprecation warnings if any
) -> EnumSchema | None:
    is_flags = isinstance(attribute, type) and issubclass(attribute, GObject.GFlags)
    is_enum = isinstance(attribute, type) and (
        issubclass(attribute, GObject.GEnum)
        or issubclass(attribute, Enum)  # due to new pygobject Enum support
    )

    if is_flags or is_enum:
        # GObject.Enum and Gobject.Flags do not have __info__ attribute
        if hasattr(attribute, "__info__"):
            _type_info = attribute.__info__  # type: ignore

            # to retrieve its docstring we need to get the name of the class
            class_name = attribute.__info__.get_name()  # type: ignore
            class_doc_data = docs.get(class_name, None)

            # class docstring
            class_docstring = None
            if class_doc_data:
                class_docstring = class_doc_data.class_docstring

            # parse all possible enum/flag values
            # and retrieve their docstrings
            args: list[EnumFieldSchema] = []
            for v in _type_info.get_values():
                element_docstring = None
                if class_doc_data:
                    element_docstring = class_doc_data.fields.get(v.get_name(), None)
                args.append(
                    EnumFieldSchema.from_gi_value_info(
                        value_info=v,
                        docstring=element_docstring,
                        deprecation_warnings=deprecation_warnings,
                    )
                )
            return EnumSchema.from_gi_object(
                obj=attribute,
                enum_type="flags" if is_flags else "enum",
                fields=args,
                docstring=class_docstring,
            )
        else:
            logger.warning(
                f"Attribute {attribute} is an enum/flag but has no __info__ attribute. Skipping."
            )

    return None
