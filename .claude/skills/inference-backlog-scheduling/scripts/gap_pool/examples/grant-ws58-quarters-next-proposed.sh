#!/bin/bash
# workspace-58 10-25: successor quarter writer, start gated 2026-10-26T03:30Z, cap 2026-10-27T06:00Z (derived from the 20261025 writer by sed; same logic).
# Queue ws58-quarters-20261026.queue, lines `id|launcher_pid|window_s|gib|regions` (regions = cpu list such as 0-23, 0-71, 72-95, 0-95).
# An item is placed when every quarter its regions touch is free (region-lock shows no claim AND no open grant names it).
# Re-offer after a clean end (rc 0/75/124); any other rc -> HELD in ws58-quarters-20261026.queue.done. Skips .complete ids and dead launchers.
# PAUSES (no new grants, sleeps 60 s) while ANY $F/HOLD_* file exists, resumes when it is gone; exits past CAP-600s (05:50Z 10-26). Every grant ends by 06:00Z 10-26.
# Stamp .wsq-granted-<id> is touched right after the .grant is written (GRANT time); liveness is `ps -o pid= -p` (kill -0 is blind here).
# START ORDER: launchers first (alive pid), THEN append the queue line, THEN this writer: a line whose launcher pid is dead is parked in the .done file for good.
# START: immediately (no predecessor wait). One live writer per region set: before starting, list other live writers.
set -u
ADAPTER=$(dirname "$(readlink -f "$0")")/.. # owner reviewed versioned installation
F=/mnt/raid0/llm/tmp/compute-flags; G=$F/grants
Q=$F/ws58-quarters-20261026.queue; D=$F/ws58-quarters-20261026.queue.done
LOG=$F/grant-ws58-quarters-20261026.log
RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
echo $$ > $F/grant-ws58-quarters-20261026.pid; touch $D
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
CAP=$(date -u -d '2026-10-27T06:00:00Z' +%s)
log "start: waiting for 2026-10-26T03:30Z"; while [ "$(date -u +%s)" -lt "$(date -u -d 2026-10-26T03:30:00Z +%s)" ]; do sleep 60; done; log "start: 03:30Z reached"
while [ "$(date -u +%s)" -lt $(( CAP - 600 )) ]; do
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
    plan=$(mktemp "$F/.gap-plan.XXXXXX")
    printf 'regions=%s start=%s end=%s\n' "$regs" "$(date -u -d "@$st" +%FT%TZ)" "$(date -u -d "@$((st+W))" +%FT%TZ)" > "$plan"
    r=$(/usr/bin/python3 -B "$ADAPTER/writer_gap_v1.py" --flags "$F" --id "$id" --plan "$plan" -- /bin/bash "$ADAPTER/normal_admission_v1.sh" "$F" "$RL" "$id" "$gib" "$W" "$regs"); rc=$?
    rm -f "$plan"
    [ "$rc" = 0 ] || { log "$id refused rc=$rc: $r"; continue; }
    touch $F/.wsq-granted-$id; log "$r; granted $id: $(cat $G/$id.grant)"; placed=1
  done < $Q
  [ $placed = 1 ] && sleep 20 || sleep 45
done
log "past 05:50Z 10-26; done"
