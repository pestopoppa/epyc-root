#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-rtg57-f32-completion/packet
export FILLER_STATE_DIR=${FILLER_STATE_DIR:-$D/state}
STOP="$D/STOP"
if [ "${FILLER_PREFLIGHT:-0}" = 1 ]; then STOP="$D/preflight-STOP"; fi
exec bash "$D/deps/filler_run12.sh" --id rtg57-c5-vkq-t48 --class cpu --role bench --gpu-quiet none --min-window 5100 --stop "$STOP" --workdir "$D" --cmd "bash $D/job.sh" --complete-cmd "test -s $D/COMPLETE"
