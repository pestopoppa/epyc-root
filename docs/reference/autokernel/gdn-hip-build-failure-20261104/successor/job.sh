#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/autokernel-all-devices-all-dimensions/hip-build-prereq-repair-20261104
: "${FILLER_CPUS:?rowflow must provide four claimed CPUs}"
[[ ${FILLER_ID:-} == codex-ni-akxall31-gdn-hip-build-repair-20261104 ]] || { echo 'wrong FILLER_ID' >&2; exit 64; }
exec taskset -c "$FILLER_CPUS" python3 -I -B "$D/job.py"
