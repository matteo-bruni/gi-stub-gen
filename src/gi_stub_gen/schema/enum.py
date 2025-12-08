from __future__ import annotations

from enum import StrEnum
import inspect
import keyword
import logging
from gi_stub_gen.gi_utils import get_safe_gi_array_length
from gi_stub_gen.manager import TemplateManager
from gi_stub_gen.parser.gir import GirClassDocs, GirFunctionDocs
from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.schema.alias import AliasSchema
from gi_stub_gen.schema.function import BuiltinFunctionSchema, FunctionSchema
from gi_stub_gen.schema.utils import ValueAny
from gi_stub_gen.utils import (
    catch_gi_deprecation_warnings,
    get_py_type_name_repr,
    get_py_type_namespace_repr,
    get_super_class_name,
    get_type_hint,
    infer_type_str,
    get_redacted_stub_value,
    sanitize_gi_module_name,
    sanitize_variable_name,
)
from gi_stub_gen.utils import (
    gi_type_is_callback,
    gi_type_to_py_type,
    is_py_builtin_type,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    SerializerFunctionWrapHandler,
    model_validator,
)
import gi._gi as GI  # pyright: ignore[reportMissingImports]
from gi.repository import GObject
from pydantic.functional_serializers import WrapSerializer
from typing import Annotated, Literal, Any

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
        value_info: GI.ValueInfo,
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
            line_comment = f"real value: ({value_info.get_name_unescaped()}) changed due to name being a python keyword"

        else:
            # some fields are not escaped by GI
            # i.e. GLIB.SpawnError.2BIG
            # so we add a generic sanitization step
            field_name, line_comment = sanitize_variable_name(value_info.get_name())

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

    def render(self) -> str:
        return TemplateManager.render_master("enum.jinja", enum=self)

    @classmethod
    def from_gi_object(
        cls,
        obj: Any,
        enum_type: Literal["enum", "flags"],
        fields: list[EnumFieldSchema],
        docstring: str | None,
    ):
        assert hasattr(obj, "__info__"), (
            "An Enum/Flags Object must have __info__ attribute"
        )

        gi_info = obj.__info__

        return cls(
            namespace=gi_info.get_namespace(),
            name=gi_info.get_name(),
            enum_type=enum_type,
            docstring=docstring,
            fields=fields,
            is_deprecated=gi_info.is_deprecated(),
            py_mro=[f"{o.__module__}.{o.__name__}" for o in obj.mro()],
        )

    @computed_field
    @property
    def py_super_type_str(self) -> str:
        """Return the python type as a string (otherwise capitalization is wrong)"""

        # in pygobject 3.50.0 GFlags and GEnum are in GObject namespace
        if self.namespace == "GObject":
            return "GFlags" if self.enum_type == "flags" else "GEnum"

        return "GObject.GFlags" if self.enum_type == "flags" else "GObject.GEnum"

    def __str__(self):
        deprecated = "[DEPRECATED]" if self.is_deprecated else ""
        args_str = "\n".join([f"   - {arg}" for arg in self.fields])
        mro = f"mro={self.py_mro}"
        return (
            f"{deprecated}namespace={self.namespace} name={self.name} {mro}\n{args_str}"
        )
