#!/bin/bash
set -euo pipefail
# Hook: PreToolUse → Bash | Write | Edit
#
# Rider R10 (handoffs/active/session-bus-thin-dispatcher.md §Rider) — refuse the
# one failure class that dominates this project's recorded incidents: touching a
# system while it is running.
#
# Two rules, both MECHANICALLY checkable. No judgment is encoded here; anything
# needing judgment belongs to a human or to the coordinator-agent, not a hook.
#
#   1. `drop_caches` while any CPU region is claimed. Post-drop_caches re-read
#      pins pages onto one NUMA node, so doing it under a live bench silently
#      corrupts that bench's memory locality — it does not error, it just makes
#      the number wrong.
#   2. Editing a shell script that is currently executing. bash reads the script
#      incrementally from its current file offset, so an in-place edit makes a
#      running script execute a spliced mixture of old and new text.
#
# FAIL-OPEN BY DESIGN. Every probe that cannot answer confidently allows the
# call. A hook that blocks on uncertainty would be worse than no hook: it would
# stall parallel sessions for reasons they cannot see. Both rules are also
# overridable with EPYC_ALLOW_LIVE_INTERFERENCE=1 for the case where the
# operator genuinely means it.
#
# TESTS: scripts/hooks/tests/test_live_holder_interference.py (--all for both
# rules). The cases live in a JSON fixture on purpose: a PreToolUse hook matches
# command TEXT, so it cannot tell "a command that writes drop_caches" from "a
# command that mentions writing drop_caches". A test embedding the patterns as
# literals gets blocked by the hook it is testing — that happened twice during
# bring-up, once on this hook's own commit message.

INPUT=$(cat)

if [[ "${EPYC_ALLOW_LIVE_INTERFERENCE:-0}" == "1" ]]; then
  exit 0
fi

command -v jq >/dev/null 2>&1 || exit 0   # no jq → cannot inspect → allow

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')
LOCK_DIR="${EPYC_REGION_LOCK_DIR:-/mnt/raid0/llm/tmp}"

# --- rule 1: drop_caches under a live region claim ---------------------------

held_region() {
  # Echo the first GLOBAL region lock currently held, or return 1.
  # Probing with `flock -n` never disturbs the holder and never blocks.
  local f
  for f in "$LOCK_DIR"/cpu_region.GLOBAL.*.lock; do
    [[ -e "$f" ]] || continue
    if ! flock -n "$f" -c true 2>/dev/null; then
      printf '%s' "$(basename "$f")"
      return 0
    fi
  done
  return 1
}

if [[ "$TOOL" == "Bash" ]]; then
  CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')
  [[ -z "$CMD" ]] && exit 0
  # Match an actual WRITE to drop_caches, not the bare word. Matching the word
  # anywhere blocked this hook's own commit message during bring-up — an
  # over-broad matcher is the failure mode this hook is supposed to avoid, since
  # a false block stalls a session for a reason it cannot see. Prose, grep
  # patterns and commit messages that merely mention drop_caches now pass.
  if printf '%s' "$CMD" | grep -qE '(>|>>|\|[[:space:]]*(sudo[[:space:]]+)?tee([[:space:]]+-a)?)[[:space:]]*/proc/sys/vm/drop_caches|sysctl[^;&|]*\bvm\.drop_caches[[:space:]]*='; then
    if REGION=$(held_region); then
      cat >&2 <<EOF
BLOCKED: drop_caches while a CPU region is claimed ($REGION).

A bench or inference run is holding that region right now. Dropping caches
under it forces a re-read that pins pages onto a single NUMA node — the run
will not error, its numbers will just be wrong.

Wait for the holder to release (scripts/region-lock status, or
epyc-orchestrator/scripts/region-lock status), or set
EPYC_ALLOW_LIVE_INTERFERENCE=1 if you genuinely mean it.
EOF
      exit 2
    fi
  fi
  exit 0
fi

# --- rule 2: editing a script that is currently executing --------------------

if [[ "$TOOL" == "Write" || "$TOOL" == "Edit" ]]; then
  FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')
  [[ -z "$FILE" ]] && exit 0
  case "$FILE" in *.sh) ;; *) exit 0 ;; esac
  TARGET=$(realpath -m "$FILE" 2>/dev/null || printf '%s' "$FILE")

  # Match only processes whose comm is a shell AND that carry the target as a
  # whole argv entry — a substring match would fire on any command mentioning
  # the path, including this hook's own caller.
  for pid in /proc/[0-9]*; do
    p=${pid#/proc/}
    [[ "$p" == "$$" || "$p" == "$PPID" ]] && continue
    comm=$(cat "$pid/comm" 2>/dev/null) || continue
    case "$comm" in bash|sh|zsh|dash|ksh) ;; *) continue ;; esac
    if tr '\0' '\n' < "$pid/cmdline" 2>/dev/null | grep -qxF "$TARGET"; then
      cat >&2 <<EOF
BLOCKED: $FILE is currently being executed by pid $p.

bash reads a script incrementally from its current file offset, so editing it
in place makes the running process execute a spliced mixture of old and new
text — usually as a confusing failure some lines later.

Wait for it to finish, edit a copy and swap it atomically, or set
EOF
      printf 'EPYC_ALLOW_LIVE_INTERFERENCE=1 if you genuinely mean it.\n' >&2
      exit 2
    fi
  done
fi

exit 0
