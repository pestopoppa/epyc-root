#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf41-supervisor-qual-20261105
printf '%s  %s\n' '253a2cbf8450d14df0b3ac18ee6bd428b71d72bec7a19905a9812b31b23e13ef' "$D/SEALED.sha256" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SEALED.sha256)
export ROWFLOW_REPO=/mnt/raid0/llm/worktrees/mains/h-kvfork
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
  : "${FILLER_DRYRUN_RESULT_PATH:?}"
  export QUAL_RESULT="$FILLER_DRYRUN_RESULT_PATH"
else
  export QUAL_RESULT="$D/out/full-attempt/RESULT.json"
fi
[[ ! -e "$QUAL_RESULT" && ! -L "$QUAL_RESULT" ]] || exit 2
export PYTHONDONTWRITEBYTECODE=1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf41-supervisor-qual-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/complete.py'" --cmd "python3 -B '$D/probe.py'"
