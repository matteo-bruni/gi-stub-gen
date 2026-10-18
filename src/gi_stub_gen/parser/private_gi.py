"""Build the deliberately bounded internal API through normal schema rendering."""

from types import ModuleType

from gi_stub_gen.overrides.private_gi import FLAG_CLASSES, FUNCTIONS, INFO_METHODS, OTHER_METHODS
from gi_stub_gen.schema.builtin_function import (
    TypeVarSchema,
)
from gi_stub_gen.schema.class_ import ClassFieldSchema, ClassSchema
from gi_stub_gen.schema.module import ModuleSchema
from gi_stub_gen.parser.declarations import parse_signature


def _field(name: str, annotation: str) -> ClassFieldSchema:
    return ClassFieldSchema(
        name=name,
        type_hint_name=annotation,
        type_hint_namespace=None,
        is_deprecated=False,
        deprecation_warnings=None,
        docstring=None,
        line_comment=None,
        may_be_null=False,
        is_readable=True,
        is_writable=True,
    )


def parse_private_gi(module: ModuleType) -> ModuleSchema:
    classes = []
    specs = {**INFO_METHODS, **OTHER_METHODS, **dict.fromkeys(FLAG_CLASSES, ())}
    for name, signatures in specs.items():
        runtime = getattr(module, name)
        bases = [base.__name__ for base in runtime.__bases__ if base.__name__ in specs]
        if name in FLAG_CLASSES:
            bases = ["type"]
        fields = (
            [_field(key, "typing.ClassVar[int]") for key in vars(runtime) if key.isupper()]
            if name in FLAG_CLASSES
            else []
        )
        if name == "Async":
            fields.append(_field("cancellable", "Gio.Cancellable").model_copy(update={"is_writable": False}))
        classes.append(
            ClassSchema(
                name=name,
                namespace="gi._gi",
                super=bases,
                allow_synthetic_props=False,
                type_vars=[TypeVarSchema(name="T")] if name == "Async" else [],
                docstring=None,
                props=[],
                fields=fields,
                methods=[],
                python_methods=[parse_signature(signature, runtime, "gi._gi") for signature in signatures],
                signals=[],
                extra=[],
                is_deprecated=False,
                required_gi_import=None,
                additional_required_imports={"GObject", "Gio", "typing", "contextvars"},
            )
        )
    return ModuleSchema(
        name="gi._gi",
        classes=classes,
        constant=[],
        enum=[],
        function=[],
        builtin_function=[parse_signature(signature, module, "gi._gi") for signature in FUNCTIONS],
        callbacks=[],
        aliases=[],
    )
