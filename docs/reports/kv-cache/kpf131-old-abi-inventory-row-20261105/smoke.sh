#!/bin/bash
set -euo pipefail
: "${FILLER_SMOKE:?publisher smoke context required}"
[[ $FILLER_SMOKE == 1 ]] || exit 64
: "${FILLER_DRYRUN_RESULT_PATH:?publisher supplies isolated smoke result}"
: "${WS58_REGIONS:?publisher supplies four smoke CPUs}"
exec "$(dirname -- "${BASH_SOURCE[0]}")/launch.sh"
