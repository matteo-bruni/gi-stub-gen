# Allow for positional arguments in Just receipes.
set positional-arguments := true


# Default recipe that runs if you type "just".
default: 
    just --list

# Build all the stub packages. accepts --debug flag
build *args:
    just build-base {{args}}
    just build-graphics-core {{args}}
    just build-gst {{args}}
    just build-gtk {{args}}
    @echo "All stub packages have been built, running tests.."
    just test || (echo "❌ Test failed! check the tests output above." && exit 1)
    @echo "✅ Tests passed."

# Build all and install in current environment
build-and-install *args:
    just build {{args}}
    just install

# build base stub package. accepts --debug flag
build-base *args:
    bash ./build-base-stubs.sh {{args}}

# build graphics-core stub package. accepts --debug flag
build-graphics-core *args:
    bash ./build-graphics-core-stubs.sh {{args}}

# build gst stub package. accepts --debug flag
build-gst *args:
    bash ./build-gst-stubs.sh {{args}}

# build gtk stub package. accepts --debug flag
build-gtk *args:
    bash ./build-gtk-stubs.sh {{args}}

# Install all generated stub packages in the current environment.
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

# show installed packages.
list:
    uv pip list

# show outdated packages.
outdated:
    uv pip list --outdated

# Run audit on all installed packages.
audit:
    uv run --with=pip-audit pip-audit

# Clean gstreamer cache.
clean-gst-cache:
    rm ~/.cache/gstreamer-1.0/registry.x86_64.bin

# Run tests.
test:
    uv run pytest -rA --tb=short  tests/

# Run Astra TY type checking ignoring some known issues.
ty:
    #!/bin/bash
    set -e
    uvx ty check \
        --ignore invalid-method-override \
        --ignore invalid-type-form \
        --ignore deprecated \
        --ignore unresolved-import \
        --ignore possibly-missing-attribute 