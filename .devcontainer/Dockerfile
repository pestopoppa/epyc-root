# syntax=docker/dockerfile:1.7

# Based on Anthropic's Claude Code devcontainer template, with:
# - Codex CLI installed
# - Passwordless sudo for the non-root user
# - NO firewall / network restrictions (internet enabled)
# - tmux installed
# - C++ build tools (cmake, g++) for llama.cpp compilation
# - NUMA support (numactl, privileged mode)

ARG NODE_IMAGE=node:22.23.4-bookworm-slim
FROM ${NODE_IMAGE} AS node

ARG CLAUDE_CODE_VERSION=latest
ARG CODEX_VERSION=latest

# Build-time npm defaults.
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_PROGRESS=false \
    NPM_CONFIG_CACHE=/root/.npm \
    PATH="/usr/local/share/npm-global/bin:${PATH}"

RUN mkdir -p /usr/local/share/npm-global

# Install Claude Code + Codex CLI + pnpm in the node stage for faster rebuilds.
RUN --mount=type=cache,target=/root/.npm \
  npm install -g \
    "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
    "@openai/codex@${CODEX_VERSION}" \
  && corepack enable --install-directory /usr/local/share/npm-global/bin \
  && corepack prepare pnpm@latest --activate

FROM ubuntu:24.04

ARG TZ
ENV TZ="${TZ}"

ARG CLAUDE_CODE_VERSION=latest
ARG CODEX_VERSION=latest

# Install common dev tools.
# Note: we intentionally do NOT install iptables/ipset or ship a firewall script.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    less \
    procps \
    sudo \
    zsh \
    fish \
    unzip \
    openssh-client \
    gh \
    jq \
    vim \
    tmux \
    ncurses-term \
    git \
    ripgrep \
    zoxide \
    fd-find \
    numactl \
    libomp-dev \
    build-essential \
    cmake \
    lsof \
    netcat-openbsd \
    htop \
    time \
    bc \
    docker.io \
    clang-20 \
    git-lfs \
    sqlite3 \
    libdrm2 \
    libdrm-amdgpu1 \
    libelf1t64 \
    libxml2 \
    pciutils \
    perl \
  && rm -rf /var/lib/apt/lists/*
RUN if command -v fdfind >/dev/null 2>&1 && [ ! -e /usr/local/bin/fd ]; then \
    ln -s /usr/bin/fdfind /usr/local/bin/fd; \
  fi

# Ubuntu 24.04 ships git 2.43, but several workspace repos require >=2.48.
# Use the same git-core PPA as the host (2.56.x on noble).
RUN apt-get update \
  && apt-get install -y --no-install-recommends software-properties-common \
  && add-apt-repository -y ppa:git-core/ppa \
  && apt-get update \
  && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/*

# eMudhra intermediate CA key compromise (2026-10-17): distrust the two
# affected roots defensively. The 24.04 ca-certificates package is expected to
# have them removed already, in which case the sed is a no-op. The openssl
# check fails the build if either is still in the bundle.
# Node uses this bundle via NODE_OPTIONS=--use-openssl-ca (devcontainer.json).
# https://emudhra.we-have-a-problem.com/
RUN sed -i -e 's|^mozilla/emSign_ECC_Root_CA_-_G3\.crt$|!&|' \
           -e 's|^mozilla/Comodo_AAA_Services_root\.crt$|!&|' /etc/ca-certificates.conf \
  && update-ca-certificates --fresh > /dev/null \
  && ! (openssl crl2pkcs7 -nocrl -certfile /etc/ssl/certs/ca-certificates.crt \
        | openssl pkcs7 -print_certs -noout \
        | grep -qE 'AAA Certificate Services|emSign ECC Root CA - G3')

# Bring in node + npm from the official node image (fast, no apt deps).
COPY --from=node /usr/local/ /usr/local/
RUN node -v && npm -v

# Ensure git worktrees use relative paths by default.
# Wildcard safe.directory: all bind-mounted repos are trusted.
RUN git config --system worktree.useRelativePaths true \
  && git config --system --add safe.directory '*'

# Match host UID (1000) to avoid file ownership conflicts on bind mounts.
# Ubuntu 25.10 has a default 'ubuntu' user at uid 1000 — remove it first.
RUN userdel -r ubuntu 2>/dev/null || true; \
  if ! id -u "node" >/dev/null 2>&1; then \
    useradd -u 1000 -m -s /usr/bin/fish "node"; \
  fi

# Ensure default node user has access to the global npm prefix.
RUN mkdir -p /usr/local/share/npm-global \
  && chown -R "node:node" /usr/local/share

# Persist shell history across container rebuilds.
RUN mkdir -p /commandhistory \
  && touch /commandhistory/.bash_history /commandhistory/.zsh_history \
  && chown -R "node:node" /commandhistory \
  && cat >/etc/profile.d/00-commandhistory.sh <<'EOF'
# Set umask so files created in container are readable by host user
umask 022

# Persist interactive shell history in /commandhistory.
if [ -d /commandhistory ]; then
  export HISTSIZE=100000
  export HISTFILESIZE=200000

  if [ -n "${BASH_VERSION:-}" ]; then
    export HISTFILE=/commandhistory/.bash_history
    shopt -s histappend 2>/dev/null || true
    PROMPT_COMMAND="history -a; ${PROMPT_COMMAND:-}"
  fi

  if [ -n "${ZSH_VERSION:-}" ]; then
    export HISTFILE=/commandhistory/.zsh_history
    export SAVEHIST=200000
    setopt APPEND_HISTORY INC_APPEND_HISTORY SHARE_HISTORY HIST_IGNORE_ALL_DUPS HIST_REDUCE_BLANKS
  fi
fi
EOF

RUN echo '. /etc/profile.d/00-commandhistory.sh' >> /etc/bash.bashrc \
  && touch /etc/zsh/zshrc \
  && echo 'source /etc/profile.d/00-commandhistory.sh' >> /etc/zsh/zshrc

# Suppress core dumps for normal container processes.
# --ulimit core=0:0 in runArgs is the primary control; this is shell defense in depth.
RUN cat >/etc/profile.d/01-nocoredumps.sh <<'EOF'
ulimit -c 0 2>/dev/null || true
EOF

RUN chmod 0644 /etc/profile.d/01-nocoredumps.sh \
  && echo '. /etc/profile.d/01-nocoredumps.sh' >> /etc/bash.bashrc \
  && echo 'source /etc/profile.d/01-nocoredumps.sh' >> /etc/zsh/zshrc

# Fish does not read /etc/profile.d.
RUN mkdir -p /etc/fish/conf.d \
  && echo 'ulimit -c 0 2>/dev/null; or true' > /etc/fish/conf.d/nocoredumps.fish

# Helpful marker for shell prompts / scripts.
ENV DEVCONTAINER=true

# Create workspace + agent config dirs and set permissions.
RUN mkdir -p /workspace /home/node/.claude /home/node/.codex /home/node/.npm /home/node/.config/fish \
  && touch /home/node/.zshrc \
  && chown -R node:node /workspace /home/node/.claude /home/node/.codex /home/node/.npm /home/node/.config /home/node/.zshrc

WORKDIR /workspace

# Install global packages.
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH="${PATH}:/usr/local/share/npm-global/bin"
ENV NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_PROGRESS=false

# Switch to non-root for normal dev.
USER node

# Runtime npm cache should be writable by node.
ENV NPM_CONFIG_CACHE=/home/node/.npm

# Default shell + editor.
ENV HOME=/home/node
ENV XDG_CONFIG_HOME=/home/node/.config
ENV SHELL=/usr/bin/fish
ENV EDITOR=vim
ENV VISUAL=vim

# Install uv (pinned: workspace venvs depend on a stable managed-Python layout)
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv

# Ensure uv is on PATH for the node user.
ENV PATH="/home/node/.local/bin:${PATH}"

# Preinstall the managed Pythons the workspace venvs rely on. A container
# rebuild destroys these interpreters even though the venvs live on bind mounts.
RUN uv python install 3.11.17 3.12.15 3.13.17 3.14.9

# Passwordless sudo for the non-root user (for unattended / automation workflows).
USER root
RUN echo "node ALL=(root) NOPASSWD: ALL" > /etc/sudoers.d/yolo \
  && chmod 0440 /etc/sudoers.d/yolo \
  && usermod -aG docker node

# Global CLI tools baked into the image so they survive container rebuilds.
RUN --mount=type=cache,target=/root/.npm \
  npm install -g gitnexus@1.6.1 @opencode/cli@2.2.5 \
  && chown -R node:node /usr/local/share/npm-global/lib/node_modules/@opencode \
  && chown -h node:node /usr/local/share/npm-global/bin/opencode /usr/local/share/npm-global/bin/opencode2

# ruff (Python linter) baked in — apt has no ruff on questing 25.10, so install
# via uv to a system dir the node user can execute (survives container rebuilds).
RUN UV_TOOL_BIN_DIR=/usr/local/bin UV_TOOL_DIR=/opt/uv-tools uv tool install ruff \
  && chmod -R a+rX /opt/uv-tools && mkdir -p /home/node/.config/opencode /home/node/.local/share/opencode /home/node/.local/state/opencode /home/node/.cache/opencode && chown -R node:node /home/node/.config /home/node/.cache /home/node/.npm /home/node/.local/share/opencode /home/node/.local/state

# btop 1.3.2 with the AMD ROCm power fix (#819). apt btop 1.3.0 crashes in
# this container's RSMI init and never assigns pwr_usage (PWR shows 0W).
# The wrapper selects a compact layout when the terminal is under 35 rows.
COPY btop-patch.py btop-wrapper.sh /tmp/
RUN curl -fsSL https://github.com/aristocratos/btop/archive/refs/tags/v1.3.2.tar.gz -o /tmp/btop.tar.gz \
  && tar -xzf /tmp/btop.tar.gz -C /tmp \
  && python3 /tmp/btop-patch.py \
  && make -C /tmp/btop-1.3.2 GPU_SUPPORT=true -j"$(nproc)" \
  && install -m 0755 /tmp/btop-1.3.2/bin/btop /usr/local/bin/btop-bin \
  && install -m 0755 /tmp/btop-wrapper.sh /usr/local/bin/btop \
  && rm -rf /tmp/btop-1.3.2 /tmp/btop.tar.gz /tmp/btop-patch.py /tmp/btop-wrapper.sh \
  && mkdir -p /home/node/.config/btop /home/node/.config/btop-small/btop \
  && printf '%s\n' 'show_gpu_info = "On"' 'shown_boxes = "cpu mem net proc gpu0"' > /home/node/.config/btop/btop.conf \
  && printf '%s\n' 'show_gpu_info = "On"' 'shown_boxes = "cpu mem gpu0"' > /home/node/.config/btop-small/btop/btop.conf \
  && chown -R node:node /home/node/.config/btop /home/node/.config/btop-small

# Ubuntu 24.04 ships GCC 13; the old 25.10 base had GCC 15. Use the Ubuntu
# Toolchain PPA and make gcc/g++/cc/c++ point at 15 (13 stays available).
RUN apt-get update \
  && add-apt-repository -y ppa:ubuntu-toolchain-r/test \
  && apt-get update \
  && apt-get install -y --no-install-recommends gcc-15 g++-15 python3-yaml \
  && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 13 \
  && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-15 15 \
  && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-13 13 \
  && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-15 15 \
  && update-alternatives --set gcc /usr/bin/gcc-15 \
  && update-alternatives --set g++ /usr/bin/g++-15 \
  && update-alternatives --install /usr/bin/cc cc /usr/bin/gcc-15 100 \
  && update-alternatives --install /usr/bin/c++ c++ /usr/bin/g++-15 100 \
  && update-alternatives --set cc /usr/bin/gcc-15 \
  && update-alternatives --set c++ /usr/bin/g++-15 \
  && for py in /home/node/.local/bin/python3.11 /home/node/.local/bin/python3.12 /home/node/.local/bin/python3.13 /home/node/.local/bin/python3.14; do \
       uv pip install --python "$py" --system --break-system-packages --no-cache pyyaml; \
     done \
  && chown -R node:node /home/node/.local/share/uv/python \
  && rm -rf /var/lib/apt/lists/*

USER node
