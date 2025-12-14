from __future__ import annotations

import logging
from typing import Any

import gi._gi as GI  # type: ignore
from gi_stub_gen.schema.function import FunctionSchema

logger = logging.getLogger(__name__)


def parse_function(
    attribute: Any,
    docstring: str | None,
    # docstring: dict[str, GirFunctionDocs],
) -> FunctionSchema | None:
    is_function = isinstance(attribute, GI.FunctionInfo)
    if not is_function:
        return None

    # this has happened in i.repository.GstVideo.VideoChromaResample
    # there is a function with an empty name ???
    if attribute.get_name() == "":
        logger.error("Found function with an empty name!?!, skipping...")
        return None

    return FunctionSchema.from_gi_object(
        obj=attribute,
        docstring=docstring,
    )
