#!/bin/bash
set -euo pipefail
[[ ${FILLER_SMOKE:-0} == 1 ]] || exit 64
: "${FILLER_DRYRUN_RESULT_PATH:?isolated publisher receipt required}"
: "${WS58_REGIONS:?four publisher smoke CPUs required}"
exec "$(dirname -- "${BASH_SOURCE[0]}")/launch.sh"
