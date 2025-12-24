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

# i think this should follow the pygobject version
# we keep the patch version for the stub package versioning
# the tool can actually create stubs for gi._gi and gi._enum too, but when i do
# the stubs stops working (???)
PYGOBJECT_VERSION=3.54
PYGOBJECT_STUB_VERSION=0
PKG_GI_BASE_STUBS_VERSION=${PYGOBJECT_VERSION}.${PYGOBJECT_STUB_VERSION}
uv run gi-stub-gen $(if [ "$ENABLE_DEBUG" = true ] ; then echo --debug ; fi) \
    gi.repository.GioUnix:2.0 \
    gi.repository.Gio:2.0 \
    gi.repository.GObject:2.0 \
    gi.repository.GLib:2.0 \
    gi.repository.GIRepository:3.0 \
    gi.repository.GModule:2.0 \
    gi \
    --pkg-name gi-base-stubs \
    --pkg-version ${PKG_GI_BASE_STUBS_VERSION} \
    --pkg-author "${STUB_AUTHOR_NAME}" \
    --pkg-author-email "${STUB_AUTHOR_EMAIL}" \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --gir-folder /usr/lib/x86_64-linux-gnu/gir-1.0 \
    --overwrite \
    --log-level INFO 
