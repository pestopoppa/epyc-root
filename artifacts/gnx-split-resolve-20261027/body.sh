#!/bin/bash
set -euo pipefail
packet=/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase/stage2-packet-r2
unset SPLIT_RUNNING
bash "$packet/guard.sh"
exec /usr/bin/python3 -I -B "$packet/supervisor.py"
