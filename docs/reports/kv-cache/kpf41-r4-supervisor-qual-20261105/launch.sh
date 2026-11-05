#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf41-r4-supervisor-qual-20261105
printf '%s  %s\n' 'c278461fc766ca887389a419bcd0a1ca62711141074ee761b6da0e661c648e17' "$D/SEALED.sha256" | sha256sum --status -c -
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
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf41-r4-supervisor-qual-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/complete.py'" --cmd "python3 -B '$D/probe.py'"
