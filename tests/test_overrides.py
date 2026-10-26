from pathlib import Path
import subprocess
import sys
from types import ModuleType

from gi.repository import GIRepository, Gst, GObject, Gio
import pytest

from gi_stub_gen.adapter import GIRepositoryCallableAdapter
from gi_stub_gen.manager.gi_repo import GIRepo
from gi_stub_gen.parser.class_ import parse_class
from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.overrides import (
    CLASS_OVERRIDES,
    apply_field_overrides,
    apply_method_overrides,
    apply_method_transforms,
    get_super_override,
    validate_class_override,
)
from gi_stub_gen.overrides.class_.GObject.GBoxed import GBOXED_COPY
from gi_stub_gen.overrides.class_.GObject.GEnum import GENUM_SCHEMA
from gi_stub_gen.overrides.class_.GObject.GType import GTYPE_NAME
from gi_stub_gen.overrides.class_.GObject.Object import OBJECT_GET_PROPERTY
from gi_stub_gen.parser.module import parse_module
from gi_stub_gen.schema.function import CallbackSchema
from gi_stub_gen.overrides.types import MethodSchema
from gi_stub_gen.parser.python_function import parse_python_function
from gi_stub_gen.parser.function import parse_function
from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema
from gi_stub_gen.manager.template import TemplateManager


def test_public_girepository_is_distinct_from_pygobject_info():
    repo = GIRepo()
    repo.require("GIRepository", "3.0")
    repo.require("Gst", "1.0")
    for cls, expected, absent in (
        (GIRepository.CallableInfo, {"get_n_args", "get_arg"}, {"get_arguments"}),
        (GIRepository.TypeInfo, {"get_tag"}, {"get_tag_as_string"}),
    ):
        parsed, _ = parse_class("gi.repository.GIRepository", cls)
        assert parsed is not None
        methods = {method.name for method in parsed.methods}
        assert expected <= methods
        assert not absent & methods
        assert all(hasattr(cls, name) for name in expected)
        assert all(not hasattr(cls, name) for name in absent)

    internal = Gst.Element.query_position
    assert hasattr(internal, "get_arguments")
    assert not hasattr(internal, "get_n_args")
    assert not hasattr(internal, "get_arg")
    assert hasattr(getattr(internal, "get_arguments")()[0].get_type_info(), "get_tag_as_string")

    raw = repo.raw.find_by_name("Gst", "version")
    assert isinstance(raw, GIRepository.FunctionInfo)
    adapter = GIRepositoryCallableAdapter(raw)
    assert len(adapter.get_arguments()) == getattr(raw, "get_n_args")()
    assert adapter.get_arguments()[0].get_type().get_tag_as_string() == "guint32"


def test_replacements_add_remove_and_do_not_share_models(monkeypatch):
    monkeypatch.setitem(
        CLASS_OVERRIDES,
        "Test",
        {
            "Sample": {
                "methods": {"get_property": OBJECT_GET_PROPERTY, "copy": GBOXED_COPY, "removed": None},
                "fields": {"name": GTYPE_NAME, "removed": None},
                "super": ["Base"],
            },
        },
    )
    original = OBJECT_GET_PROPERTY.model_copy(deep=True)
    removed = GBOXED_COPY.model_copy(update={"name": "removed"})
    methods = apply_method_overrides([original, removed], "Test", "Sample")
    assert [method.name for method in methods] == ["get_property", "copy"]
    methods[0].args[0].name = "changed"
    fresh = apply_method_overrides([], "Test", "Sample")
    assert fresh[0].args[0].name == OBJECT_GET_PROPERTY.args[0].name == original.args[0].name == "property_name"

    removed_field = GTYPE_NAME.model_copy(update={"name": "removed"})
    fields = apply_field_overrides([removed_field, GTYPE_NAME], "Test", "Sample")
    assert [field.name for field in fields] == ["name"]
    fields[0].type_hint_name = "changed"
    assert apply_field_overrides([], "Test", "Sample")[0].type_hint_name == GTYPE_NAME.type_hint_name == "str"
    bases = get_super_override("Test", "Sample")
    assert bases is not None
    bases.append("Changed")
    assert get_super_override("Test", "Sample") == ["Base"]


def test_registry_validation():
    for namespace, classes in CLASS_OVERRIDES.items():
        for name, config in classes.items():
            validate_class_override(namespace, name, config)
    with pytest.raises(ValueError, match="override model is named"):
        validate_class_override("Test", "Sample", {"methods": {"wrong": GBOXED_COPY}})
    with pytest.raises(ValueError, match="override model is named"):
        validate_class_override("Test", "Sample", {"fields": {"wrong": GTYPE_NAME}})
    with pytest.raises(ValueError, match="replacement and transform overlap"):
        validate_class_override(
            "Test",
            "Sample",
            {
                "methods": {"copy": None},
                "method_transforms": {"copy": lambda model: model},
            },
        )


@pytest.mark.parametrize("namespace", CLASS_OVERRIDES)
def test_runtime_override_members_exist(namespace):
    import importlib

    if namespace == "gi.repository.GstAnalytics":
        module = pytest.importorskip(namespace, exc_type=ImportError)
    else:
        module = importlib.import_module(namespace)
    for name, config in CLASS_OVERRIDES[namespace].items():
        cls = getattr(module, name)
        for method_name, replacement in config.get("methods", {}).items():
            assert hasattr(cls, method_name) == (replacement is not None), (namespace, name, method_name)
        for method_name in config.get("method_transforms", {}):
            assert hasattr(cls, method_name), (namespace, name, method_name)
    # Synthetic enum metaclasses and the generic Property descriptor are typing
    # models, not additional runtime members in CLASS_OVERRIDES.


def test_manual_classes_are_independent(monkeypatch):
    import gi_stub_gen.overrides as overrides

    monkeypatch.setattr(overrides, "REQUIRED_CALLBACKS", {})
    module = ModuleType("gi.repository.GObject")
    setattr(module, "GEnum", GObject.GEnum)
    setattr(module, "GFlags", GObject.GFlags)
    first, _ = parse_module(module)
    before = first.model_dump()
    for cls in first.classes:
        cls.super.append("Changed")
        if cls.fields:
            cls.fields[0].type_hint_name = "Changed"
        if cls.methods:
            cls.methods[0].return_hint = "Changed"
        if cls.python_methods:
            cls.python_methods[0].params[0].name = "changed"
    assert parse_module(module)[0].model_dump() == before


def test_importing_overrides_does_not_discover_callbacks():
    subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from unittest.mock import patch
from gi_stub_gen.manager.gi_repo import GIRepo
assert 'gi_stub_gen.overrides' not in sys.modules
with patch.object(GIRepo, 'find_callable', side_effect=AssertionError('lookup during import')):
    import gi_stub_gen.overrides
assert 'gi_stub_gen.parser.function' not in sys.modules
assert 'gi_stub_gen.parser.class_' not in sys.modules
""",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_required_callbacks_use_current_docs_and_preserve_discovered_callbacks(monkeypatch):
    import gi_stub_gen.adapter as adapter
    import gi_stub_gen.parser.module as module_parser

    real_get = adapter.get_callback_schema
    calls: list[tuple[str, str, GIRDocs | None]] = []

    def record(namespace: str, name: str, docs: GIRDocs | None = None) -> CallbackSchema:
        calls.append((namespace, name, docs))
        return real_get(namespace, name, docs)

    monkeypatch.setattr(adapter, "get_callback_schema", record)
    for namespace, names in (("GLib", ["EqualFunc", "EqualFuncFull"]), ("GObject", ["ClosureMarshal"])):
        GIRDocs.reset()
        docs = GIRDocs()
        gir = next(
            path
            for folder in ("/usr/share/gir-1.0", "/usr/lib/x86_64-linux-gnu/gir-1.0")
            if (path := Path(folder) / f"{namespace}-2.0.gir").exists()
        )
        assert docs.load(gir)
        module = ModuleType(f"gi.repository.{namespace}")
        calls.clear()
        parsed, _ = parse_module(module, docs=docs)
        assert calls == [(namespace, name, docs) for name in names]
        assert [callback.name for callback in parsed.callbacks] == names
        calls.clear()
        parse_module(module, docs=None)
        assert calls == [(namespace, name, None) for name in names]

    existing = real_get("GLib", "EqualFunc")
    existing.originated_from = {"already discovered"}
    module = ModuleType("gi.repository.GLib")
    setattr(module, "sample", object())
    monkeypatch.setattr(
        module_parser, "parse_class", lambda *args, **kwargs: (GENUM_SCHEMA.model_copy(deep=True), [existing])
    )
    calls.clear()
    parsed, _ = parse_module(module)
    assert [(ns, name) for ns, name, _ in calls] == [("GLib", "EqualFuncFull")]
    assert next(cb for cb in parsed.callbacks if cb.name == "EqualFunc").originated_from == {"already discovered"}


def test_transform_prefers_python_once_and_does_not_mutate_inputs(monkeypatch):
    class Sample:
        def copy(self, value: int = 3) -> int:
            """Keep this documentation."""
            return value

    python = parse_python_function(Sample.copy, "Test", from_class=Sample)
    assert python is not None
    gi = GBOXED_COPY.model_copy(deep=True)
    calls = []

    def transform(method: MethodSchema) -> MethodSchema:
        calls.append(method)
        assert isinstance(method, BuiltinFunctionSchema)
        method.return_hint_name = "str"
        return method

    monkeypatch.setitem(CLASS_OVERRIDES, "Test", {"Sample": {"method_transforms": {"copy": transform}}})
    methods, python_methods = apply_method_transforms([gi], [python], "Test", "Sample")
    assert len(calls) == 1 and calls[0] is python_methods[0]
    assert methods[0].is_overridden and not gi.is_overridden
    assert python_methods[0].render_return_annotation("Test") == "str"
    assert python.render_return_annotation("Test") == "int"
    assert python_methods[0].params == python.params
    assert python_methods[0].params is not python.params
    assert python_methods[0].docstring == python.docstring

    def gi_transform(method: MethodSchema) -> MethodSchema:
        method.docstring = "GI selected"
        return method

    monkeypatch.setitem(CLASS_OVERRIDES, "Test", {"Sample": {"method_transforms": {"copy": gi_transform}}})
    methods, _ = apply_method_transforms([gi], [], "Test", "Sample")
    assert methods[0].docstring == "GI selected" and gi.docstring != "GI selected"


def test_transforms_reject_missing_ambiguous_or_incompatible_targets(monkeypatch):
    monkeypatch.setitem(CLASS_OVERRIDES, "Test", {"Sample": {"method_transforms": {"copy": lambda method: method}}})
    for candidates in ([], [GBOXED_COPY, GBOXED_COPY]):
        with pytest.raises(ValueError, match="exactly one effective method"):
            apply_method_transforms(candidates, [], "Test", "Sample")

    def renamed(method: MethodSchema) -> MethodSchema:
        method.name = "wrong"
        return method

    monkeypatch.setitem(CLASS_OVERRIDES, "Test", {"Sample": {"method_transforms": {"copy": renamed}}})
    with pytest.raises(TypeError, match="preserve the GI model kind and name"):
        apply_method_transforms([GBOXED_COPY], [], "Test", "Sample")

    from gi_stub_gen.overrides.class_.Gio.Task import transform_return_value
    from gi_stub_gen.overrides.class_.Gst.Structure import transform_set_value

    with pytest.raises(ValueError, match="argument named result"):
        transform_return_value(GBOXED_COPY.model_copy(deep=True))
    with pytest.raises(TypeError, match="Python callable"):
        transform_set_value(GBOXED_COPY.model_copy(deep=True))


def test_full_replacement_still_excludes_python_method(monkeypatch):
    replacement = GBOXED_COPY.model_copy(update={"name": "set_value"}, deep=True)
    monkeypatch.setitem(CLASS_OVERRIDES["gi.repository.Gst"], "Structure", {"methods": {"set_value": replacement}})
    parsed, _ = parse_class("gi.repository.Gst", Gst.Structure)
    assert parsed is not None
    assert not any(method.name == "set_value" for method in parsed.python_methods)
    result = next(method for method in parsed.methods if method.name == "set_value")
    assert result == replacement and result is not replacement


def test_structure_set_value_still_needs_return_correction():
    # Parse the installed Python function directly, before manual transforms.
    original = parse_python_function(Gst.Structure.set_value, "Gst", from_class=Gst.Structure)
    assert original is not None, "Gst.Structure.set_value parsing changed; review transform_set_value"
    annotation = original.render_return_annotation("Gst")
    assert annotation != "None", (
        "Gst.Structure.set_value already has the correct return annotation without the override; "
        "review and remove transform_set_value if runtime behavior still agrees"
    )
    assert annotation == "bool", (
        f"Gst.Structure.set_value now returns annotation {annotation!r}; "
        "review transform_set_value against the installed library"
    )


def test_task_return_value_still_needs_payload_correction():
    # Include GIR metadata so improvements in either the library or parser count.
    docs = GIRDocs()
    assert docs.load(Path("/usr/share/gir-1.0/Gio-2.0.gir"))
    original = parse_function(Gio.Task.return_value, None, docs=docs)
    assert original is not None, "Gio.Task.return_value parsing changed; review transform_return_value"
    result = next((arg for arg in original.args if arg.name == "result"), None)
    assert result is not None, "Gio.Task.return_value result argument changed; review transform_return_value"
    annotation = result.render_type_annotation("Gio")
    assert annotation != "typing.Any", (
        "Gio.Task.return_value already exposes a Python payload without the override; "
        "review transform_return_value, including is_marshaled_gvalue_payload, before removing it"
    )
    assert annotation == "GObject.Value | None", (
        f"Gio.Task.return_value now accepts annotation {annotation!r}; "
        "review transform_return_value against the installed library"
    )


def test_targeted_corrections_keep_defaults_docs_and_runtime_behavior():
    docs = GIRDocs()
    assert docs.load(Path("/usr/share/gir-1.0/Gio-2.0.gir"))
    original = parse_function(Gio.Task.return_value, None, docs=docs)
    assert original is not None
    parsed, _ = parse_class("gi.repository.Gio", Gio.Task, docs=docs)
    assert parsed is not None
    corrected = next(method for method in parsed.methods if method.name == "return_value")
    assert corrected.docstring == docs.get_class_method_docstring("Task", "return_value")
    assert corrected.docstring
    assert corrected.args[0].default_value == original.args[0].default_value
    assert corrected.args[0].may_be_null == original.args[0].may_be_null
    assert corrected.args[0].is_marshaled_gvalue_payload
    assert corrected.render_parameter_list("Gio") == "self, result: typing.Any = None"
    task = Gio.Task.new(None, None, None, None)
    assert task.return_value(42) is None
    assert task.propagate_value() == (True, 42)

    GIRDocs.reset()
    docs = GIRDocs()
    assert docs.load(Path("/usr/share/gir-1.0/Gst-1.0.gir"))
    parsed, _ = parse_class("gi.repository.Gst", Gst.Structure, docs=docs)
    assert parsed is not None
    python = next(method for method in parsed.python_methods if method.name == "set_value")
    gi_doc = docs.get_class_method_docstring("Structure", "set_value")
    assert gi_doc and python.docstring and gi_doc in python.docstring
    assert python.render_parameter_list("Gst") == ["self", "key: str", "value: typing.Any"]
    assert python.render_return_annotation("Gst") == "None"
    TemplateManager.set_module_name("Gst")
    assert parsed.render_stub().count("def set_value(") == 1
    structure = Gst.Structure.new_empty("test")
    assert structure.set_value("answer", 42) is None
    assert structure.get_value("answer") == 42
