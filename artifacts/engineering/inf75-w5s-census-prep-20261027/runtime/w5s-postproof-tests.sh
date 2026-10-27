#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-w4-census-prep
D="$B/w5s"; X="$B/w5s-postproof"; ID=inf75-c5-w5s-full-census
mkdir -p "$X/engine" "$X/poll-grants" "$X/poll-state"
cp "$D/deps/filler_run12.sh" "$X/engine/filler_run12.sh"
printf 'print("ADMIT_PASS fixture")\n' > "$X/engine/dryrun_check.py"
for mode in stale bad good cleanup; do
 T="$X/$mode";mkdir -p "$T/grants" "$T/state"
 export FILLER_GRANTS_DIR="$T/grants" FILLER_STATE_DIR="$T/state" FILLERS_MD="$T/no-fillers" FILLER_POLL=1
 export FILLER_STUB_CMD="touch '$T/result'; exit 0"
 if [ "$mode" = bad ]; then export FILLER_STUB_CMD="touch '$T/result'; exit 7"; fi
 if [ "$mode" = stale ]; then touch "$T/result"; fi
 engine="$X/engine/filler_run12.sh"
 if [ "$mode" = cleanup ]; then
  engine="$X/engine/cleanup.sh"
  sed '/^# ------------------------------------------------------------------ inner/i kill_group() { return 1; }' "$X/engine/filler_run12.sh" > "$engine"
 fi
 printf 'regions=72,73 start=%s end=%s\n' "$(date -u -d '-1 min' +%FT%TZ)" "$(date -u -d '+5 min' +%FT%TZ)" > "$T/grants/fixture-$mode.grant"
 rc=0
 timeout 20 bash "$engine" --id "fixture-$mode" --class cpu --cmd true --min-window 1 --stop "$T/stop" --workdir "$T" --complete-cmd "test -e '$T/result'" > "$T/log" 2>&1 || rc=$?
 case "$mode" in
  stale) [ "$rc" = 70 ] && [ ! -e "$T/grants/fixture-$mode.complete" ] ;;
  bad) [ -e "$T/grants/fixture-$mode.ended" ] && [ ! -e "$T/grants/fixture-$mode.complete" ] && grep -q 'rc=7' "$T/grants/fixture-$mode.ended" ;;
  good) [ "$rc" = 0 ] && [ -e "$T/grants/fixture-$mode.complete" ] ;;
  cleanup) [ -e "$T/grants/fixture-$mode.ended" ] && [ ! -e "$T/grants/fixture-$mode.complete" ] && grep -q 'rc=70' "$T/grants/fixture-$mode.ended" ;;
 esac
 printf 'PASS engine %s\n' "$mode"
done
unset FILLER_STUB_CMD
mapfile -t proofs < <(find "$D/dryrun" -name pass.json -type f)
[ "${#proofs[@]}" = 1 ] || exit 70
POLL_PID=''
cleanup_poller() { if [ -n "$POLL_PID" ] && kill -0 "$POLL_PID" 2>/dev/null; then kill -TERM "$POLL_PID"; wait "$POLL_PID" 2>/dev/null || true; fi; }
trap cleanup_poller EXIT
FILLER_FLAGS_DIR="$X" FILLER_GRANTS_DIR="$X/poll-grants" FILLER_STATE_DIR="$X/poll-state" \
 FILLERS_MD="$X/ROW-ARMED.md" FILLER_POLL=1 bash "$D/launch.sh" > "$X/poller.log" 2>&1 &
POLL_PID=$!
sed -e "s/pid=UNARMED/pid=$POLL_PID/" -e 's/| BACKLOG |/| ARMED |/' -e 's/| n | n |/| n | y |/' \
 -e "s#dryrun_pass=NOT_YET#dryrun_pass=${proofs[0]}#" "$D/ROW-DRAFT.md" > "$X/ROW-ARMED.md"
kill -0 "$POLL_PID"
GRANT_OK_TEST_FILLERS="$X/ROW-ARMED.md" bash /mnt/raid0/llm/tmp/compute-flags/grant_ok.sh "$ID" 192 --window-s 5700 --regions 0-95 --pid "$POLL_PID"
kill -TERM "$POLL_PID"; wait "$POLL_PID" || true
kill -0 "$POLL_PID" 2>/dev/null && exit 70
POLL_PID=''
sleep 2
printf 'PASS: own temporary poller ended and short poll-sleep drained\n'
