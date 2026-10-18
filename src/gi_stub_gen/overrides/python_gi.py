"""Unannotated Python APIs, verified against PyGObject 3.58.1 source/runtime.

These declarations supplement Python inspection; they are not GI metadata.
Gst operators use include_methods and the runtime annotations instead.
"""

GI_FUNCTIONS = (
    "check_version(version: str | tuple[int, ...]) -> None",
    "require_version(namespace: str, version: str) -> None",
    "require_versions(requires: dict[str, str]) -> None",
    "get_required_version(namespace: str) -> str | None",
    "require_foreign(namespace: str, symbol: str | None = None) -> None",
    "get_option(name: str) -> bool",
    "disable_legacy_autoinit() -> None",
)

SIGNAL = (
    '__init__(self, name: str | typing.Callable[..., typing.Any] = "", func: typing.Callable[..., typing.Any] | None = None, flags: int = 1, return_type: type | GObject.GType | None = None, arg_types: collections.abc.Sequence[type | GObject.GType] | None = None, doc: str = "", accumulator: typing.Callable[..., typing.Any] | None = None, accu_data: object = None) -> None',
    "__get__(self, instance: None, owner: type | None = None) -> typing.Self",
    "__get__(self, instance: GObject.Object, owner: type | None = None) -> Signal.BoundSignal",
    "__call__(self, obj: typing.Callable[..., typing.Any]) -> typing.Self",
    "__call__(self, obj: GObject.Object, *args: object, **kargs: object) -> None",
    "copy(self, newName: str | None = None) -> typing.Self",
    "get_signal_args(self) -> tuple[int, type | GObject.GType | None, collections.abc.Sequence[type | GObject.GType], typing.Callable[..., typing.Any] | None, object]",
)
BOUND_SIGNAL = (
    "__init__(self, signal: Signal, gobj: GObject.Object) -> None",
    "__call__(self, *args: object, **kargs: object) -> typing.Any",
    "connect(self, callback: typing.Callable[..., typing.Any], *args: object, **kargs: object) -> int",
    "connect_detailed(self, callback: typing.Callable[..., typing.Any], detail: str, *args: object, **kargs: object) -> int",
    "disconnect(self, handler_id: int) -> None",
    "emit(self, *args: object, **kargs: object) -> typing.Any",
)
TEMPLATE = (
    "__init__(self, *, string: str | bytes) -> None",
    "__init__(self, *, filename: str) -> None",
    "__init__(self, *, resource_path: str) -> None",
    "from_file(cls, filename: str) -> typing.Self",
    "from_string(cls, string: str | bytes) -> typing.Self",
    "from_resource(cls, resource_path: str) -> typing.Self",
    "__call__[T: Gtk.Widget](self, cls: type[T]) -> type[T]",
)
TEMPLATE_CALLBACK = (
    "__init__(self, name: str | None = None) -> None",
    # CallThing is consumed by Template; the decorated method keeps its callable contract.
    "__call__[F: typing.Callable[..., typing.Any]](self, func: F) -> F",
)

EVENT_LOOP = (
    "__init__(self, main_context: GLib.MainContext | None = None) -> None",
    "__enter__(self) -> None",
    "__exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: types.TracebackType | None) -> None",
    "paused(self) -> contextlib.AbstractContextManager[None]",
    "running(self, quit_func: typing.Callable[[], object]) -> contextlib.AbstractContextManager[None]",
    "time(self) -> float",
    "stop(self) -> None",
    "run_forever(self) -> None",
    "close(self) -> None",
)
EVENT_POLICY = (
    "__init__(self) -> None",
    "__enter__(self) -> typing.Self",
    "__exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: types.TracebackType | None) -> typing.Literal[False]",
    "get_event_loop(self) -> GLibEventLoop",
    "get_event_loop_for_context(self, ctx: GLib.MainContext) -> GLibEventLoop",
    "new_event_loop(self) -> GLibEventLoop",
    "set_event_loop(self, loop: asyncio.AbstractEventLoop | None) -> None",
)
EVENT_TASK = (
    "set_priority(self, priority: int) -> None",
    # Upstream 3.58.1 accidentally requires this unused parameter. Recheck on upgrades.
    "get_priority(self, priority: object) -> int",
)
