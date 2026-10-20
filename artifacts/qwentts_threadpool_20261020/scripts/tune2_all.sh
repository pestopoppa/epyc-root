#!/bin/bash
T=/mnt/raid0/llm/tmp/qwentts_threadpool_20261020
CPUS=$1
echo "tune claim $CPUS $(date -u +%FT%TZ)" >> $T/tune2/claim.log
python3 -I $T/timing_tune.py --suite qts --cpus $CPUS --deadline 2026-10-21T00:25:00Z --out $T/tune2 --reps 3 --heavy-reps 3 \
  --variants "exp_futex@200,exp_futex@300,exp_futex@500,exp_futex@800,exp_yield@200,exp_yield@300,exp_yield@500,exp_yield@800" \
  --legs quiet_8T_free,quiet_8T_pinned,cont_8T_1spin,cont_8T_8spin > $T/tune2/qts.out 2>&1
echo "tune done $(date -u +%FT%TZ)" >> $T/tune2/claim.log
