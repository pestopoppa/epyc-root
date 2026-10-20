#!/bin/bash
T=/mnt/raid0/llm/tmp/qwentts_threadpool_20261020
CPUS=$1
echo "tune claim $CPUS $(date -u +%FT%TZ)" >> $T/tune/claim.log
python3 -I $T/timing_tune.py --suite qts --cpus $CPUS --deadline 2026-10-21T00:25:00Z --out $T/tune --reps 3 \
  --variants "exp_futex@100,exp_futex@500,exp_futex@2000,exp_futex@10000,exp_futex@50000,exp_yield@100,exp_yield@500,exp_yield@10000,exp_pool" \
  --legs cont_8T_1spin,quiet_8T_free > $T/tune/qts.out 2>&1
echo "tune done $(date -u +%FT%TZ)" >> $T/tune/claim.log
