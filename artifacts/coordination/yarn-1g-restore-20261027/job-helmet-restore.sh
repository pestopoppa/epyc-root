#!/bin/bash
set -euo pipefail
S=/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch
: "${HELMET_OUTPUT_BUDGET_GIB:?owner budget required}"
sha256sum -c "$S/HELMET-SOURCES.sha256"
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
  exec /usr/bin/python3 -B "$S/deps/dryrun_check.py" boundary --job "$S/job-helmet-restore.sh" --effect first-output-directory-write
fi
: "${FILLER_DEADLINE:?owner grant required}"
: "${FILLER_CPUS:?owner CPU grant required}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
exec taskset -c "$FILLER_CPUS" /usr/bin/python3 -B "$S/helmet_restore.py" --budget-gib "$HELMET_OUTPUT_BUDGET_GIB" --deadline-epoch "$FILLER_DEADLINE"
