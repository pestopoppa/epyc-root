#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
source_review_sha256_expected='9cc34dd703beda374fa7eaf79a3779ae7d9ca8090aa777e85cdef90b1c97e9e4'
source_review_sha256_actual=$(sha256sum "$D/SOURCE-REVIEW.sha256" | awk '{print $1}')
if [ "$source_review_sha256_actual" != "$source_review_sha256_expected" ]; then
  printf '%s\n' 'REFUSED: SOURCE-REVIEW.sha256 digest mismatch' >&2
  exit 65
fi
( cd "$D" && sha256sum -c SOURCE-REVIEW.sha256 )
if [ "${1:-}" = --standing-smoke ]; then
 export UFH14_A3A_SMOKE=1 FILLER_ID=ufh14-a3a-smoke FILLER_CPUS=184-185 FILLER_PIDFILE="$D/smoke-pids" FILLER_STOPFILE="$D/STOP-smoke"
 export FILLER_END=$(( $(date +%s) + 300 ))
 if [ "${UFH14_FORCE_CUTOFF:-0}" = 1 ]; then export FILLER_DEADLINE=$(( $(date +%s) + 65 )); else export FILLER_DEADLINE=$(( FILLER_END - 90 )); fi
 exec timeout --signal=TERM --kill-after=5s 290s taskset -c 184,185 bash "$D/job.sh" --standing-smoke
fi
if [ "${FILLER_PREFLIGHT:-0}" != 1 ]; then export FILLER_STATE_DIR="$D/state"; else : "${FILLER_STATE_DIR:?}"; fi
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id ufh14-a3a-single-warm-r2-20261028 --class gpu --role build --gpu-quiet exclusive --claim-cpus 184-191 --gpu-threads 184-191 --min-window 7200 --port 18445 --stop "$D/STOP" --workdir "$D" --cmd "bash $D/job.sh" --complete-cmd "if [ \"\${FILLER_DRYRUN:-0}\" = 1 ]; then test -e \"\${FILLER_DRYRUN_DIR:?}/complete\"; else python3 -B "$D/completion_unit.py" --check-production "$D" ufh14-a3a-single-warm-r2-20261028; fi"
