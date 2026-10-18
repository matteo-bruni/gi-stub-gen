import inspect
from collections.abc import Callable

import pytest
from gi.repository import GLib

from gi_stub_gen.manager.gi_repo import GIRepo
from gi_stub_gen.parser.class_ import parse_class


@pytest.mark.parametrize("runtime", [GLib.Idle, GLib.Timeout])
def test_inherited_python_wrappers_are_not_replaced_by_gi_methods(runtime: type):
    GIRepo().require("GLib", "2.0")
    base, _ = parse_class("gi.repository.GLib", GLib.Source)
    parsed, _ = parse_class("gi.repository.GLib", runtime)
    assert base is not None and parsed is not None
    for name in ("get_current_time", "set_callback"):
        assert getattr(runtime, name) is getattr(GLib.Source, name)
        assert name not in {method.name for method in (*parsed.methods, *parsed.python_methods)}
        assert name in {method.name for method in base.python_methods}
    method = next(method for method in base.python_methods if method.name == "get_current_time")
    assert method.render_parameter_list("GLib") == ["self"]
    assert method.render_return_annotation("GLib") == "float"
    assert list(inspect.signature(getattr(runtime, "get_current_time")).parameters) == ["self"]


@pytest.mark.parametrize("create", [GLib.Idle, lambda: GLib.Timeout(0)])
def test_source_runtime_time_and_callback_userdata(create: Callable[[], GLib.Source]):
    source = create()
    seen: list[tuple[int, str]] = []

    def callback(number: int, label: str) -> bool:
        seen.append((number, label))
        return False

    try:
        with pytest.warns(DeprecationWarning):
            assert isinstance(source.get_current_time(), float)
        source.set_callback(callback, 7, "payload")
        context = GLib.MainContext.new()
        source.attach(context)
        assert context.iteration(False)
        assert seen == [(7, "payload")]
    finally:
        source.destroy()
