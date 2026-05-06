#!/bin/bash
set -euo pipefail
# Post-commit hook (Claude Code PostToolUse on Bash git commit/merge):
# Incrementally refresh the KB-RAG index for any markdown files in HEAD's diff.
#
# Coexists with the GitNexus PostToolUse hook (which handles code).
# Runs as a thin shell wrapper; heavy lifting is in src/retrieval/kb_rag.py.
#
# Activation: Claude Code's PostToolUse hook configuration in
# .claude/settings.json or settings.local.json should call this script
# after `git commit` and `git merge`.
#
# Per handoffs/active/internal-kb-rag.md K5.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ORCHESTRATOR="${KB_RAG_ORCHESTRATOR:-/workspace/repos/epyc-orchestrator}"
PYTHON="${KB_RAG_PYTHON:-${ORCHESTRATOR}/.venv/bin/python}"

# Only run if the orchestrator + index infrastructure is set up.
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

if [[ ! -d "$ORCHESTRATOR/src/retrieval" ]]; then
  exit 0
fi

# Collect markdown changes from the last commit.
# Falls back gracefully if HEAD~1 doesn't exist (initial commit / shallow clone).
if ! git rev-parse --quiet --verify HEAD~1 >/dev/null 2>&1; then
  CHANGED=$(git show --name-only --pretty=format: HEAD)
else
  CHANGED=$(git diff --name-only HEAD~1 HEAD)
fi

# Filter to markdown files; rewrite to absolute paths from REPO_ROOT.
MD_FILES=$(echo "$CHANGED" | awk -v r="$REPO_ROOT" '/\.md$/ {print r"/"$0}')

if [[ -z "$MD_FILES" ]]; then
  exit 0
fi

# Run the incremental updater. Errors are logged but do not block the commit
# (this is a post-commit hook; the commit has already landed).
echo "$MD_FILES" | xargs "$PYTHON" "$ORCHESTRATOR/scripts/kb_rag/cli.py" update --files 2>&1 | tail -10 || {
  echo "kb_rag update failed (non-fatal)" >&2
  exit 0
}
