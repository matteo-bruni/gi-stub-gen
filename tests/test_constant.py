from gi.repository import GObject

from gi_stub_gen.parser.constant import parse_constant


def test_type_foundamental_max():
    """
    Test parsing of GObject.TYPE_FUNDAMENTAL_MAX constant.
    This should be parsed as a python int type.
    and shound not change (hopefully) between versions.

    """
    to_test = GObject.TYPE_FUNDAMENTAL_MAX
    parsed_constant = parse_constant(
        module_name="GObject",
        name="TYPE_FUNDAMENTAL_MAX",
        obj=to_test,
        docstring=None,
    )
    assert parsed_constant is not None, "Failed to parse GObject.TYPE_FUNDAMENTAL_MAX constant"
    assert parsed_constant.name == "TYPE_FUNDAMENTAL_MAX"
    assert parsed_constant.namespace == "GObject"
    assert parsed_constant.type_hint == "int"
    assert not parsed_constant.is_deprecated
    assert parsed_constant.variable_type.name == "PYTHON_TYPE"
