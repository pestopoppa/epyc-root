#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/cafe4-geometry-frozen-build
: "${FILLER_DEADLINE:?}" "${FILLER_STOPFILE:?}" "${FILLER_THREADS:?}"
exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env FILLER_DEADLINE="$FILLER_DEADLINE" FILLER_STOPFILE="$FILLER_STOPFILE" FILLER_THREADS="$FILLER_THREADS" FILLER_DRYRUN="${FILLER_DRYRUN:-0}" FILLER_DRYRUN_RESULT_PATH="${FILLER_DRYRUN_RESULT_PATH:-}" PATH=/usr/bin:/bin CCACHE_DISABLE=1 OMP_NUM_THREADS=1 /bin/bash "$D/build.sh"
