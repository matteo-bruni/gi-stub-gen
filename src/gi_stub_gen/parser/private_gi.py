"""Build the deliberately bounded internal API through normal schema rendering."""

import ast
from types import ModuleType

from gi_stub_gen.overrides.private_gi import FLAG_CLASSES, FUNCTIONS, INFO_METHODS, OTHER_METHODS
from gi_stub_gen.schema.builtin_function import (
    ArgKind,
    BuiltinFunctionArgumentSchema,
    BuiltinFunctionSchema,
    TypeVarSchema,
)
from gi_stub_gen.schema.class_ import ClassFieldSchema, ClassSchema
from gi_stub_gen.schema.module import ModuleSchema


def _function(signature: str, owner: object) -> BuiltinFunctionSchema:
    static = signature.startswith("@")
    node = ast.parse(f"def {signature.lstrip('@')}: ...").body[0]
    assert isinstance(node, ast.FunctionDef)
    if not hasattr(owner, node.name):
        raise RuntimeError(f"Private PyGObject API changed: {owner}.{node.name}")
    params = []
    positional = node.args.posonlyargs + node.args.args
    defaults = [None] * (len(positional) - len(node.args.defaults)) + list(node.args.defaults)
    entries = [
        (arg, ArgKind.POSITIONAL_ONLY if i < len(node.args.posonlyargs) else ArgKind.POSITIONAL_OR_KEYWORD, defaults[i])
        for i, arg in enumerate(positional)
    ]
    if node.args.vararg:
        entries.append((node.args.vararg, ArgKind.VAR_POSITIONAL, None))
    entries.extend(
        (arg, ArgKind.KEYWORD_ONLY, default) for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults)
    )
    if node.args.kwarg:
        entries.append((node.args.kwarg, ArgKind.VAR_KEYWORD, None))
    for arg, kind, default in entries:
        params.append(
            BuiltinFunctionArgumentSchema(
                name=arg.arg,
                type_hint_name=ast.unparse(arg.annotation) if arg.annotation else "object",
                type_hint_namespace=None,
                kind=kind,
                default_value=ast.unparse(default) if default is not None else None,
                is_optional=False,
                line_comment=None,
            )
        )
    return BuiltinFunctionSchema(
        name=node.name,
        namespace="gi._gi",
        is_async=False,
        is_from_class=not isinstance(owner, ModuleType),
        is_classmethod=False,
        is_staticmethod=static,
        docstring=None,
        return_hint_name=ast.unparse(node.returns) if node.returns else "None",
        return_hint_namespace=None,
        return_is_optional=False,
        params=params,
    )


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
                python_methods=[_function(signature, runtime) for signature in signatures],
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
        builtin_function=[_function(signature, module) for signature in FUNCTIONS],
        callbacks=[],
        aliases=[],
    )
