from __future__ import annotations


import logging

from gi_stub_generator.schema import BaseSchema
from gi_stub_generator.schema.utils import ValueAny
from gi_stub_generator.utils import (
    get_type_hint,
    get_redacted_stub_value,
    sanitize_module_name,
)
from gi_stub_generator.utils import (
    is_py_builtin_type,
)

import gi._gi as GI  # pyright: ignore[reportMissingImports]
from gi.repository import GObject


# GObject.remove_emission_hook
logger = logging.getLogger(__name__)


class VariableSchema(BaseSchema):
    """
    Represents a variable in the gi repository, can be a constant or a variable
    """

    namespace: (
        str  # need to be passed since it is not available in the python std types
    )
    name: str
    value: ValueAny
    # value: Any | None

    is_deprecated: bool
    """Whether this variable is deprecated (from info)"""

    deprecation_warnings: str | None
    """Deprecation warning message, if any captured from PyGIDeprecationWarning"""

    type_repr: str
    """type representation in template"""

    value_repr: str
    """value representation in template"""

    gir_docstring: str | None

    is_enum_or_flags: bool
    """Whether this variable is an enum or flags (we avoid writing the type in the template)"""

    @property
    def docstring(self):
        docstring_str: list[str] = []
        if self.deprecation_warnings:
            docstring_str.append(f"[DEPRECATED] {self.deprecation_warnings}")

        if self.gir_docstring:
            docstring_str.append(f"{self.gir_docstring}")

        return "\n".join(docstring_str) or None

    @property
    def debug(self):
        """
        Debug docstring
        """
        if self.docstring:
            return f"{self.docstring}\n[DEBUG]\n{self.model_dump_json(indent=2)}"

        return f"[DEBUG]\n{self.model_dump_json(indent=2)}"

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
        sanitized_namespace = sanitize_module_name(namespace)
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

        if is_py_builtin_type(object_type):
            # remove sensitive information from value representation
            # i.e paths from string or
            if keep_builtin_value:
                value_repr = get_redacted_stub_value(obj)
            else:
                value_repr = "..."
            # or remove directly the value from builtin types
            # value_repr = "..."
            # value_repr = repr(obj)
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
                    if obj.first_value_nick is not None:
                        value_repr = (
                            f"{object_type_repr}.{obj.first_value_nick.upper()}"
                        )
                    else:
                        # Fallback to using the real value
                        value_repr = f"{object_type_repr}({obj.real})"

                if not is_flags:
                    # it is an enum
                    value_repr = f"{object_type_repr}.{obj.value_nick.upper()}"
        elif isinstance(obj, GObject.GType):
            value_repr = "..."
        else:
            # Fallback to using the real value
            logger.warning(
                "[WARNING] Object representation not found, using real value"
            )
            value_repr = f"{object_type_repr}({obj}) # TODO: not found ??"

        # if name == "SIGNAL_ACTION":
        #     breakpoint()
        # deprecation_warnings = catch_gi_deprecation_warnings(obj, name)
        return cls(
            namespace=sanitized_namespace,
            name=name,
            type_repr=object_type_repr,
            value=obj,
            value_repr=value_repr,
            is_deprecated=is_deprecated,
            gir_docstring=docstring,
            deprecation_warnings=deprecation_warnings,
            is_enum_or_flags=is_enum_or_flags,
        )
