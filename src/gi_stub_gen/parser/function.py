from __future__ import annotations

from typing import Any

import gi._gi as GI  # type: ignore
from gi_stub_gen.schema.function import FunctionSchema


def parse_function(
    attribute: Any,
    docstring: str | None,
    # docstring: dict[str, GirFunctionDocs],
) -> FunctionSchema | None:
    is_function = isinstance(attribute, GI.FunctionInfo)
    if not is_function:
        return None

    return FunctionSchema.from_gi_object(
        obj=attribute,
        docstring=docstring,
    )
