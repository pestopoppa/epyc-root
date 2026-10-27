#!/bin/bash
# v13 (ws58 10-26 21:4xZ): v12 copied verbatim except: log/pid names, cap 2026-10-28T06:00Z (night-chain cap), and it waits for v12 (pid 1976503) to EXIT before doing anything, so only one GPU writer is ever live. v12 exits when < 2300 s remain to its 00:30Z cap.
# v12 (ws58 10-25, prepared by a subagent, NOT ARMED): replaces v11 (pid 1265567). Changes vs v11, per CALENDAR-PLAN.md section 0:
#  (a) the .wsg-granted-<id> stamp is touched INSIDE step() right after the .grant is written (GRANT time), not after step() returns. v11 stamped after
#      .ended appeared, so the stamp was always newer than .ended and the re-offer test [ ended_mtime -ge stamp_mtime ] never passed (hsf-5p-microbench).
#      An item that is skipped/refused/not ready is NOT stamped (v11 stamped refusals as granted).
#  (b) every `kill -0` liveness check is `ps -o pid= -p PID` (kill -0 is blind in this sandbox).
#  (c) cap 2026-10-27T00:30Z.
#  (d) queue-first order and the HOLD pause are kept: each loop pass offers ws58-gpu.queue items (re-offer on clean end rc 0/75/124, other rc -> HELD in
#      ws58-gpu.queue.held) before ufh14/yarn. The pause now honours ANY $F/HOLD_GPU_FOR_QUIET_* file (20261024 and 20261025 names).
#  Dropped vs v11: the fixed pre-loop sequence (pb-qcost-1-confirm-r, kpf17-4c-bisect, c4-gpu-correctness, c4-leak-check): all ended/complete before 10-25.
#  Added: on start, waits out any open GPU grant (a running yarn slice or queue item) so a swap never overlaps; refused items back off 600 s.
# One live GPU writer only: stop v11 (pid 1265567) BEFORE starting this (see README-v12-swap.txt).
set -u
F=${CTCQD_FLAGS:-/mnt/raid0/llm/tmp/compute-flags}
G=$F/grants
LOG=$F/grant-gpu-1026-v13.log
RL=${CTCQD_RL:-/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock}
GATE=${CTCQD_GATE:-$F/registration_gate.py}
echo $$ > $F/grant-gpu-1026-v13.pid
log() { echo "$(date -u +%FT%TZ) $*" >> $LOG; }
mark_held() { (
  flock -x 8 || exit 1
  [ ! -e "$F/.registration-pending.json" ] || exit 1
  grep -Fx "$2" "$F/ws58-gpu.queue" >/dev/null || exit 1
  [ "$(python3 "$GATE" --flags "$F" row-hash --id "$1")" = "$3" ] || exit 1
  [ -e "$F/.wsg-granted-$1" ] && [ -e "$G/$1.ended" ] && [ "$(stat -c %Y "$G/$1.ended")" -ge "$(stat -c %Y "$F/.wsg-granted-$1")" ] || exit 1
  [ "$(sha256sum "$G/$1.ended")" = "$4" ] && [ "$(stat -c %y "$F/.wsg-granted-$1")" = "$5" ] || exit 1
  rc=$(head -1 "$G/$1.ended" | sed -n 's/^rc=\([0-9]*\).*/\1/p'); case "$rc" in 0|75|124) exit 1;; esac
  printf '%s\n' "$1" >> "$F/ws58-gpu.queue.held"
) 8>"$F/.publication.lock"; }
ts() { date -u -d @"$1" +%Y-%m-%dT%H:%MZ; }
alive() { ps -o pid= -p "$1" >/dev/null 2>&1; }
holdfile() { local h; for h in $F/HOLD_GPU_FOR_QUIET_*; do [ -e "$h" ] && { echo "$h"; return 0; }; done; return 1; }
free_of() { # $1 regex of status lines that must be free; waits <= 10 min
  local u=$(( $(date -u +%s) + 600 ))
  while $RL status 2>/dev/null | grep -E "$1" | grep -qE 'HELD|EXCL|SHARED|SHRD'; do [ "$(date -u +%s)" -ge $u ] && return 1; sleep 10; done
}
step() {  # $1 id, $2 pid, $3 seconds, $4 min seconds, $5 GiB, $6 cap epoch, $7 free-regex, $8 regions
  local st en r
  [ -e $G/$1.complete ] && { log "$1 skipped: complete"; return 2; }
  alive "$2" || { log "$1 skipped: launcher $2 not running"; return 2; }
  free_of "$7" || { log "$1 skipped: claims still held"; return 1; }
  st=$(date -u +%s); en=$(( st + $3 )); [ $en -gt $6 ] && en=$6
  [ $(( en - st )) -lt $(( $4 + 300 )) ] && { log "$1 skipped: window $(( en - st )) s < min $4 + 300"; return 1; }
  exec 9>"$F/.publication.lock"; flock -x 9 || { exec 9>&-; return 1; }
  if holdfile >/dev/null || [ -e "$G/$1.grant" ] || [ -e "$G/$1.complete" ] || ! alive "$2"; then exec 9>&-; return 1; fi
  if [ "${9:-}" != '' ] && ! grep -Fx "${9}" "$F/ws58-gpu.queue" >/dev/null; then exec 9>&-; return 1; fi
  if [ "${9:-}" != '' ] && grep -qx "$1" "$F/ws58-gpu.queue.held" 2>/dev/null; then exec 9>&-; return 1; fi
  st=$(date -u +%s); en=$(( st + $3 )); [ "$en" -gt "$6" ] && en=$6
  [ $(( en - st )) -ge $(( $4 + 300 )) ] || { exec 9>&-; return 1; }
  if ls "$G"/*.grant >/dev/null 2>&1 && grep -l 'mi210_0' "$G"/*.grant >/dev/null 2>&1; then exec 9>&-; return 1; fi
  if "$RL" status 2>/dev/null | grep -E "$7" | grep -qE 'HELD|EXCL|SHARED|SHRD'; then exec 9>&-; return 1; fi
  gate=$(python3 "$GATE" --flags "$F" grant --id "$1" 2>&1) || { log "$1 sweep refused: $gate"; exec 9>&-; return 2; }
  log "$1 sweep: $gate"
  r=$($F/grant_ok.sh "$1" "$5" --window-s "$((en-st))" --regions "${8:-mi210_0,184-191}") || { exec 9>&-; case "$r" in *"not ready"*) log "$1 not ready: ${r:0:120}"; return 1;; esac; log "$1 refused: $r"; return 2; }
  grant_tmp=$(mktemp "$G/.$1.grant.XXXXXXXX") || { exec 9>&-; return 1; }
  if ! printf 'regions=%s start=%s end=%s\n' "${8:-mi210_0,184-191}" "$(ts $st)" "$(ts $en)" > "$grant_tmp" || ! mv -f -- "$grant_tmp" "$G/$1.grant"; then
    rm -f -- "$grant_tmp"; log "$1 grant publication failed"; exec 9>&-; return 1
  fi
  touch $F/.wsg-granted-$1; exec 9>&-          # (a) stamp at GRANT time: any later .ended is newer than the stamp
  log "$r; granted $1: $(cat $G/$1.grant)"
  while :; do
    if [ -e $G/$1.ended ] && [ "$(stat -c %Y $G/$1.ended)" -ge $st ]; then log "$1 ended: $(head -1 $G/$1.ended)"; return 0; fi
    [ "$(date -u +%s)" -ge $(( en + 300 )) ] && { log "$1: no .ended by end + 5 min"; return 0; }
    sleep 30
  done
}
GPUQ='^ *gpu-quiet'
UFH=$F/FIXED_ufh14-lb7-1-probes
P3=$(date -u -d '2026-10-28T06:00:00Z' +%s)      # (c) cap
ufh_ready() {  # fixed, not complete, launcher alive, and not already run since the FIXED flag was written
  [ -e $UFH ] && [ ! -e $G/ufh14-lb7-1-probes.complete ] && alive 2562628 || return 1
  [ -e $G/ufh14-lb7-1-probes.ended ] && [ "$(stat -c %Y $G/ufh14-lb7-1-probes.ended)" -ge "$(stat -c %Y $UFH)" ] && return 1
  return 0
}
while ps -o pid= -p 1976503 >/dev/null 2>&1; do sleep 30; done
log "v12 (1976503) gone; v13 starting"
log "armed v13 (stamp at grant, ps liveness, cap $(ts $P3)); adopting any open queue grant, then waiting it out"
GQ=$F/ws58-gpu.queue
for gf in $G/*.grant; do   # swap from v11: an item v11 granted but never stamped (stamp-after-step bug) gets the stamp it should have had: the .grant's own mtime
  [ -e "$gf" ] || continue; gid=$(basename "$gf" .grant)
  line=$(awk -F'|' -v id="$gid" '$1==id {print}' "$GQ")
  [ -n "$line" ] && grep -q 'mi210_0' "$gf" || continue
  rowhash=$(python3 "$GATE" --flags "$F" row-hash --id "$gid" 2>/dev/null) || continue
  grant_hash=$(sha256sum "$gf") || continue; grant_time=$(stat -c %y "$gf") || continue
  exec 9>"$F/.publication.lock"; flock -x 9 || { exec 9>&-; continue; }
  if [ ! -e "$F/.registration-pending.json" ] && grep -Fx "$line" "$GQ" >/dev/null &&
     [ "$(python3 "$GATE" --flags "$F" row-hash --id "$gid" 2>/dev/null)" = "$rowhash" ] &&
     [ -f "$gf" ] && [ "$(sha256sum "$gf")" = "$grant_hash" ] && [ "$(stat -c %y "$gf")" = "$grant_time" ] &&
     grep -q 'mi210_0' "$gf"; then
    if touch -r "$gf" "$F/.wsg-granted-$gid"; then log "adopted open grant $gid: stamp := .grant mtime"; fi
  else log "$gid adoption skipped: state changed or pending"; fi
  exec 9>&-
done
while ls $G/*.grant >/dev/null 2>&1 && grep -l 'mi210_0' $G/*.grant >/dev/null 2>&1 && [ "$(date -u +%s)" -lt $P3 ]; do sleep 30; done
log "no open GPU grant; entering the loop"
declare -A REFUSED
gq_next() {  # grant the first ready item of ws58-gpu.queue (id|pid|win|min|gib|free-regex|regions); 0 = something was granted and ended, 1 = nothing ran
  local id lp win mn gib rx rg erc src now
  while IFS='|' read -r id lp win mn gib rx rg; do
    case "$id" in ''|\#*) continue;; esac
    [ -e $G/$id.complete ] && continue; [ -e $G/$id.grant ] && continue; alive "$lp" || continue
    rowhash=$(python3 "$GATE" --flags "$F" row-hash --id "$id" 2>/dev/null) || continue
    grep -qx "$id" $F/ws58-gpu.queue.held 2>/dev/null && continue
    now=$(date -u +%s); [ "${REFUSED[$id]:-0}" -gt "$now" ] && continue
    if [ -e $F/.wsg-granted-$id ]; then
      [ -e $G/$id.ended ] && [ "$(stat -c %Y $G/$id.ended)" -ge "$(stat -c %Y $F/.wsg-granted-$id)" ] || continue
      erc=$(head -1 $G/$id.ended | sed -n 's/^rc=\([0-9]*\).*/\1/p')
      case "$erc" in 0|75|124) ;; *) if mark_held "$id" "$id|$lp|$win|$mn|$gib|$rx|$rg" "$rowhash" "$(sha256sum "$G/$id.ended")" "$(stat -c %y "$F/.wsg-granted-$id")"; then log "$id HELD: last end rc=$erc"; else log "$id mark skipped: state changed"; fi; continue;; esac
    fi
    step "$id" "$lp" "$win" "$mn" "$gib" $P3 "${rx:-$GPUQ}" "${rg:-mi210_0,184-191}" "$id|$lp|$win|$mn|$gib|$rx|$rg"; src=$?
    [ $src = 1 ] && continue                                   # not ready / claims held: try the next item
    [ $src = 2 ] && { REFUSED[$id]=$(( now + 600 )); continue; }   # refused / complete / launcher gone: back off, no stamp
    return 0
  done < $GQ
  return 1
}
log "loop: queue items first, then ufh14 when re-fixed, else yarn slices; paused while any HOLD_GPU_FOR_QUIET_* exists"
YARN_DONE=0
while [ $(( P3 - $(date -u +%s) )) -ge 2300 ]; do
  if h=$(holdfile); then sleep 60; continue; fi
  if [ -e $GQ ] && gq_next; then continue; fi
  if ufh_ready; then step ufh14-lb7-1-probes 2562628 6000 1920 48 $P3 '^ *(q3|gpu-quiet) '; [ $? = 1 ] && sleep 120; continue; fi
  if [ $YARN_DONE = 1 ] || [ $(( P3 - $(date -u +%s) )) -lt 7500 ]; then sleep 120; continue; fi
  step yarn-extension-arms 1198715 7800 7200 64 $P3 "$GPUQ"; rc=$?
  [ $rc = 2 ] && { YARN_DONE=1; log "yarn done/refused; loop keeps waiting for queue items/ufh14"; }
  [ $rc = 1 ] && sleep 120
done
log "done"
