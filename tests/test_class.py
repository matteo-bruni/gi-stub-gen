import sys
import typing
from types import ModuleType

import gi
from gi.repository import GObject
from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.overrides.class_.GObject.Property import CLASS_PROPERTY
import gi_stub_gen.parser.class_ as class_parser
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.schema.class_ import ClassFieldSchema
from gi_stub_gen.utils.utils import get_super_class_name


class _ForwardPropertyType:
    pass


class _PythonPropertyCases:
    @property
    def read_only(self) -> int:
        raise NotImplementedError

    def _set_write_only(self, value: str) -> None:
        raise NotImplementedError

    write_only = property(fset=_set_write_only)

    @property
    def read_write(self) -> _ForwardPropertyType:
        raise NotImplementedError

    @read_write.setter
    def read_write(self, value: _ForwardPropertyType) -> None:
        raise NotImplementedError

    @property
    def disagreeing(self) -> int:
        raise NotImplementedError

    @disagreeing.setter
    def disagreeing(self, value: str) -> None:
        raise NotImplementedError

    @property
    def unannotated(self):
        raise NotImplementedError


class _PythonAnnotatedFieldsBase:
    inherited: int


class _PythonAnnotatedFieldCases(_PythonAnnotatedFieldsBase):
    python_only: int
    forward: "_ForwardPropertyType"
    optional: "typing.Optional[_ForwardPropertyType]"
    _private: str
    constant: int = 1

    @property
    def accessor_wins(self) -> int:
        raise NotImplementedError

    def method(self) -> None:
        raise NotImplementedError


_PythonAnnotatedFieldCases.__annotations__.update(
    unresolved="MissingAnnotation",
    accessor_wins=str,
    method=int,
)


def test_gobject_property_override_renders_generic_descriptor():
    TemplateManager.set_module_name("GObject")

    rendered = CLASS_PROPERTY.render()

    assert "class Property[ValueT](builtins.property):" in rendered
    assert "getter: typing.Callable[[typing.Any], ValueT] | None = None" in rendered
    assert "setter: typing.Callable[[typing.Any, ValueT], None] | None = None" in rendered
    assert "type: type[ValueT] | GType | None = None" in rendered
    assert "nick: str = ''" in rendered
    assert "blurb: str = ''" in rendered
    assert "flags: ParamFlags = ParamFlags.READABLE | ParamFlags.WRITABLE" in rendered
    assert "minimum: typing.Any = None" in rendered
    assert "maximum: typing.Any = None" in rendered
    assert "def __call__[GetterT](" in rendered
    assert "def getter[GetterT](" in rendered
    assert "def setter(" in rendered
    assert ") -> Property[GetterT]:" in rendered
    assert ") -> Property[ValueT]:" in rendered
    assert rendered.count("@typing.overload") == 2
    assert "instance: None" in rendered
    assert ") -> ValueT:" in rendered
    assert "def __set__(" in rendered
    assert "value: ValueT" in rendered


def test_parse_class_gobject_object():
    """Test parsing of GObject.Object."""
    class_schema, callbacks = parse_class("gi.repository.GObject", GObject.Object)

    assert class_schema is not None
    assert class_schema.name == "Object"
    assert class_schema.namespace == "gi.repository.GObject"

    # Check for some known methods
    method_names = [m.name for m in class_schema.methods]
    assert "bind_property" in method_names
    assert "emit" in method_names, (
        f"Expected 'emit' method to be present in GObject.Object \n Methods found: {method_names}"
    )

    # Check for properties (GObject.Object doesn't have many props, but let's check attributes/props lists exist)
    # assert isinstance(class_schema.props, list)
    # assert isinstance(class_schema.attributes, list)


def test_public_override_mixins_are_rendered_as_bases(monkeypatch):
    override_module_name = "gi.overrides.SyntheticTest"
    override_module = ModuleType(override_module_name)
    setattr(override_module, "__all__", ["PublicMixin"])
    monkeypatch.setitem(sys.modules, override_module_name, override_module)

    repository_class = type(
        "Example",
        (object,),
        {"__module__": "gi.repository.SyntheticTest"},
    )
    public_mixin = type(
        "PublicMixin",
        (object,),
        {"__module__": override_module_name, "public_method": lambda self: None},
    )
    internal_mixin = type(
        "InternalMixin",
        (object,),
        {"__module__": override_module_name, "internal_method": lambda self: None},
    )
    override_class = type(
        "Example",
        (public_mixin, internal_mixin, repository_class),
        {"__module__": override_module_name},
    )

    parsed_class, _ = parse_class("gi.repository.SyntheticTest", override_class)

    assert parsed_class is not None
    assert parsed_class.super == ["PublicMixin", "builtins.object"]
    parsed_methods = {method.name for method in parsed_class.python_methods}
    assert "public_method" not in parsed_methods
    assert "internal_method" not in parsed_methods


def test_public_override_mixin_specializes_writable_property_and_omits_props(monkeypatch):
    class ValueBase:
        pass

    class DefaultValue(ValueBase):
        pass

    class SpecializedValue(ValueBase):
        pass

    class DefaultUnbound:
        pass

    class SpecializedUnbound:
        pass

    for value_type in (ValueBase, DefaultValue, SpecializedValue, DefaultUnbound, SpecializedUnbound):
        value_type.__module__ = "gi.repository.SyntheticGenericMixin"

    def get_default(self) -> DefaultValue:
        raise NotImplementedError

    def set_default(self, value: DefaultValue) -> None:
        raise NotImplementedError

    def get_specialized(self) -> SpecializedValue:
        raise NotImplementedError

    def set_specialized(self, value: SpecializedValue) -> None:
        raise NotImplementedError

    def get_default_unbound(self) -> DefaultUnbound:
        raise NotImplementedError

    def set_default_unbound(self, value: DefaultUnbound) -> None:
        raise NotImplementedError

    def get_specialized_unbound(self) -> SpecializedUnbound:
        raise NotImplementedError

    def set_specialized_unbound(self, value: SpecializedUnbound) -> None:
        raise NotImplementedError

    override_module_name = "gi.overrides.SyntheticGenericMixin"
    override_module = ModuleType(override_module_name)
    monkeypatch.setitem(sys.modules, override_module_name, override_module)

    public_mixin = type(
        "PublicMixin",
        (object,),
        {
            "__module__": override_module_name,
            "value": property(get_default, set_default),
            "unbound": property(get_default_unbound, set_default_unbound),
        },
    )
    repository_specialized = type(
        "Specialized",
        (object,),
        {"__module__": "gi.repository.SyntheticGenericMixin"},
    )
    specialized = type(
        "Specialized",
        (public_mixin, repository_specialized),
        {
            "__module__": override_module_name,
            "value": property(get_specialized, set_specialized),
            "unbound": property(get_specialized_unbound, set_specialized_unbound),
        },
    )
    repository_default = type(
        "Default",
        (object,),
        {"__module__": "gi.repository.SyntheticGenericMixin"},
    )
    default = type(
        "Default",
        (public_mixin, repository_default),
        {"__module__": override_module_name},
    )
    internal_mixin = type(
        "InternalMixin",
        (object,),
        {"__module__": override_module_name},
    )

    setattr(override_module, "__all__", ["PublicMixin", "Specialized", "Default"])
    setattr(override_module, "PublicMixin", public_mixin)
    setattr(override_module, "Specialized", specialized)
    setattr(override_module, "Default", default)
    setattr(override_module, "InternalMixin", internal_mixin)

    parsed_mixin, _ = parse_class("gi.repository.SyntheticGenericMixin", public_mixin)
    parsed_specialized, _ = parse_class("gi.repository.SyntheticGenericMixin", specialized)
    parsed_default, _ = parse_class("gi.repository.SyntheticGenericMixin", default)
    parsed_internal, _ = parse_class("gi.repository.SyntheticGenericMixin", internal_mixin)

    assert parsed_mixin is not None
    assert parsed_specialized is not None
    assert parsed_default is not None
    assert parsed_internal is not None
    assert parsed_mixin.type_parameters == "ValueType: ValueBase, UnboundType"
    assert next(field for field in parsed_mixin.fields if field.name == "value").type_hint_name == "ValueType"
    assert next(field for field in parsed_mixin.fields if field.name == "unbound").type_hint_name == "UnboundType"
    assert parsed_specialized.super[0] == "PublicMixin[SpecializedValue, SpecializedUnbound]"
    assert parsed_default.super[0] == "PublicMixin[DefaultValue, DefaultUnbound]"

    TemplateManager.set_module_name("SyntheticGenericMixin")
    assert "class Props" not in parsed_mixin.render()
    assert "class Props" in parsed_internal.render()


def test_python_only_property_access_and_annotations():
    parsed_class, _ = parse_class(__name__, _PythonPropertyCases)

    assert parsed_class is not None
    fields = {field.name: field for field in parsed_class.fields}

    assert fields["read_only"].type_hint_name == "int"
    assert fields["read_only"].is_readable is True
    assert fields["read_only"].is_writable is False

    assert fields["write_only"].type_hint_name == "str"
    assert fields["write_only"].is_readable is False
    assert fields["write_only"].is_writable is True

    assert fields["read_write"].type_hint_name == "_ForwardPropertyType"
    assert fields["read_write"].is_readable is True
    assert fields["read_write"].is_writable is True

    assert fields["disagreeing"].type_hint_name == "Any"
    assert fields["disagreeing"].type_hint_namespace == "typing"
    assert fields["unannotated"].type_hint_name == "Any"
    assert fields["unannotated"].type_hint_namespace == "typing"


def test_python_class_annotations_add_only_public_instance_fields():
    parsed_class, _ = parse_class(__name__, _PythonAnnotatedFieldCases)

    assert parsed_class is not None
    fields = {field.name: field for field in parsed_class.fields}

    assert fields["python_only"].type_hint("tests.test_class") == "int"
    assert fields["forward"].type_hint("tests.test_class") == "_ForwardPropertyType"
    assert fields["optional"].type_hint("tests.test_class") == "_ForwardPropertyType | None"
    assert fields["unresolved"].type_hint("tests.test_class") == "typing.Any"
    assert fields["accessor_wins"].type_hint("tests.test_class") == "int"
    assert fields["python_only"].is_readable is True
    assert fields["python_only"].is_writable is True
    assert not {"_private", "inherited", "constant", "method"} & fields.keys()
    assert len(parsed_class.fields) == len(fields)


def test_python_class_annotations_refine_gir_fields_without_losing_metadata(monkeypatch):
    class FakeField:
        def __init__(self, name: str):
            self.name = name

        def get_name(self) -> str:
            return self.name

    class FakeInfo:
        fields = [FakeField("corrected"), FakeField("unresolved_existing")]

        def get_fields(self):
            return self.fields

        def get_properties(self):
            return []

        def get_methods(self):
            return []

        def is_deprecated(self) -> bool:
            return False

    class SyntheticAnnotatedFields:
        __info__ = FakeInfo()
        __gtype__ = GObject.TYPE_INT
        corrected: "typing.Optional[_ForwardPropertyType]"
        python_only: int

        def __init__(self):
            pass

    SyntheticAnnotatedFields.__annotations__["unresolved_existing"] = "MissingAnnotation"

    gir_fields = {
        "corrected": ClassFieldSchema(
            name="corrected",
            type_hint_name="bytes",
            type_hint_namespace=None,
            is_deprecated=True,
            deprecation_warnings="deprecated",
            docstring="GIR documentation",
            line_comment="GIR comment",
            may_be_null=False,
            is_readable=True,
            is_writable=False,
        ),
        "unresolved_existing": ClassFieldSchema(
            name="unresolved_existing",
            type_hint_name="str",
            type_hint_namespace=None,
            is_deprecated=False,
            deprecation_warnings=None,
            docstring=None,
            line_comment=None,
            may_be_null=False,
            is_readable=True,
            is_writable=True,
        ),
    }

    monkeypatch.setattr(class_parser, "should_expose_class_field", lambda field: True)
    original_is_local = class_parser.is_local
    monkeypatch.setattr(
        class_parser,
        "is_local",
        lambda cls, name: cls is SyntheticAnnotatedFields and name in gir_fields or original_is_local(cls, name),
    )
    monkeypatch.setattr(
        class_parser,
        "gi_parse_field",
        lambda field, module_name, class_name: (gir_fields[field.get_name()].model_copy(), None),
    )
    monkeypatch.setattr(class_parser.GIRepo, "find_by_name", lambda self, *args, **kwargs: None)

    parsed_class, _ = parse_class(__name__, SyntheticAnnotatedFields)

    assert parsed_class is not None
    fields = {field.name: field for field in parsed_class.fields}
    corrected = fields["corrected"]
    assert corrected.type_hint(__name__) == "_ForwardPropertyType | None"
    assert corrected.docstring == "GIR documentation"
    assert corrected.is_deprecated is True
    assert corrected.deprecation_warnings == "deprecated"
    assert corrected.line_comment == "GIR comment"
    assert corrected.is_readable is True
    assert corrected.is_writable is False
    assert fields["unresolved_existing"].type_hint(__name__) == "str"
    assert fields["python_only"].type_hint(__name__) == "int"


def test_parse_class_gobject_initially_unowned():
    """Test parsing of GObject.InitiallyUnowned."""
    class_schema, callbacks = parse_class("gi.repository.GObject", GObject.InitiallyUnowned)

    assert class_schema is not None
    assert class_schema.name == "InitiallyUnowned"
    assert "Object" == class_schema.super_class


def test_runtime_fields():
    """
    In some cases, certain fields are only discoverable at runtime.
    eg: GLib.Error.message, GLib.Error.code, GLib.Error.domain
    This test ensures we can parse such classes and find these fields.

    We discover them using GIRepository directly.
    """
    from gi.repository import GLib

    class_schema, callbacks = parse_class("gi.repository.GLib", GLib.Error)

    assert class_schema is not None
    assert class_schema.name == "Error"
    field_names = [f.name for f in class_schema.fields]
    assert "message" in field_names
    assert "code" in field_names
    assert "domain" in field_names


def test_super_class():
    """Test getting the super class name of a class."""
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    obj = Gtk.Builder
    super_module, super_name = get_super_class_name(obj, current_namespace="Gtk")
    assert super_name == "Object"
    assert super_module == "gi.repository.GObject"


def test_gtk_application_inheritance_fix():
    """
    CRITICAL TEST: Gtk.Application (Namespace 'Gtk') inherits from Gio.Application (Namespace 'Gio').
    Both have the name 'Application'.

    The parser MUST verify that despite having the same name, they are different classes
    because the namespace differs.
    """
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    # Gtk.Application MRO usually:
    # [Gtk.Application, Gio.Application, GObject.Object, ...]
    cls = Gtk.Application

    module, name = get_super_class_name(cls, current_namespace="Gtk")

    # We expect it to point to Gio.Application
    assert module == "gi.repository.Gio"
    assert name == "Application"


def test_gtk_builder_shadowing_fix():
    """
    CRITICAL TEST: Gtk.Builder.
    This class usually has a Python Override.
    MRO: [gi.overrides.Gtk.Builder, gi.repository.Gtk.Builder, GObject.Object...]

    The parser MUST skip 'gi.repository.Gtk.Builder' because it has:
    1. Same Name ('Builder')
    2. Same Namespace ('Gtk')

    So the parent must be GObject.
    """

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    cls = Gtk.Builder

    module, name = get_super_class_name(cls, current_namespace="Gtk")

    # We expect it to SKIP the Gtk.Builder repo shadow and go to GObject
    assert module == "gi.repository.GObject"
    assert name == "Object"


def test_standard_widget_inheritance():
    """
    Standard Case: Gtk.Box inherits from Gtk.Widget.
    Different names, easy case.
    """
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    cls = Gtk.Box

    module, name = get_super_class_name(cls, current_namespace="Gtk")

    assert module == "gi.repository.Gtk"
    assert name == "Widget"


def test_gobject_inheritance():
    """
    Case: GObject.Object inherits from builtins.object.
    """

    cls = GObject.Object

    module, name = get_super_class_name(cls, current_namespace="GObject")

    assert module == "builtins"
    assert name == "object"


def test_ginitially_unowned():
    """
    Some GTK widgets inherit from GObject.InitiallyUnowned.
    E.g., Gtk.Widget -> GObject.InitiallyUnowned -> GObject.Object"""
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    # Gtk.Widget -> GObject.InitiallyUnowned -> GObject.Object
    cls = Gtk.Widget
    module, name = get_super_class_name(cls, current_namespace="Gtk")
    # It should point to InitiallyUnowned
    assert module == "gi.repository.GObject"
    assert name == "InitiallyUnowned"


def test_gio_file_interface():
    """
    Gio.File is an Interface, but in Python it appears as a class.
    We want to ensure we don't crash or return WeirdCThings.
    """
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio

    cls = Gio.File

    # Gio.File inherits from GObject.GInterface in MRO, but we treat it as a class base
    # or it might be a root interface.
    # Actually, Gio.File is a GInterface. In PyGObject it inherits from GObject.GInterface.

    module, name = get_super_class_name(cls, current_namespace="Gio")

    # We explicitly skip GInterface in the function, so it should fall back to object
    # OR if PyGObject exposes a prerequisite (like GObject), return that.

    # For interfaces, usually returning GObject.GInterface is what we filtered OUT.
    # So it should probably return 'object' or 'None, object'.
    assert name == "object"


def test_namespace_inference():
    """
    Test that the function can guess 'Gtk' from the object module
    if current_namespace is not provided.
    """
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    cls = Gtk.Button
    module, name = get_super_class_name(cls)  # No namespace provided

    assert module == "gi.repository.Gtk"
    assert name == "Widget"


# ============================================================================
# Super Override Tests
# ============================================================================


def test_get_super_override_returns_override():
    """Test that get_super_override returns the override when it exists."""
    from gi_stub_gen.overrides import get_super_override

    # GType should have builtins.type as super
    override = get_super_override("gi.repository.GObject", "GType")
    assert override is not None
    assert override == ["builtins.type"]


def test_get_super_override_returns_none_when_no_override():
    """Test that get_super_override returns None when no override exists."""
    from gi_stub_gen.overrides import get_super_override

    # GObject.Object should NOT have a super override
    override = get_super_override("gi.repository.GObject", "Object")
    assert override is None


def test_get_super_override_returns_none_for_unknown_class():
    """Test that get_super_override returns None for unknown classes."""
    from gi_stub_gen.overrides import get_super_override

    override = get_super_override("gi.repository.SomeUnknown", "UnknownClass")
    assert override is None


def test_gtype_class_has_builtins_type_as_super():
    """
    Test that GType class gets builtins.type as its super class via override.
    """
    from gi.repository import GObject
    from gi_stub_gen.parser.class_ import parse_class

    class_schema, _ = parse_class("gi.repository.GObject", GObject.GType)

    assert class_schema is not None
    assert class_schema.name == "GType"
    # GType should have builtins.type as super (from override)
    assert "builtins.type" in class_schema.super


def test_super_override_replaces_computed_super():
    """
    Test that when a super override exists, it replaces the computed super class,
    not append to it.
    """
    from gi.repository import GObject
    from gi_stub_gen.parser.class_ import parse_class

    class_schema, _ = parse_class("gi.repository.GObject", GObject.GType)

    assert class_schema is not None
    # The super list should only contain the override, not the original computed super
    # (which would be something like GObject.Object or similar)
    assert class_schema.super == ["builtins.type"], f"Expected super to be ['builtins.type'], got {class_schema.super}"


def test_class_without_super_override_uses_computed_super():
    """
    Test that classes without a super override use the computed super class.
    """
    from gi.repository import GObject
    from gi_stub_gen.parser.class_ import parse_class

    class_schema, _ = parse_class("gi.repository.GObject", GObject.InitiallyUnowned)

    assert class_schema is not None
    assert class_schema.super_class is not None

    # InitiallyUnowned should have Object as super (computed, no override)
    assert "Object" in class_schema.super_class


def test_gio_liststore_renders_pep695_typevar():
    """Gio.ListStore should render as a PEP 695 generic over its object item type."""
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio

    class_schema, _ = parse_class("Gio", Gio.ListStore)

    assert class_schema is not None
    assert [type_var.name for type_var in class_schema.type_vars] == ["ObjectItemType"]

    append_method = next(method for method in class_schema.methods if method.name == "append")
    append_item = next(arg for arg in append_method.args if arg.name == "item")
    assert append_item.type_hint("Gio") == "ObjectItemType"

    insert_method = next(method for method in class_schema.methods if method.name == "insert")
    insert_item = next(arg for arg in insert_method.args if arg.name == "item")
    assert insert_item.type_hint("Gio") == "ObjectItemType"

    new_method = next(method for method in class_schema.python_methods if method.name == "new")
    assert new_method.return_hint("Gio") == "ListStore[ObjectItemType]"

    TemplateManager.set_module_name("Gio")
    rendered = class_schema.render()

    assert "class ListStore[ObjectItemType: GObject.Object](GObject.Object):" in rendered
    assert "def append(self, item: ObjectItemType) -> None: ..." in rendered
    assert "def insert(self, position: int, item: ObjectItemType) -> None: ..." in rendered
    assert ") -> ListStore[ObjectItemType]:" in rendered


def test_gio_listmodel_renders_pep695_typevar():
    """Gio.ListModel should render as a PEP 695 generic over its object item type."""
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio

    class_schema, _ = parse_class("Gio", Gio.ListModel)

    assert class_schema is not None
    assert [type_var.name for type_var in class_schema.type_vars] == ["ObjectItemType"]

    get_item_method = next(method for method in class_schema.methods if method.name == "get_item")
    assert get_item_method.complete_return_hint("Gio") == "ObjectItemType | None"

    TemplateManager.set_module_name("Gio")
    rendered = class_schema.render()

    assert "class ListModel[ObjectItemType: GObject.Object]:" in rendered
    assert "def get_item(self, position: int) -> ObjectItemType | None:" in rendered
    assert "typing.Generic" not in rendered


def test_props_do_not_inherit_from_metaclass_argument():
    """Nested Props should not append .Props to class definition keyword arguments."""
    gi.require_version("GstVideo", "1.0")
    from gi.repository import GstVideo

    class_schema, _ = parse_class("GstVideo", GstVideo.VideoDirection)

    assert class_schema is not None

    TemplateManager.set_module_name("GstVideo")
    rendered = class_schema.render()

    assert "class VideoDirection(builtins.object, metaclass=GObject.GType):" in rendered
    assert "class Props:" in rendered
    assert "GObject.GType.Props" not in rendered
