#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-ram-admission-qual-20261105
export ROWFLOW_REPO=/mnt/raid0/llm/worktrees/mains/h-heterogeneous-slot-fabric-residency
printf '%s  %s\n' 5b2ce67f1ddf77e13ca7973713baccaad5475ad862ba452e5bad804dcac3e794 "$D/SEALED.sha256" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SEALED.sha256)
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
 : "${FILLER_DRYRUN_RESULT_PATH:?}"
 export RAM_RESULT="$FILLER_DRYRUN_RESULT_PATH"
else
 export RAM_RESULT="$D/out/full-attempt/RESULT.json"
fi
[[ ! -e "$RAM_RESULT" && ! -L "$RAM_RESULT" ]] || exit 2
export PYTHONDONTWRITEBYTECODE=1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf18-g3-ram-admission-qual-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/complete.py'" --cmd "python3 -B '$D/supervise.py'"
