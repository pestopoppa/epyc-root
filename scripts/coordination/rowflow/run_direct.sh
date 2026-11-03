#!/bin/bash
# run_direct.sh - ONE command to run a published row on the hardware now (2026-11-03 session review item 1).
#   run_direct.sh <ready.json | row-id> [--regions R] [--gpu-quiet none|shared|exclusive] [--timeout-s 600] [--no-wait]
#   run_direct.sh stop <row-id>      run_direct.sh status <row-id>
# Everything is in run_direct.py (deterministic, tested); this wrapper only pins the interpreter mode.
set -euo pipefail
exec python3 -I "$(dirname "$(readlink -f "$0")")/run_direct.py" "$@"
