#!/bin/bash
# workspace-58 10-25: one-shot whole-host quiet window for 3c4ca599 inf66-r2364-thread-sweep (0-95 + gpu-quiet, 92 GiB, launcher min-window 4800 s).
# Modelled on grant-inf66-20261024-v4.sh. Logic:
#  1. wait until 19:30Z 10-25.  2. write HOLD_GPU_FOR_QUIET_20261025 (trap removes it on EVERY exit; GPU writer v12 and quarter writer
#     grant-ws58-quarters-20261025 both pause on any HOLD_* file).  3. wait until no *.grant open and no region-lock claim.
#  4. if >= 5100 s remain before 03:20Z 10-26: grant inf66 0-95 --reserve gpu-quiet for min(5700, 03:20Z-now); wait for .ended.
#  5. not quiet by 01:30Z (or window short / launcher gone): log, FILLERS row -> BACKLOG blocker=no quiet window 10-25, exit.
#     Also demoted if the window ended with the row not complete (kpf64-eb gate at 03:30Z waits on any ARMED whole-host row).
#  6. always remove HOLD, touch WS58_INF66_1025_ENDED.
# Usage: grant-inf66-20261025.sh            (live)
#        grant-inf66-20261025.sh --simulate HH:MM   (prints computed times for that fake "now"; HH:MM<12:00 means 10-26; touches nothing)
set -u
F=/mnt/raid0/llm/tmp/compute-flags
G=$F/grants
LOG=$F/grant-inf66-20261025.log
RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
ID=inf66-r2364-thread-sweep; LP=591183
HOLD=$F/HOLD_GPU_FOR_QUIET_20261025
FLAG=$F/WS58_INF66_1025_ENDED
START=$(date -u -d '2026-10-25T19:30:00Z' +%s)
GIVEUP=$(date -u -d '2026-10-26T01:30:00Z' +%s)
CAP=$(date -u -d '2026-10-26T03:20:00Z' +%s)
ts() { date -u -d @"$1" +%Y-%m-%dT%H:%MZ; }

if [ "${1:-}" = "--simulate" ]; then
  hm=${2:?HH:MM}; h=${hm%%:*}; day=2026-10-25; [ $((10#$h)) -lt 12 ] && day=2026-10-26
  now=$(date -u -d "${day}T${hm}:00Z" +%s)
  echo "simulated now=$(ts $now)"
  echo "  start-wait target=$(ts $START) -> $([ $now -lt $START ] && echo "sleep $((START-now)) s, then write HOLD" || echo "already past, HOLD written immediately")"
  echo "  give-up (not quiet) at $(ts $GIVEUP) -> $([ $now -ge $GIVEUP ] && echo PAST: demote to BACKLOG now || echo "$((GIVEUP-now)) s left to get quiet")"
  W=$((CAP-now)); [ $W -gt 5700 ] && W=5700
  echo "  if quiet now: W=$W s (cap $(ts $CAP)) -> $([ $W -ge 5100 ] && echo "GRANT $(ts $now)..$(ts $((now+W)))" || echo "W<5100: demote to BACKLOG")"
  echo "  latest start with room 5100 s = $(ts $((CAP-5100)))"
  exit 0
fi

echo $$ > $F/grant-inf66-20261025.pid
log() { echo "$(date -u +%FT%TZ) $*" >> $LOG; }
# PROPOSED owner whole-producer cutover only; shared lease for every HOLD mutation.
ADAPTER=$(dirname "$(readlink -f "$0")")/..
hold_write() { /usr/bin/python3 -B "$ADAPTER/gap_serialization_v1.py" --flags "$F" --name "${HOLD##*/}" --text "$1" || exit 6; }
hold_remove() { /usr/bin/python3 -B "$ADAPTER/gap_serialization_v1.py" --flags "$F" --name "${HOLD##*/}" --remove || exit 6; }
hold_keep() { /usr/bin/python3 -B "$ADAPTER/gap_serialization_v1.py" --flags "$F" --name "${HOLD##*/}" --text "$1" --if-missing || exit 6; }
cleanup() { [ -e $HOLD ] && hold_remove && log "removed $(basename $HOLD)"; touch $FLAG; log "touched $(basename $FLAG)"; }
trap cleanup EXIT
backlog() {  # $1 = blocker text; edits only the inf66 row, cells 8 (status) 13 (ready) 18 (notes); backup first
  cp -p $F/FILLERS.md $F/FILLERS.md.bak-ws58-inf66-1025-$(date -u +%Y%m%dT%H%M%SZ)
  python3 - "$F/FILLERS.md" "$ID" "$1" <<'PY'
import sys, os, tempfile
p, rid, blk = sys.argv[1:4]
lines = open(p).read().split('\n'); n = 0
for i, l in enumerate(lines):
    if l.startswith('| ' + rid + ' |'):
        c = l.split('|')
        if len(c) < 20: sys.exit('row has %d cells, refusing' % len(c))
        c[8] = ' BACKLOG '; c[13] = ' n '; c[18] = c[18].rstrip() + ' blocker=' + blk + ' '
        lines[i] = '|'.join(c); n += 1
if n != 1: sys.exit('matched %d rows, refusing' % n)
t = tempfile.NamedTemporaryFile('w', dir=os.path.dirname(p), delete=False); t.write('\n'.join(lines)); t.close()
os.replace(t.name, p)
PY
  log "FILLERS row $ID -> BACKLOG blocker=$1 (rc=$?)"
}
quiet() { ! ls $G/*.grant >/dev/null 2>&1 && ! $RL status 2>/dev/null | grep -qE 'HELD|EXCL|SHARED|SHRD'; }
log "armed (start $(ts $START), give-up $(ts $GIVEUP), cap $(ts $CAP))"
while [ "$(date -u +%s)" -lt $START ]; do sleep 60; done
hold_write "time=$(date -u +%FT%TZ) by=workspace-58 for=$ID"; log "wrote $(basename $HOLD)"
until quiet; do
  [ "$(date -u +%s)" -ge $GIVEUP ] && { log "not quiet by $(ts $GIVEUP): grants=$(ls $G/*.grant 2>/dev/null | tr '\n' ' ')"; backlog "no quiet window 10-25"; exit 0; }
  sleep 20
done
log "host quiet"
kill -0 $LP 2>/dev/null || { log "launcher $LP gone"; backlog "launcher gone 10-25"; exit 0; }
[ -e $G/$ID.complete ] && { log "already complete"; exit 0; }
st=$(date -u +%s); W=$(( CAP - st )); [ $W -gt 5700 ] && W=5700
[ $W -lt 5100 ] && { log "window $W s < 5100"; backlog "no quiet window 10-25"; exit 0; }
r=$($F/grant_ok.sh $ID 92 --window-s $W --regions 0-95 --reserve gpu-quiet) || { log "refused: $r"; backlog "no quiet window 10-25 (grant_ok refused)"; exit 0; }
en=$(( st + W ))
printf 'regions=0-95 start=%s end=%s\n' "$(ts $st)" "$(ts $en)" > $G/$ID.grant
log "$r; granted $ID: $(cat $G/$ID.grant)"
until { [ -e $G/$ID.ended ] && [ "$(stat -c %Y $G/$ID.ended)" -ge $st ]; } || [ "$(date -u +%s)" -ge $(( en + 300 )) ]; do sleep 30; done
log "$ID ended: $(head -1 $G/$ID.ended 2>/dev/null)"
[ -e $G/$ID.complete ] || [ -e /mnt/raid0/llm/tmp/roi-prep-20261023/INF-66-R23-64/out/COMPLETE ] || backlog "window ended incomplete 10-25 (resume later)"
exit 0
