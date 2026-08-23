#!/bin/bash
set -euo pipefail
# SUPERSEDED by the unified filesystem-containment scanner (INC-20260823).
#
# This file's job moved into scripts/hooks/filesystem_containment_scan.py
# (--check-path) on 2026-08-23, and .claude/settings.json now routes the
# Write|Edit matcher to scripts/hooks/check_filesystem_containment.sh (the
# wrapper that serves both Bash and Write|Edit from ONE rule set). The old
# allow-set lived HERE as hand-written rules — a second copy that drifted from
# the scanner — and is deleted from this file so no surface can regress into a
# divergent rule table.
#
# Kept only because historical tooling references it by name
# (SPEC.md, CLAUDE_GUIDE.md, scripts/validate/repo_readiness_scorer.py,
# progress/ and repo-readiness snapshots) and no retirement pattern
# (scripts/hooks/_retired/) exists yet. Do NOT rewire any hook to this file;
# do NOT re-add rules here — the scanner is the one source of truth.
#
# Behavior if ever invoked (defense-in-depth, no rules of its own): refuse
# everything outside the scanner's containment roots. The scanner is the only
# authority on what is inside.
#
# Hook: PreToolUse → Write|Edit (LEGACY — superseded, see above)

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

case "$FILE_PATH" in
  /mnt/raid0/llm/*|/workspace/*|/workspace)
    exit 0
    ;;
esac

echo "BLOCKED: Write to '$FILE_PATH' denied. The unified containment scanner
(scripts/hooks/filesystem_containment_scan.py --check-path) is the authority:
everything outside /mnt/raid0/llm/**, /workspace/**, /tmp/**, ~/.claude/**,
~/.codex/** (plus the operator allowlist) is refused. This file is
SUPERSEDED; the Write|Edit hook no longer calls it." >&2
exit 2
