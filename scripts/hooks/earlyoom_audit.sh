#!/bin/bash
# earlyoom -N post-kill audit hook.
#
# Wired via: EARLYOOM_ARGS="... -N /mnt/raid0/llm/epyc-root/scripts/hooks/earlyoom_audit.sh"
# earlyoom runs this AFTER it kills a process, exporting:
#   EARLYOOM_PID, EARLYOOM_NAME (15-byte comm), EARLYOOM_CMDLINE, EARLYOOM_UID
# The earlyoom manpage warns EARLYOOM_NAME and EARLYOOM_CMDLINE may contain
# newlines / arbitrary special characters — so EVERY field is JSON-escaped below
# (a raw newline/control char in any field would otherwise break the JSON line).
#
# Purpose: record every early-OOM kill as a structured host event in the audit
# trail so it is NOT misattributed to the autopilot config-under-test (Pareto
# contamination — cf. feedback_autopilot_host_health_remediation).
#
# Design: fork-free on the hot path (bash parameter expansion + builtins only) —
# it fires in the immediate aftermath of an OOM event when memory is still
# recovering. Append-only; never blocks earlyoom.
set -u
export LC_ALL=C   # byte-wise semantics for the control-char range below

LOG="${EARLYOOM_AUDIT_LOG:-/mnt/raid0/llm/epyc-root/logs/agent_audit.log}"

pid="${EARLYOOM_PID:-?}"
name="${EARLYOOM_NAME:-?}"
uid="${EARLYOOM_UID:-?}"
cmd="${EARLYOOM_CMDLINE:-?}"

# JSON-escape one field; result returned in $REPLY (no command substitution = no fork).
# Escapes backslash + double-quote, then maps every C0 control char (0x01-0x1F,
# which includes \n \r \t) to a space so the emitted line is always valid JSON.
_esc() {
  local s=$1
  s=${s//\\/\\\\}                 # backslash FIRST (before we introduce our own)
  s=${s//\"/\\\"}                 # double quote
  s=${s//[$'\001'-$'\037']/ }     # ALL C0 control chars -> space
  REPLY=$s
}
_esc "$name"; name=$REPLY
_esc "$cmd";  cmd=$REPLY
_esc "$uid";  uid=$REPLY
_esc "$pid";  pid=$REPLY

# bash builtin timestamp (fork-free). +0000-style offset.
printf -v ts '%(%Y-%m-%dT%H:%M:%S%z)T' -1

printf '{"ts":"%s","session":"earlyoom","level":"WARN","cat":"EARLYOOM_KILL","msg":"earlyoom killed %s (pid %s)","details":"pid=%s uid=%s cmd=%s"}\n' \
  "$ts" "$name" "$pid" "$pid" "$uid" "$cmd" >> "$LOG"

# OPTIONAL (off by default): drop a sentinel the orchestrator/autopilot can watch
# to PAUSE new model loads after a kill, mitigating the #309 no-post-kill-backoff
# cascade risk on a box of large mlock'd servers. Enable only once a watcher exists.
# printf '%s %s\n' "$ts" "$pid" >> /mnt/raid0/llm/epyc-root/logs/earlyoom_last_kill

exit 0
