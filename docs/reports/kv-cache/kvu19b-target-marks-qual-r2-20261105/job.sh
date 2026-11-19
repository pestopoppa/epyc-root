#!/bin/bash
set -euo pipefail
: "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
exec python3 /mnt/raid0/llm/tmp/kvu/kvu19b-target-marks-qual-r2-20261105/job.py
