"""Keep the native Mtd default correction local and detect upstream runtime fixes."""

import inspect

import gi
from gi.repository import GLib, Gst
import pytest

from gi_stub_gen.manager.template import TemplateManager
from gi_stub_gen.overrides import apply_method_transforms
from gi_stub_gen.overrides.class_.GstAnalytics.Mtd import transform_iter_direct_related
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.parser.python_function import parse_python_function


@pytest.fixture
def analytics():
    try:
        gi.require_version("GstAnalytics", "1.0")
    except ValueError:
        pytest.skip("GstAnalytics is not installed")
    return pytest.importorskip("gi.repository.GstAnalytics", exc_type=ImportError)


def test_analytics_default_transform_preserves_signature_docs_and_input(analytics):
    raw = parse_python_function(analytics.Mtd.iter_direct_related, "GstAnalytics", from_class=analytics.Mtd)
    assert raw is not None
    raw.docstring = "Existing documentation."
    original = raw.model_dump()
    _, methods = apply_method_transforms([], [raw], "gi.repository.GstAnalytics", "Mtd")
    corrected = methods[0]
    assert corrected.params[-1].default_value == "..."
    assert corrected.docstring is not None
    assert corrected.docstring.startswith("Existing documentation.\n\nStub note:")
    assert "gst-python 1.28.8" in corrected.docstring
    assert "TypeError" in corrected.docstring
    assert raw.model_dump() == original
    expected = raw.model_copy(deep=True)
    expected.params[-1].default_value = "..."
    expected.docstring = corrected.docstring
    assert corrected == expected

    parsed, _ = parse_class("gi.repository.GstAnalytics", analytics.Mtd)
    assert parsed is not None
    method = next(method for method in parsed.python_methods if method.name == "iter_direct_related")
    TemplateManager.set_module_name("GstAnalytics")
    rendered = method.render_stub()
    assert "mtd_type: typing.Any = ..." in rendered
    assert "= Mtd" not in rendered
    assert "Stub note:" in rendered


@pytest.mark.parametrize("default", [None, "...", "None", "GstAnalytics.Mtd", "object"])
def test_analytics_transform_bypasses_changed_defaults(default):
    def iter_direct_related(self, relation, mtd_type=None):
        """Upstream documentation."""

    method = parse_python_function(iter_direct_related, "GstAnalytics", from_class=object)
    assert method is not None
    method.params[-1].default_value = default
    before = method.model_dump()
    assert transform_iter_direct_related(method) is method
    assert method.model_dump() == before


def test_analytics_transform_bypasses_native_methods_and_missing_parameter():
    native = parse_function(Gst.Element.query_position, "Gst")
    assert native is not None
    before = native.model_dump()
    assert transform_iter_direct_related(native) is native
    assert native.model_dump() == before

    def iter_direct_related(self, relation):
        """Upstream documentation."""

    method = parse_python_function(iter_direct_related, "GstAnalytics", from_class=object)
    assert method is not None
    before = method.model_dump()
    assert transform_iter_direct_related(method) is method
    assert method.model_dump() == before


def test_analytics_runtime_default_and_public_wrapper_still_differ(analytics):
    review = "gst-python changed: review the Mtd transform and its versioned runtime warning"
    method = analytics.Mtd.iter_direct_related
    default = inspect.signature(method).parameters["mtd_type"].default
    assert default is analytics.Mtd.__mro__[1], review
    assert default is not analytics.Mtd, review

    buffer = Gst.Buffer.new()
    meta = analytics.buffer_add_analytics_relation_meta(buffer)
    assert meta is not None
    ok, source = meta.add_od_mtd(GLib.quark_from_string("source"), 0, 0, 10, 10, 0.9)
    assert ok and source is not None
    ok, target = meta.add_od_mtd(GLib.quark_from_string("target"), 0, 0, 10, 10, 0.8)
    assert ok and target is not None
    relation = analytics.RelTypes.RELATE_TO
    assert meta.set_relation(relation, source.id, target.id)

    for args in ((), (default,), (analytics.ODMtd,)):
        results = list(source.iter_direct_related(relation, *args))
        assert [item.id for item in results] == [target.id]
        assert isinstance(results[0], analytics.ODMtd)

    try:
        list(source.iter_direct_related(relation, analytics.Mtd))
    except TypeError as error:
        assert "get_mtd_type" in str(error), review
    else:
        pytest.fail(review)

    # A filter class need not match the source's concrete type (so type[Self] is wrong).
    ok, classification = meta.add_one_cls_mtd(0.8, GLib.quark_from_string("label"))
    assert ok and classification is not None
    assert meta.set_relation(relation, source.id, classification.id)
    results = list(source.iter_direct_related(relation, analytics.ClsMtd))
    assert [item.id for item in results] == [classification.id]
    assert isinstance(results[0], analytics.ClsMtd)
