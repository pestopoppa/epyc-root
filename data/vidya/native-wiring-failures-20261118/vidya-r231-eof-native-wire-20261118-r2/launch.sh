#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/r231-eof-wire-20261118/r2
cd "$D"
sha256sum --check --status SOURCE.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id vidya-r231-eof-native-wire-20261118-r2 --class cpu --role bench --gpu-quiet none \
  --claim-cpus "${WS58_REGIONS:-0-3}" --min-window 120 --stop "$D/STOP" --workdir "$D" \
  --precond-cmd "/usr/bin/python3 -B '$D/capture.py' --precond" \
  --complete-cmd "/usr/bin/python3 -B '$D/capture.py' --complete" \
  --cmd "/usr/bin/python3 -B '$D/capture.py'"
