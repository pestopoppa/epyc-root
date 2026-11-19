#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/cafe4-native-rewind-20261104
ulimit -c 0
exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env FILLER_DEADLINE="$FILLER_DEADLINE" FILLER_STOPFILE="$FILLER_STOPFILE" FILLER_DRYRUN="${FILLER_DRYRUN:-0}" FILLER_DRYRUN_RESULT_PATH="${FILLER_DRYRUN_RESULT_PATH:-}" PATH=/usr/bin:/bin OMP_NUM_THREADS=1 /usr/bin/python3 "$D/runtime.py" run
