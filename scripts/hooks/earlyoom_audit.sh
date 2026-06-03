#!/bin/bash
# earlyoom -N post-kill audit hook.
#
# Wired via: EARLYOOM_ARGS="... -N /mnt/raid0/llm/epyc-root/scripts/hooks/earlyoom_audit.sh"
# earlyoom runs this AFTER it kills a process, exporting:
#   EARLYOOM_PID, EARLYOOM_NAME (15-byte comm), EARLYOOM_CMDLINE, EARLYOOM_UID
#
# Purpose: record every early-OOM kill as a structured host event in the audit
# trail so it is NOT misattributed to the autopilot config-under-test (Pareto
# contamination — cf. feedback_autopilot_host_health_remediation).
#
# Design: allocation-free on the hot path. No external forks (no date/sed/jq) —
# uses bash builtins only — because this fires in the immediate aftermath of an
# OOM event when memory is still recovering. Append-only; never blocks earlyoom.
set -u

LOG="${EARLYOOM_AUDIT_LOG:-/mnt/raid0/llm/epyc-root/logs/agent_audit.log}"

# Defaults so a manual/test invocation without earlyoom's env does not error.
pid="${EARLYOOM_PID:-?}"
name="${EARLYOOM_NAME:-?}"
uid="${EARLYOOM_UID:-?}"
cmd="${EARLYOOM_CMDLINE:-?}"

# Minimal JSON escaping via bash parameter expansion (no forks):
# backslash first, then double-quote, then strip control chars that would break the line.
cmd="${cmd//\\/\\\\}"
cmd="${cmd//\"/\\\"}"
cmd="${cmd//$'\n'/ }"
cmd="${cmd//$'\t'/ }"
name="${name//\\/\\\\}"
name="${name//\"/\\\"}"

# bash builtin timestamp (fork-free). +0000-style offset; close enough to the
# +00:00 used elsewhere in the log for grep/jq consumers.
printf -v ts '%(%Y-%m-%dT%H:%M:%S%z)T' -1

printf '{"ts":"%s","session":"earlyoom","level":"WARN","cat":"EARLYOOM_KILL","msg":"earlyoom killed %s (pid %s)","details":"pid=%s uid=%s cmd=%s"}\n' \
  "$ts" "$name" "$pid" "$pid" "$uid" "$cmd" >> "$LOG"

# OPTIONAL (off by default): drop a sentinel the orchestrator/autopilot can watch
# to PAUSE new model loads after a kill, mitigating the #309 no-post-kill-backoff
# cascade risk on a box of large mlock'd servers. Enable only once a watcher exists.
# printf '%s %s\n' "$ts" "$pid" >> /mnt/raid0/llm/epyc-root/logs/earlyoom_last_kill

exit 0
