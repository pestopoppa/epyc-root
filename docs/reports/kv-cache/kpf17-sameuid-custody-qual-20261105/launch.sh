#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf17-sameuid-custody-qual-20261105
ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh
exec /bin/bash "$ENGINE" --id kvfork17-sameuid-custody-qual-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 '$D/complete.py'" --cmd "python3 '$D/qualify.py'"
