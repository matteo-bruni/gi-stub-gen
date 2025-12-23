from __future__ import annotations

import enum
import logging

from gi_stub_gen.template_manager import TemplateManager
from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.utils import sanitize_variable_name
import gi._gi as GI  # pyright: ignore[reportMissingImports]
from gi.repository import GObject, GIRepository
from typing import Literal, Any

# GObject.remove_emission_hook
logger = logging.getLogger(__name__)


class EnumFieldSchema(BaseSchema):
    name: str
    value: int
    value_repr: str
    """value representation in template"""

    is_deprecated: bool

    deprecation_warnings: str | None
    """Deprecation warning message, if any captured from PyGIDeprecationWarning"""

    line_comment: str | None
    """line comment for the enum field.
    Can be used to add annotations like # type: ignore
    or to explain if the name was sanitized."""

    docstring: str | None = None

    @classmethod
    def from_gi_value_info(
        cls,
        value_info: GI.ValueInfo,  # GIRepository.ValueInfo but missing the functions addedd by pygobject
        docstring: str | None,
        deprecation_warnings: str | None,
    ):
        # TODO:
        # value_info.get_name() != value_info.get_name_unescaped()
        # example: GLib.IOCondition.IN_ vs GLib.IOCondition.IN
        # gobject escape the name in get_name because "in" is a keyword in python
        # for now we just use the unescaped name
        # field_name, line_comment = sanitize_variable_name(value_info.get_name())
        # NOW IT IS DONE DIRECTLY BY THE GI TOOLKIT
        # KEEPING THIS CODE FOR FUTURE REFERENCE

        field_name = value_info.get_name()
        line_comment = None
        if value_info.get_name_unescaped() != value_info.get_name():
            # GLib.IOCondition.IN has get_name_unescaped "in" and get_name "in_"
            # In this case escaping "in" to "in_" should not be done
            # because even if they are keywords they are valid as class fields
            # we just check again if there are other issues with the name
            field_name, line_comment = sanitize_variable_name(
                value_info.get_name_unescaped(),
                keyword_check=False,
            )
            # if value_info.get_name_unescaped() == "in":
            #     breakpoint()
            # if line_comment is not None:
            #     field_name = sane_name_unescaped

        else:
            # some fields are not escaped by GI
            # i.e. GLIB.SpawnError.2BIG
            # so we add a generic sanitization step
            # keyword are fine as class fields
            field_name, line_comment = sanitize_variable_name(
                value_info.get_name(),
                keyword_check=False,
            )

        return cls(
            name=field_name.upper(),
            value=value_info.get_value(),
            value_repr=repr(value_info.get_value()),
            is_deprecated=value_info.is_deprecated(),
            docstring=docstring,
            deprecation_warnings=deprecation_warnings,
            line_comment=line_comment,
        )

    def __str__(self):
        deprecated = "[DEPRECATED] " if self.is_deprecated else ""
        return f"name={self.name} value={self.value} {deprecated}"


class EnumSchema(BaseSchema):
    enum_type: Literal["enum", "flags"]

    py_mro: list[str]
    """Used for debugging purposes"""

    namespace: str
    name: str
    docstring: str | None = None
    is_deprecated: bool
    fields: list[EnumFieldSchema]

    super_name: str
    """Return the super type name only"""
    super_namespace: str
    """Return the super type namespace only"""

    def render(self) -> str:
        return TemplateManager.render_master("enum.jinja", enum=self)

    def super_full_type_str(self, module_name: str) -> str:
        """
        Return the full python super type as a string
        adding namespace if different from `module_name`
        """
        if self.super_namespace != module_name:
            return f"{self.super_namespace}.{self.super_name}"
        return self.super_name

    @property
    def required_gi_import(self) -> str:
        """Return the required imports for this enum/flags. (without gi.repository. prefix)"""
        return self.super_namespace

    @classmethod
    def from_gi_object(
        cls,
        obj: Any,
        enum_type: Literal["enum", "flags"],
        fields: list[EnumFieldSchema],
        docstring: str | None,
    ):
        assert hasattr(obj, "__info__"), "An Enum/Flags Object must have __info__ attribute"

        gi_info = obj.__info__
        namespace = gi_info.get_namespace()

        super_name: str
        super_namespace: str
        if enum_type == "enum":
            if GObject.GEnum in obj.mro():
                super_name = "GEnum"
                super_namespace = "GObject"
            elif enum.IntEnum in obj.mro():
                super_name = "IntEnum"
                super_namespace = "enum"
            else:
                raise AssertionError(f"Enum {gi_info.get_name()} does not inherit from GObject.GEnum or enum.IntEnum")
        else:
            if GObject.GFlags in obj.mro():
                super_name = "GFlags"
                super_namespace = "GObject"
            elif enum.IntFlag in obj.mro():
                super_name = "IntFlag"
                super_namespace = "enum"
            else:
                raise AssertionError(f"Flags {gi_info.get_name()} does not inherit from GObject.GFlags or enum.IntFlag")

        return cls(
            namespace=namespace,
            name=gi_info.get_name(),
            enum_type=enum_type,
            docstring=docstring,
            fields=fields,
            is_deprecated=gi_info.is_deprecated(),
            py_mro=[f"{o.__module__}.{o.__name__}" for o in obj.mro()],
            super_name=super_name,
            super_namespace=super_namespace,
        )

    # @computed_field
    # @property
    # def py_super_type_str(self) -> str:
    #     """Return the python type as a string (otherwise capitalization is wrong)"""

    #     # TODO: if we are in GLib this is just enum.IntFlag / enum.IntEnum

    #     # in pygobject 3.50.0 GFlags and GEnum are in GObject namespace
    #     if self.namespace == "GObject":
    #         return "GFlags" if self.enum_type == "flags" else "GEnum"
    #     elif self.namespace == "GLib":
    #         return "enum.IntFlag" if self.enum_type == "flags" else "enum.IntEnum"

    #     return "GObject.GFlags" if self.enum_type == "flags" else "GObject.GEnum"

    def __str__(self):
        deprecated = "[DEPRECATED]" if self.is_deprecated else ""
        args_str = "\n".join([f"   - {arg}" for arg in self.fields])
        mro = f"mro={self.py_mro}"
        return f"{deprecated}namespace={self.namespace} name={self.name} {mro}\n{args_str}"
