#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-pbqcost-v2-20261101
exec /usr/bin/taskset -c "$FILLER_CPUS" /usr/bin/python3.13 -B "$D/run.py" full
