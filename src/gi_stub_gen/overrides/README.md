# Manual API corrections

Use normal parsing when GI, GIR or Python annotations describe the exposed API.
Use `method_transforms` when a parsed method needs a small correction. Use a full
`methods` or `fields` definition when introspection cannot describe the member.
Keep these Python projections out of the runtime property/GStreamer catalog.

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
| GEnum/GFlags and their metaclasses | Model `IntEnum`/`IntFlag` behavior, runtime value metadata and PyGObject's implicit acceptance of enum classes as GType arguments. `_GEnumMeta`/`_GFlagsMeta` are stub-only support classes, not public runtime exports. |
| GObject.Property | Generic descriptor with overloads for class/instance access; this is static typing structure beyond the introspected runtime signature. |
| Required callbacks | ClosureMarshal, EqualFunc and EqualFuncFull are looked up through GIRepository when normal traversal has not found them; their signatures are parsed, not handwritten. |

Public `gi.repository.GIRepository.CallableInfo` exposes `get_n_args`/`get_arg`,
not `get_arguments`. Public `TypeInfo` does not expose `get_tag_as_string`.
Those helpers belong to PyGObject's internal info objects; the
`GIRepositoryCallableAdapter` normalizes the internal parsing interface without
adding them to the public GIRepository stubs.

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
