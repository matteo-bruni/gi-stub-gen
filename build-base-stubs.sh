# source ./venv/bin/activate

# enable if you want to add debug information inside the stubs
# read from environment variable, default to false
ENABLE_DEBUG=${ENABLE_DEBUG:-false}

# i think this should follow the pygobject version
# we keep the patch version for the stub package versioning
# gi._enum \
# gi._gi \
# gi.repository \
PYGOBJECT_VERSION=3.54
PYGOBJECT_STUB_VERSION=0
PKG_GI_BASE_STUBS_VERSION=${PYGOBJECT_VERSION}.${PYGOBJECT_STUB_VERSION}
gi-stub-gen $(if [ "$ENABLE_DEBUG" = true ] ; then echo --debug ; fi) \
    gi.repository.GioUnix:2.0 \
    gi.repository.Gio:2.0 \
    gi.repository.GObject:2.0 \
    gi.repository.GLib:2.0 \
    gi.repository.GIRepository:3.0 \
    gi \
    --pkg-name gi-base-stubs \
    --pkg-version ${PKG_GI_BASE_STUBS_VERSION} \
    --output ./stubs \
    --gir-folder /usr/share/gir-1.0 \
    --overwrite \
    --log-level INFO 

# these are python files no need to stub?
#  gi \
# gi._enum \
# gi._gi \
# gi.repository \


# install so we can test the stubs
# (in dev mode they do not work?)
# not addedd to the dependencies as they are only needed for testing
# uv pip install stubs/gi-base-stubs