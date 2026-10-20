#!/bin/bash
T=/mnt/raid0/llm/tmp/qwentts_threadpool_20261020
CPUS=$1
DL=2026-10-21T00:25:00Z
export EXP_Q=/mnt/raid0/llm/worktrees/qwentts-threadpool-20261020/build2
echo "final3 claim $CPUS $(date -u +%FT%TZ) load $(cut -d' ' -f1-3 /proc/loadavg); $(/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock status 2>&1 | tr '\n' ';')" >> $T/final3/claim.log
python3 -I $T/timing.py --suite qts --cpus $CPUS --deadline $DL --out $T/final3 --timeout 900 --variants prod,exp_default --legs nb_1T --reps 3 >> $T/final3/qts.out 2>&1
echo "final3 done $(date -u +%FT%TZ)" >> $T/final3/claim.log
