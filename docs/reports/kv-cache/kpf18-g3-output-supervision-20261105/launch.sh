#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf18-g3-output-supervision-20261105
export ROWFLOW_REPO=/mnt/raid0/llm/worktrees/mains/h-heterogeneous-slot-fabric-residency
printf '%s  %s\n' 319de60d864b1f743522355516fdf844933d12e1325bf56cc4ebf870eb734cca "$D/SEALED.sha256" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SEALED.sha256)
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
  : "${FILLER_DRYRUN_RESULT_PATH:?}"
  export QUAL_RESULT="$FILLER_DRYRUN_RESULT_PATH"
  [[ "$QUAL_RESULT" != "$D/out/full-attempt/RESULT.json" ]] || exit 2
else
  export QUAL_RESULT="$D/out/full-attempt/RESULT.json"
fi
[[ ! -e "$QUAL_RESULT" && ! -L "$QUAL_RESULT" ]] || exit 2
export PYTHONDONTWRITEBYTECODE=1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf18-g3-output-supervision-qual-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/complete.py'" --cmd "python3 -B '$D/job.py'"
