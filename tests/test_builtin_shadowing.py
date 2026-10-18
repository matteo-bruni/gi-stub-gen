import ast

import pytest
from gi.repository import GLib, GObject, Gst

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.manager.gi_repo import GIRepo
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.schema.class_ import _qualify_builtin_annotations


def test_qualification_changes_only_annotation_names():
    original = '''class Example[T: str]:
    """str, list and object stay unchanged in documentation."""
    str: str
    def list(self, café: list[str], value: object = object()) -> tuple[str, typing.Literal["str"]]: ...
    def qualified(self) -> builtins.str: ...
'''
    expected = original.replace("[T: str]", "[T: builtins.str]").replace(
        "str: str", "str: builtins.str"
    ).replace("café: list[str]", "café: builtins.list[builtins.str]").replace(
        "value: object", "value: builtins.object"
    ).replace("tuple[str,", "tuple[builtins.str,")
    assert _qualify_builtin_annotations(original, {"str", "list", "object"}) == expected
    assert _qualify_builtin_annotations(original, {"unrelated"}) == original
    assert _qualify_builtin_annotations(expected, {"str", "list", "object"}) == expected
    ast.parse(expected)


@pytest.mark.parametrize("namespace,runtime,shadow", [
    ("GLib", GLib.String, "str"),
    ("GObject", GObject.ParamSpecPool, "list"),
    ("Gst", Gst.BufferPool, "object"),
])
def test_runtime_shadowing_is_qualified(namespace: str, runtime: type, shadow: str):
    GIRepo().require(namespace, "1.0" if namespace == "Gst" else "2.0")
    parsed, _ = parse_class(f"gi.repository.{namespace}", runtime)
    assert parsed is not None
    assert shadow in parsed.shadowed_builtin_types
    TemplateManager.set_module_name(namespace)
    rendered = parsed.render_stub()
    assert f"builtins.{shadow}" in rendered
    assert f"def {shadow}(" in rendered or f"{shadow}: builtins.{shadow}" in rendered
    ast.parse(rendered)


def test_inherited_runtime_member_hides_builtin_in_subclass():
    class DerivedPool(Gst.BufferPool):
        pass

    parsed, _ = parse_class("gi.repository.Gst", DerivedPool, parse_even_if_alias=True)
    assert parsed is not None
    assert "object" in parsed.shadowed_builtin_types
