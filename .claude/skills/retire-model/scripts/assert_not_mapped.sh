#!/bin/bash
# REFUSAL: a model that a RUNNING server has open is not retirable.
#
# usage: assert_not_mapped.sh <gguf-path> [<gguf-path> ...]
#   exit 0  no live process holds any of these artifacts
#   exit 2  a live process holds one -- retirement is refused
#   exit 1  usage
#
# This is a READ-ONLY /proc walk. It never uses pkill/pgrep on a name pattern and
# it never signals anything: on this shared host a name pattern is a wildcard over
# other sessions' processes, and a guard's argv necessarily contains the names it
# guards (INC-20260731-broad-process-pattern-kills -- llama-server was killed twice
# and earlyoom died because its command line lists what it protects).
#
# It reads BOTH /proc/<pid>/maps and /proc/<pid>/cmdline, because those answer
# different questions: cmdline says what was ASKED FOR, maps says what is
# RESIDENT. A server started with a symlinked path shows the link in cmdline and
# the target in maps; checking only one of them is a set comparison across two
# mechanisms, which is the defect class DERIVATION.md names.
set -uo pipefail

[ $# -ge 1 ] || { echo "usage: assert_not_mapped.sh <gguf-path> [...]" >&2; exit 1; }

RC=0
UNREADABLE=0
CHECKED=0

SELF="$(basename "$0")"

for proc in /proc/[0-9]*; do
  pid="${proc#/proc/}"
  [ -r "$proc/cmdline" ] || { UNREADABLE=$((UNREADABLE + 1)); continue; }
  cmd=$(tr '\0' ' ' < "$proc/cmdline" 2>/dev/null) || continue
  # Skip this checker and anything running it. Its own argv necessarily contains
  # every artifact it was asked about, so without this it reports ITSELF as the
  # holder and refuses every retirement -- the same shape as earlyoom dying
  # because its command line listed the processes it protected.
  case "$cmd" in *"$SELF"*) continue ;; esac
  [ "$pid" = "$$" ] && continue
  CHECKED=$((CHECKED + 1))
  maps=$(cat "$proc/maps" 2>/dev/null) || maps=""
  for art in "$@"; do
    base=$(basename "$art")
    hit=""
    case "$cmd" in *"$art"*|*"$base"*) hit="cmdline" ;; esac
    if [ -z "$hit" ] && [ -n "$maps" ]; then
      case "$maps" in *"$art"*|*"$base"*) hit="maps" ;; esac
    fi
    if [ -n "$hit" ]; then
      echo "HOLDER pid=$pid via=$hit artifact=$base"
      echo "       started: $(ps -o lstart= -p "$pid" 2>/dev/null | sed 's/^ *//')"
      echo "       argv0:   $(echo "$cmd" | cut -c1-140)"
      RC=2
    fi
  done
done

echo "-- scanned $CHECKED processes ($UNREADABLE not readable by this user) --"
if [ "$RC" != 0 ]; then
  echo "REFUSED: a live process still holds this model. Retiring the registry row while a" >&2
  echo "         server serves the weights produces a lineup that disagrees with the fleet," >&2
  echo "         and the runtime attestation after stack-change phase 7 will fail on it." >&2
  echo "         Drain and stop that role through orchestrator_stack.py -- never kill it here." >&2
  exit 2
fi
if [ "$UNREADABLE" -gt 0 ]; then
  echo "NOTE: $UNREADABLE processes were not readable, so this is a clean result over what"
  echo "      this user can see, not over the whole host. Say so when you report it."
fi
echo "PASS: no readable process holds the named artifact(s)."
exit 0
