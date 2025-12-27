# 📦 GI Stub Gen

![Python Version](https://img.shields.io/badge/python-3.10-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A modern, modular type hint generator for GObject Introspection (GI) libraries (GStreamer, GTK, Gio, etc.).

This tool discovers types by importing the libraries at runtime via `gi.repository`, inspecting them, and generating fully compliant `.pyi` stub files.

## Why another stub generator?

> [!WARNING]
> ⚠️ __Disclaimer__
> 
> I am not a GI/PyGObject expert. This project started as a learning exercise to understand the internals of GObject Introspection. Mistakes are possible, and feedback is highly appreciated!

I started developing with GStreamer Python bindings and found the lack of IDE support (type hints, autocompletion) frustrating. While looking at existing solutions like `pygobject-stubs`, I found them difficult to extend due to their monolithic nature and tight coupling between parsing and generation.

Furthermore, `pygobject-stubs` rely on custom PEP 517 build backends to select stubs to install at **install time** based on a config. 
My goal is to decouple generation from installation, enabling the creation of deterministic, version-specific packages (e.g., a standalone `gtk4-stubs` package) that are easy to install and manage in any virtual environment.

GI Stub Gen takes a different approach:

1.  **Separation of Concerns:** The parsing logic is completely decoupled from the template generation.
2.  **Intermediate Representation:** All introspection data is collected into strictly typed **Pydantic models**. This allows for easy inspection, validation, and modification of data *before* the stubs are written.
3.  **Modular Output:** Instead of one giant package, this tool aims to generate separate packages for each library (e.g., `stubs-gst`, `stubs-gtk`). This allows library maintainers to potentially own their stubs.
4.  **Runtime Inspection:** By inspecting the live objects, we catch overrides and dynamic attributes that static GIR files often miss.

## Features

-   **Explicit Versioning:** Generate stubs for specific library versions (e.g., GStreamer 1.18 vs 1.20) rather than relying on the system default at runtime.
-   **Docstrings:** Uses runtime inspection for accurate types/overrides and parses `.gir` files to extract **Docstrings**. Docstrings are converted from c syntax to Python syntax where possible.
-   **Deprecation Handling:** Detects `PyDeprecationWarning` for aliases/attributes and marks functions with the `@deprecated` decorator.
-   **Signal** Better typing for GObject signals and error handling. Added `def connect()` overloads for signals with specific signatures.
-   **Protocols:** Uses `typing.Protocol` for better structural typing of interfaces.
-   **Automated Logic:** Focuses on improving the generator logic rather than manually patching the output files.

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
  libgirepository-2.0-dev
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

### GIRepository vs exploring directly using  __info__ classes
Working with `GIRepository` in Python for stub generation has some quirks. 
GIRepository reflects the underlying C API, which can differ from the Python bindings provided by PyGObject. 
This can lead to discrepancies in available methods, properties, and behaviors between the two.

As an example:
* `gi._gi.FunctionInfo` vs `GIRepository.FunctionInfo`: The Python wrapper adds pythonic methods (like `get_arguments()`) and hide the C-level methods like `get_n_args` and `get_arg`. These changes are missing when looking through `GIRepository` resulting in inconsistencies with respect to reality. 



## ✅ Todo
- [ ] Add comprehensive test suite.
- [ ] Create Docker-based build system for consistent environment reproduction.

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