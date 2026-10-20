#!/bin/bash
# runs INSIDE an exclusive bench claim on one region; arg1 = region phys cpus (e.g. 24-47)
set -uo pipefail
T=/mnt/raid0/llm/tmp/qwentts_threadpool_20261020
CPUS=$1
DL=2026-10-21T00:25:00Z
echo "gpu-quiet at start: $(/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock status 2>&1 | tr "\n" ";")" >> $T/timing/claim.log; echo "claim region $CPUS started $(date -u +%FT%TZ) loadavg $(cut -d' ' -f1-3 /proc/loadavg)" >> $T/timing/claim.log
python3 -I $T/timing.py --suite qts --cpus $CPUS --deadline $DL --out $T/timing --aa --reps 5 --heavy-reps 3 --timeout 900 > $T/timing/qts.out 2>&1
python3 -I $T/timing.py --suite whisper --cpus $CPUS --deadline $DL --out $T/timing --variants prod,exp_pool,exp_yield,exp_futex \
  --legs quiet_8T_free,cont_8T_1spin,nb_8T,cont_8T_8spin --reps 3 --heavy-reps 2 --timeout 900 > $T/timing/whisper.out 2>&1
echo "claim finished $(date -u +%FT%TZ)" >> $T/timing/claim.log
