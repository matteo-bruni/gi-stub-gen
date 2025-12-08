from __future__ import annotations


import logging

import jinja2
from gi_stub_gen.manager import TemplateManager
from gi_stub_gen.parser.gir import GirClassDocs
from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.schema.function import FunctionSchema
from gi_stub_gen.schema.constant import VariableSchema
from gi_stub_gen.utils import get_super_class_name


import gi._gi as GI  # pyright: ignore[reportMissingImports]
from gi.repository import GObject
from typing import Any, TYPE_CHECKING


# GObject.remove_emission_hook
logger = logging.getLogger(__name__)


class ClassPropSchema(BaseSchema):
    """
    Represents a property of a GI class.
    These are available in a <class>.props.<property_name> fashion.
    """

    name: str
    type: str
    is_deprecated: bool
    readable: bool
    writable: bool

    docstring: str | None

    line_comment: str | None
    """line comment for the property. 
    Can be used to add annotations like # type: ignore
    or to explain if the name was sanitized."""

    type_hint: str
    """type hint in template"""


class ClassAttributeSchema(BaseSchema):
    name: str
    type_hint: str
    """type hint in template"""

    is_deprecated: bool
    deprecation_warnings: str | None
    """Deprecation warning message, if any captured from PyGIDeprecationWarning"""

    docstring: str | None

    # @classmethod
    # def from_gi_value_info(
    #     cls,
    #     value_info: GI.ValueInfo,
    #     docstring: str | None,
    #     deprecation_warnings: str | None,
    # ):
    #     field_name = value_info.get_name()
    #     return cls(
    #         name=field_name.upper(),
    #         value=value_info.get_value(),
    #         value_repr=repr(value_info.get_value()),
    #         is_deprecated=value_info.is_deprecated(),
    #         docstring=docstring,
    #         deprecation_warnings=deprecation_warnings,
    #     )

    # def __str__(self):
    #     deprecated = "[DEPRECATED] " if self.is_deprecated else ""
    #     return f"name={self.name} value={self.value} {deprecated}"


class ClassSchema(BaseSchema):
    bases: list[str]
    namespace: str
    name: str
    docstring: str | None
    props: list[ClassPropSchema]
    attributes: list[ClassAttributeSchema]
    methods: list[FunctionSchema]
    extra: list[str]
    is_deprecated: bool

    @classmethod
    def from_gi_object(
        cls,
        namespace: str,
        obj: Any,
        docstring: GirClassDocs | None,
        props: list[ClassPropSchema],
        attributes: list[ClassAttributeSchema],
        methods: list[FunctionSchema],
        extra: list[str],
    ):
        gi_info = None
        if hasattr(obj, "__info__"):
            gi_info = obj.__info__

        is_deprecated = gi_info.is_deprecated() if gi_info else False

        ## WIP DEBUGGING PURPOSES
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
        ## END WIP DEBUGGING PURPOSES

        class_docstring = None
        if docstring:
            class_docstring = docstring.class_docstring

        return cls(
            namespace=namespace,
            name=obj.__name__,
            bases=[get_super_class_name(obj, current_namespace=namespace)],
            docstring=class_docstring,
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

    def render(self) -> str:
        return TemplateManager.render_master("class.jinja", cls_=self)


# {%- if cls.docstring %}
# \"\"\"
# {{ cls.docstring | indent(4) }}
# \"\"\"
# {%- endif %}

# {%- if not cls.methods and not cls.properties %}
# ...
# {%- endif %}

# {# PROPRIETA' #}
# {%- for prop in cls.properties %}
# @property
# def {{ prop.name }}(self) -> {{ prop.type_repr }}: ...
# {%- if prop.can_write %}
# @{{ prop.name }}.setter
# def {{ prop.name }}(self, value: {{ prop.type_repr }}): ...
# {%- endif %}
# {% endfor %}

# {# METODI #}
# {%- for method in cls.methods %}
# {# Qui chiamiamo il render del figlio e lo indentiamo di 4 spazi #}
# {{ method.render() | indent(4, first=True) }}
# {% endfor %}
