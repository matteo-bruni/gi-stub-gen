from __future__ import annotations

import logging
from typing import Any

import gi._gi as GI  # type: ignore
from gi_stub_gen.schema.function import FunctionSchema

logger = logging.getLogger(__name__)


KNOWN_UNSUPPORTED_GI_FUNCTIONS = {
    ("GObject", "signal_set_va_marshaller"): "VaClosureMarshal is marked introspectable=0 in the GIR",
}


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

    function_key = (attribute.get_namespace(), attribute.get_name())
    if function_key in KNOWN_UNSUPPORTED_GI_FUNCTIONS:
        logger.warning(
            "Skipping %s.%s: %s",
            function_key[0],
            function_key[1],
            KNOWN_UNSUPPORTED_GI_FUNCTIONS[function_key],
        )
        return None

    return FunctionSchema.from_gi_object(
        obj=attribute,
        docstring=docstring,
    )
