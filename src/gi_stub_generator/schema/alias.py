from __future__ import annotations

import logging
from gi_stub_generator.schema import BaseSchema


# GObject.remove_emission_hook
logger = logging.getLogger(__name__)


class AliasSchema(BaseSchema):
    """
    Represents an alias in the current gi repository,
    i.e. a class or a function that is an alias for another repository object
    """

    name: str
    target_name: str | None
    target_namespace: str | None
    deprecation_warning: str | None
    line_comment: str | None

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
