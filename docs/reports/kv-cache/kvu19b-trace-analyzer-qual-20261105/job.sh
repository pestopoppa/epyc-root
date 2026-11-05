#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kvu19b-trace-analyzer-qual-20261105
: "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
exec python3 "$D/job.py"
