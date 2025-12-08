from __future__ import annotations
from typing import Literal

from gi_stub_gen.manager import TemplateManager
from gi_stub_gen.schema import BaseSchema

__all__ = ["AliasSchema"]


class AliasSchema(BaseSchema):
    """
    Represents an alias in the current gi repository,
    i.e. a class or a function that is an alias for another repository object
    """

    name: str
    """name of the alias"""

    target_name: str | None
    """name of the target object"""

    target_namespace: str | None
    """namespace of the target object"""

    deprecation_warning: str | None
    """Deprecation warning message, if any captured from PyGIDeprecationWarning"""

    line_comment: str | None
    """line comment for the alias.
    Can be used to add annotations like # type: ignore
    or to explain if the name was sanitized."""

    alias_to: Literal["same_module", "other_module"]

    @property
    def target_repr(self):
        """
        Return the target representation in template
        """
        if self.target_namespace and self.target_name:
            return f"{self.target_namespace}.{self.target_name}"
        elif self.target_name:
            return self.target_name

        return "..."

    @property
    def docstring(self):
        if self.deprecation_warning:
            return f"[DEPRECATED] {self.deprecation_warning}"

        return None

    def render(self) -> str:
        return TemplateManager.render_master("alias.jinja", alias=self)
