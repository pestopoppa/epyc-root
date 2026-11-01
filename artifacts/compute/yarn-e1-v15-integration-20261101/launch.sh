#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/yarn-e1-v15-integration-20261101
ID=yarn-e1-mem-v15-r1-20261101
ENGINE=/mnt/raid0/llm/worktrees/mains/handoff-yarn/scripts/coordination/rowflow/filler_run15.sh
# Review candidate only: run.py is deliberately disabled; do not publish.
if [[ ${1:-} == --job ]]; then
  exec taskset -c "${FILLER_CPUS:?missing CPUs}" /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B "$D/run.py" --config "$D/REVIEWED-BINDING.json"
fi
[[ $# -eq 0 ]] || exit 64
exec "$ENGINE" --id "$ID" --class gpu --cmd "bash '$D/launch.sh' --job" --min-window 42000 --stop "$D/STOP" --port 18437 --workdir "$D" --complete-cmd "test -f '$D/out/FINAL-VERIFIED'"
