#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kpf18-g3-cancel-order-qual-20261105
export ROWFLOW_REPO=/mnt/raid0/llm/worktrees/mains/h-kvu
printf '%s  %s\n' df8f7f71e43511294e6429e72bb79c8bac1cfe22071aa72f89d1b025d70d532a "$D/SEALED.sha256" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SEALED.sha256)
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
 : "${FILLER_DRYRUN_RESULT_PATH:?}"; export CANCEL_RESULT="$FILLER_DRYRUN_RESULT_PATH"
else export CANCEL_RESULT="$D/out/full-attempt/RESULT.json"; fi
[[ ! -e "$CANCEL_RESULT" && ! -L "$CANCEL_RESULT" ]] || exit 2
export PYTHONDONTWRITEBYTECODE=1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf18-g3-cancel-order-qual-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/complete.py'" --cmd "python3 -B '$D/qualify.py'"
