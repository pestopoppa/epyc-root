#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/p5-sphinx-scorer-r1-20261118
cd "$D"
printf '%s  %s\n' '043d71cc481de0346f6fd186c64b6ab978758e830b1dde2cb3de41163b2cd2bf' preflight.sh | sha256sum --check --status
if [[ ${1:-} == --preflight ]]; then
  exec /bin/bash "$D/preflight.sh"
fi
if [[ ${1:-} == --job ]]; then
  /bin/bash "$D/preflight.sh"
  unset PYTHONPATH PYTHONHOME
  exec /mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python -B "$D/custody.py" run
fi
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id vb-p5-sphinx-scorer-native-20261118 --class cpu --role bench --min-window 300 \
  --stop "$D/STOP" --workdir "$D" --precond-cmd "/bin/bash $D/launch.sh --preflight" \
  --cmd "/bin/bash $D/launch.sh --job" --complete-cmd "/mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python -B $D/custody.py complete"
