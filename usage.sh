
# source ./venv/bin/activate


gi_stub_gen \
    gi._gi \
    gi.repository \
    GObject \
    GLib \
    --pkg-name gi-base-stub \
    --pkg-version 0.0.1 \
    --gi-version 2.0 \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --overwrite \
    --debug

# gi_stub_gen \
#     Gio \
#     GioUnix \
#     GIRepository \
#     --pkg-name gi-gio-stub \
#     --pkg-version 0.0.1 \
#     --gi-version 2.0 \
#     --output ./stubs \
#     --gir-folder /usr/share/gir-1.0 \
#     --overwrite \
#     --debug

# gi_stub_gen \
#     Gst \
#     GstVideo \
#     GstBase \
#     GstCheck \
#     GstController \
#     GstNet \
#     --pkg-name gi-gstreamer-stub \
#     --pkg-version 0.0.1 \
#     --gi-version 1.0 \
#     --output ./stubs \
#     --gir-folder /usr/share/gir-1.0 \
#     --debug \
#     --overwrite