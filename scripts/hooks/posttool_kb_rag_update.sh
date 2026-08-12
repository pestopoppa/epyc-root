#!/bin/bash
set -euo pipefail
# Hook: PostToolUse → Bash
# Filters for git commands that change HEAD (commit, merge, pull, rebase, cherry-pick)
# then delegates to .claude/hooks/post_commit_kb_rag_update.sh which incrementally
# refreshes the KB-RAG index for changed markdown files.
#
# Per handoffs/active/internal-kb-rag.md K5 + .claude/skills/kb-search/SKILL.md.
#
# Hook protocol: receives JSON on stdin with shape:
#   {"tool_input": {"command": "..."}, "tool_response": {...}, ...}
# Exits 0 on success or non-matching command. Errors are non-fatal — KB-RAG
# update failures must NOT block subsequent tool use.

# ---------------------------------------------------------------------------
# Canonical roots + single-rebuilder restriction (B8, 2026-08-12).
#
# This hook previously derived BOTH its log path and the delegate script from
# `${CLAUDE_PROJECT_DIR:-/workspace}`. Under the worktree-per-main model that is
# the lane worktree, so five mains would (a) write five separate kb_rag_update
# logs nobody merges, and (b) each fire a full KB index rebuild against the ONE
# shared index — five concurrent writers to a single index directory, on every
# HEAD-moving git command, which is many per wrap-up.
#
# env.sh canonicalizes PROJECT_ROOT/LOG_DIR from ANY worktree (see its B1 block),
# so the log and the delegate now resolve to one place regardless of who commits.
_KBH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${_KBH_DIR}/../lib/env.sh"

# ONE designated rebuilder, mirroring the `index_state.py` restriction that
# resolved the same collision for the generated index files (four sessions each
# rewrote a 137 KB + 114 KB pair they did not author; the fix was to let exactly
# one main run it — handoffs/active/handoff-index-and-backlog-graph.md).
# `AGENT_ID` is the fleet roster-id convention (scripts/utils/agent_log.sh:27,
# scripts/hooks/pre_push_serialization_guard.sh:293).
KB_RAG_REBUILDER="${KB_RAG_REBUILDER:-mainC}"

# Fail CLOSED on the multiplicity this exists to prevent: an unattributed session
# (no AGENT_ID) inside a LINKED worktree is exactly the "five anonymous mains"
# shape, so it declines. The canonical main working tree keeps today's behaviour
# when unattributed — that is the operator's own session and there is only one.
kb_rag_may_rebuild() {
  local git_dir common_dir
  if [[ -n "${AGENT_ID:-}" ]]; then
    [[ "${AGENT_ID}" == "${KB_RAG_REBUILDER}" ]] && return 0
    printf 'skip: AGENT_ID=%s is not the designated KB rebuilder (%s)\n' \
           "${AGENT_ID}" "${KB_RAG_REBUILDER}"
    return 1
  fi
  git_dir="$(git rev-parse --path-format=absolute --git-dir 2>/dev/null || true)"
  common_dir="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
  if [[ -n "${git_dir}" && -n "${common_dir}" && "${git_dir}" != "${common_dir}" ]]; then
    printf 'skip: unattributed session (no AGENT_ID) in a linked worktree — %s\n' \
           "cannot prove it is the single rebuilder"
    return 1
  fi
  return 0
}

INPUT=$(cat)
# jq can fail on malformed JSON — tolerate that as "nothing to do".
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)

if [[ -z "$CMD" ]]; then
  exit 0
fi

# Match git commands that move HEAD. We grep tolerantly: cmd may contain
# subshells, env prefixes, multiple statements, etc.
if echo "$CMD" | grep -qE '\bgit\s+(commit|merge|pull|rebase|cherry-pick)\b'; then
  # Run the actual update in the background — PostToolUse should not block.
  # The hook is best-effort, but keep a durable log so skipped/failed updates
  # are auditable after the triggering command has returned.
  HOOK_SCRIPT="${PROJECT_ROOT}/.claude/hooks/post_commit_kb_rag_update.sh"
  LOG_FILE="${KB_RAG_HOOK_LOG:-${LOG_DIR}/kb_rag_update.log}"
  mkdir -p "$(dirname "$LOG_FILE")"
  if ! SKIP_REASON="$(kb_rag_may_rebuild)"; then
    # Logged, never silent: a rebuild that did not happen must be attributable.
    printf '[%s] posttool %s (cmd: %s)\n' \
           "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SKIP_REASON" "$CMD" \
           >>"$LOG_FILE" 2>/dev/null || true
    exit 0
  fi
  if [[ -x "$HOOK_SCRIPT" ]]; then
    {
      printf '[%s] posttool dispatch (rebuilder=%s): %s\n' \
             "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${AGENT_ID:-canonical-tree}" "$CMD"
    } >>"$LOG_FILE" 2>/dev/null || true
    nohup bash "$HOOK_SCRIPT" >>"$LOG_FILE" 2>&1 &
    disown $! 2>/dev/null || true
  fi
fi

exit 0
