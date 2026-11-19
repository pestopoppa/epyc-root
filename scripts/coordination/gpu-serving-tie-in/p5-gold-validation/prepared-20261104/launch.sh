#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/gpu-serving-tie-in/p5-gold-offline-r3
ID=codex-gpu-serving-p5-gold-offline-r3-20261104
if [[ ${1:-} == --job ]]; then
  cd "$D"
  printf '%s  %s\n' 'f4cbcf8b12ddd6063f6d185638342f9ac3c43ed834dde9760471a0734cc55443' SOURCE.sha256 | sha256sum -c >/dev/null
  sha256sum -c SOURCE.sha256 >/dev/null
  exec taskset -c "${FILLER_CPUS:?}" /mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python -B "$D/job.py"
fi
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --role bench --claim-cpus "${WS58_REGIONS:?}" --min-window 1800 --stop "$D/STOP" --workdir "$D" --cmd "bash $D/launch.sh --job" --complete-cmd "python3 $D/complete.py"
