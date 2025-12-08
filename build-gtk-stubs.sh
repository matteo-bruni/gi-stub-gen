# source ./venv/bin/activate

# enable if you want to add debug information inside the stubs
# read from environment variable, default to false
ENABLE_DEBUG=${ENABLE_DEBUG:-false}

############################################################
# i think this should follow the gtk version
# we keep the patch version for the stub package versioning
GTK_VERSION=4.0
GTK_STUB_VERSION=0
PKG_GTK_STUBS_VERSION=${GTK_VERSION}.${GTK_STUB_VERSION}

gi-stub-gen $(if [ "$ENABLE_DEBUG" = true ] ; then echo --debug ; fi) \
    cairo:1.0 \
    Pango:1.0 \
    GdkPixbuf:2.0 \
    Gsk:4.0 \
    Gdk:4.0 \
    Gtk:4.0 \
    --preload GioUnix:2.0 \
    --preload Gio:2.0 \
    --preload GObject:2.0 \
    --preload GIRepository:3.0 \
    --pkg-name gi-gtk-stubs \
    --pkg-version ${PKG_GTK_STUBS_VERSION} \
    --pkg-dependencies gi-base-stubs \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --overwrite 
