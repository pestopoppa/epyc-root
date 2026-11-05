#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kpf17-sealed-elf-loader-20261105
printf '%s  %s\n' eec9180c1a8c9f8ac830a8a9a9934c2d6828c7d7421092db46178b3dcec5b3c5 "$D/job.py" | sha256sum --status -c -
printf '%s  %s\n' eeadfc9fb8e87e131b6ec49da9bf214fe98e4e433b399cd79c4a2c9cb722be57 "$D/fixture.c" | sha256sum --status -c -
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf17-sealed-elf-loader-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/job.py' --complete" --cmd "python3 -B '$D/job.py'"
