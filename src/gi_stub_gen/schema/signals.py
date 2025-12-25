from gi_stub_gen.schema import BaseSchema
from gi_stub_gen.schema.function import FunctionArgumentSchema, FunctionSchema


class SignalSchema(BaseSchema):
    name: str | None
    name_unescaped: str | None
    namespace: str
    handler: FunctionSchema

    docstring: str | None
    """Documentation string for the signal. """

    run_first: bool
    """Signal runs before the default handler."""
    run_last: bool
    """Signal runs after the default handler."""
    run_cleanup: bool
    """Signal runs during cleanup phase."""
    no_recurse: bool
    """Signal does not recurse."""
    detailed: bool
    """Signal is detailed."""
    action: bool
    """Signal is an action."""
    no_hooks: bool
    """Signal has no hooks."""
    must_collect: bool
    """Signal must be collected."""
    is_deprecated: bool
    """Signal is deprecated."""

    @property
    def required_gi_imports(self) -> set[str]:
        gi_imports: set[str] = set()
        gi_imports.add("typing")
        # check arguments
        if self.handler.required_imports:
            gi_imports.update(self.handler.required_imports)
        return gi_imports

    @property
    def detailed_signal_type(self) -> str:
        if not self.name:
            return "str"
        return f'typing.Literal["{self.name}"]'

    def params(self, namespace: str) -> str:
        types_types: list[str] = []
        for arg in self.handler.args:
            if arg.direction in ("IN", "INOUT"):
                types_types.append(arg.type_hint(namespace))
        if len(types_types) > 0:
            # add typing.Self as first param
            types_types.insert(0, "typing_extensions.Self")
            return f"[{', '.join(types_types)}]"
        return "..."


def generate_notify_signal(
    namespace: str,
    signal_name: str,
    signal_name_unescaped: str,
    docstring: str | None,
):
    return SignalSchema(
        docstring=docstring,
        name=f"notify::{signal_name}",
        name_unescaped=f"notify::{signal_name_unescaped}",
        namespace=namespace,
        action=False,
        detailed=False,
        is_deprecated=False,
        must_collect=False,
        no_hooks=False,
        no_recurse=False,
        run_cleanup=False,
        run_first=False,
        run_last=False,
        handler=FunctionSchema(
            name=f"notify::{signal_name}",
            namespace=namespace,
            is_method=True,
            is_deprecated=False,
            deprecation_warnings=None,
            docstring=f"Signal emitted when the '{signal_name}' property changes.",
            args=[
                FunctionArgumentSchema(
                    direction="IN",
                    name="arg1",
                    namespace=namespace,
                    may_be_null=False,
                    is_optional=False,
                    is_callback=False,
                    get_array_length=-1,
                    is_deprecated=False,
                    is_caller_allocates=False,
                    tag_as_string="??",
                    line_comment=None,
                    py_type_name="ParamSpec",
                    py_type_namespace="GObject",
                    default_value=None,
                    is_pointer=False,
                ),
                FunctionArgumentSchema(
                    direction="IN",
                    name="arg2",
                    namespace=namespace,
                    may_be_null=False,
                    is_optional=False,
                    is_callback=False,
                    get_array_length=-1,
                    is_deprecated=False,
                    is_caller_allocates=False,
                    tag_as_string="??",
                    line_comment=None,
                    py_type_name="Any",
                    py_type_namespace="typing",
                    default_value=None,
                    is_pointer=False,
                ),
            ],
            is_callback=False,
            can_throw_gerror=False,
            is_async=False,
            is_constructor=False,
            is_getter=False,
            is_setter=False,
            may_return_null=False,
            return_hint="None",
            return_hint_namespace=None,
            skip_return=False,
            wrap_vfunc=False,
            line_comment=None,
            function_type="SignalInfo",
            is_overload=True,
        ),
    )


# def connect(self,
# detailed_signal: str, handler: Callable[..., Any], *args: Any) -> int: ...
DEFAULT_CONNECT = SignalSchema(
    docstring=None,
    name=None,
    name_unescaped=None,
    namespace="",
    action=False,
    detailed=False,
    is_deprecated=False,
    must_collect=False,
    no_hooks=False,
    no_recurse=False,
    run_cleanup=False,
    run_first=False,
    run_last=False,
    handler=FunctionSchema(
        name="connect",
        namespace="",
        is_method=True,
        is_deprecated=False,
        deprecation_warnings=None,
        docstring="Default signal handler. Connects a signal to a handler. Returns the handler ID.",
        args=[],
        is_callback=False,
        can_throw_gerror=False,
        is_async=False,
        is_constructor=False,
        is_getter=False,
        is_setter=False,
        may_return_null=False,
        return_hint="Any",
        return_hint_namespace="typing",
        skip_return=False,
        wrap_vfunc=False,
        line_comment=None,
        function_type="SignalInfo",
        is_overload=True,
    ),
)
