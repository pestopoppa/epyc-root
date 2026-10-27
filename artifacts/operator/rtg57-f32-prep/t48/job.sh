#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-rtg57-f32-completion/packet
[ "${FILLER_ID:-}" = rtg57-c5-vkq-t48 ] || exit 70
[ "${FILLER_PREFLIGHT:-0}" = 1 ] || [ ! -e "$D/STOP" ] || exit 70
if compgen -G '/mnt/raid0/llm/tmp/compute-flags/HOLD_*' >/dev/null; then exit 70; fi
sha256sum -c "$D/SOURCES.sha256"
if [ "${FILLER_PREFLIGHT:-0}" = 1 ]; then
  exec /usr/bin/python3 -B "$D/deps/dryrun_check.py" boundary --job "$D/job.sh" --effect first-model-load
fi
/usr/bin/python3 -B -I "$D/approval-check.py"
BUILD=/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/jobs/cpu
grep -Fx 'BUILD_COMPLETE source=c72ec82f5417bb2937310326120f149b665e8400 kind=cpu end=2026-10-27T10:18:48Z no-model-runs=true' "$BUILD/BUILD_COMPLETE"
sha256sum -c "$BUILD/ELF.sha256"
exec /usr/bin/python3 -B -I "$D/resource-watch.py" --limit-kib 115343360 /usr/bin/python3 -B -I "$D/driver.py"
