#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf50-own-child-memory-read-20261105
printf '%s  %s\n' a814c597a7754e99293aa8fb3c46e1835b5839de75a4e79ec3c7822ade4ccf46 "$D/job.py" | sha256sum --status -c -
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf50-own-child-memory-read-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/job.py' --complete" --cmd "python3 -B '$D/job.py'"
