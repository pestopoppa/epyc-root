#!/bin/bash
# v3 D1-D4: every quarter/GPU writer rechecks keeper nonce, hashes, namespace, disk immediately before .grant.
# workspace-58 (calendar owner): the single admission check a grant writer runs before writing grants/<id>.grant.
# v2 (2026-10-23, CTC-Q-A2 + CTC-Q-C.1): grant_ok.sh + optional launcher checks. Swapped in over grant_ok.sh after review.
#   grant_ok.sh <row-id> <need_gib> [ds41]                                   (legacy form: behaves exactly as v1)
#   grant_ok.sh <row-id> <need_gib> [ds41] [--window-s N] [--regions R] [--reserve R] [--pid P]
# 1. queue validity: validate_fillers.py --row <id> --for-grant (root 03a4b109d/a367d1df0; copy at compute-flags/)
#    exit 0 grant · 2 refuse (the row is not a runnable QUEUED item) · 3 malformed table / unknown row
# 2. (any new flag given) launcher checks, grant_ok_launcher.py: the launcher is --pid P or the row's pid= (a wrapper
#    pid is followed to its filler_run*.sh child); its argv is read from /proc/<pid>/cmdline, read-only.
#      --window-s N   N >= launcher --min-window + 300 s (three exactly-equal windows were refused rc=3)
#      --regions R    the grant's regions= value: must survive the launcher's parse_regions for its --class, and must
#                     cover every region its region-lock claim takes (--claim-cpus folded onto quarters; mi210_0 =
#                     gpu-quiet). --reserve R names regions the writer's claim-wait keeps free besides the grant
#                     (e.g. gpu-quiet for --class cpu --gpu-quiet exclusive; 0-95 for a GPU job claiming the whole host).
#    and the derived booking class: validate_fillers.py --print-class <id> (printed as class=...).
#    v2.1: after those pass, the launcher's --precond-cmd is run as the engine runs it (cd --workdir && bash -c CMD, the
#    engine's environ, <=30 s); failure -> rc 12 "not ready: precond-cmd failed: CMD" (retry later, nothing recorded).
# 3. RAM: ram_admit.sh <need_gib> [ds41]
# exit 0 admit (prints the reasons; with new flags also `class=<derived> launcher=...`) · 10 validator refuse (with new
#      flags also: row not QUEUED, i.e. status != ARMED or ready != y -- --for-grant alone passes a valid BACKLOG row) ·
#      11 RAM refuse · 12 window short · 13 class/region mismatch · 14 launcher dead · 15 launcher argv unrecognised ·
#      16 launcher check failed internally · 64 usage. Every refusal is one stdout line starting "refuse:". Read-only.
# Test overrides (env, tests only): GRANT_OK_TEST_FILLERS GRANT_OK_TEST_RAM_ADMIT GRANT_OK_TEST_PROC
set -u
F=/mnt/raid0/llm/tmp/compute-flags
HERE=$(dirname "$(readlink -f "$0")")   # the helper is read from beside this script (== $F once installed)
FILLERS=${GRANT_OK_TEST_FILLERS:-$F/FILLERS.md}
RAM_ADMIT=${GRANT_OK_TEST_RAM_ADMIT:-$F/ram_admit.sh}
PROC=${GRANT_OK_TEST_PROC:-/proc}
POS=(); WIN=""; REG=""; RES=""; PID=""; NEW=0; HAVE_REG=0; HAVE_RES=0
while [ $# -gt 0 ]; do
  case $1 in
    --window-s|--regions|--reserve|--pid)
      [ $# -ge 2 ] || { echo "refuse: usage: $1 needs a value"; exit 64; }
      case $1 in
        --window-s) [[ $2 =~ ^[0-9]+$ ]] || { echo "refuse: usage: --window-s '$2' is not seconds"; exit 64; }; WIN=$2;;
        --pid) [[ $2 =~ ^[0-9]+$ ]] || { echo "refuse: usage: --pid '$2' is not a pid"; exit 64; }; PID=$2;;
        --regions) [ -n "$2" ] || { echo "refuse: usage: --regions is empty"; exit 64; }; REG=$2; HAVE_REG=1;;
        --reserve) [ -n "$2" ] || { echo "refuse: usage: --reserve is empty"; exit 64; }; RES=$2; HAVE_RES=1;;
      esac
      NEW=1; shift 2;;
    --*) echo "refuse: usage: unknown flag $1 (grant_ok.sh <row-id> <need_gib> [ds41] [--window-s N] [--regions R] [--reserve R] [--pid P])"; exit 64;;
    *) POS+=("$1"); shift;;
  esac
done
set -- "${POS[@]}"
ID=${1:?row id}; NEED=${2:?need_gib}; MODE=${3:-}
v=$(/usr/bin/python3 -I $F/validate_fillers.py --file "$FILLERS" --row "$ID" --for-grant 2>&1); rc=$?
if [ $rc -ne 0 ]; then echo "refuse: validator rc=$rc: $(echo "$v" | grep -E 'REFUSE|MALFORMED' | head -3 | tr '\n' ' ')"; exit 10; fi
if [ $NEW = 1 ]; then
  cls=$(/usr/bin/python3 -I -B $F/validate_fillers.py --file "$FILLERS" --print-class "$ID" 2>/dev/null) || cls=unknown
  args=(--row "$ID" --fillers "$FILLERS" --proc "$PROC" --derived-class "$cls")
  [ -n "$PID" ] && args+=(--pid "$PID")
  [ -n "$WIN" ] && args+=(--window-s "$WIN")
  [ $HAVE_REG = 1 ] && args+=(--regions "$REG")
  [ $HAVE_RES = 1 ] && args+=(--reserve "$RES")
  l=$(/usr/bin/python3 -I -B $HERE/grant_ok_launcher.py "${args[@]}" 2>&1); lrc=$?
  case $lrc in
    0) ;;
    10|12|13|14|15) echo "$l" | head -1; exit $lrc;;
    *) echo "refuse: launcher check failed internally (rc=$lrc): $(echo "$l" | tail -1 | cut -c1-200)"; exit 16;;
  esac
fi
# This is the common grant-time boundary for both quarter and GPU writers.
# READY enrollment may precede the actual grant by hours; the keeper scan alone
# cannot stop a stale receipt or low disk from burning that later slot.
QUAL_BIN=${WS58_QUAL_BIN:-$F/bin/qual-v1}
MANIFEST=$F/ready/armed/$ID.json
[ -f "$MANIFEST" ] || MANIFEST=$F/ready/$ID.json
[ -f "$MANIFEST" ] || { echo "refuse: mandatory qualification manifest absent for $ID"; exit 18; }
gate=$(/usr/bin/python3 -I "$QUAL_BIN/keeper_qual_gate.py" check --manifest "$MANIFEST" --flags "$F" 2>&1); grc=$?
if [ "$grc" -ne 0 ]; then
  case "$gate" in
    wait-disk*) echo "not ready: READY-WAIT-DISK $ID: ${gate#*$'\t'}"; exit 12;;
    *) echo "refuse: HARD qualification $ID: ${gate#*$'\t'}"; exit 18;;
  esac
fi
gate=$(/usr/bin/python3 -I "$QUAL_BIN/keeper_qual_gate.py" conflict --manifest "$MANIFEST" --flags "$F" 2>&1); grc=$?
[ "$grc" -eq 0 ] || { echo "not ready: READY-WAIT-CONFLICT $ID: ${gate#*$'\t'}"; exit 12; }
r=$($RAM_ADMIT "$NEED" $MODE) || { echo "$r"; exit 11; }
if [ $NEW = 1 ]; then echo "admit: validator OK; $r; class=$cls $l"; else echo "admit: validator OK; $r"; fi
