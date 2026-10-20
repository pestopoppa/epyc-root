#!/bin/bash
T=/mnt/raid0/llm/tmp/qwentts_threadpool_20261020
RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
declare -A CP=( [q0]=0-23 [q1]=24-47 )
STOP=$(date -u -d 2026-10-21T00:15:00Z +%s)
while [ $(date -u +%s) -lt $STOP ]; do
  for q in q0 q1; do
    if $RL status 2>/dev/null | grep -E "^ *$q +free" >/dev/null; then
      echo "$(date -u +%T) trying $q" >> $T/final/watch.log
      $RL run --regions $q --role bench-cpu --timeout-s 5 --tag qwentts-threadpool-final -- $T/final_all.sh ${CP[$q]} >> $T/final/watch.log 2>&1
      rc=$?; echo "$(date -u +%T) $q rc=$rc" >> $T/final/watch.log
      [ $rc -ne 75 ] && exit 0
    fi
  done
  sleep 20
done
echo "no claim before 00:15Z" >> $T/final/watch.log
