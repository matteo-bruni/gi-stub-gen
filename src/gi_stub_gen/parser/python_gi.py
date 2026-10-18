"""Public Python helpers without GIR: inspected members plus verified signatures."""
import inspect
import sys
from collections import Counter
from types import ModuleType

from gi_stub_gen.overrides import python_gi as declarations
from gi_stub_gen.parser.declarations import parse_signature
from gi_stub_gen.parser.python_function import parse_python_function
from gi_stub_gen.schema.builtin_function import BuiltinFunctionSchema, TypeVarSchema
from gi_stub_gen.schema.class_ import ClassSchema
from gi_stub_gen.schema.module import ModuleSchema


def _methods(owner: type | ModuleType, namespace: str, signatures: tuple[str, ...]) -> list[BuiltinFunctionSchema]:
    methods = []
    for signature in signatures:
        declared = parse_signature(signature, owner, namespace)
        runtime = getattr(owner, declared.name)
        parsed = parse_python_function(runtime, namespace, declared.name, owner if isinstance(owner, type) else None)
        declared.docstring = parsed.docstring if parsed is not None else inspect.getdoc(runtime)
        methods.append(declared)
    counts = Counter(method.name for method in methods)
    for method in methods:
        method.is_overload = counts[method.name] > 1
    return methods


def _class(owner: type, namespace: str, bases: list[str], signatures: tuple[str, ...],
           imports: set[str], *, type_vars: list[TypeVarSchema] | None = None,
           nested: list[ClassSchema] | None = None) -> ClassSchema:
    return ClassSchema(
        name=owner.__name__, namespace=namespace, super=bases,
        docstring=inspect.getdoc(owner), allow_synthetic_props=False,
        props=[], fields=[], methods=[], python_methods=_methods(owner, namespace, signatures),
        signals=[], extra=[], is_deprecated=False, required_gi_import=None,
        additional_required_imports=imports, type_vars=type_vars or [], nested_classes=nested or [],
    )


def apply_gi_function_signatures(module: ModuleType, schema: ModuleSchema) -> None:
    """Replace only unannotated public module functions, preserving discovered docs."""
    corrections = {method.name: method for method in _methods(module, module.__name__, declarations.GI_FUNCTIONS)}
    schema.builtin_function = [corrections.get(method.name, method) for method in schema.builtin_function]


def parse_python_helper(module: ModuleType) -> ModuleSchema:
    """Generate bounded helper modules using the normal class/function renderers."""
    namespace = module.__name__
    if namespace == "gi._signalhelper":
        imports = {"typing", "collections.abc", "GObject"}
        bound = _class(module.Signal.BoundSignal, namespace, ["str"], declarations.BOUND_SIGNAL, imports)
        signal = _class(module.Signal, namespace, ["str"], declarations.SIGNAL, imports, nested=[bound])
        classes = [signal]
    elif namespace == "gi._gtktemplate":
        imports = {"typing", "Gtk"}
        callback = _class(module.Template.Callback, namespace, [], declarations.TEMPLATE_CALLBACK, imports)
        template = _class(module.Template, namespace, [], declarations.TEMPLATE, imports, nested=[callback])
        # Template replaces Child markers with widgets whose class is defined in XML.
        template.python_methods.extend(_methods(module.Template, namespace, (
            "@Child(name: str | None = None, *, internal: bool = False) -> typing.Any",
        )))
        classes = [template]
    elif namespace == "gi.events":
        imports = {"asyncio", "typing", "types", "contextlib", "GLib"}
        base = "asyncio.ProactorEventLoop" if sys.platform == "win32" else "asyncio.SelectorEventLoop"
        loop = _class(module.GLibEventLoop, namespace, [base], declarations.EVENT_LOOP, imports)
        policy_signatures = declarations.EVENT_POLICY
        if hasattr(module.GLibEventLoopPolicy, "get_child_watcher"):
            policy_signatures += (
                "get_child_watcher(cls) -> asyncio.ThreadedChildWatcher",
                # The inherited Python method raises NotImplementedError, rather than being abstract at runtime.
                "set_child_watcher(self, watcher: asyncio.AbstractChildWatcher | None) -> typing.Never",
            )
        policy = _class(module.GLibEventLoopPolicy, namespace, ["asyncio.AbstractEventLoopPolicy"], policy_signatures, imports)
        task = _class(module.GLibTask, namespace, ["asyncio.Task[T]"], declarations.EVENT_TASK, imports,
                      type_vars=[TypeVarSchema(name="T")])
        classes = [loop, policy, task]
    else:
        raise ValueError(f"No Python helper declarations for {namespace}")
    return ModuleSchema(name=namespace, classes=classes, constant=[], enum=[], function=[], builtin_function=[], callbacks=[], aliases=[])
