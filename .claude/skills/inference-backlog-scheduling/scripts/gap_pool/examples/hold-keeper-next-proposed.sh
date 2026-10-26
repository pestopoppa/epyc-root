#!/bin/bash
# workspace-58 (10-24 19:5xZ): keep HOLD_GPU_FOR_QUIET_20261024 in place from the C4 re-run through v11-086-cpu.
# The C4 writer (grant-c4rerun) removes HOLD when it ends (about 21:50Z). Without this keeper, the GPU writer v10 would then re-offer
# yarn or hsf-5p for 1-2 h and block v11-086-cpu's whole-host quiet window (22:05Z, gpu-quiet reserved).
# From 20:40Z: if HOLD is missing, recreate it (poll 3 s). Stop once v11-086-cpu has ended after 22:05Z (fallback 01:30Z on 10-25):
# remove HOLD, THEN touch WS58_V11_QUIET_DONE (the overnight writer v2 starts on that flag).
set -u
F=/mnt/raid0/llm/tmp/compute-flags; G=$F/grants
HOLD=$F/HOLD_GPU_FOR_QUIET_20261024; LOG=$F/hold-keeper-c4-v11-20261024.log
log() { echo "$(date -u +%FT%TZ) $*" >> $LOG; }
# PROPOSED owner whole-producer cutover only; shared lease for every HOLD mutation.
ADAPTER=$(dirname "$(readlink -f "$0")")/..
hold_write() { /usr/bin/python3 -B "$ADAPTER/gap_serialization_v1.py" --flags "$F" --name "${HOLD##*/}" --text "$1" || exit 6; }
hold_remove() { /usr/bin/python3 -B "$ADAPTER/gap_serialization_v1.py" --flags "$F" --name "${HOLD##*/}" --remove || exit 6; }
hold_keep() { /usr/bin/python3 -B "$ADAPTER/gap_serialization_v1.py" --flags "$F" --name "${HOLD##*/}" --text "$1" --if-missing || exit 6; }
echo $$ > $F/hold-keeper-c4-v11-20261024.pid; log "armed pid $$"
S0=$(date -u -d '2026-10-24T20:40:30Z' +%s); V11S=$(date -u -d '2026-10-24T22:05:00Z' +%s); FB=$(date -u -d '2026-10-25T01:30:00Z' +%s)
while [ "$(date -u +%s)" -lt $S0 ]; do sleep 20; done
log "keeping HOLD"
while :; do
  now=$(date -u +%s)
  if { [ -e $G/v11-086-cpu.ended ] && [ "$(stat -c %Y $G/v11-086-cpu.ended)" -ge $V11S ]; } || [ $now -ge $FB ]; then
    hold_remove; log "v11 done or fallback ($(head -1 $G/v11-086-cpu.ended 2>/dev/null)); removed HOLD"
    echo "time=$(date -u +%FT%TZ)" > $F/WS58_V11_QUIET_DONE; exit 0; fi
  [ -e $HOLD ] || { hold_keep "time=$(date -u +%FT%TZ) by=workspace-58 hold-keeper (C4 then v11)"; log "re-created HOLD"; }
  sleep 3
done
