#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf17-alt17
ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh
exec /bin/bash "$ENGINE" --id kvfork17-alt17-custody-race-qual-20261104 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 '$D/complete.py'" --cmd "python3 '$D/qualify.py'"
