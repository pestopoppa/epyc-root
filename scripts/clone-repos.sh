#!/bin/bash
# Set up /workspace/repos/ as a single source of truth for sibling repos.
#
# History (2026-05-22): this script used to do plain `git clone` for each
# repo into /workspace/repos/. Combined with a CLAUDE.md doc that *claimed*
# the clones were symlinks, this caused parallel agent sessions to evolve
# divergent clones of the same repo without realizing it — each session
# pushed independently to origin and stomped on the other's work.
#
# Fix: this script now prefers symlinking /workspace/repos/<name> to the
# canonical clone at /mnt/raid0/llm/<MNT_PATH> if one exists. Falls back
# to a fresh `git clone` only when no canonical tree exists on the host.
# Idempotent: re-running converts any pre-existing plain-dir clone into
# a symlink (after backing it up), so a session that accidentally created
# divergent clones can be re-converged with one invocation.

set -euo pipefail

GITHUB_ORG="${GITHUB_ORG:-pestopoppa}"
REPOS_DIR="$(cd "$(dirname "$0")/.." && pwd)/repos"
MNT_BASE="${MNT_BASE:-/mnt/raid0/llm}"
DRY_RUN="${DRY_RUN:-0}"
BACKUP_TS="$(date +%Y-%m-%d-%H%M%S)"

mkdir -p "$REPOS_DIR"

# Format: <link_name>:<github_repo>:<mnt_subpath>
# - link_name = the directory name under /workspace/repos/
# - github_repo = repo name under $GITHUB_ORG (used for fallback `git clone`)
# - mnt_subpath = directory under $MNT_BASE/ to symlink to (often == link_name,
#   but llama.cpp is checked out as `llama.cpp` on the host)
repos=(
    epyc-orchestrator:epyc-orchestrator:epyc-orchestrator
    epyc-inference-research:epyc-inference-research:epyc-inference-research
    epyc-llama:llama.cpp:llama.cpp
)

run() {
    if [ "$DRY_RUN" = "1" ]; then
        echo "  DRY-RUN: $*"
    else
        eval "$*"
    fi
}

for entry in "${repos[@]}"; do
    IFS=: read -r link_name remote_name mnt_subpath <<< "$entry"
    dest="$REPOS_DIR/$link_name"
    canonical="$MNT_BASE/$mnt_subpath"

    if [ -L "$dest" ]; then
        actual_target="$(readlink "$dest")"
        if [ "$actual_target" = "$canonical" ]; then
            echo "  $link_name: already symlinked to $canonical (ok)"
        else
            echo "  $link_name: symlinked to $actual_target (expected $canonical) — leaving as-is"
        fi
        continue
    fi

    if [ -d "$dest" ]; then
        # A plain directory exists. If a canonical tree also exists, convert
        # to a symlink (after backing up). Otherwise leave it alone.
        if [ -d "$canonical/.git" ]; then
            echo "  $link_name: converting plain clone to symlink → $canonical"
            echo "    (existing tree → $dest.bak-$BACKUP_TS — delete manually after verifying)"
            run "mv \"$dest\" \"$dest.bak-$BACKUP_TS\""
            run "ln -s \"$canonical\" \"$dest\""
        else
            echo "  $link_name: already cloned (no canonical at $canonical, keeping as plain dir)"
        fi
        continue
    fi

    # Fresh setup: prefer symlink, fall back to clone.
    if [ -d "$canonical/.git" ]; then
        echo "  $link_name: linking → $canonical"
        run "ln -s \"$canonical\" \"$dest\""
    else
        echo "  $link_name: no canonical at $canonical, cloning $GITHUB_ORG/$remote_name"
        run "git clone \"https://github.com/$GITHUB_ORG/$remote_name.git\" \"$dest\""
    fi
done

echo ""
echo "All repos ready in $REPOS_DIR"
if [ "$DRY_RUN" = "1" ]; then
    echo "(DRY_RUN was set — no actual changes made)"
fi
