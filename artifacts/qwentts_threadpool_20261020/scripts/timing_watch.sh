#!/bin/bash
# zero-token watcher: waits for correctness to finish, then tries to take a free q0/q1/q2 region (never q3) for the timing run.
T=/mnt/raid0/llm/tmp/qwentts_threadpool_20261020
RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
declare -A CP=( [q0]=0-23 [q1]=24-47 [q2]=48-71 )
STOP=$(date -u -d 2026-10-21T00:15:00Z +%s)
while [ ! -f $T/corr_done.flag ]; do [ $(date -u +%s) -ge $STOP ] && { echo "no start: past 00:15Z before correctness finished" >> $T/timing/watch.log; exit 0; }; sleep 20; done
while [ $(date -u +%s) -lt $STOP ]; do
  for q in q2; do
    if $RL status 2>/dev/null | grep -E "^ *$q +free" >/dev/null; then
      echo "$(date -u +%T) trying $q" >> $T/timing/watch.log
      $RL run --regions $q --role bench-cpu --timeout-s 5 --tag qwentts-threadpool-timing -- $T/timing_all.sh ${CP[$q]} >> $T/timing/watch.log 2>&1
      rc=$?
      echo "$(date -u +%T) $q rc=$rc" >> $T/timing/watch.log
      [ $rc -ne 75 ] && exit 0
    fi
  done
  sleep 20
done
echo "no claim obtained before 00:15Z" >> $T/timing/watch.log
