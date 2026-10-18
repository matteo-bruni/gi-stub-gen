import ast
import subprocess
import sys

import pytest
from gi.repository import Gst

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.class_ import parse_class


@pytest.mark.parametrize("manual_fields", [True, False])
def test_fraction_constructor_and_fields_in_fresh_process(manual_fields):
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import ast
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
Gst.init(None)
assert Gst.is_initialized()
from gi_stub_gen.manager.gi_repo import GIRepo
from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.overrides import CLASS_OVERRIDES
from gi_stub_gen.parser.class_ import parse_class
GIRepo().require('Gst', '1.0')
manual_fields = sys.argv[1] == 'True'
if not manual_fields:
    CLASS_OVERRIDES['gi.repository.Gst']['Fraction']['fields'] = {}
schema, _ = parse_class('gi.repository.Gst', Gst.Fraction)
assert schema is not None
fields = {field.name: field for field in schema.fields}
for name in ('num', 'denom'):
    field = fields[name]
    assert field.render_type_annotation('Gst') == 'int'
    assert field.is_readable and field.is_writable
    assert bool(field.docstring) == manual_fields
TemplateManager.set_module_name('Gst')
cls = ast.parse(schema.render_stub()).body[0]
constructors = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '__init__']
assert len(constructors) == 1
init = constructors[0]
assert [arg.arg for arg in init.args.args] == ['self', 'num', 'denom']
assert [ast.unparse(arg.annotation) for arg in init.args.args[1:]] == ['int', 'int']
assert [ast.unparse(default) for default in init.args.defaults] == ['1']
assert ast.unparse(init.returns) == 'None'
assert any(method.name == '__init__' for method in schema.python_methods)
f = Gst.Fraction(num=3, denom=4)
assert (f.num, f.denom) == (3, 4)
assert Gst.Fraction(3).denom == 1
f.num, f.denom = 5, 6
assert (f.num, f.denom) == (5, 6)
""",
            str(manual_fields),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_fraction_declares_only_the_requested_operators():
    assert Gst.is_initialized()
    parsed, _ = parse_class("gi.repository.Gst", Gst.Fraction)
    assert parsed is not None
    expected = {
        "__mul__": ("self, other: Fraction | int", "Fraction"),
        "__rmul__": ("self, other: Fraction | int", "Fraction"),
        "__truediv__": ("self, other: Fraction | int", "Fraction"),
        "__rtruediv__": ("self, other: int", "Fraction"),
        "__float__": ("self", "float"),
    }
    assert {method.name for method in parsed.methods if method.name.startswith("__")} == expected.keys()
    for method in parsed.methods:
        if method.name in expected:
            assert (method.render_parameter_list("Gst"), method.render_return_annotation("Gst")) == expected[
                method.name
            ]
    assert parsed.super == ["builtins.object", "metaclass=GObject.GType"]
    TemplateManager.set_module_name("Gst")
    cls = ast.parse(parsed.render_stub()).body[0]
    assert isinstance(cls, ast.ClassDef)
    names = [node.name for node in cls.body if isinstance(node, ast.FunctionDef)]
    assert all(names.count(name) == 1 for name in expected)


def test_fraction_operators_at_runtime():
    assert Gst.is_initialized()
    fraction = Gst.Fraction(3, 4)
    for result, expected in (
        (fraction * 2, (3, 2)),
        (2 * fraction, (3, 2)),
        (fraction * Gst.Fraction(2, 3), (1, 2)),
        (fraction / 2, (3, 8)),
        (fraction / Gst.Fraction(2, 3), (9, 8)),
        (2 / fraction, (8, 3)),
    ):
        assert isinstance(result, Gst.Fraction)
        assert (result.num, result.denom) == expected
    assert float(fraction) == 0.75

    for name in ("__mul__", "__rmul__", "__truediv__", "__rtruediv__"):
        with pytest.raises(TypeError):
            getattr(fraction, name)(1.5)
