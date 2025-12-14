# Allow for positional arguments in Just receipes.
set positional-arguments := true


# Default recipe that runs if you type "just".
default: 
    just --list


build:
    bash ./build-all.sh

build-base:
    bash ./build-base-stubs.sh

build-gst:
    bash ./build-gst-stubs.sh

build-gtk:
    bash ./build-gtk-stubs.sh

install-stubs:
    uv pip install stubs/gi-base-stubs
    uv pip install stubs/gi-gst-stubs
    uv pip install stubs/gi-gtk-stubs


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
