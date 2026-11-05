#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kpf18-g3-admission-integrated-20261105
export ROWFLOW_REPO=/mnt/raid0/llm/worktrees/mains/h-kvu
printf '%s  %s\n' 1fbcf426bf478b166d2b24ea0eb9a34944cf488ee302bb53164d9808474da1ef "$D/SEALED.sha256" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SEALED.sha256)
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
 : "${FILLER_DRYRUN_RESULT_PATH:?}"; export ADMISSION_RESULT="$FILLER_DRYRUN_RESULT_PATH"
else export ADMISSION_RESULT="$D/out/full-attempt/RESULT.json"; fi
[[ ! -e "$ADMISSION_RESULT" && ! -L "$ADMISSION_RESULT" ]] || exit 2
export PYTHONDONTWRITEBYTECODE=1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf18-g3-admission-integrated-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/complete.py'" --cmd "python3 -B '$D/qualify.py'"
