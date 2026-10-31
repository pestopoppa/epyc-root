#!/usr/bin/env bash
# Tracked, versioned successor to the task-specific workspace-f8 CPU queue runner.
# This file is not installed into /mnt/raid0/llm/tmp/cpu-queue-f8 and does not
# change the historical runner or its evidence. Daily blackout is UTC
# [00:15, 06:30); absolute dated windows remain the separate window guard's job.
set -euo pipefail

CPU_QUEUE_F8_Q=${CPU_QUEUE_F8_Q:-/mnt/raid0/llm/tmp/cpu-queue-f8}
CPU_QUEUE_F8_RL=${CPU_QUEUE_F8_RL:-/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock}
CPU_QUEUE_F8_DAY_S=86400
CPU_QUEUE_F8_BLACKOUT_START_S=$((15 * 60))
CPU_QUEUE_F8_BLACKOUT_END_S=$((6 * 60 * 60 + 30 * 60))

cpu_queue_f8_valid_seconds() {
  [[ ${1:-} =~ ^[0-9]{1,18}$ ]]
}

# Return success when [start_s, start_s + duration_s) intersects any daily
# UTC blackout interval [00:15, 06:30). For duration 0, classify the instant
# itself, preserving the half-open endpoints.
cpu_queue_f8_interval_conflicts_blackout() {
  local start_s=${1:-} duration_s=${2:-}
  cpu_queue_f8_valid_seconds "$start_s" && cpu_queue_f8_valid_seconds "$duration_s" || return 2
  start_s=$((10#$start_s))
  duration_s=$((10#$duration_s))
  local max_int=$(((1 << 62) - 1 + (1 << 62)))
  (( duration_s <= max_int - start_s )) || return 2
  # Any interval at least one full UTC day long necessarily intersects the
  # recurring blackout. Shorter intervals can touch only today's or tomorrow's.
  (( duration_s < CPU_QUEUE_F8_DAY_S )) || return 0
  local end_s=$((start_s + duration_s))
  local day_s=$((start_s / CPU_QUEUE_F8_DAY_S * CPU_QUEUE_F8_DAY_S))
  local blackout_start blackout_end
  local offset
  for offset in 0 1; do
    blackout_start=$((day_s + offset * CPU_QUEUE_F8_DAY_S + CPU_QUEUE_F8_BLACKOUT_START_S))
    blackout_end=$((day_s + offset * CPU_QUEUE_F8_DAY_S + CPU_QUEUE_F8_BLACKOUT_END_S))
    if (( duration_s == 0 )); then
      (( start_s >= blackout_start && start_s < blackout_end )) && return 0
    elif (( start_s < blackout_end && end_s > blackout_start )); then
      return 0
    fi
  done
  return 1
}

# Public contract for current-time checks and queue admission. The normal
# admission loop below calls this same interval predicate with each job's
# declared maximum duration; no separate tomorrow-only check is used.
cpu_queue_f8_is_blackout() {
  cpu_queue_f8_interval_conflicts_blackout "${1:-}" 0
}

cpu_queue_f8_admission_allowed() {
  local start_s=${1:-} duration_s=${2:-}
  local rc
  if cpu_queue_f8_interval_conflicts_blackout "$start_s" "$duration_s"; then
    return 1
  else
    rc=$?
  fi
  [[ $rc == 1 ]] && return 0
  return 2
}

# This is invoked inside the region-lock command (or after the paired claim),
# immediately before the user's job process starts. The dequeue-time check is
# only an early filter; a lock wait can consume the remaining safe interval.
cpu_queue_f8_exec_if_admitted() {
  local job=${1:-} duration_s=${2:-} now rc
  [[ -n $job && -f $job ]] || { echo 'refuse: job path is missing' >&2; return 64; }
  now=$(date -u +%s)
  if cpu_queue_f8_admission_allowed "$now" "$duration_s"; then
    exec bash "$job"
  else
    rc=$?
  fi
  if [[ $rc == 1 ]]; then
    echo "defer: $job would overlap the daily UTC blackout after lock wait" >&2
    return 76
  fi
  echo 'refuse: invalid job duration or clock' >&2
  return 64
}

cpu_queue_f8_log() {
  local worker=$1; shift
  echo "$(date -u +%FT%TZ) [w$worker] $*" >> "$CPU_QUEUE_F8_Q/log/runner.log"
}

cpu_queue_f8_test_cli() {
  case ${1:-} in
    --blackout)
      [[ $# == 2 ]] || { echo 'usage: --blackout EPOCH_SECONDS' >&2; return 64; }
      if cpu_queue_f8_is_blackout "$2"; then echo blackout; else rc=$?; case $rc in 1) echo open;; 2) echo 'invalid epoch or duration' >&2; return 2;; *) return "$rc";; esac; fi
      ;;
    --admission)
      [[ $# == 3 ]] || { echo 'usage: --admission START_EPOCH_SECONDS DURATION_SECONDS' >&2; return 64; }
      if cpu_queue_f8_admission_allowed "$2" "$3"; then echo admit; else rc=$?; case $rc in 1) echo defer;; 2) echo 'invalid epoch or duration' >&2; return 2;; *) return "$rc";; esac; fi
      ;;
    *) echo 'test-only mode: use --blackout EPOCH_SECONDS or --admission START_EPOCH_SECONDS DURATION_SECONDS' >&2; return 64 ;;
  esac
}

# Sourcing exposes only the predicates; it never initializes the queue or
# starts a worker. The explicit test CLI also exits before queue setup.
if [[ ${BASH_SOURCE[0]} != "$0" ]]; then
  return 0
fi
if [[ ${CPU_QUEUE_F8_TEST_ONLY:-0} == 1 ]]; then
  cpu_queue_f8_test_cli "$@"
  exit $?
fi

cpu_queue_f8_main() {
  local worker=${1:?worker id}
  local stop_at maxjob_s now
  if [[ ! ${STOP_AT:-} =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]]; then
    echo 'refuse: normal queue mode requires explicit UTC STOP_AT=YYYY-MM-DDTHH:MM:SSZ' >&2
    return 64
  fi
  stop_at=$(date -u -d "$STOP_AT" +%s) || { echo 'refuse: STOP_AT is not a valid UTC instant' >&2; return 64; }
  now=$(date -u +%s)
  if (( stop_at <= now )); then
    echo 'refuse: STOP_AT must be in the future' >&2
    return 64
  fi
  maxjob_s=${MAXJOB_S:-7200}
  mkdir -p "$CPU_QUEUE_F8_Q/pairlock"
  cpu_queue_f8_log "$worker" start

  while (( $(date -u +%s) < stop_at )); do
    local now
    now=$(date -u +%s)
    if cpu_queue_f8_is_blackout "$now"; then sleep 60; continue; fi
    local job="" f fmax
    for f in "$CPU_QUEUE_F8_Q"/pending/*.sh; do
      [[ -e $f ]] || break
      fmax=$(grep -m1 -oE '^#maxjob_s=[0-9]+' "$f" | cut -d= -f2 || true)
      fmax=${fmax:-$maxjob_s}
      now=$(date -u +%s)
      if ! cpu_queue_f8_admission_allowed "$now" "$fmax"; then
        continue
      fi
      if mv "$f" "$CPU_QUEUE_F8_Q/running/" 2>/dev/null; then
        job="$CPU_QUEUE_F8_Q/running/$(basename "$f")"
        break
      fi
    done
    if [[ -z $job ]]; then sleep 60; continue; fi

    local q=""
    while [[ -z $q ]]; do
      now=$(date -u +%s)
      if cpu_queue_f8_is_blackout "$now"; then
        mv "$job" "$CPU_QUEUE_F8_Q/pending/"
        job=""
        break
      fi
      q=$("$CPU_QUEUE_F8_RL" status 2>/dev/null | awk '$2=="free" && $1 ~ /^q[0-3]$/ {print $1; exit}')
      if [[ -z $q && -f $CPU_QUEUE_F8_Q/PAIR_OK ]]; then
        local pq
        for pq in $("$CPU_QUEUE_F8_RL" status 2>/dev/null | awk '$2=="HELD" && $3 ~ /^build\[/ && $1 ~ /^q[0-2]$/ {print $1}'); do
          if mkdir "$CPU_QUEUE_F8_Q/pairlock/$pq" 2>/dev/null; then q="pair:$pq"; break; fi
        done
        [[ -n $q ]] && break
      fi
      [[ -n $q ]] || sleep 60
    done
    [[ -n $job ]] || continue

    local name jmax rc=0 cpus holder jpid
    name=$(basename "$job" .sh)
    jmax=$(grep -m1 -oE '^#maxjob_s=[0-9]+' "$job" | cut -d= -f2 || true)
    jmax=${jmax:-$maxjob_s}
    cpu_queue_f8_log "$worker" "run $name on $q (max ${jmax}s)"
    if [[ $q == pair:* ]]; then
      pq=${q#pair:}
      case "$pq" in q0) cpus=0-23,96-119;; q1) cpus=24-47,120-143;; q2) cpus=48-71,144-167;; esac
      holder=$("$CPU_QUEUE_F8_RL" status 2>/dev/null | awk -v q="$pq" '$1==q {print $3, $4}')
      echo "ran on $pq ($cpus) under '$holder' claim by agreement (pairing, nice 10)" > "$CPU_QUEUE_F8_Q/log/$name.log"
      timeout --signal=TERM --kill-after=120 "$jmax" nice -n 10 taskset -c "$cpus" env F8Q_CPUS="$cpus" bash -c 'source "$1"; cpu_queue_f8_exec_if_admitted "$2" "$3"' _ "$CPU_QUEUE_F8_SELF" "$job" "$jmax" >> "$CPU_QUEUE_F8_Q/log/$name.log" 2>&1 &
      jpid=$!
      setsid nohup "$CPU_QUEUE_F8_Q/pairguard.sh" "$pq" "$jpid" >> "$CPU_QUEUE_F8_Q/log/pairguard-$pq.out" 2>&1 < /dev/null &
      wait "$jpid" || rc=$?
    else
      case "$q" in q0) cpus=0-23,96-119;; q1) cpus=24-47,120-143;; q2) cpus=48-71,144-167;; q3) cpus=72-95,168-191;; esac
      timeout --signal=TERM --kill-after=120 "$jmax" "$CPU_QUEUE_F8_RL" run --regions "$q" --role build --tag "f8q-$name" --timeout-s 120 -- env F8Q_CPUS="$cpus" taskset -c "$cpus" bash -c 'source "$1"; cpu_queue_f8_exec_if_admitted "$2" "$3"' _ "$CPU_QUEUE_F8_SELF" "$job" "$jmax" > "$CPU_QUEUE_F8_Q/log/$name.log" 2>&1 || rc=$?
    fi
    [[ $q == pair:* ]] && rmdir "$CPU_QUEUE_F8_Q/pairlock/${q#pair:}" 2>/dev/null || true
    cpu_queue_f8_log "$worker" "end $name rc=$rc"
    if [[ $rc == 75 || $rc == 76 ]] || grep -q 'could not acquire\|timed out acquiring' "$CPU_QUEUE_F8_Q/log/$name.log"; then
      mv "$job" "$CPU_QUEUE_F8_Q/pending/"
      cpu_queue_f8_log "$worker" "requeued $name (claim lost)"
    else
      mv "$job" "$CPU_QUEUE_F8_Q/done/"
      echo "$rc" > "$CPU_QUEUE_F8_Q/done/$name.rc"
    fi
  done
  cpu_queue_f8_log "$worker" stop
}

CPU_QUEUE_F8_SELF=$(readlink -f "${BASH_SOURCE[0]}")
cpu_queue_f8_main "$@"
