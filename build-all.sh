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

export ENABLE_DEBUG

bash build-base-stubs.sh
bash build-gst-stubs.sh
bash build-gtk-stubs.sh

# install so we can test the stubs
# (in dev mode they do not work?)
# not addedd to the dependencies as they are only needed for testing
uv pip install stubs/gi-base-stubs
uv pip install stubs/gi-gst-stubs
uv pip install stubs/gi-gtk-stubs