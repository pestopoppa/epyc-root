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

# Emit every entry across every shard on stdout via a plain lexical `sort` of
# whole lines. What this actually guarantees, measured against the real
# corpus (not assumed): the two CURRENT writers (agent_log.sh's _agent_log,
# and scripts/hooks/earlyoom_audit.sh) emit one JSON object per line with "ts"
# as the first key, so among JSON entries a lexical sort of whole lines does
# sort by timestamp (ties break deterministically on the remaining fields
# instead of on file-iteration order). But the frozen legacy `agent_audit.log`
# also contains ~1,200 pre-2026 lines in an older, non-JSON bracketed format
# (`[2025-12-15T17:12:49+01:00] TASK_END: ...`) and a handful of `{"timestamp":
# ...}`-keyed (not "ts"-keyed) JSON lines from a third, even older format.
# Lexical sort does NOT parse timestamps across these formats — it happens to
# put every bracketed line before every JSON line only because `[` (0x5B) sorts
# before `{` (0x7B) in the byte-for-byte comparison, and that ACCIDENTALLY
# matches chronology only because the bracketed format stopped being written
# before the JSON format started. The merge is correctly described as: one
# block of legacy-format entries (in their original, already-chronological
# append order) followed by one block of "ts"-first JSON entries (sorted
# chronologically among themselves) — not a single interleaved chronology.
# Decision (2026-08-12): two-block ordering is accepted and documented, not
# fixed, because nothing has written the legacy formats since Dec 2025 (a
# frozen corpus) and a timestamp-extracting parser for three formats on this
# read path is not worth building for entries that will never again interleave
# with new writes. See scripts/utils/tests/test_agent_log_merge_format.sh for
# a fixture that pins this exact behavior. No jq dependency on the merge path.
agent_log_merged() {
  local dir="${1:-${LOG_DIR:-.}}"
  local -a files=()
  local f
  while IFS= read -r f; do files+=("$f"); done < <(agent_log_files "$dir")
  [[ ${#files[@]} -eq 0 ]] && return 0
  sort -- "${files[@]}"
}

export -f agent_log_files agent_log_merged
