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
  HOOK_SCRIPT="${CLAUDE_PROJECT_DIR:-/workspace}/.claude/hooks/post_commit_kb_rag_update.sh"
  if [[ -x "$HOOK_SCRIPT" ]]; then
    LOG_FILE="${KB_RAG_HOOK_LOG:-${CLAUDE_PROJECT_DIR:-/workspace}/logs/kb_rag_update.log}"
    mkdir -p "$(dirname "$LOG_FILE")"
    {
      printf '[%s] posttool dispatch: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$CMD"
    } >>"$LOG_FILE" 2>/dev/null || true
    nohup bash "$HOOK_SCRIPT" >>"$LOG_FILE" 2>&1 &
    disown $! 2>/dev/null || true
  fi
fi

exit 0
