"""Convert verified signatures into the same models used by runtime parsing."""
import ast
from types import ModuleType

from gi_stub_gen.schema.builtin_function import ArgKind, BuiltinFunctionArgumentSchema, BuiltinFunctionSchema, TypeVarSchema


def parse_signature(signature: str, owner: object, namespace: str) -> BuiltinFunctionSchema:
    """Parse one signature, checking the member exists without importing a module."""
    static = signature.startswith("@")
    node = ast.parse(f"def {signature.lstrip('@').strip()}: ...").body[0]
    assert isinstance(node, ast.FunctionDef)
    if not hasattr(owner, node.name):
        raise RuntimeError(f"PyGObject API changed: {owner}.{node.name}")
    positional = node.args.posonlyargs + node.args.args
    defaults = [None] * (len(positional) - len(node.args.defaults)) + list(node.args.defaults)
    entries = [(arg, ArgKind.POSITIONAL_ONLY if i < len(node.args.posonlyargs) else ArgKind.POSITIONAL_OR_KEYWORD, defaults[i])
               for i, arg in enumerate(positional)]
    if node.args.vararg:
        entries.append((node.args.vararg, ArgKind.VAR_POSITIONAL, None))
    entries.extend((arg, ArgKind.KEYWORD_ONLY, default) for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults))
    if node.args.kwarg:
        entries.append((node.args.kwarg, ArgKind.VAR_KEYWORD, None))
    params = [BuiltinFunctionArgumentSchema(
        name=arg.arg, type_hint_name=ast.unparse(arg.annotation) if arg.annotation else "object",
        type_hint_namespace=None, kind=kind, default_value=ast.unparse(default) if default is not None else None,
        is_optional=False, line_comment=None,
    ) for arg, kind, default in entries]
    return BuiltinFunctionSchema(
        name=node.name, namespace=namespace, is_async=False, is_from_class=not isinstance(owner, ModuleType),
        is_classmethod=bool(positional and positional[0].arg == "cls" and not static), is_staticmethod=static,
        docstring=None, return_hint_name=ast.unparse(node.returns) if node.returns else "None",
        return_hint_namespace=None, return_is_optional=False, params=params,
        method_type_vars=[TypeVarSchema(name=param.name, bound_hint_name=ast.unparse(param.bound) if param.bound else None)
                          for param in node.type_params if isinstance(param, ast.TypeVar)],
    )
