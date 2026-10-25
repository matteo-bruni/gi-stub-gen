# 📦 GI Stub Gen

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A modern, modular type hint generator for GObject Introspection (GI) libraries (GStreamer, GTK, Gio, etc.).

This tool inspects live libraries through `gi.repository` and generates Python `.pyi` stub files.

## Why another stub generator?

> [!WARNING]
> ⚠️ __Disclaimer__
> 
> I am not a GI/PyGObject expert. This project started as a learning exercise to understand the internals of GObject Introspection. Mistakes are possible, and feedback is highly appreciated!

I started this project to improve type hints and autocompletion for GStreamer Python development.

1.  **Architecture:** Parsers build Pydantic models, then rendering methods and Jinja templates produce the stubs.
2.  **Packaging:** Stub packages are generated and versioned before installation, with configurable namespace groupings.
3.  **Introspection:** Runtime inspection includes PyGObject overrides, while GIR files supply documentation.
4.  **Corrections:** Manual overrides live in the generator rather than in generated `.pyi` files.

## Features

-   **Versioning:** Generate stubs for the library versions available in the build environment.
-   **Docstrings:** Extract GIR documentation and translate C references to Python where supported.
-   **Deprecation:** Annotate detected deprecated APIs.
-   **Signals:** Generate `connect()` overloads for known signal signatures.
-   **Protocols:** Represent callbacks and interfaces with `typing.Protocol`.
-   **Properties:** Preserve `Props` completion with readable, writable and construct-only constraints.
-   **Async:** Generate awaitable overloads from verified GI finish metadata.
-   **Internal GI:** Include targeted `_gi` annotations without replacing public GObject definitions.

See [typing behavior and verification](docs/Typing_features.md) and the executable
[GStreamer pipeline example](examples/gstreamer_typed_pipeline.py).

Optional Pyrefly checks: `just check-types-pyrefly` for sources, tests and examples;
`just pyrefly` for generated stubs; `just pyrefly-check <paths>` for selected files.
The version is pinned in `justfile`; diagnostics remain visible and are not yet a passing gate.

---

## Getting Started

### Prerequisites

For development, use the devcontainer described below, which provides the system dependencies.
Outside the container, `PyGObject` requires system-level dependencies.

**On Ubuntu/Debian, outside the devcontainer:**
```bash
sudo apt install \
  build-essential \
  python3-dev \
  libcairo2-dev \
  libgirepository-2.0-dev \ 
  gir1.2-girepository-3.0 \
  gir1.2-glib-2.0-dev
```

### Installation & Development

This project uses `uv` for dependency management.

```bash
# Clone the repository
git clone https://github.com/matteo-bruni/gi-stub-gen.git
cd gi-stub-gen
```

### GStreamer Development Container

In VS Code, choose **Dev Containers: Reopen in Container** to use `ghcr.io/matteo-bruni/gstreamer:1.28.8-ubuntu.26.04-base-py-3.14-non-free`, published from [gstreamer-oci](https://github.com/matteo-bruni/gstreamer-oci).
The setup preserves `/opt/uv/venv` and installs the image's native wheels from `/opt/wheel`; select `/opt/uv/venv/bin/python` as the interpreter.
Outside the container, prepare compatible system libraries and bindings yourself; the [public binding indexes](https://matteo-bruni.github.io/gstreamer-oci/) require an explicit Ubuntu selection.

### Usage

Here an example to generate a stub for a specific library:

```bash
gst_version=`pkg-config --modversion gstreamer-1.0`
# Syntax: gi_stub_gen <LibraryName> <Version> > <Output.pyi>
uv run gi-stub-gen \
    gi.repository.Gst:1.0 \
    gi.repository.GstVideo:1.0 \
    --preload gi.repository.GioUnix:2.0 \
    --preload gi.repository.Gio:2.0 \
    --preload gi.repository.GObject:2.0 \
    --preload gi.repository.GIRepository:3.0 \
    --pkg-name gi-gst-stubs \
    --pkg-version $gst_version \
    --pkg-dependencies gi-base-stubs \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0
```
This generates stubs for the installed GStreamer version in the `stubs/` folder.
The generated stubs have a dependency on `gi-base-stubs`, which contains common types like `GObject` and `GLib`.
Providing the `--gir-folder` docstrings will be gathered from the corresponding `.gir` files and included in the stubs. If not provided, the stubs will be generated without docstrings. 

---

## Generated Stubs

Stub wheels are `py3-none-any` for Python 3.12+; available APIs still depend on native libraries and typelibs.
Public versions describe the verified recent API; suffixes such as `+glib2.80` identify a specific generation environment, not automatic GLib detection.
After publishing the index, select an older build explicitly with `pip install --extra-index-url https://matteo-bruni.github.io/gi-stub-gen/simple/ 'gi-base-stubs==3.58.1+glib2.80'`; otherwise installers prefer the higher local version.

You can find the generated output in the `stubs/` folder as an example. I have currently organized them into 4 packages based on an arbitrary grouping that seemed logical for dependency management.

> [!NOTE] 
> **Note:** This grouping is just my personal preference. The tool allows anyone to generate stubs with their own structure. Ideally, the maintainers of the respective libraries should generate and publish their own stubs.

| Package | Versioning | Contents |
| :--- | :--- | :--- |
| **`gi-base-stubs`** | **PyGObject + GLib** | **Core Infrastructure.**<br>Includes `GLib`, `GLibUnix` when available, `GObject`, `Gio`, `GioUnix`, `GModule`, `GIRepository`, `gi`, `gi._gi`, `gi.events`, and `gi._signalhelper`. |
| **`gi-graphics-core-stubs`** | **PyGObject + GLib + cairo** | **Graphics & Text.**<br>Includes `cairo`, `Pango`, `PangoCairo`, `HarfBuzz`, `freetype2`, `Graphene`. |
| **`gi-gtk-stubs`** | **PyGObject + GTK** | **UI Toolkit (GTK4).**<br>Includes `Gtk`, `Gdk`, `Gsk`, `GdkPixbuf`, `Atk`, and `gi._gtktemplate`. |
| **`gi-gst-stubs`** | **GStreamer** | **Multimedia (GStreamer + GES).**<br>Includes `Gst`, `GES`, and available GStreamer extension namespaces (e.g. `GstApp`, `GstAudio`, `GstVideo`, `GstWebRTC`), discovered from importable typelibs. |


To build all the stubs like `gi-base-stubs`, `gi-gtk-stubs`, `gi-graphics-core-stubs`, and `gi-gst-stubs`, you can run the provided shell scripts in the project root or use `just` commands:

```bash
just build
```
This will build all the stub packages and place them in the `stubs/` directory.
(or you can build individual packages using `just build-base`, `just build-gst`, etc.).
`just build-gst` also includes GStreamer Editing Services (`GES`) when its typelib is available.
Each build command accept a `--debug` flag to enable verbose output in the stubs (_beware! it is really verbose_) that also disable the progress bar, useful for debugging with gdb.

Package a verified build with `just release-wheels IMAGE@sha256:DIGEST --output dist/release --canonical`; omit `--canonical` for older environments and use `--revision N` for corrections.
For publication, use **Actions → Release gi-stub-gen** with `version`, then **Release GI stubs** with `generator_version`, `gstreamer_version`, `image_revision` (default `1`) and `revision` (`0` initially, `1` for `.post1`). Both workflows publish a release and refresh the shared Pages index; set **Settings → Pages → Source → GitHub Actions** and allow the generator workflow to push its version commit to the default branch. Re-running a complete release only verifies it and refreshes the index.

Stub builds install the selected published generator and use digest-pinned gstreamer-oci images for Ubuntu 24.04/26.04 and Python 3.12/3.14. Native builds retain their suffixes; recommended wheels come from Ubuntu 26.04. Published files are never replaced: use a new `.postN` revision for changed stubs.
Before generation, the Ubuntu-specific `scripts/ubuntu-*/install_deps.sh` installs GIR dependencies with `--no-install-recommends`. Bindings come from `/opt/wheel`; stub builds install the exact generator version from our index. The generator release tests its newly built wheel directly, so the first release needs no existing index entry.

The published generator does not depend on `gst-python-binding`. Supply compatible native libraries, typelibs and Python overrides through system packages, your own build, or the [gstreamer-oci indexes](https://matteo-bruni.github.io/gstreamer-oci/) (select Ubuntu and pin the binding version). The repository's `gst` dependency group and `/opt/wheel` sources are for development only; installed wheels do not inherit that uv configuration.

You can then install the generated packages in your current environment using:

```bash
just install
```

To build and install directly in one step, you can run:

```bash
just build-and-install
```

### Testing the Generated Stubs in Your IDE

To test the generated stubs in your IDE (like VSCode or PyCharm), you can add our sample packages with uv like this (until they are published on PyPI or as wheels):

```bash
uv add "git+https://github.com/matteo-bruni/gi-stub-gen.git#subdirectory=stubs/gi-base-stubs"
uv add "git+https://github.com/matteo-bruni/gi-stub-gen.git#subdirectory=stubs/gi-gst-stubs"
```
note: until the packages are published as wheels (pypi or github releases), i will not bother to update the versions, so to update to latest generated stubs, you can use:

```bash
uv sync --refresh --no-cache -P gi-base-stubs
uv sync --refresh --no-cache -P gi-gst-stubs
```
to trigger and overwrite the existing packages with the latest generated stubs.

---

## Architecture & Design Decisions

### Why not just parse `.gir` files?
Parsing only `.gir` (XML) files is insufficient because:
1.  **Overrides:** PyGObject heavily modifies the API (adding Pythonic methods like `__iter__`, `__enter__`, or custom constructors). GIR files do not reflect these Python-specific overrides.
2.  **Availability:** Runtime inspection guarantees that we generate stubs for what is *actually* available on your system.

*However, we do use GIR files to fetch docstrings, since at least in Ubuntu, these are stripped from the typelib and are not available via the Python introspection API.*

### GIRepository vs exploring directly using  `__info__` classes
Working with `GIRepository` in Python for stub generation has some quirks. 
GIRepository reflects the underlying C API, which can differ from the Python bindings provided by PyGObject. 
This can lead to discrepancies in available methods, properties, and behaviors between the two.

As an example:
* `gi._gi.FunctionInfo` vs `GIRepository.FunctionInfo`: The Python wrapper adds pythonic methods (like `get_arguments()`) and hide the C-level methods like `get_n_args` and `get_arg`. These changes are missing when looking through `GIRepository` resulting in inconsistencies with respect to reality. 



## Bug GObject

this snippet segfault python
```python
import gi
gi.require_version("GObject", "2.0")
from gi.repository import GObject
GObject.list_properties(GObject.GInterface)
```

---

### License
[MIT](LICENSE)
