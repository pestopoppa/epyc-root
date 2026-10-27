#!/bin/bash
# ws58 10-27 06:0xZ: copy of grant-ws58-quarters-20261026.sh with new queue/done/log names and cap 2026-10-28T06:00Z; start wait removed.
# workspace-58 10-25: successor quarter writer, start gated 2026-10-26T03:30Z, cap 2026-10-27T06:00Z (derived from the 20261025 writer by sed; same logic).
# Queue ws58-quarters-20261027.queue, lines `id|launcher_pid|window_s|gib|regions` (regions = cpu list such as 0-23, 0-71, 72-95, 0-95).
# An item is placed when every quarter its regions touch is free (region-lock shows no claim AND no open grant names it).
# Re-offer after a clean end (rc 0/75/124); any other rc -> HELD in ws58-quarters-20261027.queue.done. Skips .complete ids and dead launchers.
# PAUSES (no new grants, sleeps 60 s) while ANY $F/HOLD_* file exists, resumes when it is gone; exits past CAP-600s (05:50Z 10-26). Every grant ends by 06:00Z 10-26.
# Stamp .wsq-granted-<id> is touched right after the .grant is written (GRANT time); liveness is `ps -o pid= -p` (kill -0 is blind here).
# START ORDER: launchers first (alive pid), THEN append the queue line, THEN this writer: a line whose launcher pid is dead is parked in the .done file for good.
# START: immediately (no predecessor wait). One live writer per region set: before starting, list other live writers.
set -u
F=/mnt/raid0/llm/tmp/compute-flags; G=$F/grants
Q=$F/ws58-quarters-20261027.queue; D=$F/ws58-quarters-20261027.queue.done
LOG=$F/grant-ws58-quarters-20261027.log
RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
echo $$ > $F/grant-ws58-quarters-20261027.pid; touch $D
log() { echo "$(date -u +%FT%TZ) $*" >> $LOG; }
ts() { date -u -d @"$1" +%Y-%m-%dT%H:%MZ; }
holdfile() { local h; for h in $F/HOLD_*; do [ -e "$h" ] && { echo "$h"; return 0; }; done; return 1; }
quarters() {  # cpu list -> the qN names it touches
  local r out="" a b q
  for r in $(echo "$1" | tr ',' ' '); do a=${r%-*}; b=${r#*-}
    for q in 0 1 2 3; do [ $(( q*24 )) -le $b ] && [ $(( q*24+23 )) -ge $a ] && out="$out q$q"; done; done
  echo $out | tr ' ' '\n' | sort -u | tr '\n' ' '; }
qfree() {  # $1 qN
  local lo=$(( ${1#q}*24 )); local hi=$(( lo+23 ))
  $RL status 2>/dev/null | grep -E "^ *$1 " | grep -E 'HELD|EXCL|SHARED|SHRD' >/dev/null && return 1
  ls $G/*.grant 2>/dev/null | xargs -r grep -lE "regions=[^ ]*($1|0-95|$lo-$hi)" 2>/dev/null | grep . >/dev/null && return 1
  return 0; }
log "armed"
CAP=$(date -u -d '2026-10-28T06:00:00Z' +%s)
log "start (v1027: successor of the 10-26 writer, cap 10-28T06:00Z)"
while [ "$(date -u +%s)" -lt $(( CAP - 600 )) ]; do
  if h=$(holdfile); then sleep 60; continue; fi
  placed=0
  while IFS='|' read -r id lp win gib regs; do
    case "$id" in ''|\#*) continue;; esac
    grep -qx "$id" $D && continue
    [ -e $G/$id.complete ] && { echo "$id" >> $D; log "$id complete; skip"; continue; }
    [ -e $G/$id.grant ] && continue
    if [ -e $F/.wsq-granted-$id ]; then
      [ -e $G/$id.ended ] && [ "$(stat -c %Y $G/$id.ended)" -ge "$(stat -c %Y $F/.wsq-granted-$id)" ] || continue
      erc=$(head -1 $G/$id.ended | sed -n 's/^rc=\([0-9]*\).*/\1/p')
      case "$erc" in 0|75|124) ;; *) echo "$id" >> $D; log "$id HELD: last end rc=$erc"; continue;; esac
    fi
    ps -o pid= -p "$lp" >/dev/null 2>&1 || { log "$id: launcher $lp gone; skip"; echo "$id" >> $D; continue; }
    ok=1; for q in $(quarters "$regs"); do qfree $q || ok=0; done; [ $ok = 1 ] || continue
    st=$(date -u +%s); W=$(( CAP - st )); [ $W -gt $win ] && W=$win
    r=$($F/grant_ok.sh $id $gib --window-s $W --regions $regs); rc=$?
    [ $rc = 0 ] || { [ $rc = 12 ] || log "$id refused rc=$rc: $r"; continue; }
    # SMT fold (ws58 10-25): GPU host threads 184-191 are SMT siblings of q3 cores 88-95. While a GPU grant is open,
    # q3 takes only block-correctness rows (no timing work beside the GPU runner).
    case " $(quarters "$regs") " in *" q3 "*)
      if ls $G/*.grant 2>/dev/null | xargs -r grep -lE "regions=[^ ]*184-191" 2>/dev/null | grep . >/dev/null; then
        echo "$r" | grep -F "class=block-correctness" >/dev/null || { log "$id: q3 held for correctness while GPU host threads 184-191 are granted; skip"; continue; }
      fi;; esac
    printf 'regions=%s start=%s end=%s\n' "$regs" "$(ts $st)" "$(ts $(( st + W )))" > $G/$id.grant
    touch $F/.wsq-granted-$id; log "$r; granted $id: $(cat $G/$id.grant)"; placed=1
  done < $Q
  [ $placed = 1 ] && sleep 20 || sleep 45
done
log "past cap-600s 10-28; done"
