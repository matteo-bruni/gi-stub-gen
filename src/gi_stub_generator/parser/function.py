from __future__ import annotations

import gi._gi as GI  # type: ignore
from typing import Any

from gi_stub_generator.parser.gir import FunctionDocs
from gi_stub_generator.schema import FunctionSchema


def parse_function(
    attribute: Any,
    docstring: dict[str, FunctionDocs],
    deprecation_warnings: str | None,  # deprecation warnings if any
) -> FunctionSchema | None:
    is_callback = isinstance(attribute, GI.CallbackInfo)
    is_function = isinstance(attribute, GI.FunctionInfo)

    if not is_callback and not is_function:
        # print("not a callback or function skip", type(attribute))
        return None

    return FunctionSchema.from_gi_object(
        obj=attribute,
        docstring=docstring.get(attribute.get_name(), None),
    )
