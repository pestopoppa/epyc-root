#!/bin/bash
set -euo pipefail
BASE=/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/jobs/cpu
exec bash /mnt/raid0/llm/tmp/refactor-01a16fc3/compute-coordination-20261026/launch-contract-85c442b3d/filler_run12.sh --id refactor-01a16fc3-c5-cpu-build-20261027 --class cpu --claim-cpus 72-95 --role build --min-window 900 --cmd "bash $BASE/job.sh" --stop "$BASE/STOP" --workdir /mnt/raid0/llm/worktrees/prep-01a16fc3-c5-candidate
