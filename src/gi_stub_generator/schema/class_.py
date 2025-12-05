from __future__ import annotations


import logging
from gi_stub_generator.parser.gir import ClassDocs
from gi_stub_generator.schema import BaseSchema
from gi_stub_generator.schema.function import FunctionSchema
from gi_stub_generator.schema.constant import VariableSchema
from gi_stub_generator.utils import get_super_class_name


import gi._gi as GI  # pyright: ignore[reportMissingImports]
from gi.repository import GObject
from typing import Any, TYPE_CHECKING


# GObject.remove_emission_hook
logger = logging.getLogger(__name__)


class ClassPropSchema(BaseSchema):
    name: str
    type: str
    is_deprecated: bool
    readable: bool
    writable: bool

    line_comment: str | None
    type_repr: str
    """type representation in template"""


class ClassSchema(BaseSchema):
    namespace: str
    name: str
    super: list[str]
    docstring: ClassDocs | None

    props: list[ClassPropSchema]
    attributes: list[VariableSchema]
    methods: list[FunctionSchema]
    extra: list[str]

    is_deprecated: bool

    @classmethod
    def from_gi_object(
        cls,
        namespace: str,
        obj: Any,
        docstring: ClassDocs | None,
        props: list[ClassPropSchema],
        attributes: list[VariableSchema],
        methods: list[FunctionSchema],
        extra: list[str],
    ):
        gi_info = None
        if hasattr(obj, "__info__"):
            gi_info = obj.__info__

        is_deprecated = gi_info.is_deprecated() if gi_info else False
        try:
            extra.extend(
                [
                    f"mro={obj.__mro__}",
                    # f"mro={obj.mro()}",
                    f"self={obj.__module__}.{obj.__name__}",
                ]
            )
        except Exception as e:
            breakpoint()

        return cls(
            namespace=namespace,
            name=obj.__name__,
            super=[get_super_class_name(obj, current_namespace=namespace)],
            docstring=docstring,
            props=props,
            attributes=attributes,
            methods=methods,
            is_deprecated=is_deprecated,
            extra=extra,
            # _gi_callbacks=gi_callbacks,
        )

    @property
    def debug(self):
        """
        Debug docstring
        """

        data = ""
        if self.docstring:
            data = f"{self.docstring}"

        return f"{data}\n[DEBUG]\n{self.model_dump_json(indent=2)}"
