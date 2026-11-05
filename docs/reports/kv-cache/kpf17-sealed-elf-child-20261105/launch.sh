#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kpf17-sealed-elf-child-20261105
printf '%s  %s\n' 763ecb184079e9f8b2d13d1cc65093fb5f279413273344c0ad40617426ac620c "$D/child.py" | sha256sum --status -c -
printf '%s  %s\n' 94a468a2cce62cdca156dce4a71762572a251dd05b830f25e5219ddafd403876 "$D/job.py" | sha256sum --status -c -
printf '%s  %s\n' eeadfc9fb8e87e131b6ec49da9bf214fe98e4e433b399cd79c4a2c9cb722be57 "$D/fixture.c" | sha256sum --status -c -
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf17-sealed-elf-child-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/job.py' --complete" --cmd "python3 -B '$D/job.py'"
