
# source ./venv/bin/activate


gi_stub_gen \
    gi \
    gi._gi \
    gi.repository \
    GObject:2.0 \
    GLib:2.0 \
    GioUnix:2.0 \
    Gio:2.0 \
    GIRepository:3.0 \
    --pkg-name gi-base-stub \
    --pkg-version 0.0.1 \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --overwrite \
    --debug

# gi_stub_gen \
#     Gdk:4.0 \
#     Gtk:4.0 \
#     --preload GioUnix:2.0 \
#     --preload Gio:2.0 \
#     --pkg-name gi-gtk-stub \
#     --pkg-version 0.0.1 \
#     --output ./stubs \
#     --gir-folder /usr/share/gir-1.0 \
#     --overwrite \
#     --debug



# GstWebRTC:1.0 \
# GstRtspServer:1.0 \
# gi_stub_gen \
#     Gst:1.0 \
#     GstApp:1.0 \
#     GstAudio:1.0 \
#     GstBase:1.0 \
#     GstPbutils:1.0 \
#     GstRtp:1.0 \
#     GstRtsp:1.0 \
#     GstSdp:1.0 \
#     GstVideo:1.0 \
#     --preload GioUnix:2.0 \
#     --preload Gio:2.0 \
#     --pkg-name gi-gstreamer-stub \
#     --pkg-version 0.0.1 \
#     --output ./stubs \
#     --gir-folder /usr/share/gir-1.0 \
#     --debug \
#     --overwrite