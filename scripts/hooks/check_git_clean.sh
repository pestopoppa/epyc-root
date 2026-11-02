#!/bin/bash
set -euo pipefail
# Hook: PreToolUse -> Bash
# Refuses an agent-typed `git clean` that would DELETE untracked files (AUD-10).
#
# Origin: 2026-08-12 08:20Z — a `git clean` destroyed an untracked corpus 27-47 minutes
# after the destructive-revert guard (03e17111) was reverted at 3d8800e6. That guard's
# `clean -f` branch would have refused it (149 untracked entries present) and was not
# among the two HIGHs that sank the guard. Operator decision 2026-11-02 (decision tool,
# BRF-T5-2): re-land that single branch only; checkout/restore/reset stay out of scope.
#
# PRECISION: the scanner asks git (`git clean ... -n`) what the command would remove and
# refuses only a non-empty answer. Dry runs, interactive cleans and cleans of a tree with
# nothing untracked pass.
#
# Override, as in 03e17111, typed in the same command: REVERT_VERIFIED=1 git clean ...
# Scope: AGENT-TYPED Bash only — a clean inside an invoked script is outside its universe.
# Tests: scripts/hooks/tests/test_git_clean_guard.py

INPUT=$(cat)
command -v jq >/dev/null 2>&1 || exit 0
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || exit 0
case "$TOOL" in Bash|"") ;; *) exit 0 ;; esac
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
[[ -z "$CMD" ]] && exit 0
HOOK_CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null) || HOOK_CWD=""
HOOK_CWD="${HOOK_CWD:-${CLAUDE_PROJECT_DIR:-$PWD}}"

SCAN="$(dirname "${BASH_SOURCE[0]}")/git_clean_scan.py"

_textual_hit() {
  printf '%s' "$CMD" | grep -E '(^|[;&|(`]|\s)git(\s+-[-A-Za-z]+(\s+\S+)?)*\s+clean(\s|$)' >/dev/null
}

# Fail CLOSED only for the unambiguous textual form when the scanner cannot run.
if ! command -v python3 >/dev/null 2>&1 || [[ ! -f "$SCAN" ]]; then
  if _textual_hit; then
    echo "BLOCKED: the git-clean scanner is unavailable and this command runs git clean." >&2
    echo "Refusing rather than guessing. Run 'git clean -n' first; if every listed file is yours" >&2
    echo "or backed up, re-run with REVERT_VERIFIED=1 in the same command." >&2
    exit 2
  fi
  exit 0
fi

VERDICT=$(printf '%s' "$CMD" | HOOK_CWD="$HOOK_CWD" python3 "$SCAN" 2>/dev/null) || VERDICT="scanner-error"

case "$VERDICT" in
  allow)
    exit 0
    ;;
  block:clean-untracked:*)
    DETAIL="${VERDICT#block:clean-untracked:}"
    REPO="${DETAIL%%:*}"; DETAIL="${DETAIL#*:}"
    COUNT="${DETAIL%%:*}"; FIRST="${DETAIL#*:}"
    echo "BLOCKED: this git clean would DELETE ${COUNT} untracked path(s) in ${REPO}" >&2
    echo "         (first: ${FIRST//;/, })." >&2
    echo "Untracked files exist nowhere in git: no reflog, no stash, no undo. In a tree shared by" >&2
    echo "several sessions they are often another session's in-flight work (2026-08-12 08:20Z: a" >&2
    echo "clean destroyed an untracked corpus; AUD-10)." >&2
    echo "" >&2
    echo "Do instead: run the same command with -n and read the list. Move or delete only your own" >&2
    echo "files by name. If every listed path is yours or backed up, re-run with:" >&2
    echo "    REVERT_VERIFIED=1 <same command>" >&2
    exit 2
    ;;
  block:clean-unresolvable:*)
    echo "BLOCKED: git clean with -f where the scanner cannot tell which tree it runs in" >&2
    echo "(${VERDICT#block:clean-unresolvable:}). Use an absolute 'cd' or 'git -C <path>'," >&2
    echo "check with -n first, then REVERT_VERIFIED=1 <same command> if verified." >&2
    exit 2
    ;;
  *)
    if _textual_hit; then
      echo "BLOCKED: the git-clean scanner errored on a command that runs git clean." >&2
      echo "Refusing rather than guessing. Check with 'git clean -n' first; REVERT_VERIFIED=1 if verified." >&2
      exit 2
    fi
    exit 0
    ;;
esac
