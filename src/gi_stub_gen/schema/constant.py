from __future__ import annotations


import enum
import logging

from gi_stub_gen.gi_utils import get_gi_module_from_name
from gi_stub_gen.template_manager import TemplateManager
from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.schema.utils import ValueAny
from gi_stub_gen.utils import (
    get_type_hint,
    get_redacted_stub_value,
    sanitize_gi_module_name,
    sanitize_variable_name,
)
from gi_stub_gen.utils import (
    is_py_builtin_type,
)

import gi._gi as GI  # pyright: ignore[reportMissingImports]
from gi.repository import GObject


# GObject.remove_emission_hook
logger = logging.getLogger(__name__)


class VariableType(enum.Enum):
    PYTHON_TYPE = "PYTHON_TYPE"  # i.e int, str, float, dict, list, tuple
    GENUM = "GENUM"
    GFLAGS = "GFLAGS"
    UNKNOWN = "UNKNOWN"  # fallback type


class VariableSchema(BaseSchema):
    """
    Represents a variable in the gi repository, can be a constant or a variable
    """

    namespace: str  # need to be passed since it is not available in the python std types
    name: str
    value: ValueAny
    # value: Any | None

    is_deprecated: bool
    """Whether this variable is deprecated (from info)"""

    deprecation_warnings: str | None
    """Deprecation warning message, if any captured from PyGIDeprecationWarning"""

    type_hint: str
    """type representation in template"""

    value_repr: str
    """value representation in template"""

    gir_docstring: str | None

    is_enum_or_flags: bool
    """Whether this variable is an enum or flags (we avoid writing the type in the template)"""

    line_comment: str | None
    """line comment for the alias.
    Can be used to add annotations like # type: ignore
    or to explain if the name was sanitized."""

    variable_type: VariableType
    """Type of the variable, used mainly for debugging purposes"""

    @property
    def docstring(self):
        docstring_str: list[str] = []
        if self.deprecation_warnings:
            docstring_str.append(f"[DEPRECATED] {self.deprecation_warnings.strip()}")

        if self.gir_docstring:
            docstring_str.append(f"{self.gir_docstring}")

        return "\n".join(docstring_str) or None

    def render(self) -> str:
        return TemplateManager.render_master("constant.jinja", constant=self)

    @classmethod
    def from_gi_object(
        cls,
        obj,
        namespace: str,  # need to be passed since it is not available for python std types
        name: str,
        docstring: str | None,
        deprecation_warnings: str | None = None,
        keep_builtin_value: bool = False,
    ):
        # breakpoint()
        sanitized_namespace = sanitize_gi_module_name(namespace)
        object_type = type(obj)
        object_type_namespace: str | None = None
        if hasattr(obj, "__info__"):
            if obj.__info__.get_namespace() != sanitized_namespace:
                object_type_namespace = str(obj.__info__.get_namespace())

        # type representation in template should include namespace only if
        # it is different from the current namespace
        object_type_repr = object_type.__name__
        if object_type_namespace and object_type_namespace != sanitized_namespace:
            object_type_repr = f"{object_type_namespace}.{object_type_repr}"

        # get value representation in template
        value_repr: str = ""
        is_deprecated = False
        is_enum_or_flags = False
        line_comment: str | None = None
        variable_type: VariableType = VariableType.UNKNOWN

        if is_py_builtin_type(object_type):
            variable_type = VariableType.PYTHON_TYPE
            # remove sensitive information from value representation
            # i.e paths from string or
            if keep_builtin_value:
                value_repr = get_redacted_stub_value(obj)
            else:
                value_repr = "..."
            if isinstance(obj, (dict, list, tuple)):
                # for dicts we also include the type representation
                # value_repr = "..."
                object_type_repr = get_type_hint(obj)

        elif hasattr(obj, "__info__"):
            if hasattr(obj.__info__, "is_deprecated"):
                is_deprecated = obj.__info__.is_deprecated()

            # value is from gi: can be an enum or flags
            # both are GI.EnumInfo
            if type(obj.__info__) is GI.EnumInfo:
                is_flags = obj.__info__.is_flags()
                is_enum_or_flags = True

                if is_flags:
                    variable_type = VariableType.GFLAGS
                    flags_field_name = obj.first_value_nick if hasattr(obj, "first_value_nick") else None
                    # check if valid identifier

                    # if flags_field_name.upper() == "IN":
                    #     breakpoint()

                    if flags_field_name is not None:
                        # note: keyword are fine as class fields
                        # we just need to check if they are valid identifiers
                        is_valid = flags_field_name.isidentifier()
                        if is_valid:
                            value_repr = f"{object_type_repr}.{flags_field_name.upper()}"
                        else:
                            # Fallback to using the real value
                            value_repr = f"{object_type_repr}({obj.real})"
                            line_comment = f"nick: ({object_type_repr}.{flags_field_name.upper()}) changed due to name being a python keyword or invalid identifier"
                    else:
                        # some flags inherit from enum.IntFlag and not from GObject.Flags
                        # so first_value_nick is not present
                        try:
                            # try to get the flag name instantiating the enum class
                            module = get_gi_module_from_name(f"gi.repository.{str(obj.__info__.get_namespace())}", None)
                            enum_class = getattr(module, object_type.__name__)

                            flags_field_name = enum_class(obj.real).name
                            if flags_field_name is not None:
                                value_repr = f"{object_type.__name__}.{flags_field_name}"
                            else:
                                # Fallback to using the real value
                                value_repr = f"{object_type_repr}({obj.real})"
                        except Exception:
                            # Fallback to using the real value
                            value_repr = f"{object_type_repr}({obj.real})"
                else:
                    variable_type = VariableType.GENUM
                    # it is an enum
                    enum_field_name = obj.value_nick.upper() if hasattr(obj, "value_nick") else None

                    if enum_field_name is not None:
                        # the value of the enum could be invalid due to not being
                        # a valid python identifier
                        # we apply the same logic when parsing enum/flags fields
                        sanitized_name, line_comment = sanitize_variable_name(enum_field_name)

                        value_repr = f"{object_type_repr}.{sanitized_name}"
                    else:
                        # some enums inherit from enum.IntEnum and not from GObject.Enum
                        # so value_nick is not present
                        try:
                            # try to get the value name instantiating the enum class
                            module = get_gi_module_from_name(f"gi.repository.{str(obj.__info__.get_namespace())}", None)
                            enum_class = getattr(module, object_type.__name__)
                            enum_field_name = enum_class(obj.value).name

                            if enum_field_name is not None:
                                value_repr = f"{object_type.__name__}.{enum_class(obj.value).name}"
                            else:
                                # Fallback to using the real value
                                value_repr = f"{object_type_repr}({obj.value})"
                        except Exception:
                            # Fallback to using the real value
                            value_repr = f"{object_type_repr}({obj.value})"

        elif isinstance(obj, GObject.GType):
            value_repr = "..."
        else:
            # Fallback to using the real value
            logger.warning("[WARNING] Object representation not found, using real value")
            value_repr = f"{object_type_repr}({obj})"
            line_comment = "TODO: not found ??"

        return cls(
            namespace=sanitized_namespace,
            name=name,
            type_hint=object_type_repr,
            value=obj,
            value_repr=value_repr,
            is_deprecated=is_deprecated,
            gir_docstring=docstring,
            deprecation_warnings=deprecation_warnings,
            is_enum_or_flags=is_enum_or_flags,
            line_comment=line_comment,
            variable_type=variable_type,
        )
