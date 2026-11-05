#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kvu19b-multi-clock-20261105
exec python3 "$D/supervise.py" "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}" python3 "$D/job.py"
