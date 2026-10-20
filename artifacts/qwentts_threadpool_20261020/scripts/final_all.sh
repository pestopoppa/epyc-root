#!/bin/bash
# FINAL qwentts matrix on the committed candidate build (build2), inside an exclusive bench claim. arg1 = region cpus
T=/mnt/raid0/llm/tmp/qwentts_threadpool_20261020
CPUS=$1
DL=2026-10-21T00:25:00Z
export EXP_Q=/mnt/raid0/llm/worktrees/qwentts-threadpool-20261020/build2
echo "final claim $CPUS $(date -u +%FT%TZ) load $(cut -d' ' -f1-3 /proc/loadavg); $(/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock status 2>&1 | tr '\n' ';')" >> $T/final/claim.log
run() { python3 -I $T/timing.py --suite qts --cpus $CPUS --deadline $DL --out $T/final --timeout 900 "$@" >> $T/final/qts.out 2>&1; }
run --variants prod,exp_ctl,exp_pool,exp_default --legs quiet_1T,quiet_8T_free,quiet_8T_pinned --reps 5 --aa
run --variants prod,exp_pool,exp_default --legs cont_1T_1spin,cont_8T_1spin --reps 5
run --variants prod,exp_default --legs nb_1T,nb_8T --reps 3
run --variants exp_default,prod --legs cont_8T_8spin --heavy-reps 3
echo "final done $(date -u +%FT%TZ)" >> $T/final/claim.log
