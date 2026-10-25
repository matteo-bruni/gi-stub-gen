#!/usr/bin/env bash
set -euo pipefail

stage=$1
# Use the image's interpreter and venv; uv must not reinstall the checkout or replace its ABI.
export UV_NO_SYNC=1 UV_PYTHON=/opt/uv/venv/bin/python UV_PYTHON_DOWNLOADS=never
export VIRTUAL_ENV=/opt/uv/venv UV_PROJECT_ENVIRONMENT=/opt/uv/venv
export PATH="/opt/uv/venv/bin:/opt/uv/bin:$PATH"
mkdir -p .release-logs
trap 'code=$?; tail -n 60 .release-logs/*.log >&2; exit "$code"' ERR

if [[ $stage != consumers ]]; then
    # Prepare missing distro metadata before installing or running the generator wheel.
    bash "scripts/ubuntu-$4/install_deps.sh" > .release-logs/apt.log 2>&1
fi

# Native wheels match this image's ABI; use its local directory rather than an external binding index.
uv pip install --no-index --find-links /opt/wheel pygobject pycairo gst-python-binding
uv pip install --group dev -r pyproject.toml
if [[ $stage == generator ]]; then
    # Verify the new candidate before publishing, including the first release's bootstrap.
    uv pip install --no-deps .release-input/*.whl
else
    # Only the generator comes from our index; ordinary dependencies were installed above.
    version=$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
    uv pip install --no-deps --index-url "${UV_INDEX_URL:-https://matteo-bruni.github.io/gi-stub-gen/simple/}" "gi-stub-gen==$version"
fi

# Check the actual runtime after dependency preparation and record it in the build provenance.
python - <<'PY'
from importlib.metadata import version
from pathlib import Path
import json, platform, tomllib
import gi_stub_gen
assert '/site-packages/' in str(gi_stub_gen.__file__), gi_stub_gen.__file__
assert version('gi-stub-gen') == tomllib.loads(Path('pyproject.toml').read_text())['project']['version']
image = json.loads(Path('.release-input/image.json').read_text())
assert platform.python_version().startswith(image['python'] + '.')
assert platform.freedesktop_os_release()['VERSION_ID'] == image['ubuntu']
from gi_stub_gen.release import environment
native = environment(image['image'])
assert native['gstreamer'] == image['metadata']['build']['gstreamer_version']
Path('.release-logs/environment.json').write_text(json.dumps(native, indent=2) + '\n')
PY
gi-stub-gen --help > .release-logs/entry-point.txt

if [[ $stage == consumers ]]; then
    # Cross-environment checks reuse prepared release wheels rather than regenerating them.
    GI_STUB_WHEELS=$2 just test-installed-stubs
    exit
fi

image=$2
revision=$3
ubuntu=$4
# Keep generation on the same recipes used locally, with verbose output retained as artifacts.
just build --no-debug > .release-logs/build.log 2>&1
# Source checking must see the newly generated annotations, not an older installed stub package.
just install > .release-logs/install.log 2>&1
just check-types > .release-logs/types.log 2>&1
just test-installed-stubs > .release-logs/consumers.log 2>&1
# Full-stub ty findings remain a visible secondary report; consumer checks above are gates.
just ty > .release-logs/ty.log 2>&1 || test "$?" -eq 1

if [[ $stage == stubs ]]; then
    # Native variants come from their own environment; only the verified recent build is recommended.
    options=()
    [[ $revision == 0 ]] || options+=(--revision "$revision")
    if [[ $ubuntu == 26.04 ]] && python -c 'import sys; sys.exit(sys.version_info[:2] != (3, 14))'; then
        options+=(--canonical)
    fi
    python -m gi_stub_gen.release --output .release-output --image "$image" "${options[@]}"
fi
