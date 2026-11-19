#!/bin/bash
set -euo pipefail
# Hook: PreToolUse -> Bash
# Refuses `git worktree repair|prune`, `git gc` (incl. --auto) and `git maintenance run` (gc task)
# in /workspace, the shared epyc-inference-research and
# epyc-orchestrator clones, and their worktrees.
#
# Origin: 2026-11-06 21:19Z -- a subagent ran `git worktree repair` in
# /mnt/raid0/llm/epyc-inference-research (extensions.worktreeConfig=true). repair set
# core.bare=true in the shared config, so `git status` broke and serialized_push refused
# every push until it was reset by hand. Operator: "Add guard" (2026-11-06).
# Scope: agent-typed Bash only. Target repo = `git -C DIR` if given, else the hook cwd.
# 2026-11-06 operator: "yes, block prune and gc too" (CLAUDE.md: prune and gc destroyed all five
# lanes on 2026-08-12 because the repo is reachable at two path depths).
# `git worktree remove|list` are NOT blocked.
# Tests: scripts/hooks/tests/test_worktree_repair_guard.py

INPUT=$(cat)
command -v jq >/dev/null 2>&1 || exit 0
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || exit 0
case "$TOOL" in Bash|"") ;; *) exit 0 ;; esac
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
[[ -z "$CMD" ]] && exit 0
HOOK_CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null) || HOOK_CWD=""
HOOK_CWD="${HOOK_CWD:-${CLAUDE_PROJECT_DIR:-$PWD}}"

# git [global opts incl. -C DIR / -c k=v] <verb>
PRE='(^|[;&|(`]|[[:space:]])git((([[:space:]]+-C[[:space:]]+[^[:space:]]+)|([[:space:]]+-c[[:space:]]+[^[:space:]]+)|([[:space:]]+--?[A-Za-z][-A-Za-z=]*))*)[[:space:]]+'
END='([[:space:]]|$|[;&|)])'
RE="${PRE}(worktree[[:space:]]+(repair|prune)|gc|maintenance[[:space:]]+run)${END}"
[[ "$CMD" =~ $RE ]] || exit 0
OPTS="${BASH_REMATCH[2]}"
FULL="${BASH_REMATCH[0]}"
VERB="${BASH_REMATCH[7]}"
VERB="${VERB%%[;&|)]}"; VERB="${VERB//[[:space:]]/ }"; VERB="${VERB% }"
if [[ "$VERB" == maintenance* ]]; then
  # block unless an explicit --task list is given that excludes gc (default run includes gc)
  REST="${CMD#*"$FULL"}"
  TRE='--task[=[:space:]]+[a-z-]+'; GRE='--task[=[:space:]]+gc'
  if [[ "$REST" =~ $TRE ]] && ! [[ "$REST" =~ $GRE ]]; then exit 0; fi
fi

TARGET="$HOOK_CWD"
if [[ "$OPTS" =~ -C[[:space:]]+([^[:space:]]+) ]]; then
  TARGET="${BASH_REMATCH[1]}"
  TARGET="${TARGET//\"/}"; TARGET="${TARGET//\'/}"
  [[ "$TARGET" != /* ]] && TARGET="$HOOK_CWD/$TARGET"
fi
TARGET=$(realpath -m "$TARGET" 2>/dev/null || echo "$TARGET")

# Resolve the target repository: a linked worktree anywhere shares its main clone's common dir.
TCOMMON=$(git -C "$TARGET" rev-parse --git-common-dir 2>/dev/null || true)
if [[ -n "$TCOMMON" ]]; then
  [[ "$TCOMMON" != /* ]] && TCOMMON="$TARGET/$TCOMMON"
  TCOMMON=$(realpath -m "$TCOMMON" 2>/dev/null || echo "$TCOMMON")
fi
PROT_REPOS=(/workspace /mnt/raid0/llm/epyc-inference-research /mnt/raid0/llm/epyc-orchestrator)
REPO_HIT=0
if [[ -n "$TCOMMON" ]]; then
  for R in "${PROT_REPOS[@]}"; do
    RC=$(git -C "$R" rev-parse --git-common-dir 2>/dev/null || true)
    [[ -z "$RC" ]] && continue
    [[ "$RC" != /* ]] && RC="$R/$RC"
    RC=$(realpath -m "$RC" 2>/dev/null || echo "$RC")
    [[ "$TCOMMON" == "$RC" ]] && REPO_HIT=1
  done
fi

PROTECTED=(/workspace /mnt/raid0/llm/epyc-inference-research /mnt/raid0/llm/epyc-orchestrator /mnt/raid0/llm/worktrees)
for P in "${PROTECTED[@]}"; do
  RP=$(realpath -m "$P" 2>/dev/null || echo "$P")
  if [[ "$REPO_HIT" == 1 || "$TARGET" == "$P" || "$TARGET" == "$P"/* || "$TARGET" == "$RP" || "$TARGET" == "$RP"/* ]]; then
    {
      echo "BLOCKED: 'git $VERB' in $TARGET."
      echo "Rule (CLAUDE.md, Process Management): worktree prune and gc destroyed all five lanes on"
      echo "2026-08-12 because the repo is reachable at two path depths; repair can also write"
      echo "core.bare=true into the shared config (incident 2026-11-06 21:19Z), breaking git status and"
      echo "serialized_push. Do not run repair/prune/gc/maintenance-gc on a shared clone; report to the"
      echo "owning session. 'git worktree remove' and 'list' are allowed."
    } >&2
    exit 2
  fi
done
exit 0
