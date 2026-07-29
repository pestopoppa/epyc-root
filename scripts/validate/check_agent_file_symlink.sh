#!/bin/bash
set -euo pipefail

# Verify that AGENTS.md is a symlink to CLAUDE.md (single source of truth
# for both Claude Code and Codex / AGENTS.md-consuming agents).
#
# Usage:
#   scripts/validate/check_agent_file_symlink.sh                 # check $PWD
#   scripts/validate/check_agent_file_symlink.sh <repo_dir>      # check named repo
#   scripts/validate/check_agent_file_symlink.sh --all           # check all known owned repos
#
# Exit codes:
#   0 — symlink is correct (or only CLAUDE.md exists, no AGENTS.md)
#   1 — drift detected (AGENTS.md is a regular file, or symlink targets
#       something other than CLAUDE.md)
#   2 — usage error (e.g., dir doesn't exist)
#
# Background: as of 2026-05-27, AGENTS.md and CLAUDE.md are kept in sync
# by making AGENTS.md a symlink to CLAUDE.md in each of the three owned
# repos (epyc-root, epyc-orchestrator, epyc-inference-research). This
# validator fails fast if any future agent-file refactor accidentally
# turns AGENTS.md back into a regular file, which would re-diverge what
# Claude Code and Codex see.

OWNED_REPOS=(
    /mnt/raid0/llm/epyc-root
    /mnt/raid0/llm/epyc-orchestrator
    /mnt/raid0/llm/epyc-inference-research
)

check_one() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        printf "✗ %s: directory does not exist\n" "$dir" >&2
        return 2
    fi
    local agents="$dir/AGENTS.md"
    local claude="$dir/CLAUDE.md"

    if [[ ! -e "$claude" ]]; then
        printf "✗ %s: CLAUDE.md missing — cannot serve as symlink target\n" "$dir" >&2
        return 1
    fi
    if [[ ! -e "$agents" && ! -L "$agents" ]]; then
        printf "✗ %s: AGENTS.md missing (expected symlink to CLAUDE.md)\n" "$dir" >&2
        return 1
    fi
    if [[ ! -L "$agents" ]]; then
        printf "✗ %s/AGENTS.md is a regular file — should be a symlink to CLAUDE.md\n" "$dir" >&2
        return 1
    fi
    local target
    target="$(readlink "$agents")"
    if [[ "$target" != "CLAUDE.md" ]]; then
        printf "✗ %s/AGENTS.md → %s — expected CLAUDE.md\n" "$dir" "$target" >&2
        return 1
    fi
    printf "✓ %s: AGENTS.md → CLAUDE.md\n" "$dir"
    return 0
}

mode="${1:-.}"

if [[ "$mode" == "--all" ]]; then
    fail=0
    for repo in "${OWNED_REPOS[@]}"; do
        check_one "$repo" || fail=1
    done
    exit "$fail"
elif [[ "$mode" == "-h" || "$mode" == "--help" ]]; then
    sed -n '3,22p' "$0"
    exit 0
else
    check_one "$(cd "$mode" && pwd)"
fi
