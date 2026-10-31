#!/bin/bash
# Optional metadata only. Caller retains every command, exit code, lock and grant.
# No state file, deletion, replacement, daemon or conversation reads.
lm_emit() {
  [ "${LM_ENABLED:-0}" = 1 ] || return 0
  local body=$1
  if ! python3 -B -I "$LM_HELPER" --ledger "$LOOP_METRICS_LEDGER" --event "$body" >&2; then
    LM_BROKEN=1
    printf '%s\n' 'loop metrics: metadata unavailable; coverage remains unknown' >&2
  fi
  LM_ORD=$((LM_ORD + 1))
  return 0
}
lm_common() {
  printf '"producer":"launcher-entry","session":"%s","ordinal":%s' "$LM_SESSION" "$LM_ORD"
}
lm_start() {
  LM_ENABLED=0
  [ -n "${LOOP_METRICS_LEDGER:-}" ] || return 0
  LM_HELPER=${LOOP_METRICS_HELPER:-$(dirname "$SELF")/../handoffs/loop_metrics_events.py}
  LM_ENABLED=1; LM_BROKEN=0; LM_ORD=0; LM_PHASE=${1:-launcher-admission}; LM_BASE_PHASE=$LM_PHASE
  LM_SESSION="p$$-$(date -u +%s%N)"; LM_ATTEMPT=""; LM_RESULT=""
  lm_emit "{\"kind\":\"coverage_open\",$(lm_common),\"resources\":[]}"
}
lm_attempt_begin() {
  [ "${LM_ENABLED:-0}" = 1 ] || return 0
  LM_ATTEMPT="a$LM_ORD"; LM_RESULT=""; LM_PHASE=${LM_BASE_PHASE:-launcher-admission}
  lm_emit "{\"kind\":\"attempt_begin\",$(lm_common),\"attempt\":\"$LM_ATTEMPT\",\"phase\":\"$LM_PHASE\"}"
}
lm_job_dispatched() {
  [ "${LM_ENABLED:-0}" = 1 ] || return 0
  lm_emit "{\"kind\":\"attempt_end\",$(lm_common),\"attempt\":\"$LM_ATTEMPT\",\"phase\":\"$LM_PHASE\",\"rc\":0}"
  LM_PHASE=job-outcome
  lm_emit "{\"kind\":\"attempt_begin\",$(lm_common),\"attempt\":\"$LM_ATTEMPT\",\"phase\":\"$LM_PHASE\"}"
}
lm_attempt_end() {
  [ "${LM_ENABLED:-0}" = 1 ] || return 0
  local outcome
  if [ "$1" = 9 ]; then
    lm_emit "{\"kind\":\"attempt_deferred\",$(lm_common),\"attempt\":\"$LM_ATTEMPT\",\"phase\":\"$LM_PHASE\"}"
  else
    # Entry is launcher admission/dispatch, never an assertion of native model success.
    outcome=${LM_RESULT:-255}
    lm_emit "{\"kind\":\"attempt_end\",$(lm_common),\"attempt\":\"$LM_ATTEMPT\",\"phase\":\"$LM_PHASE\",\"rc\":$outcome}"
  fi
  LM_ATTEMPT=""
  return 0
}
lm_close() {
  local original_rc=$?
  if [ "${LM_ENABLED:-0}" = 1 ] && [ "$LM_BROKEN" = 0 ] && [ -z "$LM_ATTEMPT" ]; then
    lm_emit "{\"kind\":\"coverage_close\",$(lm_common),\"expected_events\":$((LM_ORD - 1))}"
  fi
  return "$original_rc"
}

lm_admission_result() {
  [ "${LM_ENABLED:-0}" = 1 ] || return 0
  lm_emit "{\"kind\":\"attempt_end\",$(lm_common),\"attempt\":\"$LM_ATTEMPT\",\"phase\":\"$LM_PHASE\",\"rc\":$1}"
  LM_ATTEMPT=""
  return 0
}

lm_kernel_sample() {
  # LOOP-5 optional kernel-accounted CPU idle counters (iowait excluded).
  # Every invocation is read-only except its own append-only metadata ledger.
  if [ -n "${LOOP_METRICS_LEDGER:-}" ] && [ -r "${LOOP_METRICS_HELPER:-}" ]; then
    if [ -z "${LM_COUNTER_SESSION:-}" ]; then
      LM_COUNTER_SESSION="p$$-$(date -u +%s%N)"; LM_COUNTER_ORD=0
    fi
    python3 -B -I "$LOOP_METRICS_HELPER" --ledger "$LOOP_METRICS_LEDGER" \
      --capture-cpus 0-95 --session "$LM_COUNTER_SESSION" --ordinal "$LM_COUNTER_ORD" || \
      log "LOOP-METRICS counter append refused; covered interval remains unavailable"
    LM_COUNTER_ORD=$((LM_COUNTER_ORD + 1))
  fi
}
