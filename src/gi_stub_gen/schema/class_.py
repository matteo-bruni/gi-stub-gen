from __future__ import annotations


import logging

from typing import Any
from gi_stub_gen.manager import TemplateManager
from gi_stub_gen.parser.gir import GirClassDocs
from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.schema.function import FunctionSchema
from gi_stub_gen.utils import get_super_class_name, sanitize_gi_module_name


# GObject.remove_emission_hook
logger = logging.getLogger(__name__)


class ClassPropSchema(BaseSchema):
    """
    Represents a property of a GI class.
    These are available in a <class>.props.<property_name> fashion.
    """

    name: str
    # type: str
    is_deprecated: bool
    readable: bool
    writable: bool

    docstring: str | None

    line_comment: str | None
    """line comment for the property. 
    Can be used to add annotations like # type: ignore
    or to explain if the name was sanitized."""

    type_hint_full: str
    """type hint in template (with namespace if different from parent)"""

    type_hint_namespace: str | None
    """type hint namespace, if any"""

    type_hint_name: str
    """type hint name (without namespace)"""

    may_be_null: bool
    """True if the property may be None, False otherwise."""


class ClassAttributeSchema(BaseSchema):
    name: str
    type_hint: str
    """type hint in template"""

    is_deprecated: bool
    deprecation_warnings: str | None
    """Deprecation warning message, if any captured from PyGIDeprecationWarning"""

    docstring: str | None

    required_gi_import: str | None
    """required gi.repository<NAME> import for the property type, if any"""

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

    required_gi_import: str | None
    """required gi.repository<NAME> import for the property type, if any"""

    @property
    def required_gi_imports(self) -> set[str]:
        """
        Required gi.repository<NAME> import for the class, if any.
        Gather from properties and attributes.
        """
        gi_imports: set[str] = set()
        if self.required_gi_import:
            gi_imports.add(self.required_gi_import)
        for prop in self.props:
            if prop.type_hint_namespace:
                gi_imports.add(prop.type_hint_namespace)
        for attr in self.attributes:
            if attr.required_gi_import:
                gi_imports.add(attr.required_gi_import)
        for method in self.methods:
            gi_imports.update(method.required_gi_imports)
        return gi_imports

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

        base_class_namespace, base_class_name = get_super_class_name(
            obj,
            current_namespace=namespace,
        )

        sane_namespace = sanitize_gi_module_name(namespace)
        sane_super_namespace = (
            sanitize_gi_module_name(base_class_namespace)
            if base_class_namespace
            else None
        )
        # some super classes are in "gi" namespace
        # which is actually gi._gi hidden in the C modules
        # to use it in python we import it as: import gi._gi as GI
        # for example the actual base classed of
        # gi.Struct is actually in gi._gi.Struct
        # gi.Boxed is actually in gi._gi.Boxed
        # we map them to the closes objects in GObject
        if sane_super_namespace == "gi" and base_class_name == "Boxed":
            sane_super_namespace = "GObject"
            base_class_name = "GBoxed"
        if sane_super_namespace == "gi" and base_class_name == "Struct":
            sane_super_namespace = "GObject"
            base_class_name = "GPointer"
        if sane_super_namespace == "gi" and base_class_name == "Fundamental":
            sane_super_namespace = None
            base_class_name = "object"

        # build the super class name in the template
        required_gi_import = None
        base_class = base_class_name
        if sane_namespace != sane_super_namespace and sane_super_namespace is not None:
            # they are in different namespaces
            # so we add it to the repr
            base_class = f"{sane_super_namespace}.{base_class_name}"
            if sane_super_namespace != "GI":
                # we exclude GI which is from "import gi._gi as GI" which is always imported
                required_gi_import = sane_super_namespace

        # if "." in base_class:
        #     base_module = base_class.split(".")[0]
        #     if base_module != namespace:
        #         required_gi_import = base_module

        return cls(
            namespace=namespace,
            name=obj.__name__,
            bases=[base_class],
            docstring=class_docstring,
            props=props,
            attributes=attributes,
            methods=methods,
            is_deprecated=is_deprecated,
            extra=extra,
            required_gi_import=required_gi_import,
            # _gi_callbacks=gi_callbacks,
        )

    @property
    def super_class(self) -> str | None:
        """
        Get the super class name, if any.
        """
        return ", ".join(self.bases)

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
