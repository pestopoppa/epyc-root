#!/bin/bash
set -euo pipefail
S=/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch
HELMET_OUTPUT_BUDGET_GIB=32
export HELMET_OUTPUT_BUDGET_GIB
export FILLER_STATE_DIR=${FILLER_STATE_DIR:-$S/state-helmet}
repeat=()
[[ ${FILLER_PREFLIGHT:-0} == 1 ]] || repeat+=(--repeat)
exec "$S/deps/filler_run12.sh" --id ni-yarn-1g-helmet-restore --class cpu --role build --min-window 3600 --stop /mnt/raid0/llm/tmp/compute-flags/STOP.ni-yarn-1g-helmet-restore --workdir "$S" --cmd "bash $S/job-helmet-restore.sh" --complete-cmd "test -s $S/helmet-data/RESTORE_RECEIPT.json" "${repeat[@]}"
