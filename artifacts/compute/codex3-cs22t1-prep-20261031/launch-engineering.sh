#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/cs22t1
cd "$D"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1
case ${1:-} in
 --smoke) export FILLER_CPUS=128,129; exec /usr/bin/taskset -c "$FILLER_CPUS" /usr/bin/python3 -B "$D/smoke-supervisor.py" 265 -- /usr/bin/python3 -B "$D/worker_engineering.py";;
 *) exit 64;;
esac
