#!/bin/bash
set -euo pipefail
# Hook: PreToolUse -> Bash
# Refuses recursive / inline-script deletes under /mnt/raid0/llm/{tmp,worktrees,.trash,state}
# unless routed through the sanctioned tools (scripts/safety/guarded_rm.sh etc.).
#
# Origin: 2026-10-20 E2 purge (purge_batch.py shutil.rmtree'd the trash batch 20 s-2 min after
# guarded_rm); 244 real tmp losses reconciled 2026-10-25,
# docs/reference/tmp-loss-reconcile-2026-10-25.md section 2 and section 6 guard 5, NIB2-108.
# Limits: cannot see deletes in already-running processes or files it cannot read; fail-open on
# unparseable input (the hygiene-tick backstop covers those). Rules live in the scanner.
# Override: EPYC_ALLOW_SCRATCH_DELETE="operator: <who> <date>: <reason>" in the hook env.
# Tests: scripts/hooks/tests/test_destructive_scratch_hook.sh

INPUT=$(cat)
command -v jq >/dev/null 2>&1 || exit 0
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || exit 0
case "$TOOL" in Bash|"") ;; *) exit 0 ;; esac
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
[[ -z "$CMD" ]] && exit 0

SCAN="$(dirname "${BASH_SOURCE[0]}")/destructive_scratch_scan.py"
if ! command -v python3 >/dev/null 2>&1 || [[ ! -f "$SCAN" ]]; then
  exit 0
fi

set +e
printf '%s' "$CMD" | python3 "$SCAN"
RC=$?
set -e
[[ "$RC" == "2" ]] && exit 2
exit 0
