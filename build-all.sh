# source ./venv/bin/activate

# enable if you want to add debug information inside the stubs
# read from environment variable, default to false
ENABLE_DEBUG=${ENABLE_DEBUG:-false}

export ENABLE_DEBUG

bash build-base-stubs.sh
bash build-gst-stubs.sh
bash build-gtk-stubs.sh


# install so we can test the stubs
# (in dev mode they do not work?)
# not addedd to the dependencies as they are only needed for testing
uv pip install stubs/gi-base-stubs
uv pip install stubs/gi-gstreamer-stubs
uv pip install stubs/gi-gtk-stubs