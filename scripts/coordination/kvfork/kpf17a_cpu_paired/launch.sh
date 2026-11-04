#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf17a-cpu-paired
ENGINE=/mnt/raid0/llm/tmp/kvfork/kpf17a-cpu-paired/filler_run15.sh
exec bash "$ENGINE" --id kvfork17a-cpu-paired --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" \
  --complete-cmd "test -e '$D/out/COMPLETE'" --workdir "$D" \
  --cmd "python3 '$D/job.py'" --precond-cmd "python3 '$D/job.py' --check"
