#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf18-g3-preload-entry-qual-20261105
export ROWFLOW_REPO=/mnt/raid0/llm/worktrees/mains/h-heterogeneous-slot-fabric-residency
printf '%s  %s\n' 'd7e2614cf0da5b26e541299eacfee7f58e9a137454f967b35da9d9edc277a892' "$D/SEALED.sha256" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SEALED.sha256)
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
  : "${FILLER_DRYRUN_RESULT_PATH:?}" "${FILLER_DRYRUN_DIR:?}"
  [[ "$FILLER_DRYRUN_DIR" == /mnt/raid0/llm/tmp/compute-flags/dryrun/kpf18-g3-preload-entry-qual-20261105 ]] || exit 2
  export QUAL_RESULT="$FILLER_DRYRUN_RESULT_PATH" QUAL_EXPECTED_STOP="$FILLER_DRYRUN_DIR/stop"
  [[ "$QUAL_RESULT" != "$D/out/full-attempt/RESULT.json" ]] || exit 2
else
  export QUAL_RESULT="$D/out/full-attempt/RESULT.json" QUAL_EXPECTED_STOP="$D/STOP"
fi
[[ ! -e "$QUAL_RESULT" && ! -L "$QUAL_RESULT" ]] || exit 2
export PYTHONDONTWRITEBYTECODE=1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf18-g3-preload-entry-qual-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/complete.py'" --cmd "python3 -B '$D/job.py'"
