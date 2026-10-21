#!/bin/bash
# CS-11 chained, self-starting launcher. Start with:  setsid nohup ./chained_launch.sh < /dev/null > flags/launch.out 2>&1 &
# Waits for C2 item e's end flag AND not before NOT_BEFORE; refuses without a valid APPROVED; ALWAYS touches flags/CS11_DONE (rc inside) via trap.
set -uo pipefail
D=/mnt/raid0/llm/tmp/cs11-20261022; F=$D/flags
E=/mnt/raid0/llm/tmp/c2-regate-20261021/flags            # chain_launch.sh e touches e.DONE | e.FAILED | e.SKIPPED here
NOT_BEFORE=2026-10-22T10:45:00Z; HARD_STOP=2026-10-22T12:15:00Z; HARNESS_DEADLINE=2026-10-22T12:10:00Z
LATEST_START=2026-10-22T11:10:00Z                       # a start later than this cannot finish N=3 ABA for both roles (~50 min) before 12:10
rc=1; CH=""; SP=""
say() { echo "[$(date -u +%FT%TZ)] cs11: $*" >> "$F/launch.log"; }
finish() { printf 'rc=%s\nutc=%s\nlauncher_pid=%s\n' "$rc" "$(date -u +%FT%TZ)" "$$" > "$F/CS11_DONE.tmp" && mv -f "$F/CS11_DONE.tmp" "$F/CS11_DONE"; say "CS11_DONE rc=$rc"; }
trap finish EXIT
trap 'say "TERM"; [ -n "$CH" ] && kill "$CH" 2>/dev/null; [ -n "$SP" ] && kill "$SP" 2>/dev/null; rc=143; exit 143' TERM
trap 'say "INT"; [ -n "$CH" ] && kill "$CH" 2>/dev/null; [ -n "$SP" ] && kill "$SP" 2>/dev/null; rc=130; exit 130' INT
nap() { sleep "$1" & SP=$!; wait "$SP"; SP=""; }   # interruptible sleep: traps fire immediately; only our own captured pids are signalled
ts() { date -u -d "$1" +%s; }
rm -f "$F/CS11_DONE"
verify_approved() {
  [ -s "$D/APPROVED" ] || { say "REFUSED: no APPROVED"; return 4; }
  for f in PREDECLARED.md cs11_harness.py analyze.py run_cs11.sh resolve_recipes.py dry/recipes.json chained_launch.sh; do
    grep -q "  $f\$" "$D/APPROVED" || { say "REFUSED: APPROVED lacks $f"; return 4; }
  done
  ( cd "$D" && sha256sum -c --quiet APPROVED ) >> "$F/launch.log" 2>&1 || { say "REFUSED: sha256 mismatch vs APPROVED"; return 4; }
}
say "armed pid=$$ not-before=$NOT_BEFORE hard-stop=$HARD_STOP waiting on $E/e.{DONE,FAILED,SKIPPED}"
verify_approved || { rc=4; exit 4; }
HS=$(ts $HARD_STOP); NB=$(ts $NOT_BEFORE)
while [ "$(date -u +%s)" -lt "$NB" ]; do [ "$(date -u +%s)" -ge "$HS" ] && { rc=5; exit 5; }; nap 20; done
while :; do
  for w in e.DONE e.FAILED e.SKIPPED; do [ -e "$E/$w" ] && { say "item e end flag: $w"; break 2; }; done
  [ "$(date -u +%s)" -ge "$HS" ] && { say "hard stop reached before e ended"; rc=5; exit 5; }
  nap 20
done
[ "$(date -u +%s)" -ge "$(ts $LATEST_START)" ] && { say "too late to start (> $LATEST_START)"; rc=6; exit 6; }
verify_approved || { rc=4; exit 4; }
say "running"
LEFT=$(( HS - $(date -u +%s) ))
timeout --signal=TERM --kill-after=60 "$LEFT" "$D/run_cs11.sh" "$HARNESS_DEADLINE" >> "$F/run.out" 2>&1 &
CH=$!
wait "$CH"; rc=$?
CH=""
say "run rc=$rc"
exit $rc
