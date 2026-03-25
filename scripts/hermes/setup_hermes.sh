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

# 4. Create .env with no-op API key (prevents Hermes from prompting for one)
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
