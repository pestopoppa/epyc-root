#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-code-requal-v3-20261104
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id rtg58-kpf26-code-off-diag-r2-20261104 --class cpu --role bench --gpu-quiet none --min-window 900 --stop "$D/off.STOP" --port 18978,18078 --workdir "$D" --complete-cmd "test -e '$D/off.COMPLETE'" --cmd "bash '$D/job.sh' off"
