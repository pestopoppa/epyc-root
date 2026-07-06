#!/bin/bash
set -euo pipefail
# One-time setup: symlink Hermes config from repo to ~/.hermes/
# Run this after ./scripts/install.sh completes in /mnt/raid0/llm/hermes-agent

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_SRC="${SCRIPT_DIR}/hermes-config.yaml"
CONFIG_DST="${HOME}/.hermes/config.yaml"

echo "=== Hermes Agent Setup ==="

# 1. Verify hermes-agent is installed
if [[ ! -d "${HOME}/.hermes/hermes-agent" ]]; then
    echo "ERROR: Hermes not installed. Run first:"
    echo "  cd /mnt/raid0/llm/hermes-agent && ./scripts/install.sh"
    exit 1
fi

# 2. Symlink config
if [[ -f "$CONFIG_DST" && ! -L "$CONFIG_DST" ]]; then
    echo "Backing up existing config to ${CONFIG_DST}.bak"
    mv "$CONFIG_DST" "${CONFIG_DST}.bak"
fi

ln -sf "$CONFIG_SRC" "$CONFIG_DST"
echo "Symlinked: $CONFIG_DST -> $CONFIG_SRC"

# 3. Symlink HERMES.md into hermes-agent dir (loaded as context file on startup)
HERMES_MD_SRC="${SCRIPT_DIR}/HERMES.md"
HERMES_MD_DST="/mnt/raid0/llm/hermes-agent/HERMES.md"
if [[ -f "$HERMES_MD_SRC" ]]; then
    ln -sf "$HERMES_MD_SRC" "$HERMES_MD_DST"
    echo "Symlinked: $HERMES_MD_DST -> $HERMES_MD_SRC"
fi

# 4. Sync EPYC Hermes skills into ~/.hermes/skills/epyc/
EPYC_SKILLS_SRC="${SCRIPT_DIR}/skills"
EPYC_SKILLS_DST="${HOME}/.hermes/skills/epyc"
if [[ -d "$EPYC_SKILLS_SRC" ]]; then
    if [[ -e "$EPYC_SKILLS_DST" && ! -d "$EPYC_SKILLS_DST" ]]; then
        rm -f "$EPYC_SKILLS_DST"
    fi
    mkdir -p "$EPYC_SKILLS_DST"
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --delete "${EPYC_SKILLS_SRC}/" "${EPYC_SKILLS_DST}/"
        echo "Synced: $EPYC_SKILLS_DST <- $EPYC_SKILLS_SRC"
    else
        rm -rf "$EPYC_SKILLS_DST"
        mkdir -p "$EPYC_SKILLS_DST"
        cp -a "${EPYC_SKILLS_SRC}/." "$EPYC_SKILLS_DST/"
        echo "Copied: $EPYC_SKILLS_DST <- $EPYC_SKILLS_SRC"
    fi
fi

# 5. Sync EPYC Hermes plugins into ~/.hermes/plugins/<plugin>/
EPYC_PLUGINS_SRC="${SCRIPT_DIR}/plugins"
EPYC_PLUGINS_DST="${HOME}/.hermes/plugins"
if [[ -d "$EPYC_PLUGINS_SRC" ]]; then
    mkdir -p "$EPYC_PLUGINS_DST"
    for plugin_src in "${EPYC_PLUGINS_SRC}"/*; do
        [[ -d "$plugin_src" ]] || continue
        plugin_name="$(basename "$plugin_src")"
        plugin_dst="${EPYC_PLUGINS_DST}/${plugin_name}"
        mkdir -p "$plugin_dst"
        if command -v rsync >/dev/null 2>&1; then
            rsync -a --delete "${plugin_src}/" "${plugin_dst}/"
            echo "Synced plugin: ${plugin_dst} <- ${plugin_src}"
        else
            rm -rf "$plugin_dst"
            mkdir -p "$plugin_dst"
            cp -a "${plugin_src}/." "$plugin_dst/"
            echo "Copied plugin: ${plugin_dst} <- ${plugin_src}"
        fi
    done
fi

# 6. Create .env with no-op API key (prevents Hermes from prompting for one)
ENV_FILE="${HOME}/.hermes/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" << 'ENVEOF'
# Local-only mode — no cloud API keys needed
OPENAI_API_KEY=sk-no-key
OPENAI_BASE_URL=http://localhost:8099/v1
ENVEOF
    echo "Created: $ENV_FILE (local-only mode)"
else
    echo "Exists: $ENV_FILE (not overwritten)"
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1. Start backend:  ${SCRIPT_DIR}/launch_hermes_backend.sh"
echo "  2. Start Hermes:   hermes  (or: cd /mnt/raid0/llm/hermes-agent && python cli.py)"
echo "  3. Think tokens:   export HERMES_DISABLE_CHAT_TEMPLATE=1 or set HERMES_CHAT_TEMPLATE_FILE=/path/to/template.jinja"
