#!/usr/bin/env bash
set -euo pipefail
# Keep distro-specific package names here; do not run this list on another Ubuntu release.
source /etc/os-release
if [[ $ID != ubuntu || $VERSION_ID != 26.04 ]]; then
    echo "Expected Ubuntu 26.04, found $VERSION_ID" >&2
    exit 1
fi

# Runtime images lack GIR sources and Cairo's pkg-config metadata; omit optional packages.
apt-get update
apt-get install -y --no-install-recommends \
    pkg-config gir1.2-glib-2.0-dev gir1.2-girepository-3.0-dev gir1.2-freedesktop-dev \
    libcairo2-dev libgtk-4-dev libatk1.0-dev libpango1.0-dev libharfbuzz-dev \
    libgraphene-1.0-dev libgdk-pixbuf-2.0-dev
