from gi.repository import Gst

from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.parser.function import parse_function


def test_gst_environment():
    assert Gst.version()[0] >= 1


def test_constructor_gst_pipeline_new():
    """
    class constructor should return the class type properly.
    """
    class_to_test = Gst.Pipeline
    constructor_to_test = "new"

    parsed_class, _ = parse_class("Gst", class_to_test)
    assert parsed_class is not None, "Failed to parse Gst.Pipeline class"

    # find the constructor
    constructor = [m for m in parsed_class.methods if m.name == constructor_to_test]
    assert len(constructor) == 1, "Failed to find Gst.Pipeline.new constructor method"
    parsed_constructor = constructor[0]

    # check the return hint
    assert parsed_constructor.complete_return_hint(namespace="GObject") == "Gst.Pipeline"
    assert parsed_constructor.complete_return_hint(namespace="Gst") == "Pipeline"
    # should have no parameters
    assert parsed_constructor.render_args(namespace="Gst", one_line=True) == "cls, name: str | None = None"


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
