#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/hsf1-skipped-source-census-20261105
printf '%s  %s\n' b6051af2f344f753e8145f20b47a6d0ad16bf9abcd0605b99f02879c25e93e94 "$D/SHA256SUMS" | sha256sum --status -c -
sha256sum --quiet -c "$D/SHA256SUMS"
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id hsf1-skipped-source-census-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/job.py' --complete" --precond-cmd "python3 -B '$D/job.py' --check" --cmd "python3 -B '$D/job.py'"
