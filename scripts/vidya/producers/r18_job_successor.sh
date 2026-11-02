#!/bin/bash
set -euo pipefail
# An independently admitted successor must provide its own filler identity and fresh scratch.
: "${FILLER_ID:?}" "${FILLER_CPUS:?}" "${FILLER_DEADLINE:?}" "${R18_SCRATCH:?}"
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec /usr/bin/python3 -B "$HERE/r18_run_full_successor.py" --source /dev/shm/historical-ffc1-source-20261030 --scratch "$R18_SCRATCH" --mode full
