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
F=${CTCQD_FLAGS:-/mnt/raid0/llm/tmp/compute-flags}; G=$F/grants
Q=$F/ws58-quarters-20261027.queue; D=$F/ws58-quarters-20261027.queue.done
LOG=$F/grant-ws58-quarters-20261027.log
RL=${CTCQD_RL:-/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock}
GATE=${CTCQD_GATE:-$F/registration_gate.py}
echo $$ > $F/grant-ws58-quarters-20261027.pid; touch $D
log() { echo "$(date -u +%FT%TZ) $*" >> $LOG; }
mark_done() { (
  flock -x 8 || exit 1
  [ ! -e "$F/.registration-pending.json" ] || exit 1
  grep -Fx "$1|$2|$3|$4|$5" "$Q" >/dev/null || exit 1
  [ "$(python3 "$GATE" --flags "$F" row-hash --id "$1")" = "$7" ] || exit 1
  case "$6" in
    complete) [ -e "$G/$1.complete" ] && [ "$(sha256sum "$G/$1.complete")" = "$8" ] || exit 1 ;;
    dead) ! ps -o pid= -p "$2" >/dev/null 2>&1 || exit 1 ;;
    failed) [ -e "$F/.wsq-granted-$1" ] && [ -e "$G/$1.ended" ] && [ "$(stat -c %Y "$G/$1.ended")" -ge "$(stat -c %Y "$F/.wsq-granted-$1")" ] || exit 1
      [ "$(sha256sum "$G/$1.ended")" = "$8" ] && [ "$(stat -c %y "$F/.wsq-granted-$1")" = "$9" ] || exit 1
      rc=$(head -1 "$G/$1.ended" | sed -n 's/^rc=\([0-9]*\).*/\1/p'); case "$rc" in 0|75|124) exit 1;; esac ;;
    *) exit 1 ;;
  esac
  printf '%s\n' "$1" >> "$D"
) 8>"$F/.publication.lock"; }
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
    rowhash=$(python3 "$GATE" --flags "$F" row-hash --id "$id" 2>/dev/null) || continue
    [ -e $G/$id.complete ] && { if mark_done "$id" "$lp" "$win" "$gib" "$regs" complete "$rowhash" "$(sha256sum "$G/$id.complete")" ''; then log "$id complete; skip"; else log "$id mark skipped: state changed"; fi; continue; }
    [ -e $G/$id.grant ] && continue
    if [ -e $F/.wsq-granted-$id ]; then
      [ -e $G/$id.ended ] && [ "$(stat -c %Y $G/$id.ended)" -ge "$(stat -c %Y $F/.wsq-granted-$id)" ] || continue
      erc=$(head -1 $G/$id.ended | sed -n 's/^rc=\([0-9]*\).*/\1/p')
      case "$erc" in 0|75|124) ;; *) if mark_done "$id" "$lp" "$win" "$gib" "$regs" failed "$rowhash" "$(sha256sum "$G/$id.ended")" "$(stat -c %y "$F/.wsq-granted-$id")"; then log "$id HELD: last end rc=$erc"; else log "$id mark skipped: state changed"; fi; continue;; esac
    fi
    ps -o pid= -p "$lp" >/dev/null 2>&1 || { if mark_done "$id" "$lp" "$win" "$gib" "$regs" dead "$rowhash" '' ''; then log "$id: launcher $lp gone; skip"; else log "$id mark skipped: state changed"; fi; continue; }
    ok=1; for q in $(quarters "$regs"); do qfree $q || ok=0; done; [ $ok = 1 ] || continue
    st=$(date -u +%s); W=$(( CAP - st )); [ $W -gt $win ] && W=$win
    # One lease covers final queue/claim recheck, sweep, admission and grant write.
    exec 9>"$F/.publication.lock"; flock -x 9 || { exec 9>&-; continue; }
    if holdfile >/dev/null || [ -e "$G/$id.grant" ] || grep -qx "$id" "$D" || ! grep -Fx "$id|$lp|$win|$gib|$regs" "$Q" >/dev/null; then exec 9>&-; continue; fi
    st=$(date -u +%s); W=$(( CAP - st )); [ "$W" -gt "$win" ] && W=$win
    [ "$W" -gt 0 ] || { exec 9>&-; continue; }
    ok=1; for q in $(quarters "$regs"); do qfree "$q" || ok=0; done
    [ "$ok" = 1 ] || { exec 9>&-; continue; }
    gate=$(python3 "$GATE" --flags "$F" grant --id "$id" 2>&1) || { log "$id sweep refused: $gate"; exec 9>&-; continue; }
    log "$id sweep: $gate"
    r=$($F/grant_ok.sh $id $gib --window-s $W --regions $regs); rc=$?
    [ $rc = 0 ] || { [ $rc = 12 ] || log "$id refused rc=$rc: $r"; exec 9>&-; continue; }
    # SMT fold (ws58 10-25): GPU host threads 184-191 are SMT siblings of q3 cores 88-95. While a GPU grant is open,
    # q3 takes only block-correctness rows (no timing work beside the GPU runner).
    case " $(quarters "$regs") " in *" q3 "*)
      if ls $G/*.grant 2>/dev/null | xargs -r grep -lE "regions=[^ ]*184-191" 2>/dev/null | grep . >/dev/null; then
        echo "$r" | grep -F "class=block-correctness" >/dev/null || { log "$id: q3 held for correctness while GPU host threads 184-191 are granted; skip"; exec 9>&-; continue; }
      fi;; esac
    grant_tmp=$(mktemp "$G/.${id}.grant.XXXXXXXX") || { exec 9>&-; continue; }
    if ! printf 'regions=%s start=%s end=%s\n' "$regs" "$(ts $st)" "$(ts $(( st + W )))" > "$grant_tmp" || ! mv -f -- "$grant_tmp" "$G/$id.grant"; then
      rm -f -- "$grant_tmp"; log "$id grant publication failed"; exec 9>&-; continue
    fi
    touch $F/.wsq-granted-$id; exec 9>&-; log "$r; granted $id: $(cat $G/$id.grant)"; placed=1
  done < $Q
  [ $placed = 1 ] && sleep 20 || sleep 45
done
log "past cap-600s 10-28; done"
