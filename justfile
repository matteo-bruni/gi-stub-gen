# Allow for positional arguments in Just receipes.
set positional-arguments := true


# Default recipe that runs if you type "just".
default: 
    just --list


build:
    bash ./build-all.sh

build-and-install:
    just build
    just install

build-base:
    bash ./build-base-stubs.sh

build-graphics-core:
    bash ./build-graphics-core-stubs.sh

build-gst:
    bash ./build-gst-stubs.sh

build-gtk:
    bash ./build-gtk-stubs.sh

install:
    #!/bin/bash
    set -e
    uv pip install --force-reinstall \
        stubs/gi-base-stubs \
        stubs/gi-graphics-core-stubs \
        stubs/gi-gst-stubs \
        stubs/gi-gtk-stubs

# Install dependencies for local development.
sync:
    uv sync --dev

# Format code.
format:
    ruff check format .

list:
    uv pip list

# show outdated packages.
outdated:
    uv pip list --outdated

# Run audit on all installed packages.
audit:
    uv run --with=pip-audit pip-audit

clean-gst-cache:
    rm ~/.cache/gstreamer-1.0/registry.x86_64.bin

test:
    pytest -rA --tb=short  tests/

ty:
    #!/bin/bash
    set -e
    uvx ty check \
        --ignore  invalid-method-override \
        --ignore invalid-type-form \
        --ignore deprecated \
        --ignore unresolved-import \
        --ignore possibly-missing-attribute
        stubs/