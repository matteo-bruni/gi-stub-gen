ARG BASE_IMAGE=ghcr.io/matteo-bruni/gstreamer
ARG BASE_IMAGE_TAG=1.28.3-ubuntu.24.04-base-py-3.12

FROM ${BASE_IMAGE}:${BASE_IMAGE_TAG}

ARG USER
ARG UID
ARG GID

ENV UV_SYSTEM_CERTS=true
ENV UV_LINK_MODE=copy

# install all necessary packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # essentials
    sudo openssh-client git build-essential wget graphviz unzip \
    # commodities
    less nano bat ripgrep htop jq uuid bash-completion iputils-ping x11-apps \
    # used by codex for running commands in a sandboxed environment
    bubblewrap \
    # required to build pygobject
    gcc pkg-config \
    libcairo2-dev libgirepository-2.0-dev \
    gir1.2-girepository-3.0 gir1.2-glib-2.0-dev \
    # for gtk4
    libatk1.0-dev libgtk-4-dev gir1.2-gtk-4.0 && \
    rm -rf /var/lib/apt/lists/* && \
    # make bubblewrap setuid so that it can be used by non-root users
    chmod u+s /usr/bin/bwrap && \
    # clear the venv so we start with a clean slate
    # otherwise we can have some issues with compatibility in pygobject
    rm -rf $VIRTUAL_ENV

# create user with appropriate username / uid / gid / home path
# and give user root privileges
RUN (userdel -f -r ubuntu || true) && \
    addgroup --gid "${GID}" "${USER}" && \
    adduser --disabled-password --shell /usr/bin/bash --home "/home/${USER}" --uid "${UID}" --gid "${GID}" --gecos "${USER}" "${USER}" && \
    usermod -aG sudo,video "${USER}" && \
    sh -c 'echo "${USER} ALL=(ALL:ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/${USER}'

# install github cli
RUN arch=$(dpkg --print-architecture) && \
    GH_VERSION=$(curl --silent "https://api.github.com/repos/cli/cli/releases/latest" | jq -r .tag_name | cut -d "v" -f 2) && \
    cli_filename="gh_${GH_VERSION}_linux_${arch}.deb" && \
    mkdir -p /tmp/ghcli && \
    wget --progress=dot:giga https://github.com/cli/cli/releases/download/v${GH_VERSION}/${cli_filename} -O /tmp/ghcli/${cli_filename} && \
    dpkg -i /tmp/ghcli/${cli_filename} && \
    rm -rf /tmp/ghcli


