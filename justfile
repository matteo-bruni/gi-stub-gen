# Allow for positional arguments in Just receipes.

set positional-arguments
set dotenv-load

# python code to find gi overrides paths

# sys_overrides := `/usr/bin/python3 -c 'import os, gi; print(os.path.join(os.path.dirname(gi.__file__), "overrides"))' `
# venv_overrides := `uv run python3 -c 'import os, gi; print(os.path.join(os.path.dirname(gi.__file__), "overrides"))' `

# Default recipe that runs if you type "just".
default:
    just --list

# Build all the stub packages. accepts --debug flag
build *args:
    #!/usr/bin/env bash
    set -euo pipefail

    just build-base {{ args }}
    just build-graphics-core {{ args }}
    # just build-gst {{ args }}
    just build-gtk {{ args }}
    @echo "All stub packages have been built, running tests.."
    just test || (echo "❌ Test failed! check the tests output above." && exit 1)
    @echo "✅ Tests passed."

# Build all and install in current environment
build-and-install *args:
    #!/usr/bin/env bash
    set -euo pipefail

    just build {{ args }}
    just install

# build base stub package. accepts --debug flag
build-base *args:
    #!/usr/bin/env bash
    set -euo pipefail

    bash ./build-base-stubs.sh {{ args }}
    just diff-gobject

# build graphics-core stub package. accepts --debug flag
build-graphics-core *args:
    #!/usr/bin/env bash
    set -euo pipefail

    bash ./build-graphics-core-stubs.sh {{ args }}

# build gst stub package. accepts --debug flag
build-gst *args:
    #!/usr/bin/env bash
    set -euo pipefail

    docker run --rm \
        -v $(pwd):/app \
        -w /app \
        -e USER_ID=$(id -u) \
        -e USER_GROUP_ID=$(id -g) \
        --env-file .env \
        ghcr.io/matteo-bruni/gstreamer:1.28.3-ubuntu.24.04-base-py-3.12 \
        bash ./build-gst-stubs-in-container.sh {{ args }}

    just diff-gst

# build gtk stub package. accepts --debug flag
build-gtk *args:
    #!/usr/bin/env bash
    set -euo pipefail

    bash ./build-gtk-stubs.sh {{ args }}

# Install all generated stub packages in the current environment.
install:
    #!/usr/bin/env bash
    set -euo pipefail

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
        --ignore possibly-missing-attribute \
        stubs

diff:
    just diff-gobject
    just diff-gst

diff-gobject:
    uv run gi-stub-diff \
        "stubs/gi-base-stubs/src/gi-stubs/repository/GObject.pyi" \
        "https://github.com/pygobject/pygobject-stubs/blob/master/src/gi-stubs/repository/GObject.pyi" \
        --name1 "gi-stub-gen" \
        --name2 "pygobject-stubs" \
        --namespace GObject \
        -o docs/GObject_diff.md

diff-gst:
    uv run gi-stub-diff \
        "stubs/gi-gst-stubs/src/gi-stubs/repository/Gst.pyi" \
        "https://github.com/pygobject/pygobject-stubs/blob/master/src/gi-stubs/repository/Gst.pyi" \
        --name1 "gi-stub-gen" \
        --name2 "pygobject-stubs" \
        --namespace Gst \
        -o docs/Gst_diff.md

# # Sync degli override
# sync-gst:
#     @echo "🔄 Synchronizing GStreamer Overrides from ubuntu system to venv"
#     # --- Check Python Versions ---
#     @SYS_VER=$(/usr/bin/python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'); \
#     VENV_VER=$(uv run python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'); \
#     if [ "$SYS_VER" != "$VENV_VER" ]; then \
#         echo "❌ Error: Version Mismatch !"; \
#         echo "   System: $SYS_VER"; \
#         echo "   Venv:   $VENV_VER"; \
#         exit 1; \
#     fi
#     @echo "✅ Venv and System Python versions aligned ($SYS_VER). Proceeding..."
#     # ---------------------------------

#     @echo "  📂 Source: {{ sys_overrides }}"
#     @echo "  📂 Destination: {{ venv_overrides }}"

#     # Create the directory if it doesn't exist
#     mkdir -p "{{ venv_overrides }}"

#     # Copy the files (handles error if none found)
#     cp -v "{{ sys_overrides }}"/Gst* "{{ venv_overrides }}/"
#     cp -v "{{ sys_overrides }}"/_gi_gst* "{{ venv_overrides }}/"

#     @echo "✅ Completed."
