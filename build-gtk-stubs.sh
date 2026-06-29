#!/usr/bin/env bash
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

STUB_PACKAGE_NAME=${STUB_PACKAGE_NAME:-"gi-gtk-stubs"}
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
PYGOBJECT_VERSION=$(uv run python3 -c "import gi; print(gi.__version__)")
GTK_VERSION=$(uv run python3 -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print(f'{Gtk.MAJOR_VERSION}.{Gtk.MINOR_VERSION}')")
PKG_GTK_STUBS_VERSION=${PYGOBJECT_VERSION}+gtk${GTK_VERSION}
WHEEL_PACKAGE_NAME=${STUB_PACKAGE_NAME//-/_}

# if we want to add gdkpixbuf to the local version.
# GDK_PIXBUF_VERSION=$(uv run python3 -c "import gi; gi.require_version('GdkPixbuf', '2.0'); from gi.repository import GdkPixbuf; print(f'{GdkPixbuf.PIXBUF_MAJOR}.{GdkPixbuf.PIXBUF_MINOR}')")
# PKG_GTK_STUBS_VERSION=${PYGOBJECT_VERSION}+gtk${GTK_VERSION}.gdkpixbuf${GDK_PIXBUF_VERSION}

uv run gi-stub-gen $(if [ "$ENABLE_DEBUG" = true ] ; then echo --debug ; fi) \
    gi.repository.Gsk:4.0 \
    gi.repository.GdkPixbuf:2.0 \
    gi.repository.Gdk:4.0 \
    gi.repository.Gtk:4.0 \
    gi.repository.Atk:1.0 \
    --preload gi.repository.GioUnix:2.0 \
    --preload gi.repository.Gio:2.0 \
    --preload gi.repository.GObject:2.0 \
    --preload gi.repository.GIRepository:3.0 \
    --pkg-name ${STUB_PACKAGE_NAME} \
    --pkg-version ${PKG_GTK_STUBS_VERSION} \
    --pkg-dependencies gi-graphics-core-stubs \
    --pkg-author "${STUB_AUTHOR_NAME}" \
    --pkg-author-email "${STUB_AUTHOR_EMAIL}" \
    --pkg-description "GI Stubs for GTK" \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --overwrite 


# create the wheel package
uv build --wheel --out-dir ./stubs/wheel ./stubs/${STUB_PACKAGE_NAME}

# # add platform tags
# PYTAG=$(uv run python -c "import sys; print(f'cp{sys.version_info.major}{sys.version_info.minor}')")
# PLAT=$(uv run python -c "import sysconfig; print(sysconfig.get_platform().replace('-','_').replace('.','_'))")

# # set the abi tag and the platform tag
# uv run python -m wheel tags \
#     --python-tag "${PYTAG}" \
#     --abi-tag "${PYTAG}" \
#     --platform-tag "${PLAT}" \
#     --remove \
#     ./stubs/wheel/${WHEEL_PACKAGE_NAME}-${PKG_STUBS_VERSION}*.whl