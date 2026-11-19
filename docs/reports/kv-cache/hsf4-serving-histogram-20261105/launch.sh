#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/hsf4-serving-histogram-20261105
printf '%s  %s\n' 6c349b6f7a56ff8e90310c3a1c4fc1718ed4b54760f9a6014b4b18ff790f7a9a "$D/job.py" | sha256sum --status -c -
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id hsf4-serving-histogram-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/job.py' --complete" --cmd "python3 -B '$D/job.py'"
