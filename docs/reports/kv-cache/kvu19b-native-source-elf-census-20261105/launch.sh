#!/bin/bash
set -euo pipefail
D=$(cd -- "$(dirname -- "$0")" && pwd)
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu19b-native-source-elf-census-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "cd '$D' && sha256sum -c seals.sha256" --complete-cmd "python3 -I -B '$D/complete.py'" --cmd "python3 -I -B '$D/job.py'"
