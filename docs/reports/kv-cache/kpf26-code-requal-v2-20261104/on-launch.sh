#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-code-requal-v2-20261104
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id rtg58-kpf26-code-on-diag-20261102 --class cpu --role bench --gpu-quiet none --min-window 900 --stop "$D/on.STOP" --port 18979,18079 --workdir "$D" --complete-cmd "test -e '$D/on.COMPLETE'" --cmd "bash '$D/job.sh' on"
