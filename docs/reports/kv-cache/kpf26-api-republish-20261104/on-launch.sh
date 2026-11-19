#!/bin/bash
set -euo pipefail
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
D=/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-api-republish-20261104
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id rtg58-kpf26-api-on-diag-20261102 --class cpu --role bench --gpu-quiet none --min-window 900 --stop "$D/on.STOP" --port 18977,18077 --workdir "$D" --complete-cmd "test -e '$D/on.COMPLETE'" --cmd "bash '$D/job.sh' on"
