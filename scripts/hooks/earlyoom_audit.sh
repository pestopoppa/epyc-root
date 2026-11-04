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
#
# Shard: this is a host-level writer independent of any agent's AGENT_ID, and
# runs concurrently with every agent's own agent_log.sh shard (scripts/utils/
# agent_log.sh), so it gets its own dedicated shard file rather than either
# colliding with a main's shard or reverting to the old shared monolithic log.
# Readers merge it back in via the agent_audit*.log glob
# (scripts/utils/agent_log_read.sh) — same "session":"earlyoom" value as before.
set -u
export LC_ALL=C   # byte-wise semantics for the control-char range below

LOG="${EARLYOOM_AUDIT_LOG:-/mnt/raid0/llm/epyc-root/logs/agent_audit-earlyoom.log}"

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

# --- Memory snapshot, once per kill burst (NIB2-97(b), INC-20261021-earlyoom-session-kills) ---
# The 2026-10-21 trigger left no memory sample anywhere on disk (13 kills in 16 s, no dmesg,
# no journal). So the FIRST kill of a burst also appends one JSON line to a sidecar log: the
# /proc/meminfo fields below, the memory PSI line, and the top-10 processes by VmRSS read from
# /proc/<pid>/status. READ-ONLY on /proc; it writes only the sidecar log and its stamp. Still
# fork-free (globs, read, printf). Rate limit: a snapshot is taken when none was taken in the
# last EARLYOOM_SNAPSHOT_WINDOW seconds (default 60). The stamp is created with noclobber, so
# two hooks racing on the FIRST kill take one snapshot; two racing to replace a stale stamp may
# both take one, which costs a duplicate line, never a missing one.
# Test knobs: EARLYOOM_PROC_ROOT (default /proc), EARLYOOM_SNAPSHOT_LOG, EARLYOOM_SNAPSHOT_STAMP.
SNAP_LOG="${EARLYOOM_SNAPSHOT_LOG:-${LOG%/*}/earlyoom_meminfo_snapshots.log}"
SNAP_STAMP="${EARLYOOM_SNAPSHOT_STAMP:-${LOG%/*}/earlyoom_snapshot_stamp.log}"
SNAP_WINDOW="${EARLYOOM_SNAPSHOT_WINDOW:-60}"
PROC="${EARLYOOM_PROC_ROOT:-/proc}"
[[ "$SNAP_WINDOW" =~ ^[0-9]+$ ]] || SNAP_WINDOW=60
printf -v now '%(%s)T' -1

_snapshot_due() {
  local last=""
  set -C
  if { printf '%s\n' "$now" > "$SNAP_STAMP"; } 2>/dev/null; then set +C; return 0; fi
  set +C
  { read -r last < "$SNAP_STAMP"; } 2>/dev/null
  [[ "$last" =~ ^[0-9]+$ ]] || last=0
  (( now - last < SNAP_WINDOW )) && return 1
  { printf '%s\n' "$now" >| "$SNAP_STAMP"; } 2>/dev/null
  return 0
}

_snapshot() {
  local k v rest mem="" psi="" f name spid rss i j top=""
  local -a trss=() tpid=() tname=()
  while read -r k v rest; do
    case "$k" in
      MemTotal:|MemFree:|MemAvailable:|Cached:|AnonPages:|Mlocked:|SwapTotal:|SwapFree:)
        [[ "$v" =~ ^[0-9]+$ ]] && mem+="${mem:+,}\"${k%:}_kB\":$v" ;;
    esac
  done < "$PROC/meminfo"
  if { read -r psi < "$PROC/pressure/memory"; } 2>/dev/null; then _esc "$psi"; psi=$REPLY; fi
  for f in "$PROC"/[0-9]*/status; do
    name="" spid="" rss=""
    { while read -r k v rest; do
        case "$k" in
          Name:) name="$v${rest:+ $rest}" ;;
          Pid:) spid=$v ;;
          VmRSS:) rss=$v; break ;;
        esac
      done < "$f"; } 2>/dev/null
    [[ "$rss" =~ ^[0-9]+$ && "$spid" =~ ^[0-9]+$ ]] || continue   # kernel threads have no VmRSS
    (( ${#trss[@]} == 10 && rss <= trss[9] )) && continue
    i=${#trss[@]}; (( i == 10 )) && i=9
    while (( i > 0 && trss[i-1] < rss )); do
      trss[i]=${trss[i-1]}; tpid[i]=${tpid[i-1]}; tname[i]=${tname[i-1]}; i=$((i - 1))
    done
    _esc "$name"
    trss[i]=$rss; tpid[i]=$spid; tname[i]=$REPLY
  done
  for (( j = 0; j < ${#trss[@]}; j++ )); do
    top+="${top:+,}{\"pid\":${tpid[j]},\"name\":\"${tname[j]}\",\"VmRSS_kB\":${trss[j]}}"
  done
  printf '{"ts":"%s","session":"earlyoom","cat":"EARLYOOM_MEM_SNAPSHOT","trigger_pid":"%s","meminfo":{%s},"psi_memory_some":"%s","top_vmrss":[%s]}\n' \
    "$ts" "$pid" "$mem" "$psi" "$top" >> "$SNAP_LOG"
}

if _snapshot_due; then
  { _snapshot; } 2>/dev/null || true
fi

# OPTIONAL (off by default): drop a sentinel the orchestrator/autopilot can watch
# to PAUSE new model loads after a kill, mitigating the #309 no-post-kill-backoff
# cascade risk on a box of large mlock'd servers. Enable only once a watcher exists.
# printf '%s %s\n' "$ts" "$pid" >> /mnt/raid0/llm/epyc-root/logs/earlyoom_last_kill

exit 0
