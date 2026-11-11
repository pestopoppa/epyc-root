#!/bin/bash
set -euo pipefail
# Hook: PreToolUse -> Bash
# DP-4: refuses an agent-typed git WRITE (add/commit/checkout/...) in a SHARED child clone
# (/mnt/raid0/llm/<name>) while that clone has a live sequencer (CHERRY_PICK_HEAD, MERGE_HEAD,
# REVERT_HEAD, REBASE_HEAD, rebase-merge/apply) or unmerged paths. See git_sequencer_scan.py.
# Override for the session that OWNS the sequence: SEQUENCER_OWNER=1 git ...
# Tests: scripts/hooks/tests/test_git_sequencer_guard.py

INPUT=$(cat)
command -v jq >/dev/null 2>&1 || exit 0
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || exit 0
case "$TOOL" in Bash|"") ;; *) exit 0 ;; esac
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
[[ -z "$CMD" ]] && exit 0
[[ "$CMD" =~ (^|[^A-Za-z0-9_-])git([[:space:]]|$) ]] || exit 0
HOOK_CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null) || HOOK_CWD=""
HOOK_CWD="${HOOK_CWD:-${CLAUDE_PROJECT_DIR:-$PWD}}"
SCAN="$(dirname "${BASH_SOURCE[0]}")/git_sequencer_scan.py"
# Fail OPEN: this is a coordination guard, not a data-loss guard; a scanner fault must not wedge git.
command -v python3 >/dev/null 2>&1 && [[ -f "$SCAN" ]] || exit 0
VERDICT=$(printf '%s' "$CMD" | HOOK_CWD="$HOOK_CWD" python3 "$SCAN" 2>/dev/null) || exit 0
case "$VERDICT" in
  block:sequencer:*)
    D="${VERDICT#block:sequencer:}"
    REPO="${D%%:*}"; D="${D#*:}"; VERB="${D%%:*}"; STATE="${D#*:}"
    echo "BLOCKED: 'git ${VERB}' in shared clone ${REPO}, which has a live sequencer: ${STATE//;/, }." >&2
    echo "That index/sequencer belongs to another session's in-flight operation; writing into it" >&2
    echo "contaminates their commit (2026-08-12, 42 files staged into a live cherry-pick; DP-4)." >&2
    echo "Do instead: work in your own git worktree of this repo, or wait for the owner to finish." >&2
    echo "If YOU own the sequence: SEQUENCER_OWNER=1 <same command>." >&2
    exit 2
    ;;
  *) exit 0 ;;
esac
