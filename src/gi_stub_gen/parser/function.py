from __future__ import annotations

import gi
import gi._gi as GI  # type: ignore


from typing import Any

from gi_stub_gen.gi_utils import get_gi_type_info
from gi_stub_gen.parser.gir import GirFunctionDocs
from gi_stub_gen.schema.function import FunctionSchema, FunctionArgumentSchema
from gi_stub_gen.utils import gi_type_is_callback


def parse_function(
    attribute: Any,
    docstring: str | None,
    # docstring: dict[str, GirFunctionDocs],
    deprecation_warnings: str | None,  # deprecation warnings if any
) -> FunctionSchema | None:
    # if it is a class exit

    is_function = isinstance(attribute, GI.FunctionInfo)
    if not is_function:
        return None

    return FunctionSchema.from_gi_object(
        obj=attribute,
        docstring=docstring,
        # docstring=docstring.get(attribute.get_name(), None),
    )
