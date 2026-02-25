#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# 1. Clone repos
"$SCRIPT_DIR/clone-repos.sh"

# 2. Install orchestrator
cd "$ROOT_DIR/repos/epyc-orchestrator"
if [ -f "pyproject.toml" ]; then
    pip install -e ".[dev]" 2>/dev/null || echo "Install manually: pip install -e '.[dev]'"
fi

# 3. Copy .env.example if no .env
if [ ! -f "$ROOT_DIR/repos/epyc-orchestrator/.env" ] && [ -f "$ROOT_DIR/repos/epyc-orchestrator/.env.example" ]; then
    cp "$ROOT_DIR/repos/epyc-orchestrator/.env.example" "$ROOT_DIR/repos/epyc-orchestrator/.env"
    echo "Created .env from .env.example -- edit paths for your system"
fi

# 4. Verify llama.cpp build
if [ -d "$ROOT_DIR/repos/epyc-llama" ]; then
    if [ ! -f "$ROOT_DIR/repos/epyc-llama/build/bin/llama-server" ]; then
        echo "llama-server not built. Run: cd repos/epyc-llama && cmake -B build && cmake --build build -j\$(nproc)"
    fi
fi

echo "Setup complete. Run 'cd repos/epyc-orchestrator && orch --help' to get started."
