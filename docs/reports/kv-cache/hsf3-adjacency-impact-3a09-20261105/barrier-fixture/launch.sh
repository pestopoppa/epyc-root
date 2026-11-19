#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/hsf3-native-barrier-qualification-20261105
export HSF3_INVOCATION_ID
HSF3_INVOCATION_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
export FILLER_STOPFILE="${FILLER_STOPFILE:-$D/STOP}"
PRECOND="cd '$D' && sha256sum --check runtime.sha256"
if [ "${FILLER_SMOKE:-0}" = 1 ]; then
    : "${FILLER_DRYRUN_RESULT_PATH:?fresh publisher smoke path required}"
    RESULT="$FILLER_DRYRUN_RESULT_PATH"
    JOB="python3 -B '$D/job.py'"
else
    RESULT="$D/out/RESULT.json"
    PRECOND="$PRECOND && test ! -e out"
    JOB="mkdir '$D/out' && python3 -B '$D/job.py' >'$D/out/run.stdout' 2>'$D/out/run.stderr'"
fi
printf -v RESULT_QUOTED '%q' "$RESULT"
COMPLETE="python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x.get(\"row_id\")==\"hsf3-native-barrier-qualification-20261105\" and x.get(\"invocation_id\")==sys.argv[2] and x.get(\"completed_epoch\",0)>=x.get(\"started_epoch\",1) and x.get(\"schema\")==\"hsf3_native_barrier_qualification.v1\" and x.get(\"status\") in (\"PASS\",\"UNSAFE\")' $RESULT_QUOTED '$HSF3_INVOCATION_ID'"
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
 --id hsf3-native-barrier-qualification-20261105 --class cpu --role build --gpu-quiet none --min-window 120 \
 --stop "$D/STOP" --workdir "$D" --precond-cmd "$PRECOND" --complete-cmd "$COMPLETE" --cmd "$JOB"
