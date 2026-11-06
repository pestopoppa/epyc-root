#!/bin/bash
set -euo pipefail
# Hook: PreToolUse -> Bash
# Refuses `git worktree repair` in /workspace, the shared epyc-inference-research and
# epyc-orchestrator clones, and their worktrees.
#
# Origin: 2026-11-06 21:19Z -- a subagent ran `git worktree repair` in
# /mnt/raid0/llm/epyc-inference-research (extensions.worktreeConfig=true). repair set
# core.bare=true in the shared config, so `git status` broke and serialized_push refused
# every push until it was reset by hand. Operator: "Add guard" (2026-11-06).
# Scope: agent-typed Bash only. Target repo = `git -C DIR` if given, else the hook cwd.
# Tests: scripts/hooks/tests/test_worktree_repair_guard.py

INPUT=$(cat)
command -v jq >/dev/null 2>&1 || exit 0
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || exit 0
case "$TOOL" in Bash|"") ;; *) exit 0 ;; esac
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
[[ -z "$CMD" ]] && exit 0
HOOK_CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null) || HOOK_CWD=""
HOOK_CWD="${HOOK_CWD:-${CLAUDE_PROJECT_DIR:-$PWD}}"

# git [global opts incl. -C DIR / -c k=v] worktree repair
RE='(^|[;&|(`]|[[:space:]])git((([[:space:]]+-C[[:space:]]+[^[:space:]]+)|([[:space:]]+-c[[:space:]]+[^[:space:]]+)|([[:space:]]+--?[A-Za-z][-A-Za-z=]*))*)[[:space:]]+worktree[[:space:]]+repair([[:space:]]|$|[;&|)])'
[[ "$CMD" =~ $RE ]] || exit 0

OPTS="${BASH_REMATCH[2]}"
TARGET="$HOOK_CWD"
if [[ "$OPTS" =~ -C[[:space:]]+([^[:space:]]+) ]]; then
  TARGET="${BASH_REMATCH[1]}"
  TARGET="${TARGET//\"/}"; TARGET="${TARGET//\'/}"
  [[ "$TARGET" != /* ]] && TARGET="$HOOK_CWD/$TARGET"
fi
TARGET=$(realpath -m "$TARGET" 2>/dev/null || echo "$TARGET")

PROTECTED=(/workspace /mnt/raid0/llm/epyc-inference-research /mnt/raid0/llm/epyc-orchestrator /mnt/raid0/llm/worktrees)
for P in "${PROTECTED[@]}"; do
  RP=$(realpath -m "$P" 2>/dev/null || echo "$P")
  if [[ "$TARGET" == "$P" || "$TARGET" == "$P"/* || "$TARGET" == "$RP" || "$TARGET" == "$RP"/* ]]; then
    {
      echo "BLOCKED: 'git worktree repair' in $TARGET."
      echo "Hazard: these clones set extensions.worktreeConfig=true. repair can write core.bare=true"
      echo "into the shared config, after which 'git status' fails ('this operation must be run in"
      echo "a work tree') and serialized_push refuses every push. Incident 2026-11-06 21:19Z in"
      echo "epyc-inference-research. Do not run repair/prune/gc on a shared clone; if a worktree"
      echo "link is broken, report it to the owning session (check: git config --get core.bare)."
    } >&2
    exit 2
  fi
done
exit 0
