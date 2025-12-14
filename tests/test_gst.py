from gi.repository import Gst, GObject

from gi_stub_gen.parser.function import parse_function


def test_gst_environment():
    assert Gst.version()[0] >= 1


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
