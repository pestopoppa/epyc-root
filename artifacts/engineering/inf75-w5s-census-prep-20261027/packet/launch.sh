#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-w4-census-prep/w5s
export FILLER_STATE_DIR=${FILLER_STATE_DIR:-$D/state}
exec bash "$D/deps/filler_run12.sh" --id inf75-c5-w5s-full-census --class cpu --gpu-quiet none --role build \
 --min-window 5400 --port 18678 --stop "$D/STOP" --workdir "$D" --cmd "bash $D/job.sh" --complete-cmd "test -s $D/COMPLETE"
