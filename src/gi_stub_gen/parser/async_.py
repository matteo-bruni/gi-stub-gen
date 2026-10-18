"""Describe PyGObject awaitables without guessing async/finish name pairs."""

import gi._gi as GI

from gi_stub_gen.manager.gir_docs import GIRDocs
from gi_stub_gen.schema.function import FunctionSchema


def add_async_overloads(info: GI.FunctionInfo, function: FunctionSchema, docs: GIRDocs | None) -> None:
    if function.is_constructor or function.output or function.return_hint is not None:
        return
    callbacks = []
    cancellables = []
    for arg in info.get_arguments():
        argument_type = arg.get_type_info()
        if argument_type.get_tag() != GI.TypeTag.INTERFACE:
            continue
        interface = argument_type.get_interface()
        if interface is None or interface.get_namespace() != "Gio":
            continue
        if interface.get_name() == "AsyncReadyCallback":
            callbacks.append(arg.get_name())
        elif interface.get_name() == "Cancellable":
            cancellables.append(arg.get_name())
    if len(callbacks) != 1 or len(cancellables) != 1:
        return
    finish = info.get_finish_func()
    if finish is None or finish.equal(info) or finish.get_flags() & GI.FunctionInfoFlags.IS_CONSTRUCTOR:
        return
    callback = next((arg for arg in function.input_args if arg.name == callbacks[0]), None)
    if callback is None:
        return
    callback_index = function.args.index(callback)
    # Only the closure may follow the callback in this first implementation.
    if any(not arg.is_variadic for arg in function.args[callback_index + 1 :]):
        return

    from gi_stub_gen.parser.function import parse_callable

    result = parse_callable(finish, docs=docs, include_async=False)
    awaitable = function.model_copy(deep=True)
    awaitable.args = awaitable.args[:callback_index]
    awaitable.type_parameters = []
    awaitable.return_hint = f"Async[{result.render_return_annotation(function.namespace)}]"
    awaitable.return_hint_namespace = "gi._gi"
    awaitable.return_type_imports.update(result.required_imports)
    awaitable.may_return_null = False
    awaitable.is_async = False

    positional = function.model_copy(deep=True)
    positional.args[callback_index].is_required = True
    # Gio.AsyncReadyCallback is emitted by the base package.
    if positional.args[callback_index].line_comment == "type: ignore":
        positional.args[callback_index].line_comment = None
    positional.is_async = False

    keyword = positional.model_copy(deep=True)
    keyword.args = keyword.args[: callback_index + 1]
    keyword.args[-1].is_keyword_only = True
    keyword.args[-1].py_type_name = keyword.args[-1].py_type_name.replace(", *UserData", "")
    keyword.type_parameters = []
    function.overloads = [awaitable, positional, keyword]
