"""Specialize only callback call sites whose Python marshalling is verified."""

from gi_stub_gen.schema.function import FunctionSchema


from gi_stub_gen.overrides.callbacks import PRECISE_CALLBACKS


def specialize_callback(function: FunctionSchema, owner: str | None) -> None:
    if owner is None:
        return
    selection = PRECISE_CALLBACKS.get((function.namespace, owner, function.name))
    if selection is None:
        return
    callback_name, source = selection
    callback = next(cb for cb in function._gi_callbacks if cb.name == callback_name).model_copy(deep=True)
    # Keep the original Protocol for unverified call sites, with its existing fallback.
    callback.name += "WithData"
    callback.function.type_parameters = (["Source"] if source else []) + ["*UserData"]
    callback.function.positional_only = True
    for arg in callback.function.input_args:
        arg.is_optional = False
    data = callback.function.input_args[-1]
    data.is_variadic = True
    data.type_var_name = "*UserData"
    data.may_be_null = False
    if source:
        first = callback.function.input_args[0]
        first.type_var_name = "Source"
        first.may_be_null = False
    argument = next(arg for arg in function.args if arg.is_callback and arg.py_type_name == callback_name)
    argument.py_type_name = f"{callback.name}[{source + ', ' if source else ''}*UserData]"
    argument.type_hint_cb_return_name = None
    argument.type_hint_cb_return_namespace = None
    closure = next(arg for arg in function.args if arg.is_variadic)
    closure.type_var_name = "*UserData"
    closure.may_be_null = False
    closure.is_optional = False
    function.type_parameters = ["*UserData"]
    function._gi_callbacks.append(callback)
