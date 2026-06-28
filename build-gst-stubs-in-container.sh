#!/usr/bin/env bash
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

USER_ID=${USER_ID:-1}
USER_GROUP_ID=${USER_GROUP_ID:-1}

# if -1 raise error and exit
if [ "$USER_ID" -eq -1 ] || [ "$USER_GROUP_ID" -eq -1 ]; then
    echo "Error: USER_ID and USER_GROUP_ID must be set to a valid value."
    exit 1
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

# Prepare the virtual environment #########################

# clear the virtual env so we will rebuild gobject
# and all deps just for the project
rm -rf "$VIRTUAL_ENV"

# instal pygobject build deps
apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    pkg-config \
    libcairo2-dev \
    libgirepository-2.0-dev \
    gir1.2-girepository-3.0 \
    util-linux

# install stubs dependencies
uv sync

# install the gstreamer python binding that are awailable in the system
# to be able to use them in the venv
uv pip install /opt/wheel/*.whl


# utility to build as user and group id, so we can write to the host mounted volume

# Directory/cache usate dai comandi eseguiti come USER_ID:USER_GROUP_ID.
# HOME e UV_CACHE_DIR devono essere scrivibili dall'utente target.
RUN_HOME="/tmp/gi-stub-gen-home-${USER_ID}"
RUN_UV_CACHE="/tmp/uv-cache-${USER_ID}"

install -d -o "$USER_ID" -g "$USER_GROUP_ID" "$RUN_HOME"
install -d -o "$USER_ID" -g "$USER_GROUP_ID" "$RUN_UV_CACHE"
install -d -o "$USER_ID" -g "$USER_GROUP_ID" ./stubs

run_as_target_user() {
    env \
        HOME="$RUN_HOME" \
        UV_CACHE_DIR="$RUN_UV_CACHE" \
        setpriv \
            --reuid "$USER_ID" \
            --regid "$USER_GROUP_ID" \
            --clear-groups \
            "$@"
}

# Build the actual stub ####################################
PKG_GST_STUBS_VERSION=$(uv run python3 -c 'import gi; gi.require_version("Gst", "1.0"); from gi.repository import Gst; Gst.init(None); v = Gst.version(); print(f"{v.major}.{v.minor}.{v.micro}")')
WHEEL_PACKAGE_NAME=${STUB_PACKAGE_NAME//-/_}

run_as_target_user uv run gi-stub-gen $(if [ "$ENABLE_DEBUG" = true ] ; then echo --debug ; fi) \
    gi.repository.Gst:1.0 \
    gi.repository.GstApp:1.0 \
    gi.repository.GstAudio:1.0 \
    gi.repository.GstBase:1.0 \
    gi.repository.GstPbutils:1.0 \
    gi.repository.GstRtp:1.0 \
    gi.repository.GstRtsp:1.0 \
    gi.repository.GstSdp:1.0 \
    gi.repository.GstVideo:1.0 \
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


# create the wheel package
run_as_target_user uv build --wheel --out-dir ./stubs/wheel ./stubs/${STUB_PACKAGE_NAME}

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