# Manual API corrections

Use normal parsing when GI, GIR or Python annotations describe the exposed API.
Use `method_transforms` when a parsed method needs a small correction. Use a full
`methods` or `fields` definition when introspection cannot describe the member.
Keep these Python projections out of the runtime property/GStreamer catalog.

Interface inheritance is inferred from the runtime's direct Python bases, with
the same-name repository layer of Python overrides expanded in place. Keep
interfaces nominal and preserve the runtime's selected method when bases share
a name. For example, `Socket.condition_wait` has no timeout argument, although
`DatagramBased.condition_wait(socket, ...)` does. Do not add the interface's
signature as an overload of the bound Socket method. `super` still replaces
inferred bases; synthetic `Props` composition is handled separately by the parser.
These native collisions remain visible to stub checkers. Comments at the targeted
transforms explain the runtime choice; do not add blanket ignores or merge the
conflicting signatures. Consumers needing the other native entry point can call
the interface method explicitly, as in the Socket example above.

## Application rules

`ClassOverride` is a TypedDict, not another runtime model. `methods` and `fields`
replace or add members; `None` removes them. Full method replacements prevent
the Python fallback from being parsed. `super` replaces the inferred bases.

`init_factory` builds a constructor from the namespace (without `gi.repository.`)
and runtime class, replacing only `__init__` before generic adaptation. It must
return a fresh `FunctionSchema` named `__init__` and cannot coexist with a full
replacement/removal or transform of that method. Use it only for verified
wrappers whose constructor metadata can be recovered; generic `*args, **kwargs`
alone does not justify replacing a Python constructor. Factories run during
class parsing, never during registry import.

`method_transforms` receives a deep copy of the effective method: the Python
method when present, otherwise the GI method. It runs once before generic type
adaptation and must preserve the model kind and name. Missing/ambiguous targets,
incompatible input models and replacement/transform conflicts are errors.
Transform only the incorrect fields, preserving defaults, flags and docs.

Registry models, including enum support classes and the Property descriptor,
are copied deeply when inserted into a result. Do not mutate registry constants.
The required callback names in `REQUIRED_CALLBACKS` are resolved only during
module parsing, with that call's explicit `docs`; already discovered callbacks win.
Importing the registry must not perform GI lookups or parse callbacks.

## Evidence and limits

Unless stated otherwise, the following evidence was checked with PyGObject 3.56.3, GLib 2.80 and
GStreamer/gst-python 1.28.3 in the prepared devcontainer. These are observations,
not version gates; rerun runtime checks when dependencies change.

| Family | Reason and source |
|---|---|
| GObject.Object methods | PyGObject C method descriptors do not expose signatures to `inspect.signature`; explicit Python signatures remain necessary. Runtime member existence is tested. |
| GObject.GType fields/methods | C getset/method descriptors; fields and methods are checked against the installed GType. The `builtins.type` base is a typing projection, not a claim about native GType inheritance. |
| GObject.GBoxed.copy | C method with a subtype-preserving return represented by `Self`. |
| Gst.Fraction | Upstream class annotations already supply `num: int` and `denom: int`; the field overrides retain their documentation. Only `__mul__`, `__rmul__`, `__truediv__`, `__rtruediv__` and `__float__` are declared manually, matching the initialized runtime. The constructor is parsed from the Python class. The general special-method filter and numeric bases remain unchanged. |
| Gio.Task.return_value | GIR describes a GValue input, but `return_value(42)` followed by `propagate_value()` returns `(True, 42)`. Correct only the result argument to a marshalled Python payload. |
| Gio.DBusConnection.__init__ | Verified with PyGObject 3.58.1 / GLib 2.80: `gi.overrides.Gio._warn_init` forwards arguments and warns against direct construction, but exposes only `*args, **kwargs`. Reuse the property constructor builder and retain the warning. Prefer `new_sync` / `new_for_address_sync` or their asynchronous counterparts for initialized connections. |
| Gst.Structure.set_value | Installed gst-python annotates the Python override as `bool`; `set_value("answer", 42)` returns `None`. Correct only the return annotation. |
| GioUnix.InputStream/OutputStream.get_fd | PyGObject 3.58.1's bound wrappers return the native integer descriptor but lack return annotations. Preserve the bound signature and recover `int`; the interface's static entry point is unchanged. |
| Atk.Object.get_name/get_description | Atk 2.52.0 returns `None` for unset values on NoOpObject, although GI declares a non-null string. Mark only these two returns nullable. |
| Gtk.TreeViewColumn.set_cell_data_func | PyGObject 3.58.1's wrapper accepts one `func_data` and loses callback/return annotations. Preserve the parsed wrapper and docs; overload omitted data, typed data and callback removal with `None`. Renderer types use a bound, not a closed list of concrete GTK renderers. |
| GEnum/GFlags and their metaclasses | Model `IntEnum`/`IntFlag` behavior, runtime value metadata and PyGObject's implicit acceptance of enum classes as GType arguments. `_GEnumMeta`/`_GFlagsMeta` are stub-only support classes, not public runtime exports. |
| GObject.Property | Generic descriptor with overloads for class/instance access; this is static typing structure beyond the introspected runtime signature. |
| Required callbacks | ClosureMarshal, EqualFunc and EqualFuncFull are looked up through GIRepository when normal traversal has not found them; their signatures are parsed, not handwritten. |

Public `gi.repository.GIRepository.CallableInfo` exposes `get_n_args`/`get_arg`,
not `get_arguments`. Public `TypeInfo` does not expose `get_tag_as_string`.
Those helpers belong to PyGObject's internal info objects; the
`GIRepositoryCallableAdapter` normalizes the internal parsing interface without
adding them to the public GIRepository stubs.

The base build now generates a bounded `gi._gi` stub from `private_gi.py` through
the normal schemas/templates. Its C signatures are checked against PyGObject
3.58.1 sources; generation checks member presence. Recheck these declarations
on upgrades, including integer tag results and Async's omitted-callback behavior.
`callbacks.py` selects only the four verified call sites that use the precise
`WithData` Protocol variants; other sites retain their original Protocol/fallback.
`Gst.Bus.set_sync_handler` is checked with zero/multiple user-data values,
bound/callable/partial handlers and callback removal. Its signature still comes
from GI. Signal `connect` overloads correlate their extra arguments with the
handler through `UserData`; the emitter is always present, including signals
without native arguments. The dynamic-name fallback remains permissive, even
for a known literal signal. Installed-wheel tests also check the precise signal
overloads in isolation so that this fallback cannot hide incorrect declarations.
Checker limits remain: ty 0.0.89 misses user-data pack mismatches; Pyrefly 1.4.0
misses a completely omitted BusSyncHandler payload. Pyright 1.1.414 checks these
calls but rejects direct assignment to `BusSyncHandlerWithData[int, str]` with
spurious parameter-name errors. Prefer normal annotated functions passed to
`set_sync_handler`, whose inferred packs are checked correctly.
See [typing features and verification](../../../docs/Typing_features.md).

`ControlBinding.property_comments["name"]` documents a native inheritance
exception verified with GStreamer 1.28.3: `Object.name` is writable, but
`ControlBinding.name` is construct-only. Its getter has a local override
diagnostic suppression for Pyright, ty and Pyrefly; writes remain forbidden.
The runtime/consumer tests in `test_props_access.py` and `tests/typing/` retain
these constraints. Revisit the comment if the runtime flags or checker rules
change; never make this property writable merely to satisfy inheritance.

Tests must distinguish runtime members from typing-only support. Check registry
key/model name agreement, member existence, precedence, independent results,
runtime behavior and rendered signatures. Review generated diffs separately
from source refactoring; a correct runtime fix may intentionally change a stub.

The necessity tests for Task.return_value and Structure.set_value inspect the
uncorrected parser output. They deliberately fail when the known defect disappears
or changes, prompting review of the transform after dependency/parser upgrades.
Keep the runtime behavior tests when removing a redundant transform, and remove
its corresponding necessity test. These checks run against installed libraries;
they do not monitor upstream releases automatically.

`tests/test_consumer_corrections.py` applies the same necessity checks to the
GioUnix, Atk and TreeViewColumn transforms. Its GTK callback integration test
requires a display and skips explicitly otherwise; constructing TreeViewColumn
headlessly can crash GTK. Consumer fixtures cover callback arity, renderer and
payload types, bound/callable/partial handlers, reset, and nullable text getters.

`tests/test_dbus_connection.py` disables `init_factory` to check that normal
parsing still exposes the generic constructor. If upstream restores a precise
signature, removes its wrapper, or the parser learns to recover it, the test
fails with a request to review/remove the factory. A simulated upstream signature
fix verifies this guard. When the factory is no longer needed, remove its
necessity test and keep the constructor and runtime behavior checks.

Fraction tests initialize Gst in fresh processes and check its rendered constructor
with and without manual field definitions. Runtime arithmetic and the typed example
in `tests/apps/fraction.py` verify the five explicit methods. Check the example
against regenerated Gst stubs; previously installed stubs lack those operators.

## Python helpers and selected special methods (PyGObject 3.58.1)

`include_methods` extends the normal Python-member filter for one class. Use it
when a private/special method already has useful runtime annotations. Caps
includes `__getitem__`/`__len__`; Structure additionally includes `__setitem__`.
Their signatures are parsed from initialized gst-python, not copied into the
registry. Other classes retain the existing filter.

`python_gi.py` supplies signatures for unannotated public Python APIs: the seven
`gi` configuration/version functions, Signal/BoundSignal, Template/Callback/Child,
and the GLib asyncio helpers. `parser/python_gi.py` checks member existence,
retains inspected documentation, and uses the existing Pydantic/Jinja pipeline.
`parser/declarations.py` is also used by the bounded `_gi` declarations; it does
not discover arbitrary modules or run introspection at registry import.

Template.Child's widget type depends on the XML, so its factory returns Any.
Signal arguments remain dynamic. Neither helper introduces blanket module
fallbacks. Only base owns `_signalhelper.pyi` and `events.pyi`; GTK owns
`_gtktemplate.pyi`, avoiding a mandatory GTK import for base-only installations.

On PyGObject upgrades rerun `tests/test_parity_features.py` and the installed
consumers. In 3.58.1 `GLibTask.get_priority(self, priority)` requires an unused
argument: the stub preserves it and a necessity test requests review when its
signature changes. GLibEventLoop.__enter__ returns None. The policy's inherited
set_child_watcher raises NotImplementedError; it is represented explicitly
because typeshed marks that method abstract although the runtime class can be
instantiated. Child-watcher declarations are included only when present.
