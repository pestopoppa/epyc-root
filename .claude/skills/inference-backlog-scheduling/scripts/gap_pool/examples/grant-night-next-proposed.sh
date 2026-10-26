#!/bin/bash
# workspace-58 whole-host night 2026-10-26 (PREPARED, NOT ARMED). Chain: wait KPF-64.3 EB end -> HOLD -> whole-host quiet ->
#  akx-lb3-2-cv2-pair-20261026 (0-95, 110 GiB, reserve gpu-quiet, min(7500,cap-now), min 6900+300) -> v11-086-cpu (0-95, 95 GiB, 6600 s, min 6300,
#  only if ARMED ready=y + live launcher) -> release HOLD. Cap 2026-10-27T10:00Z. Flag WS58_NIGHT_1026_ENDED on every exit.
# HOLD content names the step being granted (grant=<id>): a job guard may accept a HOLD whose grant= equals its own FILLER_ID; any other HOLD refuses.
# HOLD is written only AFTER EB ended: the EB writer pauses on any HOLD_* file and would otherwise never start.
# Usage: grant-night-1026.sh [--simulate]   (--simulate prints constants, touches nothing)
set -euo pipefail
F=/mnt/raid0/llm/tmp/compute-flags; G=$F/grants; LOG=$F/grant-night-1026.log
RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
HOLD=$F/HOLD_GPU_FOR_QUIET_NIGHT_20261026; FLAG=$F/WS58_NIGHT_1026_ENDED
EB=kpf64-eb-q2q3; EBD=/mnt/raid0/llm/tmp/cal-1025/kpf64-eb-q2q3
GIVEUP=$(date -u -d '2026-10-27T10:00:00Z' +%s)
ts() { date -u -d @"$1" +%Y-%m-%dT%H:%MZ; }
if [ "${1:-}" = "--simulate" ]; then echo "giveup/cap $(ts $GIVEUP) hold=$HOLD flag=$FLAG"; exit 0; fi
echo $$ > $F/grant-night-1026.pid
log() { echo "$(date -u +%FT%TZ) $*" >> $LOG; }
# PROPOSED owner whole-producer cutover only; shared lease for every HOLD mutation.
ADAPTER=$(dirname "$(readlink -f "$0")")/..
hold_write() { /usr/bin/python3 -B "$ADAPTER/gap_serialization_v1.py" --flags "$F" --name "${HOLD##*/}" --text "$1" || exit 6; }
hold_remove() { /usr/bin/python3 -B "$ADAPTER/gap_serialization_v1.py" --flags "$F" --name "${HOLD##*/}" --remove || exit 6; }
hold_keep() { /usr/bin/python3 -B "$ADAPTER/gap_serialization_v1.py" --flags "$F" --name "${HOLD##*/}" --text "$1" --if-missing || exit 6; }
cleanup() { [ -e $HOLD ] && hold_remove && log "removed $(basename $HOLD)"; touch $FLAG; log "touched $(basename $FLAG)"; }
trap cleanup EXIT
late() { [ "$(date -u +%s)" -ge $GIVEUP ]; }
rowpid() { grep "^| $1 |" $F/FILLERS.md | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2 || true; }
row_ready() {  # ARMED + ready=y (cells 8, 13 of split('|'))
  /usr/bin/python3 -I - $F/FILLERS.md "$1" <<'PY'
import sys
for l in open(sys.argv[1]):
    if l.startswith('| '+sys.argv[2]+' |'):
        c = l.split('|')
        sys.exit(0 if len(c) >= 20 and c[8].strip() == 'ARMED' and c[13].strip() == 'y' else 1)
sys.exit(1)
PY
}
backlog() {  # $1 id $2 blocker : demote row to BACKLOG ready=n with blocker= note
  [ -e $F/FILLERS.md ] || return 0
  cp -p $F/FILLERS.md $F/FILLERS.md.bak-ws58-night1026-$(date -u +%Y%m%dT%H%M%SZ)
  /usr/bin/python3 -I - "$F/FILLERS.md" "$1" "$2" <<'PY' || log "backlog edit of $1 failed"
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
  log "FILLERS row $1 -> BACKLOG blocker=$2"
}
eb_ended() {  # EB granted (stamp) and a newer .ended exists, no open EB grant; or EB done (complete/PASSED)
  [ -e $G/$EB.complete ] || [ -e $EBD/PASSED ] && return 0
  [ -e $G/$EB.grant ] && return 1
  [ -e $F/.wsq-granted-$EB ] && [ -e $G/$EB.ended ] && [ "$(stat -c %Y $G/$EB.ended)" -ge "$(stat -c %Y $F/.wsq-granted-$EB)" ]
}
quiet() { ! ls $G/*.grant >/dev/null 2>&1 && ! $RL status 2>/dev/null | grep -E 'HELD|EXCL|SHARED|SHRD' >/dev/null; }
# step id pid secs minsecs gib : returns 0 granted+ended, 1 not run
step() {
  local id=$1 pid=$2 sec=$3 min=$4 gib=$5 st W r rc en
  [ -e $G/$id.complete ] && { log "$id skipped: complete"; return 1; }
  ps -o pid= -p "$pid" >/dev/null 2>&1 || { log "$id skipped: launcher '$pid' not running"; backlog $id "launcher gone night 10-26"; return 1; }
  st=$(date -u +%s); W=$(( GIVEUP - st )); [ $W -gt $sec ] && W=$sec
  [ $W -lt $(( min + 300 )) ] && { log "$id skipped: window $W s < $min + 300"; backlog $id "no quiet window night 10-26"; return 1; }
  set +e; r=$($F/grant_ok.sh $id $gib --window-s $W --regions 0-95 --reserve gpu-quiet); rc=$?; set -e
  [ $rc = 0 ] || { log "$id refused rc=$rc: $r"; backlog $id "grant_ok refused rc=$rc night 10-26"; return 1; }
  en=$(( st + W ))
  printf 'regions=0-95 start=%s end=%s\n' "$(ts $st)" "$(ts $en)" > $G/$id.grant
  touch $F/.wsg-granted-$id
  log "$r; granted $id: $(cat $G/$id.grant)"
  until { [ -e $G/$id.ended ] && [ "$(stat -c %Y $G/$id.ended)" -ge $st ]; } || [ "$(date -u +%s)" -ge $(( en + 300 )) ]; do sleep 30; done
  log "$id ended: $(head -1 $G/$id.ended 2>/dev/null || echo none)"
  if [ ! -e $G/$id.complete ]; then
    local erc; erc=$(head -1 $G/$id.ended 2>/dev/null | sed -n 's/^rc=\([0-9]*\).*/\1/p' || true)
    backlog $id "window ended incomplete rc=${erc:-none} night 10-26"
  fi
  return 0
}
log "armed (giveup/cap $(ts $GIVEUP))"
until eb_ended; do late && { log "EB not ended by cap"; exit 0; }; sleep 60; done
log "EB ended"
hold_write "time=$(date -u +%FT%TZ) by=workspace-58 for=night-1026"; log "wrote $(basename $HOLD)"
until quiet; do late && { log "not quiet by cap: grants=$(ls $G/*.grant 2>/dev/null | tr '\n' ' ')"; exit 0; }; sleep 20; done
log "host quiet"
A=akx-lb3-2-cv2-pair-20261026
ran=0
until [ $ran = 1 ]; do   # the launcher is started later by Codex: wait for an ARMED ready=y row with a live pid
  p=$(rowpid $A); if [ -n "$p" ] && row_ready $A && ps -o pid= -p "$p" >/dev/null 2>&1; then
    quiet || { late && break; sleep 20; continue; }
    hold_write "time=$(date -u +%FT%TZ) by=workspace-58 for=night-1026 grant=$A"
    step $A "$p" 7500 6900 110 && ran=1 || ran=1; break
  fi
  late && { log "$A: no ARMED ready=y row with live launcher by cap"; break; }
  sleep 30
done
V=v11-086-cpu
vp=$(rowpid $V)
if [ -n "$vp" ] && row_ready $V && ps -o pid= -p "$vp" >/dev/null 2>&1; then
  until quiet; do late && { log "$V: not quiet by cap"; exit 0; }; sleep 20; done
  hold_write "time=$(date -u +%FT%TZ) by=workspace-58 for=night-1026 grant=$V"
  step $V "$vp" 6600 6300 95 || true
else
  log "$V skipped: not ARMED ready=y with live launcher (pid='${vp:-}')"
fi
exit 0
