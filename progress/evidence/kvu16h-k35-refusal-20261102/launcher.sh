#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/k35-native-validation-20261102
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id handoff-kvu16h-k35-native-20261102 --class gpu \
  --cmd "python3 $D/native_job.py" --min-window 600 \
  --stop "$D/stop" --port 19761,19762 --gpu-quiet exclusive \
  --claim-cpus 0-95 --gpu-threads 184-191 --role bench --workdir "$D" \
  --complete-cmd "python3 $D/check_complete.py"
