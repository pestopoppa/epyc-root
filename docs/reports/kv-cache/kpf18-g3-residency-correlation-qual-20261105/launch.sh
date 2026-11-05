#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-residency-correlation-qual-20261105
export ROWFLOW_REPO=/mnt/raid0/llm/worktrees/mains/h-heterogeneous-slot-fabric-residency
printf '%s  %s\n' 1f461ba92d362f47fd6df21e60943ef7b26281443d8274d2d43d9b38b1d0dbf9 "$D/SEALED.sha256" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SEALED.sha256)
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
 : "${FILLER_DRYRUN_RESULT_PATH:?}"
 export CORRELATION_RESULT="$FILLER_DRYRUN_RESULT_PATH"
else
 export CORRELATION_RESULT="$D/out/full-attempt/RESULT.json"
fi
[[ ! -e "$CORRELATION_RESULT" && ! -L "$CORRELATION_RESULT" ]] || exit 2
export PYTHONDONTWRITEBYTECODE=1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf18-g3-residency-correlation-qual-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/complete.py' '$CORRELATION_RESULT'" --cmd "python3 -B '$D/qualify.py'"
