#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-w4-census-prep
D="$B/w5s"
ID=inf75-c5-w5s-full-census
P=/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/phase-b-candidate-venv/bin/python
bash "$B/model-free-tests.sh"
bash "$D/seal-draft.sh"
"$P" -B "$B/root-main/scripts/coordination/validate_fillers.py" --file "$D/ROW-DRAFT.md" --row "$ID"
marker="$B/pf-start-$$"; touch "$marker"
/usr/bin/python3 -B "$D/deps/dryrun_check.py" run --id "$ID" --row-file "$D/ROW-DRAFT.md" --min-window-s 5400 \
 --launcher "$D/launch.sh" --job "$D/job.sh" --engine "$D/deps/filler_run12.sh" --source-manifest "$D/SOURCES.sha256" \
 --scoped-pf --entry-json "[\"/bin/bash\",\"$D/launch.sh\"]" --effect first-native-canary-output-model-load-or-socket \
 --regions 72-73 --required-cpus 72,73 --allowed-cpus 72,73 --cwd "$D" --region-lock-shim "$D/pf-shim.sh" --timeout-s 90
mapfile -t proofs < <(find "$D/dryrun" -name pass.json -type f -newer "$marker")
[ "${#proofs[@]}" = 1 ] || { printf 'REFUSED unexpected proof count\n' >&2; exit 70; }
T="$D/pregrant-$$"
mkdir -p "$T/poll-grants" "$T/poll-state"
POLL_PID=''
cleanup() {
 if [ -n "$POLL_PID" ] && kill -0 "$POLL_PID" 2>/dev/null; then kill -TERM "$POLL_PID"; fi
 if [ -n "$POLL_PID" ]; then wait "$POLL_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT
FILLER_FLAGS_DIR="$T" FILLER_GRANTS_DIR="$T/poll-grants" \
 FILLER_STATE_DIR="$T/poll-state" FILLERS_MD="$T/ROW-ARMED.md" \
 FILLER_POLL=1 bash "$D/launch.sh" > "$T/launcher.log" 2>&1 &
POLL_PID=$!
sed -e "s/pid=UNARMED/pid=$POLL_PID/" -e 's/| BACKLOG |/| ARMED |/' -e 's/| n | n |/| n | y |/' \
 -e "s#dryrun_pass=NOT_YET#dryrun_pass=${proofs[0]}#" "$D/ROW-DRAFT.md" > "$T/ROW-ARMED.md"
kill -0 "$POLL_PID"
"$P" -B "$B/root-main/scripts/coordination/validate_fillers.py" --file "$T/ROW-ARMED.md" --row "$ID" --for-grant
start_epoch=$(( $(date -u +%s) / 60 * 60 ))
start=$(date -u -d "@$start_epoch" +%Y-%m-%dT%H:%MZ)
end=$(date -u -d "@$((start_epoch+5700))" +%Y-%m-%dT%H:%MZ)
printf 'regions=0-95 start=%s end=%s\n' "$start" "$end" > "$T/normal-admit.grant"
/usr/bin/python3 -B "$D/deps/dryrun_check.py" admit --id "$ID" --row-file "$T/ROW-ARMED.md" \
 --grant "$T/normal-admit.grant" --min-window-s 5400 --require-proof --engine "$D/deps/filler_run12.sh"
GRANT_OK_TEST_FILLERS="$T/ROW-ARMED.md" bash /mnt/raid0/llm/tmp/compute-flags/grant_ok.sh "$ID" 192 \
 --window-s 5700 --regions 0-95 --pid "$POLL_PID"
kill -TERM "$POLL_PID"
wait "$POLL_PID" || true
if kill -0 "$POLL_PID" 2>/dev/null; then printf 'REFUSED poller not reaped\n' >&2; exit 70; fi
POLL_PID=''
sleep 2
printf 'PASS: normal-minute admission, validator, official grant_ok, captured poller reaped\n'
