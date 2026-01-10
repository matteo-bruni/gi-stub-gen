"""
Tests for function decorator detection (@staticmethod, @classmethod) and is_class_member logic.

These tests ensure that:
1. Module-level functions do NOT get @staticmethod decorator
2. Class static methods DO get @staticmethod decorator
3. Class methods DO get @classmethod decorator
4. Regular instance methods have no special decorators
5. PyGObject wrapper methods (like disconnect) are correctly parsed as instance methods
"""

from gi.repository import GObject, Gst

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
