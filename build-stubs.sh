# source ./venv/bin/activate

# enable if you want to add debug information inside the stubs
# ENABLE_DEBUG=true
ENABLE_DEBUG=false

# i think this should follow the pygobject version?
BASE_STUB_VERSION=3.54.0
gi-stub-gen $(if [ "$ENABLE_DEBUG" = true ] ; then echo --debug ; fi) \
    GioUnix:2.0 \
    Gio:2.0 \
    gi \
    gi._gi \
    gi.repository \
    GObject:2.0 \
    GLib:2.0 \
    GIRepository:3.0 \
    --pkg-name gi-base-stub \
    --pkg-version 0.0.1 \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --overwrite \
    --log-level INFO 
    
gi-stub-gen \
    Gdk:4.0 \
    Gtk:4.0 \
    --preload GioUnix:2.0 \
    --preload Gio:2.0 \
    --preload GObject:2.0 \
    --preload GIRepository:3.0 \
    --pkg-name gi-gtk-stub \
    --pkg-version 0.0.1 \
    --pkg-dependencies gi-base-stub \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --overwrite \
    --debug

# GstWebRTC:1.0 \
# GstRtspServer:1.0 \

# we can assume bindings compatibility within the same minor version
# e.g. 1.26.x
# we keep the patch version for the stub package versioning
GST_VERSION=1.26
GST_STUB_VERSION=0
GST_STUB_FULL_VERSION=${GST_VERSION}.${GST_STUB_VERSION}
gi-stub-gen \
    Gst:1.0 \
    GstApp:1.0 \
    GstAudio:1.0 \
    GstBase:1.0 \
    GstPbutils:1.0 \
    GstRtp:1.0 \
    GstRtsp:1.0 \
    GstSdp:1.0 \
    GstVideo:1.0 \
    --preload GioUnix:2.0 \
    --preload Gio:2.0 \
    --preload GObject:2.0 \
    --preload GIRepository:3.0 \
    --pkg-name gi-gstreamer-stub \
    --pkg-version ${GST_STUB_FULL_VERSION} \
    --pkg-dependencies gi-base-stub \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --debug \
    --overwrite