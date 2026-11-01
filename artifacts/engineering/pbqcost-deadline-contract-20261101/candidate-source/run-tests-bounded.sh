#!/bin/bash
set -euo pipefail
ROOT=/mnt/raid0/llm/tmp/codex-ni-pbqcost-v2-20261101
LOCK=/mnt/raid0/llm/tmp/compute-flags/prep-locks/36-37.lock
LOG=$ROOT/test-run.log
flock -n "$LOCK" bash -c '
  set -euo pipefail
  ROOT=/mnt/raid0/llm/tmp/codex-ni-pbqcost-v2-20261101
  printf "task=PBQ-v2-deadline-tests relocated_cpus=84-85 base_pair=36-37 time_utc=%s\n" "$(date -u +%FT%TZ)" > /mnt/raid0/llm/tmp/compute-flags/prep-locks/36-37.lock
  ulimit -v 8388608
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 timeout --signal=TERM --kill-after=5s 900s /usr/bin/taskset -c 84-85 /usr/bin/python3.13 -m pytest -q -p no:cacheprovider "$ROOT/tests" > "$ROOT/test-run.log" 2>&1 &
  child=$!
  start=$(date +%s)
  peak_kib=0
  while ps -p "$child" -o stat= | grep -q .; do
    now=$(date +%s)
    [ $((now-start)) -le 900 ] || { kill -TERM "$child" 2>/dev/null || true; }
    rss=$(awk "/^VmRSS:/ {print \$2}" "/proc/$child/status" 2>/dev/null || echo 0)
    [ -n "$rss" ] || rss=0
    [ "$rss" -le 8388608 ] || { kill -TERM "$child" 2>/dev/null || true; }
    [ "$rss" -le "$peak_kib" ] || peak_kib=$rss
    sleep 1
  done
  set +e
  wait "$child"; rc=$?
  set -e
  printf "rc=%s elapsed_s=%s sampled_peak_rss_kib=%s cpus=84-85 omp_threads=1\n" "$rc" "$(($(date +%s)-start))" "$peak_kib" > "$ROOT/TEST-RESOURCE-RECEIPT.txt"
  exit "$rc"
' || exit $?
