#!/bin/bash
set -euo pipefail

GITHUB_ORG="${GITHUB_ORG:-pestopoppa}"
REPOS_DIR="$(cd "$(dirname "$0")/.." && pwd)/repos"
mkdir -p "$REPOS_DIR"

repos=(
    epyc-orchestrator
    epyc-inference-research
    epyc-llama:llama.cpp  # remote name differs
)

for entry in "${repos[@]}"; do
    IFS=: read -r local remote <<< "$entry"
    remote="${remote:-$local}"
    dest="$REPOS_DIR/$local"
    if [ -d "$dest" ]; then
        echo "  $local already cloned"
    else
        echo "Cloning $remote -> $dest"
        git clone "https://github.com/$GITHUB_ORG/$remote.git" "$dest"
    fi
done

echo "All repos ready in $REPOS_DIR"
