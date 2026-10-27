#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-shipped-parity/successor
cd "$D"
sha256sum --quiet -c SOURCE.SHA256SUMS
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
 /mnt/raid0/llm/tmp/repl-emb-25-26-20261020/venv/bin/python -B "$D/deps/dryrun_check.py" boundary --job "$D/job.sh" --effect server-start
 exit 0
fi
[[ ${FILLER_ID:-} == codex-ni-ufh12-gp1-r2-20261027 && ${FILLER_CPUS:-} == 72-95 && ${FILLER_NEEDGPU:-1} == 0 ]]
[[ ${FILLER_DEADLINE:-} =~ ^[0-9]+$ && $EPOCHSECONDS -lt $FILLER_DEADLINE ]]
[[ ! -e "$D/out" && ! -e "$D/run" && ! -e "$D/COMPLETE.json" ]]
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
exec /mnt/raid0/llm/tmp/repl-emb-25-26-20261020/venv/bin/python -B "$D/run_real.py"
