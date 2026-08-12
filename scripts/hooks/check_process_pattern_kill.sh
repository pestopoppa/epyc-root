#!/bin/bash
set -euo pipefail
# Hook: PreToolUse → Bash
# Refuses `pkill`/`pgrep` aimed at a NAME PATTERN on this shared host.
#
# Origin: INC-20260731 (a name-pattern kill took out another agent's llama-server
# twice, and earlyoom, whose argv contains the names it guards) and INC-20260812
# (a coordinator subagent used `pkill -f` on a task-output path to reap its own
# background waiter — no damage, self-disclosed, and filed because the rule existed
# and was assumed-guarded when it was not).
#
# SCOPED TO INVOCATIONS, NOT TEXT. The scanner strips quoted strings and heredocs
# first, so this file, the CLAUDE.md rule, and the bus message reporting an incident
# all pass. A guard that forbids its own documentation is the failure C21 already
# paid for once.

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[[ -z "$CMD" ]] && exit 0

SCAN="$(dirname "${BASH_SOURCE[0]}")/process_pattern_kill_scan.py"

# Fail CLOSED only for the unambiguous form. If the precise scanner cannot run we
# still refuse a literal `pkill`/`pgrep` at a command position, because a missed
# pattern kill costs another session's work and a false block costs a rephrase.
if ! command -v python3 >/dev/null 2>&1 || [[ ! -f "$SCAN" ]]; then
  if echo "$CMD" | grep -qE '(^|[;&|]|\s)(pkill|pgrep)\s'; then
    echo "BLOCKED: the pattern-kill scanner is unavailable and this command invokes pkill/pgrep." >&2
    echo "Refusing rather than guessing. Kill a PID you captured yourself, or use TaskStop." >&2
    exit 2
  fi
  exit 0
fi

VERDICT=$(printf '%s' "$CMD" | python3 "$SCAN" 2>/dev/null) || VERDICT="SCANNER-FAILED"

case "$VERDICT" in
  kill-pattern)
    echo "BLOCKED: pkill against a NAME PATTERN. This is a shared host, so a name pattern is a" >&2
    echo "wildcard over other sessions' processes — and a guard process's argv necessarily contains" >&2
    echo "the names it guards (earlyoom died this way: --ignore ^(llama-server|sd-server)\$)." >&2
    echo "" >&2
    echo "Use instead: kill \$PID for a pid you captured yourself, or TaskStop on the job id." >&2
    echo "Then verify it is dead (ps -p \$PID) before reporting success." >&2
    echo "Origin: INC-20260731, INC-20260812 — docs/reference/agent-config/INCIDENT_LOG.md" >&2
    exit 2
    ;;
  grep-pattern)
    echo "BLOCKED: pgrep against a NAME PATTERN. The rule covers pgrep too, because the PIDs it" >&2
    echo "returns are what gets killed next — the selection is the dangerous step, not the signal." >&2
    echo "" >&2
    echo "Use instead: a pid you captured at launch, pgrep -P <ppid> / -s <sid> (pid-scoped), or" >&2
    echo "ps -o pid,lstart,args -p <pid> to inspect one process you already own." >&2
    exit 2
    ;;
  SCANNER-FAILED)
    if echo "$CMD" | grep -qE '(^|[;&|]|\s)(pkill|pgrep)\s'; then
      echo "BLOCKED: the pattern-kill scanner errored and this command invokes pkill/pgrep." >&2
      echo "Refusing rather than guessing." >&2
      exit 2
    fi
    exit 0
    ;;
esac

exit 0
