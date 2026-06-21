#!/bin/bash
set -euo pipefail
# Post-commit hook (Claude Code PostToolUse on Bash git commit/merge):
# Incrementally refresh the KB-RAG index from the project-wiki source manifest.
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

COMPILE_SOURCES="${REPO_ROOT}/.claude/skills/project-wiki/scripts/compile_sources.py"

if [[ ! -f "$COMPILE_SOURCES" ]]; then
  exit 0
fi

TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/kb-rag-manifest.XXXXXX")
trap 'rm -rf "$TMP_DIR"' EXIT
DELTA_MANIFEST="${TMP_DIR}/source_manifest_delta.json"
MANIFEST_ERR="${TMP_DIR}/source_manifest.err"

if ! "$PYTHON" "$COMPILE_SOURCES" --changed-since-manifest >"$DELTA_MANIFEST" 2>"$MANIFEST_ERR"; then
  if grep -q "manifest not found" "$MANIFEST_ERR"; then
    "$PYTHON" "$COMPILE_SOURCES" --full >"$DELTA_MANIFEST" 2>"$MANIFEST_ERR" || {
      tail -10 "$MANIFEST_ERR" >&2
      exit 0
    }
  else
    tail -10 "$MANIFEST_ERR" >&2
    exit 0
  fi
fi

if ! "$PYTHON" - "$DELTA_MANIFEST" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf-8"))
if manifest.get("sources") or manifest.get("removed_sources"):
    raise SystemExit(0)
raise SystemExit(1)
PY
then
  exit 0
fi

# Run the incremental updater. Errors are logged but do not block the commit
# (this is a post-commit hook; the commit has already landed). Keep the saved
# source manifest unchanged on failure so the next hook run can retry.
"$PYTHON" "$ORCHESTRATOR/scripts/kb_rag/cli.py" update \
  --manifest "$DELTA_MANIFEST" \
  --manifest-root "$REPO_ROOT" 2>&1 | tail -10 || {
  echo "kb_rag update failed (non-fatal)" >&2
  exit 0
}

"$PYTHON" "$COMPILE_SOURCES" --full --write-manifest >/dev/null 2>&1 || {
  echo "project-wiki source manifest refresh failed (non-fatal)" >&2
  exit 0
}
