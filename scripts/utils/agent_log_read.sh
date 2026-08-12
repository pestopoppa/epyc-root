#!/bin/bash
# agent_log_read.sh — shared read-side helper for sharded agent_audit logs.
#
# WHY THIS EXISTS: agent_log.sh shards its writes across one file per AGENT_ID
# (mainA, mainB, ..., auditor, coordinator-agent, inference, earlyoom, ...) to
# remove the concurrent-append merge tax on a single tracked file. That is only
# safe if EVERY reader merges ALL shards back into one chronological stream.
# A reader that opens only the legacy `agent_audit.log` or only one shard does
# not fail loudly — it prints a plausible, confidently-wrong summary that looks
# exactly like a correct one but silently covers a fraction of the fleet. Every
# reader of this log MUST go through agent_log_files()/agent_log_merged() below
# instead of hardcoding a single path.
#
# Source AFTER scripts/lib/env.sh (needs $LOG_DIR). Read-only: does not create
# the session file or any shard.

# List every audit-log file that currently exists: the frozen legacy monolith
# (agent_audit.log, pre-sharding history — still readable, no longer written)
# plus every per-writer shard (agent_audit-<id>.log). One glob covers both
# since `agent_audit*.log` matches the empty infix as well as `-<id>`.
# Order is NOT chronological across files — callers needing global order MUST
# use agent_log_merged, not this list directly.
agent_log_files() {
  local dir="${1:-${LOG_DIR:-.}}"
  local f
  for f in "$dir"/agent_audit*.log; do
    [[ -f "$f" ]] && printf '%s\n' "$f"
  done
}

# Emit every entry across every shard, merged into one global chronological
# stream on stdout. Both current writers (agent_log.sh's _agent_log, and
# scripts/hooks/earlyoom_audit.sh) emit one JSON object per line with the same
# key order — "ts" first — so a plain lexical `sort` of whole lines already
# sorts by timestamp; ties break deterministically on the remaining fields
# instead of on file-iteration order. No jq dependency on the merge path.
agent_log_merged() {
  local dir="${1:-${LOG_DIR:-.}}"
  local -a files=()
  local f
  while IFS= read -r f; do files+=("$f"); done < <(agent_log_files "$dir")
  [[ ${#files[@]} -eq 0 ]] && return 0
  sort -- "${files[@]}"
}

export -f agent_log_files agent_log_merged
