#!/bin/bash
# grant_ok.sh v4 (ws58 2026-11-01, operator: remove every gate that is not indispensable) - the ONE admission check a
# grant writer runs before writing grants/<id>.grant. Same CLI as v3 (writers are not edited):
#   grant_ok.sh <row-id> <need_gib> [ds41] [--window-s N] [--regions R] [--reserve R] [--pid P]
# Checks, in order:
#   1. rowflow status --grant: an epyc.row.v3 row whose dry run PASSED and whose launcher sha256 is unchanged since
#      (compute-flags/dryrun/<id>/PASS.json). Anything else -> refuse rc 10 (no v3 row / failed / parked / stale / done).
#      LEGACY rows (no v3 row) are refused: migrate with `rowflow.py publish --migrate ready/<id>.json`.
#   2. (any launcher flag given) grant_ok_launcher.py: the live poller's argv is parsed read-only from /proc so the grant's
#      window covers --min-window + 300 and its regions survive the engine's parse / cover its region-lock claim; its
#      --precond-cmd is run (rc 12 "not ready" when it fails). Unchanged from v3.
#   3. ram_admit.sh <need_gib> [ds41].
# Exit: 0 admit (prints reasons) - 10 row not grantable - 11 RAM refuse - 12 window short / not ready - 13 class/region
# mismatch - 14 launcher dead - 15 argv unrecognised - 16 launcher check internal - 64 usage. Read-only.
# REMOVED vs v3: validate_fillers.py (18-cell FILLERS.md row), keeper_qual_gate check (nonce/receipt/breaker/namespace
# fingerprint) and conflict (ports/exclusive_class/shared_state declarations): the dry run on the real lane is the proof.
# Test overrides (env, tests only): GRANT_OK_TEST_RAM_ADMIT GRANT_OK_TEST_PROC ROWFLOW_FLAGS
set -u
F=${ROWFLOW_FLAGS:-/mnt/raid0/llm/tmp/compute-flags}
HERE=$(dirname "$(readlink -f "$0")")
ROWFLOW=${ROWFLOW_PY:-$F/bin/rowflow/rowflow.py}
LAUNCHER_CHECK=${ROWFLOW_LAUNCHER_CHECK:-$F/bin/rowflow/grant_ok_launcher.py}
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
    --*) echo "refuse: usage: unknown flag $1"; exit 64;;
    *) POS+=("$1"); shift;;
  esac
done
set -- "${POS[@]}"
ID=${1:?row id}; NEED=${2:?need_gib}; MODE=${3:-}
row=$(/usr/bin/python3 -I "$ROWFLOW" --flags "$F" status "$ID" --grant 2>&1); rc=$?
[ $rc -eq 0 ] || { echo "refuse: ${row:0:220}"; exit 10; }
l=""
if [ $NEW = 1 ]; then
  cls=$(/usr/bin/python3 -I - "$F/ready/$ID.json" <<'PY'
import json,sys
try:
    m=json.load(open(sys.argv[1])); regs=str(m.get('regions',''))
    print('gpu' if 'mi210' in regs else ('whole-host' if regs=='0-95' else 'block-correctness'))
except Exception: print('unknown')
PY
)
  args=(--row "$ID" --fillers /dev/null --proc "$PROC" --derived-class "$cls")
  [ -n "$PID" ] && args+=(--pid "$PID")
  [ -n "$WIN" ] && args+=(--window-s "$WIN")
  [ $HAVE_REG = 1 ] && args+=(--regions "$REG")
  [ $HAVE_RES = 1 ] && args+=(--reserve "$RES")
  if [ -n "$PID" ]; then
    l=$(/usr/bin/python3 -I -B "$LAUNCHER_CHECK" "${args[@]}" 2>&1); lrc=$?
    case $lrc in
      0) ;;
      10|12|13|14|15) echo "$l" | head -1; exit $lrc;;
      *) echo "refuse: launcher check failed internally (rc=$lrc): $(echo "$l" | tail -1 | cut -c1-200)"; exit 16;;
    esac
  fi
fi
r=$($RAM_ADMIT "$NEED" $MODE) || { echo "$r"; exit 11; }
echo "admit: $row; $r${NEW:+; class=$cls} $l"
