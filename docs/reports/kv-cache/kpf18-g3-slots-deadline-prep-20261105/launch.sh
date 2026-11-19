#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/g3-slots-deadline-qual-20261105
export ROWFLOW_REPO=/mnt/raid0/llm/worktrees/mains/h-kvfork
printf '%s  %s\n' 7cd5804fbbb155815baa0579e61407950474114082e57b92f9d7c017f056bb70 "$D/SEALED.sha256" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SEALED.sha256)
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
  : "${FILLER_DRYRUN_RESULT_PATH:?}"
  export SLOTS_RESULT="$FILLER_DRYRUN_RESULT_PATH"
else
  export SLOTS_RESULT="$D/out/full-attempt/RESULT.json"
fi
[[ ! -e "$SLOTS_RESULT" && ! -L "$SLOTS_RESULT" ]] || exit 2
[[ ${FILLER_SMOKE:-0} != 1 || "$SLOTS_RESULT" != "$D/out/full-attempt/RESULT.json" ]] || exit 2
export PYTHONDONTWRITEBYTECODE=1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf18-g3-slots-deadline-qual-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -c 'import json,os; r=json.load(open(os.environ["SLOTS_RESULT"])); assert r["status"]=="PASS" and r["tests"]==11 and not r["errors"] and not r["failures"]'" --cmd "python3 -B '$D/test_slots.py'"
