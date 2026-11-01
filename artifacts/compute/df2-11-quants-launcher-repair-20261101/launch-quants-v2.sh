#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/h-df2-11-quants-20261101
export FILLER_RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
export HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 CUDA_VISIBLE_DEVICES=-1
[[ $# == 0 ]] || exit 64
[[ ! -L "$D" && ! -L "$D/attempt.lock" && ! -L "$D/results" && ! -L "$D/outputs" && ! -L "$D/logs" ]] || exit 65
exec 9>"$D/attempt.lock"
flock -n 9 || { echo 'REFUSED: scratch already owned'; exit 75; }
(cd "$D" && sha256sum --check INPUTS-v2.sha256)
mkdir -p "$D/results"
rm -f -- "$D/results/COMPLETE.json" "$D/results/RESULT.json" "$D/results/artifacts.jsonl"
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
 --id h-df2-11-quants-20261101 --class cpu --role build \
 --min-window 300 \
 --complete-cmd 'test -s /mnt/raid0/llm/tmp/h-df2-11-quants-20261101/results/COMPLETE.json' \
 --cmd 'taskset -c "$FILLER_CPUS" /usr/bin/python3 -I -B /mnt/raid0/llm/tmp/h-df2-11-quants-20261101/quantize.py' \
 --stop "$D/STOP" --workdir "$D"
