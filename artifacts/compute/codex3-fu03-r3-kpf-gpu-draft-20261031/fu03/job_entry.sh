#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-backlog-20261031-0255/r3
/usr/bin/python3 -B "$D/job.py" "$1" "$2"
exec /usr/bin/python3 -B "$D/check_complete.py" "$2"
