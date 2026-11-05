#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/g3-slots-deadline-qual-r2-20261105
export ROWFLOW_REPO=/mnt/raid0/llm/worktrees/mains/h-kvfork
printf '%s  %s\n' 25f07ac9e5f66b7f67b2ae172cfad94f5538f31a15e33de4de100c681cc69e68 "$D/SEALED.sha256" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SEALED.sha256)
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
  : "${FILLER_DRYRUN_RESULT_PATH:?}"
  export SLOTS_RESULT="$FILLER_DRYRUN_RESULT_PATH"
else
  export SLOTS_RESULT="$D/out/full-attempt/RESULT.json"
fi
[[ ! -e "$SLOTS_RESULT" && ! -L "$SLOTS_RESULT" ]] || exit 2
export PYTHONDONTWRITEBYTECODE=1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf18-g3-slots-deadline-qual-r2-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/complete.py'" --cmd "python3 -B '$D/test_slots.py'"
