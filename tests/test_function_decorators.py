"""
Tests for function decorator detection (@staticmethod, @classmethod) and is_class_member logic.

These tests ensure that:
1. Module-level functions do NOT get @staticmethod decorator
2. Class static methods DO get @staticmethod decorator
3. Class methods DO get @classmethod decorator
4. Regular instance methods have no special decorators
5. PyGObject wrapper methods (like disconnect) are correctly parsed as instance methods
"""

from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GstAudio", "1.0")

from gi.repository import GLib, GObject, Gio, Gst, GstAudio

from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.parser.python_function import parse_python_function


class TestGIFunctionDecorators:
    """Test decorator detection for GObject Introspection (GI) functions."""

    def test_module_level_function_no_staticmethod(self):
        """
        Module-level GI functions should NOT have @staticmethod decorator.
        Example: Gst.version() is a module-level function, not a class method.
        """
        parsed = parse_function(Gst.version, None)
        assert parsed is not None

        # is_class_member should be False for module-level functions
        assert parsed.is_class_member is False

        # Should have no decorators
        assert "@staticmethod" not in parsed.decorators
        assert "@classmethod" not in parsed.decorators

    def test_module_level_function_version_string(self):
        """Another module-level function: Gst.version_string()"""
        parsed = parse_function(Gst.version_string, None)
        assert parsed is not None
        assert parsed.is_class_member is False
        assert "@staticmethod" not in parsed.decorators

    def test_gobject_unintrospectable_function_is_skipped(self):
        """
        GObject.signal_set_va_marshaller references VaClosureMarshal, which is
        marked introspectable=0 in the GIR and should be skipped.
        """
        assert parse_function(GObject.signal_set_va_marshaller, None) is None  # type: ignore

    def test_class_static_method_has_decorator(self):
        """
        Static methods inside classes SHOULD have @staticmethod decorator.
        Example: Gst.Allocator.find() is a static method.
        """
        parsed_class, _ = parse_class("Gst", Gst.Allocator)
        assert parsed_class is not None

        # Find the 'find' static method
        find_method = next((m for m in parsed_class.methods if m.name == "find"), None)
        assert find_method is not None, "Gst.Allocator.find not found"

        # Should be marked as class member and have @staticmethod
        assert find_method.is_class_member is True
        assert "@staticmethod" in find_method.decorators

    def test_class_instance_method_no_staticmethod(self):
        """
        Regular instance methods should NOT have @staticmethod decorator.
        Example: Gst.Element.get_state() is an instance method.
        """
        parsed_class, _ = parse_class("Gst", Gst.Element)
        assert parsed_class is not None

        # Find an instance method
        get_state = next((m for m in parsed_class.methods if m.name == "get_state"), None)
        assert get_state is not None, "Gst.Element.get_state not found"

        # Should be a class member but NOT static
        assert get_state.is_class_member is True
        assert "@staticmethod" not in get_state.decorators

    def test_constructor_no_staticmethod(self):
        """
        Constructors should NOT have @staticmethod decorator.
        Example: Gst.Pipeline.new() is a constructor.
        """
        parsed_class, _ = parse_class("Gst", Gst.Pipeline)
        assert parsed_class is not None

        # Find the constructor
        new_method = next((m for m in parsed_class.methods if m.name == "new"), None)
        assert new_method is not None, "Gst.Pipeline.new not found"

        # Constructors are class members but should not be marked as static
        assert new_method.is_class_member is True
        assert "@staticmethod" not in new_method.decorators


class TestPythonFunctionDecorators:
    """Test decorator detection for pure Python functions/methods."""

    def test_module_level_python_function_no_staticmethod(self):
        """
        Module-level Python functions should NOT have @staticmethod.
        Example: Gst.init_python() is a Python override at module level.
        """
        # Parse without from_class (module-level)
        parsed = parse_python_function(Gst.init_python, "gi.repository.Gst")
        assert parsed is not None

        # Should not be from a class
        assert parsed.is_from_class is False

        # Should have no decorators
        assert "@staticmethod" not in parsed.decorators
        assert "@classmethod" not in parsed.decorators

    def test_class_method_with_from_class(self):
        """
        When parsing a method with from_class, it should be marked as from_class.
        """
        # GObject.Object has Python methods like disconnect, handler_block
        disconnect_method = getattr(GObject.Object, "disconnect", None)
        assert disconnect_method is not None

        parsed = parse_python_function(disconnect_method, "gi.repository.GObject", from_class=GObject.Object)
        assert parsed is not None

        # Should be from a class
        assert parsed.is_from_class is True

        # disconnect is a regular instance method, not static
        assert "@staticmethod" not in parsed.decorators
        assert "@classmethod" not in parsed.decorators

    def test_gobject_signal_wrappers_consume_bound_receiver(self):
        """Module helper signatures copied onto Object must not duplicate self."""
        expected_parameters = {
            "disconnect": ["self", "handler_id: int"],
            "handler_disconnect": ["self", "handler_id: int"],
            "handler_block": ["self", "handler_id: int"],
            "handler_unblock": ["self", "handler_id: int"],
            "handler_is_connected": ["self", "handler_id: int"],
            "stop_emission_by_name": ["self", "detailed_signal: str"],
        }

        for method_name, expected in expected_parameters.items():
            parsed = parse_python_function(
                getattr(GObject.Object, method_name),
                "GObject",
                from_class=GObject.Object,
            )
            assert parsed is not None
            assert parsed.param_signature("GObject") == expected

    def test_gobject_module_signal_helper_keeps_instance_argument(self):
        """The unbound GI helper still requires its explicit instance."""
        parsed = parse_function(GObject.signal_handler_disconnect, None)
        assert parsed is not None
        assert parsed.render_args("GObject") == "instance: Object, handler_id: int"

    def test_gobject_handler_block(self):
        """
        GObject.Object.handler_block is a PyGObject wrapper method.
        It should be detected as an instance method when from_class is provided.
        """
        handler_block = getattr(GObject.Object, "handler_block", None)
        assert handler_block is not None

        parsed = parse_python_function(handler_block, "gi.repository.GObject", from_class=GObject.Object)
        assert parsed is not None
        assert parsed.is_from_class is True
        assert "@staticmethod" not in parsed.decorators

    def test_parsed_class_python_methods_have_self(self):
        """
        When parsing a class, Python methods like disconnect should have 'self'.
        """
        parsed_class, _ = parse_class("gi.repository.GObject", GObject.Object)
        assert parsed_class is not None

        # Find disconnect in python_methods
        disconnect = next((m for m in parsed_class.python_methods if m.name == "disconnect"), None)
        assert disconnect is not None, "disconnect not found in python_methods"

        # Should be from a class
        assert disconnect.is_from_class is True

        # Should NOT have @staticmethod
        assert "@staticmethod" not in disconnect.decorators

    def test_python_override_renders_enum_default_name(self):
        """connect_data should render ConnectFlags.DEFAULT instead of the raw 0 value."""
        assert int(GObject.ConnectFlags.DEFAULT) == 0

        parsed = parse_python_function(
            GObject.Object.connect_data,
            "GObject",
            from_class=GObject.Object,
        )
        assert parsed is not None

        connect_flags = next(param for param in parsed.params if param.name == "connect_flags")
        assert connect_flags.type_hint_name == "ConnectFlags"
        assert connect_flags.default_value == "ConnectFlags.DEFAULT"

    def test_python_override_renders_self_namespace(self):
        """GLib.Error.copy annotates return as string Self and should qualify it."""
        parsed = parse_python_function(GLib.Error.copy, "GLib", from_class=GLib.Error)
        assert parsed is not None

        assert parsed.return_hint_name == "Self"
        assert parsed.return_hint_namespace == "typing_extensions"
        assert parsed.return_hint("GLib") == "typing_extensions.Self"

        parsed_class, _ = parse_class("GLib", GLib.Error)
        assert parsed_class is not None

        TemplateManager.set_module_name("GLib")
        rendered = parsed_class.render()
        assert ") -> typing_extensions.Self:" in rendered

    def test_python_override_keeps_gst_iterator_type(self):
        """
        Python Gst overrides can use postponed annotations such as Iterator[Element].
        Those should resolve to Gst.Iterator, not typing.Iterator.
        """
        parsed = parse_python_function(
            Gst.Bin.iterate_all_by_element_factory_name,
            "Gst",
            from_class=Gst.Bin,
        )
        assert parsed is not None

        assert parsed.return_hint_namespace == "Gst"
        assert parsed.return_hint_name == "Iterator[Element]"
        assert parsed.return_hint("Gst") == "Iterator[Element]"

    def test_gst_iterator_renders_pep695_typevar(self):
        """Gst.Iterator should render as generic so Iterator[Element] is valid."""
        assert GIRDocs().load(Path("/usr/share/gir-1.0/Gst-1.0.gir"))
        parsed_class, _ = parse_class("Gst", Gst.Iterator)

        assert parsed_class is not None
        assert [type_var.name for type_var in parsed_class.type_vars] == ["T"]

        iter_method = next(method for method in parsed_class.python_methods if method.name == "__iter__")
        assert iter_method.return_hint("Gst") == "collections.abc.Iterator[T]"

        TemplateManager.set_module_name("Gst")
        rendered = parsed_class.render()

        assert "class Iterator[T](GObject.GBoxed, metaclass=GObject.GType):" in rendered
        assert "def __iter__(" in rendered
        assert ") -> collections.abc.Iterator[T]:" in rendered

        next_method = next(method for method in parsed_class.methods if method.name == "next")
        find_custom = next(method for method in parsed_class.methods if method.name == "find_custom")
        assert next_method.complete_return_hint("Gst") == "tuple[IteratorResult, T]"
        assert find_custom.complete_return_hint("Gst") == "tuple[bool, T]"

    def test_gst_override_mixin_methods_are_inherited(self):
        """Public override mixins are rendered as bases instead of being flattened."""
        assert GIRDocs().load(Path("/usr/share/gir-1.0/Gst-1.0.gir"))

        parsed_buffer, _ = parse_class("gi.repository.Gst", Gst.Buffer)
        assert parsed_buffer is not None
        assert parsed_buffer.super[:2] == ["MiniObjectMixin[BufferFlags]", "GObject.GBoxed"]
        assert "is_writable" not in {method.name for method in parsed_buffer.methods}
        assert "make_writable" not in {method.name for method in parsed_buffer.methods}
        assert "is_writable" not in {method.name for method in parsed_buffer.python_methods}
        assert "make_writable" not in {method.name for method in parsed_buffer.python_methods}

        parsed_mixin, _ = parse_class("gi.repository.Gst", Gst.MiniObjectMixin)
        assert parsed_mixin is not None
        mixin_methods = {method.name: method for method in parsed_mixin.python_methods}
        assert mixin_methods["is_writable"].return_hint("Gst") == "bool"
        assert mixin_methods["make_writable"].return_hint("Gst") == "bool"

    def test_caller_allocated_out_gvalue_is_unwrapped_to_any(self):
        """PyGObject returns the Python payload, not a GObject.Value wrapper."""
        assert GIRDocs().load(Path("/usr/share/gir-1.0/Gio-2.0.gir"))
        parsed = parse_function(Gio.Task.propagate_value, None)
        assert parsed is not None

        value = next(arg for arg in parsed.args if arg.name == "value")
        assert value.is_marshaled_gvalue_payload is True
        assert value.type_hint("Gio") == "typing.Any"
        assert parsed.complete_return_hint("Gio") == "tuple[bool, typing.Any]"

        parsed_class, _ = parse_class("gi.repository.Gio", Gio.Task)
        assert parsed_class is not None
        return_value = next(method for method in parsed_class.methods if method.name == "return_value")
        assert return_value.render_args("Gio") == "self, result: typing.Any = None"
        assert return_value.complete_return_hint("Gio") == "None"

        assert GIRDocs().load(Path("/usr/share/gir-1.0/GObject-2.0.gir"))
        invoke = parse_function(GObject.Closure.invoke, None)
        assert invoke is not None
        param_values = next(arg for arg in invoke.args if arg.name == "param_values")
        assert param_values.type_hint("GObject") == "list[typing.Any]"

        getv = parse_function(GObject.Object.getv, None)
        assert getv is not None
        values = next(arg for arg in getv.args if arg.name == "values")
        assert values.type_hint("GObject") == "list[Value]"

    def test_gtype_function_inputs_remain_gtype(self):
        """The enum metaclasses make a separate widened input alias unnecessary."""
        parsed = parse_function(GObject.type_is_a, None)
        assert parsed is not None
        assert [arg.type_hint("GObject") for arg in parsed.input_args] == [
            "GType",
            "GType",
        ]

        signal_newv = parse_function(GObject.signal_newv, None)
        assert signal_newv is not None
        param_types = next(arg for arg in signal_newv.input_args if arg.name == "param_types")
        assert param_types.type_hint("GObject") == "list[GType] | None"

    def test_gtype_virtual_function_inputs_remain_gtype(self):
        """Virtual handler arguments are delivered by GI, not supplied by callers."""

        class VirtualHandler:
            def do_handle(self, value: GObject.GType) -> None:
                pass

        parsed = parse_python_function(
            VirtualHandler.do_handle,
            "GObject",
            from_class=VirtualHandler,
        )
        assert parsed is not None
        value = next(param for param in parsed.params if param.name == "value")
        assert value.type_hint("GObject") == "GType"

    def test_gst_context_managers_render_enter_exit(self):
        """Gst override context managers should expose the context manager protocol."""
        TemplateManager.set_module_name("Gst")

        for context_manager, enter_return in (
            (Gst.PadProbeInfoObjectContextManager, "MiniObject"),
            (Gst.StructureContextManager, "Structure"),
        ):
            parsed_class, _ = parse_class("Gst", context_manager)
            assert parsed_class is not None

            enter_method = next(method for method in parsed_class.python_methods if method.name == "__enter__")
            exit_method = next(method for method in parsed_class.python_methods if method.name == "__exit__")

            assert enter_method.return_hint("Gst") == enter_return
            assert exit_method.return_hint("Gst") == "None"

            rendered = parsed_class.render()
            assert "def __enter__(" in rendered
            assert f") -> {enter_return}:" in rendered
            assert "def __exit__(" in rendered
            assert ") -> None:" in rendered

    def test_python_override_keeps_callable_argument_types(self):
        """
        Callable annotations from overrides expose their parameter list as a literal
        list in typing.get_args(); those entries still need proper type rendering.
        """
        parsed = parse_python_function(
            GstAudio.AudioClock.new,
            "GstAudio",
            from_class=GstAudio.AudioClock,
        )
        assert parsed is not None

        func_param = next(param for param in parsed.params if param.name == "func")
        assert func_param.type_hint_namespace == "collections.abc"
        assert func_param.type_hint_name == "Callable[[Gst.Clock, typing.Any], int]"
        assert func_param.type_hint("GstAudio") == "collections.abc.Callable[[Gst.Clock, typing.Any], int]"

    def test_python_override_avoids_same_module_prefix_in_generics(self):
        """
        Generic arguments from the current module should not be redundantly prefixed.
        """
        parsed = parse_python_function(
            Gio.AppLaunchContext.do_get_display,
            "Gio",
            from_class=Gio.AppLaunchContext,
        )
        assert parsed is not None

        files_param = next(param for param in parsed.params if param.name == "files")
        assert files_param.type_hint_name == "list[File]"
        assert files_param.type_hint_namespace is None
        assert files_param.type_hint("Gio") == "list[File]"

    def test_python_override_uses_gir_docstring_when_python_doc_missing(self, tmp_path):
        gir_file = tmp_path / "Gst-1.0.gir"
        gir_file.write_text(
            """<?xml version="1.0"?>
<repository version="1.2" xmlns="http://www.gtk.org/introspection/core/1.0" xmlns:c="http://www.gtk.org/introspection/c/1.0" xmlns:glib="http://www.gtk.org/introspection/glib/1.0">
  <namespace name="Gst" version="1.0" shared-library="libgstreamer-1.0.so" c:identifier-prefixes="Gst" c:symbol-prefixes="gst">
    <record name="Buffer">
      <method name="map" c:identifier="gst_buffer_map">
        <doc xml:space="preserve">Maps the buffer for test docs.</doc>
        <return-value transfer-ownership="none">
          <type name="gboolean" c:type="gboolean"/>
        </return-value>
      </method>
    </record>
  </namespace>
</repository>
""",
            encoding="utf-8",
        )
        assert GIRDocs().load(gir_file)

        parsed_class, _ = parse_class("Gst", Gst.Buffer)
        assert parsed_class is not None

        map_method = next(method for method in parsed_class.python_methods if method.name == "map")
        assert map_method.docstring is not None
        assert (
            "[is-override: Note this method is an override in Python of the original gi implementation.]"
            in map_method.docstring
        )
        assert "Maps the buffer for test docs." in map_method.docstring

    def test_python_override_detects_typevar_bound(self):
        """Gio.ListStore.insert_sorted exposes ObjectItemType bound to GObject.Object."""
        parsed = parse_python_function(
            Gio.ListStore.insert_sorted,
            "Gio",
            from_class=Gio.ListStore,
        )
        assert parsed is not None

        item_param = next(param for param in parsed.params if param.name == "item")
        assert item_param.type_hint_name == "ObjectItemType"
        assert item_param.type_hint_namespace is None
        assert item_param.type_var_names == ["ObjectItemType"]

        assert len(parsed.type_vars) == 1
        type_var = parsed.type_vars[0]
        assert type_var.name == "ObjectItemType"
        assert type_var.bound_hint_name == "Object"
        assert type_var.bound_hint_namespace == "GObject"


class TestClassMethodDetection:
    """Test @classmethod detection for Python methods."""

    def test_classmethod_detected(self):
        """
        Test that @classmethod decorator is properly detected.
        Example: Gst.AtomicQueue.new is a classmethod.
        """
        # AtomicQueue.new is a classmethod
        new_method = getattr(Gst.AtomicQueue, "new", None)
        assert new_method is not None

        parsed = parse_python_function(new_method, "gi.repository.Gst", from_class=Gst.AtomicQueue)
        assert parsed is not None
        assert parsed.is_from_class is True
        assert "@classmethod" in parsed.decorators
        assert "@staticmethod" not in parsed.decorators

    def test_classmethod_in_parsed_class(self):
        """
        When parsing AtomicQueue, the 'new' method should have @classmethod.
        """
        parsed_class, _ = parse_class("Gst", Gst.AtomicQueue)
        assert parsed_class is not None

        # Find 'new' in python_methods
        new_method = next((m for m in parsed_class.python_methods if m.name == "new"), None)
        assert new_method is not None, "AtomicQueue.new not found"
        assert "@classmethod" in new_method.decorators


class TestStaticMethodDetection:
    """Test @staticmethod detection for Python methods."""

    def test_staticmethod_detected(self):
        """
        Test that @staticmethod decorator is properly detected on Python methods.
        """

        # Create a test class with a staticmethod
        class TestClass:
            @staticmethod
            def static_func():
                pass

            @classmethod
            def class_func(cls):
                pass

            def instance_func(self):
                pass

        # Test staticmethod
        parsed_static = parse_python_function(TestClass.static_func, "test", from_class=TestClass)
        assert parsed_static is not None
        assert parsed_static.is_from_class is True
        assert "@staticmethod" in parsed_static.decorators
        assert "@classmethod" not in parsed_static.decorators

        # Test classmethod
        parsed_class = parse_python_function(TestClass.class_func, "test", from_class=TestClass)
        assert parsed_class is not None
        assert parsed_class.is_from_class is True
        assert "@classmethod" in parsed_class.decorators
        assert "@staticmethod" not in parsed_class.decorators

        # Test instance method
        parsed_instance = parse_python_function(TestClass.instance_func, "test", from_class=TestClass)
        assert parsed_instance is not None
        assert parsed_instance.is_from_class is True
        assert "@staticmethod" not in parsed_instance.decorators
        assert "@classmethod" not in parsed_instance.decorators


class TestNoFromClassMeansModuleLevel:
    """Test that without from_class, functions are treated as module-level."""

    def test_no_from_class_not_class_member(self):
        """
        When from_class is not provided, the function should not be marked as class member.
        """

        # Even if we pass a method, without from_class it's treated as module-level
        def some_func():
            pass

        parsed = parse_python_function(some_func, "test")
        assert parsed is not None
        assert parsed.is_from_class is False
        assert "@staticmethod" not in parsed.decorators
        assert "@classmethod" not in parsed.decorators


class TestPropertyDecorator:
    """Test @property decorator for getter methods."""

    def test_gi_getter_is_not_property(self):
        """
        GI methods with IS_GETTER flag should NOT be marked as @property.
        They are regular methods in Python, even though they are getters in C.
        Example: Gst.Pad.get_direction has IS_GETTER=True but is a method.
        """
        parsed_class, _ = parse_class("Gst", Gst.Pad)
        assert parsed_class is not None

        get_direction = next((m for m in parsed_class.methods if m.name == "get_direction"), None)
        assert get_direction is not None, "Gst.Pad.get_direction not found"

        # Should be a getter in GI terms
        assert get_direction.is_getter is True

        # But should NOT be a property in Python terms
        assert get_direction.is_property is False
        assert "@builtins.property" not in get_direction.decorators

    def test_explicit_property_override(self):
        """
        Methods explicitly marked as is_property=True should have @property decorator.
        Example: GObject.GEnum.value_name is defined with is_property=True in overrides.
        """
        from gi_stub_gen.overrides.class_.GObject.GEnum import GENUM_SCHEMA

        # Check the override schema
        value_name = next((m for m in GENUM_SCHEMA.methods if m.name == "value_name"), None)
        assert value_name is not None, "value_name not found in GENUM_SCHEMA"

        # Should be explicitly marked as property
        assert value_name.is_property is True
        assert "@builtins.property" in value_name.decorators
