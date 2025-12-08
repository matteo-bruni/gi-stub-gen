# source ./venv/bin/activate

# enable if you want to add debug information inside the stubs
# read from environment variable, default to false
ENABLE_DEBUG=${ENABLE_DEBUG:-false}

###########################################################
# we can assume bindings compatibility within the same minor version
# e.g. 1.26.x
# we keep the patch version for the stub package versioning
GST_VERSION=1.26
GST_STUB_VERSION=0
PKG_GST_STUBS_VERSION=${GST_VERSION}.${GST_STUB_VERSION}
gi-stub-gen $(if [ "$ENABLE_DEBUG" = true ] ; then echo --debug ; fi) \
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
    --pkg-name gi-gstreamer-stubs \
    --pkg-version ${PKG_GST_STUBS_VERSION} \
    --pkg-dependencies gi-base-stubs \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --overwrite

# todo test
# GstWebRTC:1.0 \
# GstRtspServer:1.0 \
