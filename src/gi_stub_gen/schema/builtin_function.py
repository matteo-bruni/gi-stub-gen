from enum import StrEnum
import inspect

from pydantic import BaseModel, Field

from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.t_manager import TemplateManager


class FunctionMethodType(StrEnum):
    INSTANCE = "INSTANCE"  # def method(self, ...)
    CLASS = "CLASS"  # @classmethod def method(cls, ...)
    STATIC = "STATIC"  # @staticmethod def method(...)
    UNKNOWN = "UNKNOWN"


class ArgKind(StrEnum):
    POSITIONAL_OR_KEYWORD = "POS_OR_KW"  # Standard (a)
    POSITIONAL_ONLY = "POS_ONLY"  # Python 3.8+ (a, /)
    KEYWORD_ONLY = "KW_ONLY"  # (*, a)
    VAR_POSITIONAL = "VAR_POS"  # *args
    VAR_KEYWORD = "VAR_KW"  # **kwargs

    @classmethod
    def from_inspect(cls, kind: inspect._ParameterKind) -> "ArgKind":
        """
        Factory method to convert inspect.Parameter.kind to ArgKind.
        """
        # Mapping definition (optimized via dict lookup)
        mapping = {
            inspect.Parameter.POSITIONAL_ONLY: cls.POSITIONAL_ONLY,
            inspect.Parameter.KEYWORD_ONLY: cls.KEYWORD_ONLY,
            inspect.Parameter.VAR_POSITIONAL: cls.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD: cls.VAR_KEYWORD,
            # POSITIONAL_OR_KEYWORD is the default fallback
        }
        return mapping.get(kind, cls.POSITIONAL_OR_KEYWORD)


class BuiltinFunctionArgumentSchema(BaseModel):
    name: str
    type_hint_name: str = Field(
        description="String representation of the type",
    )
    type_hint_namespace: str | None = Field(
        None,
        description="Namespace of the type hint. None if not applicable.",
    )
    kind: ArgKind
    default_value: str | None = Field(
        None,
        description="Reprr string of default value. None if required.",
    )
    is_optional: bool
    line_comment: str | None = Field(
        description="Optional line comment for the argument.",
    )

    @property
    def is_required(self) -> bool:
        return self.default_value is None and self.kind not in (
            ArgKind.VAR_POSITIONAL,
            ArgKind.VAR_KEYWORD,
        )

    def type_hint(self, namespace: str) -> str:
        """
        type representation in template.
        computed with respect to the given namespace.

        if is in the same we avoid adding the namespace prefix.
        """

        full_type = self.type_hint_name

        if self.type_hint_namespace:
            if self.type_hint_namespace != namespace:
                full_type = f"{self.type_hint_namespace}.{self.type_hint_name}"

        if self.is_optional and self.type_hint_name != "Any":
            return f"{full_type} | None"

        return full_type

    def as_str(self, namespace: str, force_no_default: bool = False) -> str:
        """
        Returns the formatted argument string.
        Args:
            force_no_default: If True, omits the '= value' part even if present.
                              Used to fix syntax errors when optional args precede required ones.
        """

        if self.name in ("self", "cls") and self.kind == ArgKind.POSITIONAL_OR_KEYWORD:
            return self.name

        prefix = {ArgKind.VAR_POSITIONAL: "*", ArgKind.VAR_KEYWORD: "**"}.get(self.kind, "")
        default = ""
        if (
            not force_no_default
            and self.default_value is not None
            and self.kind
            not in (
                ArgKind.VAR_POSITIONAL,
                ArgKind.VAR_KEYWORD,
            )
        ):
            default = f" = {self.default_value}"
        # elif self.default_value is None and self.is_optional:
        #     default = " = None"

        return f"{prefix}{self.name}: {self.type_hint(namespace)}{default}"


class BuiltinFunctionSchema(BaseSchema):
    name: str
    namespace: str
    is_async: bool
    is_method: bool
    is_classmethod: bool
    is_staticmethod: bool
    docstring: str | None
    return_hint_name: str
    return_hint_namespace: str | None
    return_is_optional: bool
    params: list[BuiltinFunctionArgumentSchema]

    def render(self) -> str:
        return TemplateManager.render_master("builtin_function.jinja", fun=self)

    def return_hint(self, namespace: str) -> str:
        """
        type representation in template.
        computed with respect to the given namespace.

        if is in the same we avoid adding the namespace prefix.
        """

        full_type = self.return_hint_name
        if self.return_hint_namespace:
            if self.return_hint_namespace != namespace:
                full_type = f"{self.return_hint_namespace}.{self.return_hint_name}"

        if self.return_is_optional and self.return_hint_name != "Any":
            return f"{full_type} | None"

        return full_type

    @property
    def decorators(self) -> list[str]:
        """
        Generate decorators for the function based on its properties.
        """
        decs = []
        # if self.is_deprecated:
        #     deprecation_msg = self.deprecation_warnings or "deprecated"
        #     decs.append(f'@deprecated("{deprecation_msg}")')

        if self.is_classmethod:
            decs.append("@classmethod")

        if not self.is_classmethod and not self.is_method:
            decs.append("@staticmethod")

        # if self.is_getter:
        #     decs.append("@property")

        # if self.is_overload:
        #     decs.append("@typing.overload")

        return decs

    def param_signature(self, namespace: str) -> list[str]:
        """Generates the full parameter string with '/' and '*' separators."""

        # 1. Analisi preliminare per SyntaxError (non-default follows default)
        # Prendiamo solo gli argomenti standard (POS_OR_KW)
        pos_kw_params = [p for p in self.params if p.kind == ArgKind.POSITIONAL_OR_KEYWORD]

        # Troviamo l'indice dell'ULTIMO parametro che è obbligatorio (default_value is None)
        last_required_idx = -1
        for i, p in enumerate(pos_kw_params):
            if p.default_value is None:
                last_required_idx = i

        # Logica: Qualsiasi parametro POS_OR_KW che si trova PRIMA di last_required_idx
        # DEVE essere stampato senza default, altrimenti Python darà SyntaxError.

        # 2. Group params by kind efficiently
        groups = {k: [] for k in ArgKind}

        # Contatore per sapere a che punto siamo nei POS_OR_KW
        current_pos_kw_idx = 0

        for p in self.params:
            force_no_default = False

            if p.kind == ArgKind.POSITIONAL_OR_KEYWORD:
                # Se siamo prima dell'ultimo obbligatorio, forziamo la rimozione del default
                if current_pos_kw_idx < last_required_idx:
                    force_no_default = True
                current_pos_kw_idx += 1

            # Chiamiamo as_str con il flag
            groups[p.kind].append(p.as_str(namespace, force_no_default=force_no_default))

        # 3. Build the parts list (Identico a prima)
        parts = []

        # A. Positional Only
        if groups[ArgKind.POSITIONAL_ONLY]:
            parts.extend(groups[ArgKind.POSITIONAL_ONLY])
            parts.append("/")

        # B. Standard Positional/Keyword
        parts.extend(groups[ArgKind.POSITIONAL_OR_KEYWORD])

        # C. Handle *args or bare '*' separator
        if groups[ArgKind.VAR_POSITIONAL]:
            parts.extend(groups[ArgKind.VAR_POSITIONAL])
        elif groups[ArgKind.KEYWORD_ONLY]:
            parts.append("*")

        # D. Keyword Only & **kwargs
        parts.extend(groups[ArgKind.KEYWORD_ONLY])
        parts.extend(groups[ArgKind.VAR_KEYWORD])

        # 4. Handle SELF / CLS (La logica che abbiamo fatto prima)
        first_param_name = self.params[0].name if self.params else None
        implicit_arg = None

        if self.is_classmethod:
            if first_param_name != "cls":
                implicit_arg = "cls"
        elif self.is_method and not self.is_staticmethod:  # assumendo tu abbia is_staticmethod disponibile
            if first_param_name != "self":
                implicit_arg = "self"

        if implicit_arg:
            parts.insert(0, implicit_arg)

        return parts
