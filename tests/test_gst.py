from gi.repository import Gst

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.utils.gst import get_fraction_value


def test_gst_environment():
    assert Gst.version()[0] >= 1


def test_constructor_gst_new_returns_class_type():
    """
    class constructor should return the class type properly.
    """
    constructor_to_test = "new"

    for class_to_test, return_hint in ((Gst.Bin, "Bin"), (Gst.Pipeline, "Pipeline")):
        parsed_class, _ = parse_class("Gst", class_to_test)
        assert parsed_class is not None, f"Failed to parse Gst.{return_hint} class"

        # find the constructor
        constructor = [m for m in parsed_class.methods if m.name == constructor_to_test]
        assert len(constructor) == 1, f"Failed to find Gst.{return_hint}.new constructor method"
        parsed_constructor = constructor[0]

        # check the return hint
        assert parsed_constructor.complete_return_hint(namespace="GObject") == f"Gst.{return_hint}"
        assert parsed_constructor.complete_return_hint(namespace="Gst") == return_hint
        # should have no parameters
        assert parsed_constructor.render_args(namespace="Gst", one_line=True) == "cls, name: str | None = None"

        python_constructor = [m for m in parsed_class.python_methods if m.name == constructor_to_test]
        assert len(python_constructor) == 1, f"Failed to find Gst.{return_hint}.new python override"
        assert python_constructor[0].return_hint(namespace="Gst") == return_hint

        TemplateManager.set_module_name("Gst")
        rendered = parsed_class.render()
        assert f") -> {return_hint}:" in rendered


def test_gst_object_parent_renders_direct_property():
    parsed_class, _ = parse_class("Gst", Gst.Object)
    assert parsed_class is not None

    parent = next(field for field in parsed_class.fields if field.name == "parent")
    assert parent.type_hint("Gst") == "Object | None"
    assert parent.is_property is True

    TemplateManager.set_module_name("Gst")
    rendered = parsed_class.render()
    assert "def parent(self) -> Object | None:" in rendered


def test_function_gst_version():
    function_to_test = Gst.version

    # do the parsing
    parsed_function = parse_function(function_to_test, None)
    assert parsed_function is not None, "Failed to parse Gst.version function"

    # check the return hint
    assert parsed_function.complete_return_hint(namespace="Gst") == "tuple[int, int, int, int]"
    # should have no parameters
    assert parsed_function.render_args(namespace="Gst", one_line=True) == ""


def test_function_gst_version_string():
    function_to_test = Gst.version_string

    # do the parsing
    parsed_function = parse_function(function_to_test, None)
    assert parsed_function is not None, "Failed to parse Gst.version function"

    # check the return hint
    assert parsed_function.complete_return_hint(namespace="Gst") == "str"
    # should have no parameters
    assert parsed_function.render_args(namespace="Gst", one_line=True) == ""


def test_fraction():
    frac = Gst.Fraction(num=3, denom=4)
    assert frac.num == 3
    assert frac.denom == 4


def test_fraction_values():
    frac = Gst.Fraction(num=1, denom=100)

    assert frac.num == 1
    assert frac.denom == 100

    value = get_fraction_value(frac)
    assert value == "Gst.Fraction(num=1, denom=100)"
