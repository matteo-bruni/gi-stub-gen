#!/bin/bash

# this commands are run after the container is created and started, 
# and after the devcontainer features have been installed

# set ownership of the config folder to the user, so that it can be used without sudo
sudo chown -R ${USER}:${USER} ~/.config
# also for the venv in the containerv
sudo chmod -R o+w /opt/uv

# APT Autocompletion Setup
# to be able to use apt autocompletion inside the container
# we need to remove the docker-clean file that prevents it
sudo rm /etc/apt/apt.conf.d/docker-clean

# UV SETUP #############################################################################################################
mkdir -p ~/.local/share/bash-completion/completions

echo "Setting up UV: update venv"
# uv sync --dev --frozen 

echo "Generating UV bash completion"
# ~/.cargo/bin/uv generate-shell-completion bash > ~/.local/share/bash-completion/completions/uv.bash
uv generate-shell-completion bash > ~/.local/share/bash-completion/completions/uv.bash

uv sync
uv pip install /opt/wheel/gst_python_binding-*.whl