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
    assert "from __future__ import annotations" not in module.render_stub([], {})


def test_stub_formatting_sorts_imports_without_removing_exports():
    import ast
    import shutil
    import subprocess
    from gi_stub_gen.utils.utils import format_stub_with_ruff

    source = """import typing_extensions as typing_extensions
from gi.repository import GObject as GObject
import typing
import builtins
import _gi_gst as _gi_gst  # type: ignore

class Example:
    value: typing.Any
"""
    formatted = format_stub_with_ruff(source, "example.pyi")
    ruff = shutil.which("ruff")
    assert ruff is not None
    result = subprocess.run(
        [ruff, "check", "--select", "I,F401", "--stdin-filename", "example.pyi", "-"],
        input=formatted, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "import _gi_gst as _gi_gst  # type: ignore" in formatted
    assert "import typing_extensions as typing_extensions" in formatted
    assert "from gi.repository import GObject as GObject" in formatted
    before, after = ast.parse(source), ast.parse(formatted)
    before.body = [node for node in before.body if not (isinstance(node, ast.Import) and node.names[0].name == "builtins")]
    assert sorted(ast.dump(node) for node in before.body) == sorted(ast.dump(node) for node in after.body)


def test_stub_formatting_removes_unused_helpers_but_keeps_forward_annotations():
    import ast
    from gi_stub_gen.utils.utils import format_stub_with_ruff

    source = '''from typing_extensions import deprecated
import typing_extensions
from gi.repository import GLib

def example(value: "GLib.Bytes") -> str:
    """Retain this documentation."""
'''
    formatted = format_stub_with_ruff(source)
    assert "typing_extensions" not in formatted
    assert "from gi.repository import GLib" in formatted
    function = ast.parse(formatted).body[-1]
    assert isinstance(function, ast.FunctionDef)
    assert ast.get_docstring(function) == "Retain this documentation."


def test_package_metadata_is_not_processed_by_import_sorter(monkeypatch):
    import shutil
    import subprocess
    from types import SimpleNamespace
    from gi_stub_gen.utils.utils import format_stub_with_ruff

    calls = []
    monkeypatch.setattr(shutil, "which", lambda name: "/bin/ruff")
    def run(args, *, input, **kwargs):
        calls.append(args)
        return SimpleNamespace(stdout=input)
    monkeypatch.setattr(subprocess, "run", run)
    source = '[project]\nname = "example"\n'
    assert format_stub_with_ruff(source, "pyproject.toml") == source
    assert len(calls) == 1 and calls[0][1] == "format"


def test_stub_formatting_failure_preserves_original_text():
    from gi_stub_gen.utils.utils import format_stub_with_ruff

    source = "def unfinished("
    assert format_stub_with_ruff(source) == source


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
