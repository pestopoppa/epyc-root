#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf18-g3-output-supervision-r2-20261105
export ROWFLOW_REPO=/mnt/raid0/llm/worktrees/mains/h-heterogeneous-slot-fabric-residency
printf '%s  %s\n' 67bef537a25407337a72ada3f861d59a2391fbf433758b12cd5f462107f7c2cf "$D/SEALED.sha256" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SEALED.sha256)
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
  : "${FILLER_DRYRUN_RESULT_PATH:?}"
  export QUAL_RESULT="$FILLER_DRYRUN_RESULT_PATH"
  : "${FILLER_DRYRUN_DIR:?}"
  [[ "$FILLER_DRYRUN_DIR" == /mnt/raid0/llm/tmp/compute-flags/dryrun/kpf18-g3-output-supervision-qual-r2-20261105 ]] || exit 2
  export QUAL_EXPECTED_STOP="$FILLER_DRYRUN_DIR/stop"
  [[ "$QUAL_RESULT" != "$D/out/full-attempt/RESULT.json" ]] || exit 2
else
  export QUAL_RESULT="$D/out/full-attempt/RESULT.json"
  export QUAL_EXPECTED_STOP="$D/STOP"
fi
[[ ! -e "$QUAL_RESULT" && ! -L "$QUAL_RESULT" ]] || exit 2
export PYTHONDONTWRITEBYTECODE=1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf18-g3-output-supervision-qual-r2-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/complete.py'" --cmd "python3 -B '$D/job.py'"
