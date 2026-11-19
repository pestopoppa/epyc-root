#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
[ "${FILLER_DRYRUN:-0}" = 1 ] || [ "${FILLER_SMOKE:-0}" = 1 ]
: "${FILLER_DRYRUN_RESULT_PATH:?Separate synthetic smoke output required}"
exec python3 -I -B smoke.py
