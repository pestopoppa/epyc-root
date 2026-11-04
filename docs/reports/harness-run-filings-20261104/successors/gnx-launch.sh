#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/repl-embedding-retrieval/gnx-shadow/successor-v2
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
exec bash "$D/filler_run15.sh" --id codex-ufh12-shadow-gnx-v2-20261104 --class cpu --role build --claim-cpus 0-95 --gpu-quiet none --min-window 300 --stop "$D/STOP" --complete-cmd "test -e '$D/out/COMPLETE'" --workdir "$D" --cmd "python3 '$D/job.py'" --precond-cmd "python3 '$D/job.py' --check"
