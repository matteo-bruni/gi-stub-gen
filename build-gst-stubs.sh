#!/usr/bin/env bash
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

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


###########################################################
# we can assume bindings compatibility within the same minor version
# e.g. 1.26.x
# we keep the patch version for the stub package versioning
GST_VERSION=1.26
GST_STUB_VERSION=0
PKG_GST_STUBS_VERSION=${GST_VERSION}.${GST_STUB_VERSION}
uv run gi-stub-gen $(if [ "$ENABLE_DEBUG" = true ] ; then echo --debug ; fi) \
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
    --pkg-name gi-gst-stubs \
    --pkg-version ${PKG_GST_STUBS_VERSION} \
    --pkg-dependencies gi-base-stubs \
    --pkg-author "${STUB_AUTHOR_NAME}" \
    --pkg-author-email "${STUB_AUTHOR_EMAIL}" \
    --pkg-description "GI Stubs for GStreamer" \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --overwrite

# todo test
# GstWebRTC:1.0 \
# GstRtspServer:1.0 \
