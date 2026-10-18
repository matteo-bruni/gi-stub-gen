import pytest


@pytest.mark.parametrize(
    "name,expected_sane_name,expected_comment",
    [
        ("valid_name", "valid_name", None),
        (
            "1invalid-name",
            "_1invalid_name",
            "[1invalid-name]: changed because contained invalid characters, started with a number",
        ),
        ("class", "class_", "[class]: changed, name is a reserved keyword"),
        ("class!", "class_", "[class!]: changed because contained invalid characters"),
    ],
)
def test_sanitize_variable_name(
    name: str,
    expected_sane_name: str,
    expected_comment: str | None,
):
    from gi_stub_gen.utils.utils import sanitize_variable_name

    sane_variable, comment = sanitize_variable_name(name)
    assert sane_variable == expected_sane_name
    assert comment == expected_comment


def test_expected_failure_on_empty_name():
    from gi_stub_gen.utils.utils import sanitize_variable_name

    with pytest.raises(ValueError):
        sane_variable, comment = sanitize_variable_name(None)  # type: ignore


def test_module_imports_do_not_duplicate_typing_extensions():
    from gi_stub_gen.schema.module import ModuleSchema

    module = ModuleSchema(
        name="gi.repository.GLib",
        classes=[],
        constant=[],
        enum=[],
        function=[],
        builtin_function=[],
        callbacks=[],
        aliases=[],
    )

    _, extra_imports = module.collect_imports(extra_imports=["typing_extensions"])

    assert "typing_extensions" not in extra_imports


def test_gi_container_types_are_runtime_generic_aliases():
    from types import GenericAlias
    from typing import get_args, get_origin
    from gi import _gi
    from gi.repository import GLib, Gst
    from gi_stub_gen.utils.gi_utils import gi_type_to_py_type

    list_elements = Gst.ElementFactory.list_get_elements
    decode = GLib.base64_decode
    assert isinstance(list_elements, _gi.FunctionInfo)
    assert isinstance(decode, _gi.FunctionInfo)
    result = gi_type_to_py_type(list_elements.get_return_type())
    assert isinstance(result, GenericAlias)
    assert result == list[Gst.ElementFactory]
    assert get_origin(result) is list
    assert get_args(result) == (Gst.ElementFactory,)
    assert gi_type_to_py_type(decode.get_return_type()) is bytes


def test_inspect_parameter_kinds():
    import inspect
    from gi_stub_gen.schema.builtin_function import ArgKind

    for kind in inspect._ParameterKind:
        assert ArgKind.from_inspect(kind).name == kind.name
