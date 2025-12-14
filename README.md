# 📦 GI Stub Gen

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python Version](https://img.shields.io/badge/python-3.10-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A modern, modular type hint generator for GObject Introspection (GI) libraries (GStreamer, GTK, Gio, etc.).

This tool discovers types by importing the libraries at runtime via `gi.repository`, inspecting them, and generating fully compliant `.pyi` stub files.

## ⚡ Why another stub generator?

I started developing with GStreamer Python bindings and found the lack of IDE support (type hints, autocompletion) frustrating. While looking at existing solutions like `pygobject-stubs`, I found them difficult to extend due to their monolithic nature and tight coupling between parsing and generation.

GI Stub Gen takes a different approach:

1.  **Separation of Concerns:** The parsing logic is completely decoupled from the template generation.
2.  **Intermediate Representation:** All introspection data is collected into strictly typed **Pydantic models**. This allows for easy inspection, validation, and modification of data *before* the stubs are written.
3.  **Modular Output:** Instead of one giant package, this tool aims to generate separate packages for each library (e.g., `stubs-gst`, `stubs-gtk`). This allows library maintainers to potentially own their stubs.
4.  **Runtime Inspection:** By inspecting the live objects, we catch overrides and dynamic attributes that static GIR files often miss.

## ✨ Features

-   **Explicit Versioning:** Generate stubs for specific library versions (e.g., GStreamer 1.18 vs 1.20) rather than relying on the system default at runtime.
-   **Hybrid Approach:** Uses runtime inspection for accurate types/overrides and parses `.gir` files to extract **Docstrings**.
-   **Deprecation Handling:** Detects `PyDeprecationWarning` for aliases/attributes and marks functions with the `@deprecated` decorator.
-   **Signal & GError Support:** (WIP) Better typing for GObject signals and error handling.
-   **Automated Logic:** Focuses on improving the generator logic rather than manually patching the output files.

---

## 🚀 Getting Started

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
git clone [https://github.com/matteo-bruni/gi-stub-gen.git](https://github.com/matteo-bruni/gi-stub-gen.git)
cd gi-stub-gen

# Sync dependencies and activate venv
uv sync
source .venv/bin/activate
```

### Usage

To generate a stub for a specific library:

```bash
# Syntax: gi_stub_gen <LibraryName> <Version> > <Output.pyi>
uv run gi-stub-gen \
    gi.repository.Gst:1.0 \
    gi.repository.GstVideo:1.0 \
    --preload gi.repository.GioUnix:2.0 \
    --preload gi.repository.Gio:2.0 \
    --preload gi.repository.GObject:2.0 \
    --preload gi.repository.GIRepository:3.0 \
    --pkg-name gi-gst-stubs \
    --pkg-version 1.26.9 \
    --pkg-dependencies gi-base-stubs \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0
```
This will generate stubs for GStreamer 1.26.9 in the `stubs/` folder.
The generated stubs have a dependency on `gi-base-stubs`, which contains common types like `GObject` and `GLib`.

---

## 🏗 Architecture & Design Decisions

### Why not just parse `.gir` files?
Parsing only `.gir` (XML) files is insufficient for a great Python developer experience because:
1.  **Overrides:** PyGObject heavily modifies the API at runtime (adding Pythonic methods like `__iter__`, `__enter__`, or custom constructors). GIR files do not reflect these Python-specific overrides.
2.  **Availability:** Runtime inspection guarantees that we generate stubs for what is *actually* available on your system.

*However, we do use GIR files to fetch docstrings, as these are not currently exposed via the Python introspection API.*

### The Parsing Challenge
Working with `GIRepository` in Python has some quirks. For instance:
* `gi._gi.FunctionInfo` vs `GIRepository.FunctionInfo`: The Python wrapper adds methods (like `get_arguments()`) that are missing when using `GIRepository`. (and it will not hide the C-level methods that are actually removed from the Python exposure, like `get_n_args` and `get_arg`)
* Inconsistencies in `TypeInfo` methods between the internal C implementation and the Python exposure.


---

## 📂 Generated Stubs
You can find examples of generated output in the `stubs/` folder.
Ideally, in the future:
* A base package `gi-base-stubs` will contain common types (`GObject`, `GLib`).
* Specific libraries will depend on the base package.
* These can be published to PyPI individually.

## ⚠️ Disclaimer
I am not a GI/PyGObject expert. This project started as a learning exercise to understand the internals of GObject Introspection. Mistakes are possible, and feedback is highly appreciated!

## ✅ Todo
- [ ] Add comprehensive test suite.
- [ ] Improve `.gir` file parsing for documentation.
- [ ] Create Docker-based build system for consistent environment reproduction.
- [ ] Handle `GValue` marshalling edge cases.

---

### License
[MIT](LICENSE)