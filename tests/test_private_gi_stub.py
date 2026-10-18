import ast

import gi._gi as GI
from gi.repository import Gio, GIRepository

from gi_stub_gen.parser.private_gi import parse_private_gi


def test_private_declarations_render_and_match_runtime():
    schema = parse_private_gi(GI)
    text = schema.render_stub([], {})
    tree = ast.parse(text, feature_version=(3, 12))
    methods = {
        node.name: ast.unparse(node.returns)
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.returns is not None
    }
    assert "class Async[T]" in text
    assert methods["get_arguments"] == "tuple[ArgInfo, ...]"
    assert methods["get_tag_as_string"] == "str"
    assert methods["get_tag"] == "int"
    assert "__getattr__" not in text
    assert "class Props" not in text
    assert not hasattr(GIRepository.CallableInfo, "get_arguments")
    assert isinstance(Gio.File.load_contents_async, GI.FunctionInfo)
    assert type(Gio.File.load_contents_async.get_return_type().get_tag()) is int
    assert isinstance(Gio.File.load_contents_async.get_return_type(), GI.TypeInfo)
    assert isinstance(Gio.File.load_contents_async.get_arguments(), tuple)
    finish = Gio.File.load_contents_async.get_finish_func()
    assert finish is not None and finish.get_name() == "load_contents_finish"


def test_private_models_are_fresh():
    first = parse_private_gi(GI)
    original = first.model_dump()
    first.classes[0].python_methods[0].params[0].name = "changed"
    assert parse_private_gi(GI).model_dump() == original
