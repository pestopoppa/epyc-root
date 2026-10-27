#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-w4-census-prep/w5s
BASE=/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-census-prep
refuse() { printf 'REFUSED: %s\n' "$*" >&2; exit 70; }
[ "${FILLER_ID:-}" = inf75-c5-w5s-full-census ] || refuse wrong-id
[ ! -e "$D/STOP" ] || refuse STOP
if compgen -G '/mnt/raid0/llm/tmp/compute-flags/HOLD_*' >/dev/null; then refuse HOLD; fi
sha256sum -c "$D/SOURCES.sha256" || refuse source-drift
sha256sum -c "$D/PYTHON.sha256" || refuse python-drift
if [ "${FILLER_PREFLIGHT:-0}" = 1 ]; then
  exec /usr/bin/python3 -B "$D/deps/dryrun_check.py" boundary --job "$D/job.sh" --effect first-native-canary-output-model-load-or-socket
fi
[ "${FILLER_CPUS:-}" = 0-95 ] || refuse wrong-claim
[ "$(awk '/Cpus_allowed_list/{print $2}' /proc/self/status)" = 0-95 ] || refuse wrong-affinity
[ "$((FILLER_DEADLINE-$(date -u +%s)))" -ge 5100 ] || refuse insufficient-attempt-window
for stale in COMPLETE LAST-RESULT owner-start.json out out-pre-eviction.json runtime-slots; do
 [ ! -e "$D/$stale" ] || refuse "stale prior artifact $stale"
done
JOB=/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/jobs/cpu
B=/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/buildcpu
grep -Fx 'BUILD_COMPLETE source=c72ec82f5417bb2937310326120f149b665e8400 kind=cpu end=2026-10-27T10:18:48Z no-model-runs=true' "$JOB/BUILD_COMPLETE" || refuse build-receipt
sha256sum -c "$JOB/ELF.sha256" || refuse stale-image
strings "$B/bin/libggml-base.so" | grep -Fx c72ec82f5 >/dev/null || refuse wrong-compiled-commit
strings "$B/bin/libggml-base.so" | grep -Fx GGML_SCHED_DEBUG >/dev/null || refuse missing-scheduler-knob
export LD_LIBRARY_PATH="$B/bin:/usr/lib/llvm-20/lib" EPYC_ROOT_REPO=/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-w4-census-prep/root-main
unset LD_PRELOAD
bash "$D/verify_ggml_linkage.sh" "$B/bin/llama-server" "$B/bin" || refuse linkage
/usr/bin/python3 -B "$BASE/owner_start.py" "$D/owner-start.json" "$$" "/mnt/raid0/llm/tmp/compute-flags/grants/$FILLER_ID.grant" "$D/SOURCES.sha256" "$D/job.sh"
set +e
/usr/bin/python3 -B "$D/rss_watch.py" --limit-kib $((192 * 1024 * 1024)) \
 /mnt/raid0/llm/tmp/refactor-01a16fc3/ci/phase-b-candidate-venv/bin/python -B "$D/driver.py"
rc=$?
set -e
[ "$rc" -ne 125 ] || exit 70
exit "$rc"
