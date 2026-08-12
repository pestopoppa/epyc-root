#!/bin/bash
set -euo pipefail
# Hook: PreToolUse → Bash
# Refuses `git checkout --`/`git restore`/`reset --hard`/`clean -f` forms that would
# DESTROY uncommitted work in the shared multi-writer tree.
#
# Origin: INC-20260812-destructive-revert — two agents, minutes apart, each ran
# `git checkout -- <path>` at a "clean up after myself" moment and silently
# discarded ANOTHER agent's uncommitted safety fix. Recovered both times by luck
# (an incidental cp), not process. A revert leaves no record: unstaged work it
# discards exists nowhere in git afterwards.
#
# PRECISION-TARGETED: reverting a CLEAN path is a no-op and passes. The block
# fires only when the target actually carries uncommitted content. Reverting
# your OWN work is legitimate — type the auditable override in the same command:
#     REVERT_VERIFIED=1 git checkout -- <path>
# which asserts you ran `git status --short <path>` and the content is yours or
# backed up.
#
# Like the pkill guard: this sees AGENT-TYPED commands, not script internals.

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[[ -z "$CMD" ]] && exit 0

SCAN="$(dirname "${BASH_SOURCE[0]}")/destructive_revert_scan.py"

_textual_hit() {
  echo "$CMD" | grep -qE '(^|[;&|]|\s)git\s+(-C\s+\S+\s+)?(checkout|restore|reset\s+--hard|clean\s)'
}

# Fail CLOSED only for the unambiguous textual form when the scanner cannot run.
if ! command -v python3 >/dev/null 2>&1 || [[ ! -f "$SCAN" ]]; then
  if _textual_hit; then
    echo "BLOCKED: the destructive-revert scanner is unavailable and this command contains a" >&2
    echo "git revert-class form. Refusing rather than guessing: run 'git status --short <path>'" >&2
    echo "first; if clean, re-run with REVERT_VERIFIED=1." >&2
    exit 2
  fi
  exit 0
fi

VERDICT=$(printf '%s' "$CMD" | HOOK_CWD="${CLAUDE_PROJECT_DIR:-$PWD}" python3 "$SCAN" 2>/dev/null) || VERDICT="scanner-error"

case "$VERDICT" in
  allow)
    exit 0
    ;;
  block:revert-dirty:*)
    DETAIL="${VERDICT#block:revert-dirty:}"
    echo "BLOCKED: this revert targets a path carrying UNCOMMITTED work (${DETAIL})." >&2
    echo "In a five-writer tree that content may be ANOTHER AGENT'S in-flight fix — a revert" >&2
    echo "deletes it with no reflog, no undo, no trace (INC-20260812: it happened twice in one" >&2
    echo "night, both at 'clean up after myself' moments; a failed scripted edit is the most" >&2
    echo "likely moment to reach for a revert and the worst moment to do it blind — the anchor" >&2
    echo "fails precisely when the file is not as you expected, i.e. when someone else changed it)." >&2
    echo "" >&2
    echo "Do instead: git status --short <path>  → if the changes are NOT yours, leave them and" >&2
    echo "ask on the bus; if yours (or backed up), re-run with:  REVERT_VERIFIED=1 <same command>" >&2
    exit 2
    ;;
  block:repo-destructive:*)
    echo "BLOCKED: repo-wide destructive form (${VERDICT#block:repo-destructive:}) on a tree with" >&2
    echo "uncommitted modifications — some of which may be other agents' in-flight work." >&2
    echo "git status --short first; REVERT_VERIFIED=1 to proceed if verified yours/backed up." >&2
    exit 2
    ;;
  block:clean-untracked:*)
    echo "BLOCKED: git clean -f with UNTRACKED files present. Untracked work exists nowhere in" >&2
    echo "git — clean deletes it unrecoverably (tonight's merge blocker and two orphaned fixes" >&2
    echo "were exactly such files). git status --short first; REVERT_VERIFIED=1 if verified." >&2
    exit 2
    ;;
  *)
    if _textual_hit; then
      echo "BLOCKED: the destructive-revert scanner errored on a revert-class command." >&2
      echo "Refusing rather than guessing. git status --short first; REVERT_VERIFIED=1 to proceed." >&2
      exit 2
    fi
    exit 0
    ;;
esac
