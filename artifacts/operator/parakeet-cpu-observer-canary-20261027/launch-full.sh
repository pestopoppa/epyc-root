#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-parakeet-cpu-v2
exec bash /mnt/raid0/llm/tmp/refactor-01a16fc3/compute-coordination-20261026/launch-contract-85c442b3d/filler_run12.sh --id codex-ni-parakeet-observed-full-20261027 --class cpu --claim-cpus 24-25 --role build --min-window 3600 --cmd "bash $D/job.sh full" --stop "$D/STOP-full" --workdir "$D"
