#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf174d-build-pinned/v3
: "${FILLER_DEADLINE:?}" "${FILLER_STOPFILE:?}" "${FILLER_THREADS:?}" "${FILLER_DRYRUN:=0}"
exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env FILLER_DEADLINE="$FILLER_DEADLINE" FILLER_STOPFILE="$FILLER_STOPFILE" FILLER_THREADS="$FILLER_THREADS" FILLER_DRYRUN="$FILLER_DRYRUN" FILLER_DRYRUN_RESULT_PATH="${FILLER_DRYRUN_RESULT_PATH:-}" PATH=/opt/rocm/bin:/usr/bin:/bin CCACHE_DISABLE=1 OMP_NUM_THREADS=1 /bin/bash "$D/host-job.sh"
