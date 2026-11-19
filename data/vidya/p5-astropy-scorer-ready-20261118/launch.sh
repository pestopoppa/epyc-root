#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/p5-astropy-native-r1-20261118
cd "$D"
printf '%s  %s\n' '2383a87055b057879f68c5e53c9935447dd002d1927fa9ec4f3eac6ba7215765' preflight.sh | sha256sum --check --status
if [[ ${1:-} == --job ]]; then
  /bin/bash "$D/preflight.sh"
  unset PYTHONPATH PYTHONHOME PYTHONOPTIMIZE
  exec /mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python -B "$D/custody.py" run
fi
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id vb-p5-astropy-scorer-native-20261118 --class cpu --role bench --min-window 300 \
  --stop "$D/STOP" --workdir "$D" --precond-cmd "/bin/bash $D/preflight.sh" \
  --cmd "/bin/bash $D/launch.sh --job" --complete-cmd "/mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python -B $D/custody.py complete"
