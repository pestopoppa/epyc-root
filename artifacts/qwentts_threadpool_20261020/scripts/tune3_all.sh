#!/bin/bash
T=/mnt/raid0/llm/tmp/qwentts_threadpool_20261020
CPUS=$1
echo "tune3 claim $CPUS $(date -u +%FT%TZ)" >> $T/tune3/claim.log
EXP_Q=/mnt/raid0/llm/worktrees/qwentts-threadpool-20261020/build2 python3 -I $T/timing_tune.py --suite qts --cpus $CPUS --deadline 2026-10-21T00:25:00Z --out $T/tune3 --reps 3 --heavy-reps 3 \
  --variants "exp_futex,exp_futex@4000,exp_futex@2000@100,exp_futex@2000@400,exp_futexfix@2000" \
  --legs quiet_1T,quiet_8T_free,quiet_8T_pinned,cont_8T_1spin,cont_8T_8spin > $T/tune3/qts.out 2>&1
echo "tune3 done $(date -u +%FT%TZ)" >> $T/tune3/claim.log
