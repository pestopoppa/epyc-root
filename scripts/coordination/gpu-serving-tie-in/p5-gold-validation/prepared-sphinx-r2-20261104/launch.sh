#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/gpu-serving-tie-in/p5-sphinx-second-r2-20261104
ID=codex-gpu-serving-p5-sphinx-gold-r2-20261104
if [[ ${1:-} == --job ]]; then
  cd "$D"
  test -f "$D/PREPARATION_READY"
  printf '%s  %s\n' '0d7bda06d2df025afe509b9b78981c80ea96e3bff6b78f212d76ee2bcfaf87c7' SOURCE.sha256 | sha256sum -c >/dev/null
  sha256sum -c SOURCE.sha256 >/dev/null
  export P5_INSTRUMENT_DEADLINE=$(/mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python -B -c 'import time; print(time.time()+270)')
  export TMPDIR="$D/control-tmp"
  test -d "$TMPDIR"
  taskset -c "${FILLER_CPUS:?}" /mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python -B "$D/run-controls.py" > "$D/controls.log" 2>&1
  exec taskset -c "${FILLER_CPUS:?}" /mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python -B "$D/job.py"
fi
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --role bench --claim-cpus "${WS58_REGIONS:?}" --min-window 300 --stop "$D/STOP" --workdir "$D" --cmd "bash $D/launch.sh --job" --complete-cmd "python3 $D/complete.py"
