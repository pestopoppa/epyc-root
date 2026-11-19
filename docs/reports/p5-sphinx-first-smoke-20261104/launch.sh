#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/gpu-serving-tie-in/p5-sphinx-second-20261104
ID=codex-gpu-serving-p5-sphinx-gold-20261104
if [[ ${1:-} == --job ]]; then
  cd "$D"
  test -f "$D/PREPARATION_READY"
  printf '%s  %s\n' '3f26e8c4c4b3a0bb30a45c0350e94c20e0b8e8ff43dc1463df33264174e596b1' SOURCE.sha256 | sha256sum -c >/dev/null
  sha256sum -c SOURCE.sha256 >/dev/null
  exec taskset -c "${FILLER_CPUS:?}" /mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python -B "$D/job.py"
fi
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --role bench --claim-cpus "${WS58_REGIONS:?}" --min-window 300 --stop "$D/STOP" --workdir "$D" --cmd "bash $D/launch.sh --job" --complete-cmd "python3 $D/complete.py"
