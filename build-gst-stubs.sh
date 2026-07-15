#!/usr/bin/env bash
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

STUB_PACKAGE_NAME=${STUB_PACKAGE_NAME:-"gi-gst-stubs"}
STUB_AUTHOR_NAME=${STUB_AUTHOR_NAME:-"Unknown Author"}
STUB_AUTHOR_EMAIL=${STUB_AUTHOR_EMAIL:-"unknown@example.com"}

# enable if you want to add debug information inside the stubs
# read from environment variable, default to false
ENABLE_DEBUG=${ENABLE_DEBUG:-false}

# parse CLI args to override ENABLE_DEBUG
while [ "$#" -gt 0 ]; do
    case "$1" in
        --debug|-d)
            ENABLE_DEBUG=true
            shift
            ;;
        --no-debug)
            ENABLE_DEBUG=false
            shift
            ;;
        *)
            # ignore any other arguments
            shift
            ;;
    esac
done


# Build the actual stub ####################################
UV_RUN=(uv run --group gst --locked)

PKG_GST_STUBS_VERSION=$("${UV_RUN[@]}" python3 -c 'import gi; gi.require_version("Gst", "1.0"); from gi.repository import Gst; Gst.init(None); v = Gst.version(); print(f"{v.major}.{v.minor}.{v.micro}")')
WHEEL_PACKAGE_NAME=${STUB_PACKAGE_NAME//-/_}

mapfile -t GST_MODULES < <("${UV_RUN[@]}" --quiet python3 <<'PY'
from pathlib import Path

import gi

gi.require_version("GIRepository", "3.0")
from gi.repository import GIRepository

modules: dict[str, set[str]] = {}
for search_path in GIRepository.Repository().get_search_path():
    base = Path(search_path)
    if not base.exists():
        continue
    for typelib in base.glob("*Gst*.typelib"):
        namespace, version = typelib.stem.rsplit("-", 1)
        modules.setdefault(namespace, set()).add(version)

for namespace, versions in sorted(modules.items()):
    for version in sorted(versions):
        try:
            gi.require_version(namespace, version)
            __import__(f"gi.repository.{namespace}", fromlist=[namespace])
        except (ImportError, ValueError):
            continue
        print(f"gi.repository.{namespace}:{version}")
PY
)

if [ "${#GST_MODULES[@]}" -eq 0 ]; then
    echo "Error: no importable Gst typelibs found."
    exit 1
fi


"${UV_RUN[@]}" gi-stub-gen $(if [ "$ENABLE_DEBUG" = true ] ; then echo --debug ; fi) \
    "${GST_MODULES[@]}" \
    --preload gi.repository.GioUnix:2.0 \
    --preload gi.repository.Gio:2.0 \
    --preload gi.repository.GObject:2.0 \
    --preload gi.repository.GIRepository:3.0 \
    --pkg-name ${STUB_PACKAGE_NAME} \
    --pkg-version ${PKG_GST_STUBS_VERSION} \
    --pkg-dependencies gi-base-stubs \
    --pkg-author "${STUB_AUTHOR_NAME}" \
    --pkg-author-email "${STUB_AUTHOR_EMAIL}" \
    --pkg-description "GI Stubs for GStreamer" \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --overwrite

uv build --wheel --out-dir ./stubs/wheel ./stubs/${STUB_PACKAGE_NAME}

# not needed right now to platform tag
# # add platform tags
# PYTAG=$(run_as_target_user uv run python -c "import sys; print(f'cp{sys.version_info.major}{sys.version_info.minor}')")
# PLAT=$(run_as_target_user uv run python -c "import sysconfig; print(sysconfig.get_platform().replace('-','_').replace('.','_'))")

# # set the abi tag and the platform tag
# run_as_target_user uv run python -m wheel tags \
#     --python-tag "${PYTAG}" \
#     --abi-tag "${PYTAG}" \
#     --platform-tag "${PLAT}" \
#     --remove \
#     ./stubs/wheel/${WHEEL_PACKAGE_NAME}-${PKG_GST_STUBS_VERSION}*.whl
