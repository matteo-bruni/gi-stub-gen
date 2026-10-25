"""Cross-version regressions: portable annotations, defaults and verified helpers."""

import ast
import contextlib
import importlib
import sys

import gi
import pytest

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.parser.declarations import parse_signature
from gi_stub_gen.parser.python_function import parse_python_function
from gi_stub_gen.parser.python_gi import parse_python_helper
from gi_stub_gen.utils.inspect_utils import _extract_annotation_type_info


@pytest.mark.parametrize("namespace", ["gi", "gi._gi"])
def test_repository_get_default_preserves_precise_return(namespace):
    from gi import _gi

    assert isinstance(_gi.Repository.get_default(), _gi.Repository)
    schema, _ = parse_class(namespace, _gi.Repository)
    assert schema is not None
    method = next(m for m in schema.python_methods if m.name == "get_default")
    assert method.params == []
    assert method.is_staticmethod
    assert method.render_return_annotation(namespace) == "Repository"


@pytest.mark.parametrize("default,expected", [(dict, "dict"), (object(), "...")])
def test_python_object_defaults_remain_optional_and_valid(default, expected):
    def example(value=default):
        pass

    parsed = parse_python_function(example, "Gst")
    assert parsed is not None
    assert parsed.params[0].default_value == expected
    TemplateManager.set_module_name("Gst")
    ast.parse(parsed.render_stub())


def test_analytics_class_default():
    try:
        gi.require_version("GstAnalytics", "1.0")
    except ValueError:
        pytest.skip("GstAnalytics is not installed")
    GstAnalytics = pytest.importorskip("gi.repository.GstAnalytics", exc_type=ImportError)

    parsed = parse_python_function(GstAnalytics.Mtd.iter_direct_related, "GstAnalytics", from_class=GstAnalytics.Mtd)
    assert parsed is not None
    assert next(p for p in parsed.params if p.name == "mtd_type").default_value == "Mtd"
    TemplateManager.set_module_name("GstAnalytics")
    ast.parse(parsed.render_stub())


def test_context_manager_retains_exit_result_on_old_python():
    assert _extract_annotation_type_info(contextlib.AbstractContextManager[None]) == (
        "ContextManager[None, bool | None]", "typing_extensions",
    )


def test_events_child_watchers_are_guarded_on_every_generation_python():
    module = parse_python_helper(importlib.import_module("gi.events"))
    text = module.render_stub([], {})
    ast.parse(text)
    assert "import sys" in text
    assert text.count("if sys.version_info < (3, 14):") == 2
    assert "def get_child_watcher" in text and "def set_child_watcher" in text


def test_version_guard_does_not_hide_unexpected_missing_members():
    with pytest.raises(RuntimeError, match="API changed"):
        parse_signature("absent(self) -> None", object, "test")
    if sys.version_info >= (3, 14):
        parsed = parse_signature("absent(self) -> None", object, "test", python_version_before=(3, 14))
        assert parsed.python_version_before == (3, 14)
