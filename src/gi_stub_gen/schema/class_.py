from __future__ import annotations


import logging

from typing import Any
from gi_stub_gen.gir_manager import GIRDocs
from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema
from gi_stub_gen.template_manager import TemplateManager
from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.schema.function import (
    FunctionArgumentSchema,
    FunctionSchema,
)
from gi_stub_gen.schema.signals import SignalSchema
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


class ClassSchema(BaseSchema):
    bases: list[str]
    namespace: str
    name: str
    docstring: str | None
    props: list[ClassPropSchema]
    getters: list[ClassFieldSchema]
    """Getters as fields for the class. type of getset_descriptors"""

    fields: list[ClassFieldSchema]
    methods: list[FunctionSchema]
    python_methods: list[BuiltinFunctionSchema]
    """Python methods for the class. Probably from overrides?"""

    signals: list[SignalSchema]
    extra: list[str]
    is_deprecated: bool

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
        for signal in self.signals:
            gi_imports.update(signal.required_gi_imports)
        return gi_imports

    def add_init_method(self):
        """
        In parsed classes, add an __init__ method if not present.

        In GI classes, the __init__ method is present but its the same as the new() method if existing
        So we make a copy of the new() method and rename it to __init__

        if there is no new() method, we should pick the next new_<something>() method
        but we skip this for now.
        """
        is_init_present_in_methods = any(method.name == "__init__" for method in self.methods)
        is_init_present_in_python_methods = any(method.name == "__init__" for method in self.python_methods)
        if is_init_present_in_methods or is_init_present_in_python_methods:
            logger.debug(f"Class {self.namespace}.{self.name} already has __init__ method, skipping adding it.")
            return

        args: list[FunctionArgumentSchema] = []
        for prop in self.props:
            if prop.writable:
                args.append(
                    FunctionArgumentSchema(
                        direction="IN",
                        name=prop.name,
                        namespace=self.namespace,
                        may_be_null=prop.may_be_null,
                        is_optional=prop.may_be_null,
                        is_callback=False,
                        get_array_length=-1,
                        is_deprecated=False,
                        is_caller_allocates=False,
                        tag_as_string="??",
                        line_comment=None,
                        py_type_name=prop.type_hint_name,
                        py_type_namespace=prop.type_hint_namespace,
                        default_value="...",
                    )
                )
        class_init = FunctionSchema(
            name="__init__",
            namespace=self.namespace,
            is_method=True,
            is_deprecated=False,
            deprecation_warnings=None,
            docstring="Generated __init__ stub method. order not guaranteed. ",
            args=args,
            is_callback=False,
            can_throw_gerror=False,
            is_async=False,
            is_constructor=False,
            is_getter=False,
            is_setter=False,
            may_return_null=False,
            return_hint="None",
            return_hint_namespace=None,
            skip_return=False,
            wrap_vfunc=False,
            line_comment=None,
            function_type="FunctionInfo",
            is_overload=False,
        )
        self.methods.insert(0, class_init)

    @classmethod
    def from_gi_object(
        cls,
        namespace: str,
        obj: Any,
        props: list[ClassPropSchema],
        fields: list[ClassFieldSchema],
        getters: list[ClassFieldSchema],
        methods: list[FunctionSchema],
        signals: list[SignalSchema],
        builtin_methods: list[BuiltinFunctionSchema],
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
        except Exception:
            breakpoint()
        ## END WIP DEBUGGING PURPOSES

        class_docstring = GIRDocs().get_class_docstring(obj.__name__)
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
                base_class_name = "object"

            # elif base_class_name == "PyGIDeprecationWarning":
            #     # this is actually importable from gi so we can keep it
            #     # keep it as is
            #     pass
            # else:
            #     # other classes in gi are actually in gi._gi
            #     # so this should only happen for gi._gi itself
            #     sane_super_namespace = None

        # build the super class name in the template
        # TODO: move to runtime function
        required_gi_import = None
        base_class = base_class_name
        if sane_namespace != sane_super_namespace and sane_super_namespace is not None:
            # they are in different namespaces
            # so we add it to the repr
            base_class = f"{sane_super_namespace}.{base_class_name}"
            if sane_super_namespace != "GI":
                # we exclude GI which is from "import gi._gi as GI" which is always imported
                required_gi_import = sane_super_namespace

        instance = cls(
            namespace=namespace,
            name=obj.__name__,
            bases=[base_class],
            docstring=class_docstring,
            props=props,
            fields=fields,
            methods=methods,
            signals=signals,
            getters=getters,
            is_deprecated=is_deprecated,
            extra=extra,
            required_gi_import=required_gi_import,
            python_methods=builtin_methods,
        )
        instance.add_init_method()
        return instance

    @property
    def super_class(self) -> str | None:
        """
        Get the super class name, if any.
        """
        return ", ".join(self.bases)

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
