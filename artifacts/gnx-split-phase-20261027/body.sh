#!/bin/bash
set -euo pipefail
root=/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase
unset SPLIT_RUNNING
bash "$root/admission.sh"
case "$FILLER_ID" in
  codex-ni-gnx-split-parse-20261027) stage=prepare19 ;;
  codex-ni-gnx-split-resolve-20261027) stage=resolve ;;
  *) exit 6 ;;
esac
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
  if [[ $stage == prepare19 ]]; then
    exec /usr/bin/python3 -I "$root/stage1-supervisor.py"
  fi
  src="$root/t1-source"; state="$root/t1-state"
else
  if [[ $stage == prepare19 ]]; then
    exec /usr/bin/python3 -I "$root/stage1-supervisor.py"
  fi
  echo 'SPLIT_RESOLVE_DISABLED: sentinels and profile not reviewed' >&2
  exit 6
fi
exec /usr/bin/python3 -I "$root/split.py" "$stage" "$src" "$state"
