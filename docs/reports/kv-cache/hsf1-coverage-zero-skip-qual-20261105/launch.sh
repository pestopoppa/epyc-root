#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/hsf1-coverage-zero-skip-qual-20261105
printf '%s  %s\n' 38a5a69dc64b52e84a5729679ea9829e5d9a43e7cb157ec773bdc58a210dc005 "$D/SEALED.sha256" | sha256sum --status -c -
sha256sum --quiet -c "$D/SEALED.sha256"
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id hsf1-coverage-zero-skip-qual-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/qualify.py' --complete" --cmd "python3 -B '$D/qualify.py'"
