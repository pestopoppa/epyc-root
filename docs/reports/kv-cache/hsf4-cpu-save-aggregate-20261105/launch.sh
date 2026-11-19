#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/hsf4-cpu-save-aggregate-20261105
printf '%s  %s\n' e3381b91151295349e8287ef36672091ce9e87d2269e7fa0a3fb678f4a09c4e3 "$D/job.py" | sha256sum --status -c -
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id hsf4-cpu-save-aggregate-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/job.py' --complete" --cmd "python3 -B '$D/job.py'"
