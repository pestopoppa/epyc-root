#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/parity-native-20261118
cd "$D"
/usr/bin/sha256sum --check --strict --status SOURCE.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id q38p4-greedy-parity-20261118-r1 --class gpu --gpu-quiet exclusive --claim-cpus 184-191 --role correctness \
  --min-window 330 --stop-grace 40 --gpu-threads 184-191 --port 19433,19434 \
  --cmd "/usr/bin/python3 -B $D/runner.py" --complete-cmd "/usr/bin/python3 -B $D/check.py" \
  --stop "$D/STOP" --workdir "$D"
