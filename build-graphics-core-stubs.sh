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

############################################################
# i think this should follow pygobject version
# we keep the patch version for the stub package versioning
PYGOBJECT_VERSION=3.54
PYGOBJECT_STUB_VERSION=0
PKG_GTK_STUBS_VERSION=${PYGOBJECT_VERSION}.${PYGOBJECT_STUB_VERSION}

uv run gi-stub-gen $(if [ "$ENABLE_DEBUG" = true ] ; then echo --debug ; fi) \
    gi.repository.freetype2:2.0 \
    gi.repository.cairo:1.0 \
    gi.repository.Pango:1.0 \
    gi.repository.PangoCairo:1.0 \
    gi.repository.HarfBuzz:0.0 \
    gi.repository.Graphene:1.0 \
    --preload gi.repository.GioUnix:2.0 \
    --preload gi.repository.Gio:2.0 \
    --preload gi.repository.GObject:2.0 \
    --preload gi.repository.GIRepository:3.0 \
    --pkg-name gi-graphics-core-stubs \
    --pkg-version ${PKG_GTK_STUBS_VERSION} \
    --pkg-dependencies gi-base-stubs \
    --pkg-author "${STUB_AUTHOR_NAME}" \
    --pkg-author-email "${STUB_AUTHOR_EMAIL}" \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --overwrite 
