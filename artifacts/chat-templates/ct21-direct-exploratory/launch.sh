#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-ct21-cause-audit
C=/mnt/raid0/llm/tmp/refactor-01a16fc3/compute-coordination-20261026/launch-contract-85c442b3d
exec bash "$C/filler_run12.sh" --id ct21-direct-exploratory-v1 --class gpu --gpu-quiet shared --no-fold-siblings --role build --min-window 900 --stop "$D/STOP" --port 18822 --workdir "$D" --cmd "bash $D/job.sh"
