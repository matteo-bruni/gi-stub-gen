# AGENTS.md

## Repository workflow

This repository generates Python type stubs for GObject Introspection (GI)
packages. The files under `stubs/` are generated, versioned artifacts: inspect
and review them, but do not fix them by hand. Fix the generator and regenerate
the affected package instead.

### Generator architecture

The CLI in `src/gi_stub_gen/cli/gi_stub_gen.py` loads live GI modules and GIR
documentation. Code in `src/gi_stub_gen/parser/` converts the inspected API into
the Pydantic models in `src/gi_stub_gen/schema/`; those models are rendered by
the Jinja templates in `src/gi_stub_gen/templates/`, and
`src/gi_stub_gen/package.py` writes the stub packages. Use
`src/gi_stub_gen/overrides/` for deliberate library-specific exceptions that
cannot be inferred reliably.

Keep complex construction in `parser/`; models own data, invariants and pure
calculations. Stub text methods use `render_*` names and may remain in the stub
models. Pass `docs` explicitly (`None` means no documentation); progress callbacks
must not require Rich or configured logging handlers. Preserve the metadata's
origin namespace separately from the rendering destination, including nested
types and their imports.

Keep serializable runtime descriptors independent of GI, Rich and Jinja.
`parser/gobject.py` handles generic runtime GType/ParamSpec inspection;
GStreamer-specific logic belongs in `parser/gstreamer.py`. These descriptors
describe native metadata, not PyGObject signatures or executable configuration.
Do not use OpenAPI as their common intermediate representation. Use GType names,
not process-local numeric IDs, for serialized references. The catalog's `types`
contains referenced enum/flags definitions only, including shared/inherited ones.
Preserve unavailable/unsupported defaults explicitly; do not serialize arbitrary
`repr` values or infer setter validity from nullability/defaults. Pad templates
and caps describe possibilities, not instantiated pads or negotiated caps.

Resolve Python property types before collecting runtime enum metadata: reading
`ParamSpec.enum_class` can register wrappers and change later type resolution.
Keep that ordering and its GstBadAudio regression test. Initialize Gst before
inspecting its Python overrides. Native metadata and public GIRepository classes
are not interchangeable with PyGObject's internal info objects.

Prefer normal parsing, then a targeted transform, then a complete override only
when necessary; follow `src/gi_stub_gen/overrides/README.md`. Preserve discovered
docs/defaults, deep-copy registry models, avoid GI lookup at registry import, and
retain tests that detect when upstream makes an override unnecessary.

For refactors, compare regenerated file inventories and contents against a fresh
baseline in the same environment, including wheel payloads and package metadata.
Ignore only packaging dates and ZIP timestamps; investigate missing files and
review the GObject comparison report separately.

### PyGObject upgrades

Whenever PyGObject is upgraded, recheck the private `gi._gi.enum_add` and
`gi._gi.flags_add` calls in `src/gi_stub_gen/parser/gobject.py`. These create
Python wrappers for registered native enum/flags types without a wrapper;
their signatures and behavior are not a public compatibility guarantee.
Compare their use with the installed PyGObject `ParamSpecEnum.enum_class` and
`ParamSpecFlags.flags_class` implementations. In the running devcontainer,
rerun `tests/test_gstreamer_catalog.py` and `tests/test_property_descriptors.py`,
including fresh-process checks for initially missing wrappers (for example
`GstAutoplugSelectResult` and `GstVideoTestSrcPattern`). Verify enum/flags values
and serialization, and check generated stubs for unintended changes: wrapper
creation changes `gtype.pytype` within the process. Keep catalog verification
and stub generation in separate processes.

Also rerun `tests/test_dbus_connection.py` and `tests/test_overrides.py` on
PyGObject upgrades. The DBusConnection necessity test disables `init_factory`
and checks that the uncorrected constructor is still `self, *args, **kwargs`.
If it fails because upstream or the parser now exposes a precise signature,
review/remove the factory and its necessity test, retaining the constructor
and runtime behavior checks. Do not merely update the expectation to keep a
redundant override. These tests check installed libraries, not upstream releases
automatically.

Recheck `overrides/private_gi.py`, `tests/test_private_gi_stub.py` and
`tests/test_async.py` on PyGObject upgrades. `_gi` coverage is deliberately
bounded; do not add a catch-all `__getattr__` or alias public GObject bases to it.
Async overloads require finish metadata, not a name suffix; omitted callback
and explicit `None` have different returns. Keep constructors and hidden Python
wrappers excluded until verified. Compare Props access constraints and callback
`TypeVarTuple` consumers with both checkers. The `ty-misses:` fixture markers
record known false negatives, not permission to ignore new errors; revisit them
on checker updates. See `docs/Typing_features.md` for evidence and inherited
property conflicts that must not be hidden by weakening types.

### Development loop

1. Start with `git status --short` and preserve all pre-existing user changes.
2. Locate the incorrect generated declaration under `stubs/`, then reproduce
   the generator behavior with a focused test under `tests/` when practical.
3. Change the generator under `src/gi_stub_gen/`, not the generated `.pyi` file.
4. Run the focused test while iterating, for example
   `uv run --group gst --locked pytest tests/test_gst.py -q`, followed by `just test`.
5. Regenerate only the affected package first:
   - `just build-base`
   - `just build-graphics-core`
   - `just build-gst`
   - `just build-gtk`
6. Inspect the resulting diff under `stubs/`. Generated changes are part of the
   implementation and must match the intended generator change.
7. Before handing off a generator change, run `just build` when the environment
   provides all required GI libraries, then run `just ty`. `just build`
   regenerates every stub package and runs the test suite.

### Required source type checking

Every Python code change must include a type check of the affected source code
using Pyright or ty, in the running devcontainer as the devcontainer user from `/code` with
the `/opt/uv/venv` environment. Check the full generator when changing shared
models, parsers or their interfaces. For example:

```sh
just check-types
```

Check changed tests and examples as well when applicable. Compare diagnostics
before and after the change, fix new errors, and report any remaining pre-existing
errors. Do not suppress errors or weaken checker settings just to obtain a pass.
`just ty` checks generated files under `stubs/`; it does **not** replace checking
the generator sources. Passing runtime tests or producing identical stubs does
not establish that the modified source code is correctly typed.

### Installed stubs and checker updates

After changing generation or packaging, run `just test-installed-stubs` after
regeneration. Unlike the unit tests in `just test`, this explicitly selected
integration test builds all four wheels, installs them into a temporary venv,
and checks positive/negative consumers with both checkers. It checks shared
marker ownership, partial-package fallback, and addon uninstall/reinstall.
It does not reinstall packages into the development venv. Keep expected-invalid
fixtures as `.py.txt` files so source checking does not treat them as regressions.
Only base owns `gi-stubs/repository/__init__.pyi` and `gi-stubs/py.typed` with
`partial`; addon wheels must not duplicate them.

`justfile` pins the verified ty and Pyright versions. Revisit ty frequently,
especially before releases or when investigating a checker limitation; the pin
is a reproducible baseline, not a long-term freeze. To update, record the old
`just ty` diagnostics, change `ty_version`, then run `just check-types`,
`just test-installed-stubs` and `just ty`. Compare diagnostic locations/rules,
not only totals, and document changed inference or resolved checker limitations
in `docs/Typing_diagnostics_analysis.md`. Use the same process for Pyright's pin.
Do not weaken useful stub types or add blanket ignores to accommodate a new
checker. ty remains a secondary, evolving checker; its full-stub diagnostics
are not all established API defects. Neither checker replaces a direct Pylance
completion/hover check.

Pyrefly is an optional third checker, pinned by `pyrefly_version` in `justfile`.
Use `just check-types-pyrefly` for sources/tests/examples, `just pyrefly` for
generated stubs, or `just pyrefly-check <paths>` for a focused check. These use
the project interpreter without installing Pyrefly into the development venv.
Keep its diagnostics visible; it does not replace the required Pyright/ty checks
or constitute a passing gate until its findings have been assessed.

This devcontainer already contains GStreamer and its Python bindings, so use
`just build-gst` directly. `just build-gst-in-container` is for building from a
host that does not already provide the prepared GStreamer environment.

GStreamer builds discover available typelibs and skip modules that cannot be
imported. The build scripts use `--overwrite`, which removes existing `.pyi`
files that are no longer generated. An incomplete environment can therefore
cause unrelated stub deletions; check these against the available GI libraries
before including them in a change.

All build recipes accept `--debug`, but it adds very verbose diagnostics to the
generated stubs and disables the progress display. Use it only for diagnosis
and regenerate without it before handing off changes.

`just build-base` (and therefore `just build`) also runs `just diff-gobject`,
which can update `docs/GObject_diff.md` even when only its generation date has
changed. The comparison recipes access the upstream stub over the network.
Review these report changes separately from semantic stub changes.

After generation, check `git status --short` and the relevant `git diff` again.
Do not discard or overwrite unrelated changes that were already present.

Behavioral guidelines below reduce common LLM coding mistakes. Apply them
together with the project-specific instructions above.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial
tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## Cost control - Codex credit usage

Before starting or continuing a task, check `/status` when practical. If the remaining included Codex time is close to zero, or if continuing may start using paid workspace credits, pause and ask me for confirmation before proceeding. Do not ask for confirmation when the included time is clearly still available.
