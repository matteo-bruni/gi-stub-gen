from __future__ import annotations


import logging

from typing import Any, TYPE_CHECKING
from pydantic import Field
from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema, TypeVarSchema
from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.schema.function import FunctionArgumentSchema, FunctionSchema
from gi_stub_gen.schema.signals import SignalSchema
from gi_stub_gen.utils.gi_utils import do_class_need_gtype_metaclass
from gi_stub_gen.utils.utils import get_super_class_name, sanitize_gi_module_name

if TYPE_CHECKING:
    pass


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

    # type_hint_full: str
    # """type hint in template (with namespace if different from parent)"""

    type_hint_namespace: str | None
    """type hint namespace, if any"""

    type_hint_name: str
    """type hint name (without namespace)"""

    may_be_null: bool
    """True if the property may be None, False otherwise."""

    def type_hint(self, namespace: str) -> str:
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

    def type_hint(self, namespace: str) -> str:
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


def _normalize_type_namespace(namespace: str | None) -> str | None:
    if namespace is None:
        return None
    return sanitize_gi_module_name(namespace)


def _hint_matches_class(
    hint_name: str | None,
    hint_namespace: str | None,
    class_name: str,
    class_namespace: str,
) -> bool:
    if hint_name != class_name:
        return False

    normalized_hint_namespace = _normalize_type_namespace(hint_namespace)
    normalized_class_namespace = _normalize_type_namespace(class_namespace)
    return normalized_hint_namespace in {None, normalized_class_namespace}


def _collect_class_type_vars(
    builtin_methods: list[BuiltinFunctionSchema],
) -> tuple[list[TypeVarSchema], dict[str, set[str]]]:
    type_vars_by_name: dict[str, TypeVarSchema] = {}
    param_names_by_type_var: dict[str, set[str]] = {}

    for method in builtin_methods:
        for type_var in method.type_vars:
            existing = type_vars_by_name.get(type_var.name)
            if existing is None or (existing.bound_hint_name is None and type_var.bound_hint_name is not None):
                type_vars_by_name[type_var.name] = type_var

        for param in method.params:
            for type_var_name in param.type_var_names:
                param_names_by_type_var.setdefault(type_var_name, set()).add(param.name)

    return list(type_vars_by_name.values()), param_names_by_type_var


def _arg_matches_type_var_bound(arg: FunctionArgumentSchema, type_var: TypeVarSchema) -> bool:
    if type_var.bound_hint_name is None:
        return False

    return arg.py_type_name == type_var.bound_hint_name and _normalize_type_namespace(
        arg.py_type_namespace
    ) == _normalize_type_namespace(type_var.bound_hint_namespace)


def _apply_class_type_vars(
    namespace: str,
    class_name: str,
    methods: list[FunctionSchema],
    builtin_methods: list[BuiltinFunctionSchema],
    initial_type_vars: list[TypeVarSchema] | None = None,
) -> list[TypeVarSchema]:
    method_type_vars, param_names_by_type_var = _collect_class_type_vars(builtin_methods)
    type_vars_by_name = {type_var.name: type_var for type_var in initial_type_vars or []}
    for type_var in method_type_vars:
        existing = type_vars_by_name.get(type_var.name)
        if existing is None or (existing.bound_hint_name is None and type_var.bound_hint_name is not None):
            type_vars_by_name[type_var.name] = type_var
    type_vars = list(type_vars_by_name.values())
    if not type_vars and _normalize_type_namespace(namespace) == "Gio" and class_name == "ListModel":
        type_vars = [
            TypeVarSchema(
                name="ObjectItemType",
                bound_hint_name="Object",
                bound_hint_namespace="GObject",
            )
        ]
    if not type_vars:
        return []

    generic_class_name = f"{class_name}[{', '.join(type_var.name for type_var in type_vars)}]"
    sane_namespace = _normalize_type_namespace(namespace)
    iterator_item_type_vars = {
        method.return_type_var_names[0]
        for method in builtin_methods
        if method.name == "__iter__" and len(method.return_type_var_names) == 1
    }
    iterator_item_type_var = next(iter(iterator_item_type_vars)) if len(iterator_item_type_vars) == 1 else None

    for method in methods:
        if _hint_matches_class(method.return_hint, method.return_hint_namespace, class_name, namespace):
            method.return_hint = generic_class_name
            method.return_hint_namespace = sane_namespace

        if (
            _normalize_type_namespace(namespace) == "Gio"
            and class_name == "ListModel"
            and method.name == "get_item"
            and _hint_matches_class(method.return_hint, method.return_hint_namespace, "Object", "GObject")
        ):
            method.return_hint = "ObjectItemType"
            method.return_hint_namespace = None

        for arg in method.args:
            if arg.direction == "OUT" and arg.is_marshaled_gvalue_payload and iterator_item_type_var is not None:
                arg.type_var_name = iterator_item_type_var
                continue

            if arg.direction == "OUT":
                continue

            for type_var in type_vars:
                if arg.name not in param_names_by_type_var.get(type_var.name, set()):
                    continue
                if _arg_matches_type_var_bound(arg, type_var):
                    arg.type_var_name = type_var.name
                    break

    for method in builtin_methods:
        if _hint_matches_class(method.return_hint_name, method.return_hint_namespace, class_name, namespace):
            method.return_hint_name = generic_class_name
            method.return_hint_namespace = sane_namespace

    return type_vars


class ClassSchema(BaseSchema):
    super: list[str]
    namespace: str
    name: str
    type_vars: list[TypeVarSchema] = Field(default_factory=list)
    props_ignored_super_classes: set[str] = Field(default_factory=set)
    allow_synthetic_props: bool = True
    additional_required_imports: set[str] = Field(default_factory=set)
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
        for prop in self.props:
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

    @classmethod
    def from_gi_object(
        cls,
        namespace: str,
        obj: Any,
        props: list[ClassPropSchema],
        fields: list[ClassFieldSchema],
        methods: list[FunctionSchema],
        signals: list[SignalSchema],
        builtin_methods: list[BuiltinFunctionSchema],
        override_mixins: list[str],
        extra: list[str],
        inferred_type_vars: list[TypeVarSchema] | None = None,
        allow_synthetic_props: bool = True,
        additional_required_imports: set[str] | None = None,
    ):
        """
        Create a ClassSchema from a GI object.

        This method also applies all class overrides (methods, fields, super class)
        defined in gi_stub_gen.overrides.
        """
        # Import here to avoid circular import
        from gi_stub_gen.overrides import (
            get_super_override,
            apply_method_overrides,
            apply_field_overrides,
        )

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
        except Exception:
            breakpoint()
        ## END WIP DEBUGGING PURPOSES

        class_docstring = GIRDocs().get_class_docstring(obj.__name__)

        # ================================================================
        # Apply all overrides (methods, fields, super)
        # ================================================================
        methods = apply_method_overrides(methods, namespace, obj.__name__)
        fields = apply_field_overrides(fields, namespace, obj.__name__)

        # Sort after overrides are applied
        fields.sort(key=lambda x: x.name)
        methods.sort(key=lambda x: x.name)
        props.sort(key=lambda x: x.name)

        # ================================================================
        # Compute super class
        # ================================================================
        base_class_namespace, base_class_name = get_super_class_name(
            obj,
            current_namespace=namespace,
        )

        sane_namespace = sanitize_gi_module_name(namespace)
        sane_super_namespace = sanitize_gi_module_name(base_class_namespace) if base_class_namespace else None
        # some super classes are in "gi" namespace
        # which is actually gi._gi hidden in the C modules
        # to use it in python we import it as: import gi._gi as GI
        # for example the actual base classed of
        # gi.Struct is actually in gi._gi.Struct
        # gi.Boxed is actually in gi._gi.Boxed
        # we map them to the closes objects in GObject
        if sane_super_namespace == "gi":
            if base_class_name == "Boxed":
                sane_super_namespace = "GObject"
                base_class_name = "GBoxed"

            elif base_class_name == "Struct":
                sane_super_namespace = "GObject"
                base_class_name = "GPointer"

            elif base_class_name == "Fundamental":
                sane_super_namespace = None
                base_class_name = "builtins.object"

        # build the super class name in the template
        # TODO: move to runtime function
        required_gi_import = None
        base_class = base_class_name
        if sane_namespace != sane_super_namespace and sane_super_namespace is not None:
            # they are in different namespaces
            # so we add it to the repr
            base_class = f"{sane_super_namespace}.{base_class_name}"
            if sane_super_namespace != sanitize_gi_module_name(namespace):
                required_gi_import = sane_super_namespace

        # check if we need to add GType as metaclass
        is_gtype = do_class_need_gtype_metaclass(obj)

        super_list = [base_class]
        if is_gtype:
            if sane_namespace == "GObject":
                super_list.append("metaclass=GType")
            else:
                super_list.append("metaclass=GObject.GType")

        # Check for super class override
        super_override = get_super_override(namespace, obj.__name__)
        if super_override is not None:
            super_list = super_override
            # Extract required imports from overridden super classes
            for super_cls in super_override:
                if "." in super_cls and not super_cls.startswith("builtins."):
                    # e.g. "GObject.SomeClass" -> need to import GObject
                    override_namespace = super_cls.split(".")[0]
                    if override_namespace != sane_namespace:
                        required_gi_import = override_namespace

        super_list = [
            *override_mixins,
            *(super_cls for super_cls in super_list if super_cls not in override_mixins),
        ]

        type_vars = _apply_class_type_vars(
            namespace=namespace,
            class_name=obj.__name__,
            methods=methods,
            builtin_methods=builtin_methods,
            initial_type_vars=inferred_type_vars,
        )

        instance = cls(
            namespace=namespace,
            name=obj.__name__,
            super=super_list,
            type_vars=type_vars,
            props_ignored_super_classes=set(override_mixins),
            allow_synthetic_props=allow_synthetic_props,
            additional_required_imports=additional_required_imports or set(),
            docstring=class_docstring,
            props=props,
            fields=fields,
            methods=methods,
            signals=signals,
            is_deprecated=is_deprecated,
            extra=extra,
            required_gi_import=required_gi_import,
            python_methods=builtin_methods,
        )
        # instance.add_init_method()
        return instance

    @property
    def type_parameters(self) -> str | None:
        if not self.type_vars:
            return None
        return ", ".join(type_var.type_parameter(self.namespace) for type_var in self.type_vars)

    @property
    def super_class(self) -> str | None:
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

    @property
    def props_super_class(self) -> str | None:
        for super_cls in self.super:
            if super_cls.startswith(("metaclass=", "typing.Generic")):
                continue
            if super_cls in self.props_ignored_super_classes:
                continue
            if super_cls == "builtins.object":
                return None
            return f"{super_cls}.Props"
        return None

    def render(self) -> str:
        return TemplateManager.render_master("class.jinja", cls_=self)

    def render_signals(self) -> str:
        return TemplateManager.render_master(
            "class_signals.jinja",
            signals=self.signals,
        )

    def render_fields(self) -> str:
        return TemplateManager.render_master(
            "class_fields.jinja",
            fields=self.fields,
        )

    def render_props(self) -> str:
        return TemplateManager.render_master(
            "class_props.jinja",
            props=self.props,
            props_super_class=self.props_super_class,
            allow_synthetic_props=self.allow_synthetic_props,
        )

    @property
    def has_any_data(self):
        """
        used in template check if class has any data to render
        """
        return bool(self.props or self.fields or self.methods or self.python_methods or self.signals)
