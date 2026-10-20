#!/bin/bash
# re-run of the q0 reps that overlapped the coordinator's co-run windows (contamination notice 22:3xZ). arg1 = region cpus
T=/mnt/raid0/llm/tmp/qwentts_threadpool_20261020
CPUS=$1
DL=2026-10-21T00:25:00Z
export EXP_Q=/mnt/raid0/llm/worktrees/qwentts-threadpool-20261020/build2
echo "final2 claim $CPUS $(date -u +%FT%TZ) load $(cut -d' ' -f1-3 /proc/loadavg); $(/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock status 2>&1 | tr '\n' ';')" >> $T/final2/claim.log
run() { python3 -I $T/timing.py --suite qts --cpus $CPUS --deadline $DL --out $T/final2 --timeout 900 "$@" >> $T/final2/qts.out 2>&1; }
run --variants prod,exp_pool,exp_default --legs cont_8T_1spin --reps 5
run --variants exp_default --legs cont_1T_1spin --reps 5
run --variants prod,exp_default --legs nb_1T --reps 3
run --variants prod --legs nb_8T --reps 1
echo "final2 done $(date -u +%FT%TZ)" >> $T/final2/claim.log
