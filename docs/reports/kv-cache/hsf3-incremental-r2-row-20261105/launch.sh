#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/hsf3-incremental-r2-20261105
PRECOND="cd '$D' && sha256sum --check runtime.sha256"
if [ "${FILLER_SMOKE:-0}" = 1 ]; then
    : "${FILLER_DRYRUN_RESULT_PATH:?fresh publisher smoke result path required}"
    RESULT="$FILLER_DRYRUN_RESULT_PATH"
    JOB="timeout 10m nice -n 19 python3 -B '$D/census.py'"
else
    RESULT="$D/out/RESULT.json"
    PRECOND="$PRECOND && test ! -e out"
    JOB="mkdir '$D/out' && timeout 10m nice -n 19 python3 -B '$D/census.py' >'$D/out/run.stdout' 2>'$D/out/run.stderr'"
fi
# Quote the external result path for the engine's bash -c boundary.
printf -v RESULT_QUOTED '%q' "$RESULT"
COMPLETE="python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x.get(\"schema\")==\"hsf3_incremental_progress.v1\"' $RESULT_QUOTED"
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
 --id hsf3-incremental-r2-20261105 --class cpu --role build --gpu-quiet none --min-window 120 \
 --stop "$D/STOP" --workdir "$D" \
 --precond-cmd "$PRECOND" \
 --complete-cmd "$COMPLETE" \
 --cmd "$JOB"
