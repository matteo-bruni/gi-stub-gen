# 📦 GI Stub Gen

![Python Version](https://img.shields.io/badge/python-3.10-blue)
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

---

## Getting Started

### Prerequisites

This project relies on `PyGObject`, which requires system-level dependencies.

**On Ubuntu/Debian:**
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

# Sync dependencies and activate venv
uv sync
```

### !! Warning on Gstreamer.
Until gstreamer start publishing gst-python wheels on pypi we need to install gst-python from the system packages and copy the overrides in the venv.
Since i'm using ubuntu 25.10 i'm forced to use python 3.13 for the venv since the _gi_gst compiled library is distribuited via python3-gst-1.0 package only.

in Ubuntu:
```bash
sudo apt install python3-gst-1.0 gstreamer1.0-python3-plugin-loader
just sync-gst
```
(make sure you created the uv venv with the same python version of the system gst-python package)

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
This will generate stubs for GStreamer 1.26 in the `stubs/` folder. (because that is the version installed on my system).
The generated stubs have a dependency on `gi-base-stubs`, which contains common types like `GObject` and `GLib`.
Providing the `--gir-folder` docstrings will be gathered from the corresponding `.gir` files and included in the stubs. If not provided, the stubs will be generated without docstrings. 

---

## Generated Stubs

You can find the generated output in the `stubs/` folder as an example. I have currently organized them into 4 packages based on an arbitrary grouping that seemed logical for dependency management.

> [!NOTE] 
> **Note:** This grouping is just my personal preference. The tool allows anyone to generate stubs with their own structure. Ideally, the maintainers of the respective libraries should generate and publish their own stubs.

| Package | Versioning | Contents |
| :--- | :--- | :--- |
| **`gi-base-stubs`** | Follows **PyGObject** | **Core Infrastructure.**<br>Includes `GLib`, `GObject`, `Gio`, `GioUnix`, `GModule`, `GIRepository`, and the `gi` module. |
| **`gi-graphics-core-stubs`** | Follows **PyGObject** | **Graphics & Text.**<br>Includes `cairo`, `Pango`, `PangoCairo`, `HarfBuzz`, `freetype2`, `Graphene`. |
| **`gi-gtk-stubs`** | Follows **GTK** | **UI Toolkit (GTK4).**<br>Includes `Gtk`, `Gdk`, `Gsk`, `GdkPixbuf`, `Atk`. |
| **`gi-gst-stubs`** | Follows **GStreamer** | **Multimedia (GStreamer).**<br>Includes `Gst`, `GstBase`, `GstVideo`, `GstAudio`, `GstApp`, `GstPbutils`, `GstRtp`, `GstRtsp`, `GstSdp`. |


To build all the stubs like `gi-base-stubs`, `gi-gtk-stubs`, `gi-graphics-core-stubs`, and `gi-gst-stubs`, you can run the provided shell scripts in the project root or use `just` commands:

```bash
just build
```
This will build all the stub packages and place them in the `stubs/` directory.
(or you can build individual packages using `just build-base`, `just build-gst`, etc.).
Each build command accept a `--debug` flag to enable verbose output in the stubs (_beware! it is really verbose_) that also disable the progress bar, useful for debugging with gdb.

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
