from __future__ import annotations


import ast
import builtins
import logging

from typing import TYPE_CHECKING
from pydantic import Field
from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema, TypeVarSchema
from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.schema.function import FunctionSchema
from gi_stub_gen.schema.signals import SignalSchema
from gi_stub_gen.utils.utils import sanitize_gi_module_name

if TYPE_CHECKING:
    pass


# GObject.remove_emission_hook
logger = logging.getLogger(__name__)


def _qualify_builtin_annotations(text: str, member_names: set[str]) -> str:
    """Qualify hidden builtin types in annotations, preserving other stub text."""
    names = {name for name in member_names if isinstance(getattr(builtins, name, None), type)}
    if not names:
        return text
    positions: set[tuple[int, int]] = set()
    for node in ast.walk(ast.parse(text)):
        annotation = None
        if isinstance(node, (ast.arg, ast.AnnAssign)):
            annotation = node.annotation
        elif isinstance(node, ast.FunctionDef):
            annotation = node.returns
        elif isinstance(node, ast.TypeVar):
            annotation = node.bound
        if annotation is not None:
            for part in ast.walk(annotation):
                if isinstance(part, ast.Name) and part.id in names:
                    positions.add((part.lineno - 1, part.col_offset))
    # AST columns count UTF-8 bytes; insert from right to left without reformatting.
    lines = text.encode("utf-8").splitlines(keepends=True)
    for line, column in sorted(positions, reverse=True):
        lines[line] = lines[line][:column] + b"builtins." + lines[line][column:]
    return b"".join(lines).decode("utf-8")


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
    construct_only: bool = False
    """Allow assignment only during construction, even if the native WRITABLE flag is set."""
    write_type_hint_name: str | None = None
    """Setter type without its namespace; None reuses the complete getter annotation."""
    write_type_hint_namespace: str | None = None
    """Namespace of the setter type, or None for a builtin or unqualified type."""
    write_may_be_null: bool | None = None
    """Whether the setter accepts None; unset when no separate write annotation is supplied."""
    type_imports: set[str] = Field(default_factory=set)
    """Imports needed by accessor annotations, including types nested inside containers."""

    docstring: str | None

    line_comment: str | None
    """line comment for the property. 
    Can be used to add annotations like # type: ignore
    or to explain if the name was sanitized."""

    declaration_comment: str | None = None
    """Explicit override comment on the attribute/getter declaration, separate from name sanitization."""

    # type_hint_full: str
    # """type hint in template (with namespace if different from parent)"""

    type_hint_namespace: str | None
    """type hint namespace, if any"""

    type_hint_name: str
    """type hint name (without namespace)"""

    may_be_null: bool
    """True if the property may be None, False otherwise."""

    def render_type_annotation(self, namespace: str) -> str:
        """
        Get the full type hint for the field,
        adding the namespace if different from the given one.
        """
        if self.type_hint_namespace and sanitize_gi_module_name(self.type_hint_namespace) != sanitize_gi_module_name(
            namespace
        ):
            hint = f"{self.type_hint_namespace}.{self.type_hint_name}"
        else:
            hint = self.type_hint_name

        if self.may_be_null:
            hint = f"{hint} | None"

        return hint

    def render_write_annotation(self, namespace: str) -> str:
        """Return the setter annotation, falling back to the property type."""
        if self.write_type_hint_name is None:
            return self.render_type_annotation(namespace)
        return self.model_copy(update={
            "type_hint_name": self.write_type_hint_name,
            "type_hint_namespace": self.write_type_hint_namespace,
            "may_be_null": self.write_may_be_null,
        }).render_type_annotation(namespace)

    @property
    def can_write(self) -> bool:
        return self.writable and not self.construct_only

    def uses_attribute_annotation(self, namespace: str) -> bool:
        return (
            self.readable and self.can_write
            and self.render_type_annotation(namespace) == self.render_write_annotation(namespace)
        )


class ClassFieldSchema(BaseSchema):
    """
    Represents a field of a GI class.
    These are present in boxed structs
    """

    name: str
    type_hint_name: str
    """type hint in template"""

    type_hint_namespace: str | None
    """type hint in template (namespace part, if any)"""

    is_deprecated: bool
    deprecation_warnings: str | None
    """Deprecation warning message, if any captured from PyGIDeprecationWarning"""

    docstring: str | None

    line_comment: str | None
    """line comment for the field."""

    may_be_null: bool
    """True if the field may be None, False otherwise."""

    is_readable: bool
    """Whether the field is readable"""

    is_writable: bool
    """Whether the field is writable"""

    def render_type_annotation(self, namespace: str) -> str:
        """
        Get the full type hint for the field,
        adding the namespace if different from the given one.
        """
        if self.type_hint_namespace and sanitize_gi_module_name(self.type_hint_namespace) != sanitize_gi_module_name(
            namespace
        ):
            hint = f"{self.type_hint_namespace}.{self.type_hint_name}"
        else:
            hint = self.type_hint_name
        if self.may_be_null:
            hint = f"{hint} | None"

        return hint

    @property
    def is_property(self) -> bool:
        """
        if read only we set it as a property so it fixes
        overrides errors in pylance (i.e see object in Gst.BufferPool)
        """
        return self.is_readable and not self.is_writable


class ClassSchema(BaseSchema):
    super: list[str]
    namespace: str
    name: str
    type_vars: list[TypeVarSchema] = Field(default_factory=list)
    props_ignored_super_classes: set[str] = Field(default_factory=set)
    allow_synthetic_props: bool = True
    additional_required_imports: set[str] = Field(default_factory=set)
    shadowed_builtin_types: set[str] = Field(default_factory=set)
    """Builtin type names hidden by runtime members, including inherited members."""
    docstring: str | None
    props: list[ClassPropSchema]

    fields: list[ClassFieldSchema]
    """Fields of the class, if readonly we consider them @property"""

    methods: list[FunctionSchema]
    """Methods of the class parsed from GI."""

    python_methods: list[BuiltinFunctionSchema]
    """Python methods for the class. Probably from overrides?"""

    signals: list[SignalSchema]
    """Signals of the class."""

    extra: list[str]
    """Extra debug info lines to add in the class docstring."""

    is_deprecated: bool
    """Whether the class is deprecated."""

    line_comment: str | None = None
    """Optional comment rendered immediately before the class declaration."""

    required_gi_import: str | None
    """required gi.repository<NAME> import for the property type, if any"""

    @property
    def debug(self) -> str:
        super_debug = super().debug
        if self.extra:
            super_debug = f"{super_debug}\n[EXTRA]\n" + "\n".join(self.extra)
        return super_debug

    @property
    def required_imports(self) -> set[str]:
        """
        Required gi.repository<NAME> import for the class, if any.
        Gather from properties and attributes.
        """
        gi_imports: set[str] = set()
        gi_imports.update(self.additional_required_imports)
        if self.required_gi_import:
            gi_imports.add(self.required_gi_import)
        if self.allow_synthetic_props or self.props:
            gi_imports.add("typing")
        for prop in self.props:
            gi_imports.update(prop.type_imports)
            if prop.write_type_hint_namespace:
                gi_imports.add(prop.write_type_hint_namespace)
            if prop.type_hint_namespace:
                gi_imports.add(prop.type_hint_namespace)
        for attr in self.fields:
            if attr.type_hint_namespace:
                gi_imports.add(attr.type_hint_namespace)
        for method in self.methods:
            gi_imports.update(method.required_imports)
        for method in self.python_methods:
            gi_imports.update(method.required_imports)
        for type_var in self.type_vars:
            if type_var.bound_hint_namespace:
                gi_imports.add(type_var.bound_hint_namespace)
        for signal in self.signals:
            gi_imports.update(signal.required_gi_imports)
        return gi_imports

    def render_type_parameters(self) -> str | None:
        """Return stub text, or None when absent."""
        if not self.type_vars:
            return None
        return ", ".join(type_var.render_type_parameter(self.namespace) for type_var in self.type_vars)

    def render_bases(self) -> str | None:
        """
        Get the super class name, if any.
        """
        super_classes = self.super
        if self.type_vars:
            super_classes = [
                super_cls
                for super_cls in super_classes
                if not super_cls.startswith("typing.Generic") and super_cls != "builtins.object"
            ]
        return ", ".join(super_classes) or None

    def render_props_base(self) -> str | None:
        """Return stub text, or None when absent."""
        for super_cls in self.super:
            if super_cls.startswith(("metaclass=", "typing.Generic")):
                continue
            if super_cls in self.props_ignored_super_classes:
                continue
            if super_cls == "builtins.object":
                return None
            return f"{super_cls}.Props"
        return None

    def render_stub(self) -> str:
        """Return stub text as a string."""
        member_names = self.shadowed_builtin_types | {
            member.name for member in (*self.fields, *self.props, *self.methods, *self.python_methods)
        }
        return _qualify_builtin_annotations(
            TemplateManager.render_master("class.jinja", cls_=self), member_names
        )

    def render_signals(self) -> str:
        """Return stub text as a string."""
        return TemplateManager.render_master(
            "class_signals.jinja",
            signals=self.signals,
        )

    def render_fields(self) -> str:
        """Return stub text as a string."""
        return TemplateManager.render_master(
            "class_fields.jinja",
            fields=self.fields,
        )

    def render_props(self) -> str:
        """Return stub text as a string."""
        return TemplateManager.render_master(
            "class_props.jinja",
            props=[prop for prop in self.props if prop.readable or prop.can_write],
            props_super_class=self.render_props_base(),
            allow_synthetic_props=self.allow_synthetic_props,
        )

    @property
    def has_any_data(self):
        """
        used in template check if class has any data to render
        """
        return bool(self.props or self.fields or self.methods or self.python_methods or self.signals)
