#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf17-memfd-seal-control-20261105
printf '%s  %s\n' dc88e15a0121b75866143bb5b9d267349c5e95d7188a28180ab4b8db11223f1e "$D/job.py" | sha256sum --status -c -
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf17-memfd-seal-control-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/job.py' --complete" --cmd "python3 -B '$D/job.py'"
