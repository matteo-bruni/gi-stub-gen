#!/usr/bin/env bash

set -e

touch .devcontainer/bash/.bash_history
touch .devcontainer/bash/.bashrc_custom_${USER}.bash
touch /tmp/Xauthority.fake

# touch config of gh cli
mkdir -p ~/.config/gh

# temp folder to share files with host
mkdir -p /tmp/gi-stub-tmp/

# needed to unlock the X server to docker processes
xhost +local:docker || true
