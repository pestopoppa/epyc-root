#!/bin/bash
# inference_guard.sh — Pre-run check for nightshift
#
# Checks whether heavy inference is running, so nightshift can restrict itself to
# analysis-only tasks (no test execution — which would fail the 100GB-free-RAM
# conftest guard anyway) instead of launching an agent workload on top of a live
# 200GB inference run.
#
# ---------------------------------------------------------------------------
# AUD-7 (2026-08-12): THIS GUARD USED TO FAIL OPEN.
#
# The old measurement was one pipeline:
#     pgrep -f 'llama-server|llama.cpp' | xargs -I{} awk '/^VmRSS:/{print $2}' \
#         /proc/{}/status 2>/dev/null || true
# summed into a total. EVERY failure mode of that pipeline sums to 0 and prints
# "No heavy inference detected":
#   * pgrep not installed          -> command not found, `|| true` swallows it
#   * the binary was renamed       -> zero matches, indistinguishable from idle
#   * argv drift (a wrapper, a
#     different launcher path)     -> zero matches
#   * xargs/awk error, /proc read
#     denied, pids exiting mid-read-> 2>/dev/null, then 0
# A guard whose BROKEN reading and whose ALL-CLEAR reading are the same value is
# not a guard. The wrapper then launched the full workload on top of live inference.
#
# The fix is three-valued — `measured <N>GB` / an honest 0 / `MEASUREMENT FAILED` —
# published in NIGHTSHIFT_GUARD_STATE, and run_wrapper.sh REFUSES to launch on
# `failed` rather than proceeding.
#
# SECOND CHANNEL. The asset being protected is RAM HEADROOM, not the existence of a
# process called llama-server. MemAvailable from /proc/meminfo measures the asset
# directly and cannot be defeated by a renamed binary, an argv change or a pgrep
# that is not installed — so a run that would trample a 200GB resident model is
# caught even when the process channel sees nothing at all.
#
# NOTE ON pgrep: this is READ-ONLY process inspection. Nothing here signals a
# process. The host-wide ban is on `pkill`/`pgrep` NAME PATTERNS FEEDING A KILL
# (INC-20260731-broad-process-pattern-kills); a pattern that only ever contributes
# to a sum has no blast radius.
#
# Usage:
#   source scripts/nightshift/inference_guard.sh
#
# Exports:
#   NIGHTSHIFT_GUARD_STATE        measured | failed
#   NIGHTSHIFT_GUARD_REASON       why, when state=failed (empty otherwise)
#   NIGHTSHIFT_INFERENCE_ACTIVE   1 | 0   (meaningless unless state=measured)
#   NIGHTSHIFT_INFERENCE_RSS_GB   integer GB, or "unknown" when the channel failed
#   NIGHTSHIFT_MEMAVAIL_GB        integer GB, or "unknown"
#   NIGHTSHIFT_TASK_FILTER        set only when inference is active
#
# Called by: scripts/nightshift/run_wrapper.sh

set -euo pipefail

# Threshold: llama-server RSS at or above this (GB) means inference is active.
INFERENCE_RAM_THRESHOLD_GB="${NIGHTSHIFT_INFERENCE_THRESHOLD_GB:-200}"
# Second, argv-independent channel: less free RAM than this (GB) means the machine
# is already committed, whatever the process table says. 100GB matches the
# conftest free-RAM guard the test tasks would hit anyway.
MIN_MEMAVAIL_GB="${NIGHTSHIFT_MIN_MEMAVAIL_GB:-100}"

# Analysis-only tasks (safe to run during inference — no test execution)
ANALYSIS_ONLY_TASKS="dead-code,test-gap,security-footgun,perf-regression,doc-drift,docs-backfill,skill-groom"

INFERENCE_PATTERN="${NIGHTSHIFT_INFERENCE_PATTERN:-llama-server|llama.cpp|sd-server|whisper-cli|qwentts}"

# Echoes: "<state> <gb> <detail>"  where state is measured|failed.
# `measured 0 no-matching-processes` is an HONEST zero and is distinct from
# `failed <anything>`; that distinction is the entire point of this function.
measure_inference_rss_gb() {
  local pids rc=0 total_kb=0 reads_ok=0 pid_count=0 rss

  if ! command -v pgrep >/dev/null 2>&1; then
    echo "failed 0 pgrep-not-installed"
    return 0
  fi

  # rc 0 = matches, rc 1 = no matches (the honest zero), rc >= 2 = pgrep ERROR.
  # Captured explicitly because `set -e` would otherwise abort on rc 1, and a
  # blanket `|| true` is exactly how rc 2 used to be laundered into rc 0.
  pids="$(pgrep -f "$INFERENCE_PATTERN" 2>/dev/null)" || rc=$?
  if (( rc >= 2 )); then
    echo "failed 0 pgrep-rc-$rc"
    return 0
  fi
  if (( rc == 1 )) || [[ -z "${pids//[[:space:]]/}" ]]; then
    echo "measured 0 no-matching-processes"
    return 0
  fi

  local pid
  for pid in $pids; do
    pid_count=$(( pid_count + 1 ))
    # A pid that exits between pgrep and this read is normal, not a failure — it is
    # only a failure if EVERY read fails, which is what a permissions or /proc
    # problem looks like.
    rss="$(awk '/^VmRSS:/{print $2; exit}' "/proc/$pid/status" 2>/dev/null || true)"
    if [[ "$rss" =~ ^[0-9]+$ ]]; then
      total_kb=$(( total_kb + rss ))
      reads_ok=$(( reads_ok + 1 ))
    fi
  done

  if (( reads_ok == 0 )); then
    echo "failed 0 ${pid_count}-pids-found-but-zero-VmRSS-reads-succeeded"
    return 0
  fi
  echo "measured $(( total_kb / 1024 / 1024 )) ${reads_ok}/${pid_count}-pids-read"
}

# Echoes: "<state> <gb>" — the argv-independent channel.
measure_memavailable_gb() {
  local kb
  kb="$(awk '/^MemAvailable:/{print $2; exit}' /proc/meminfo 2>/dev/null || true)"
  if [[ "$kb" =~ ^[0-9]+$ ]]; then
    echo "measured $(( kb / 1024 / 1024 ))"
  else
    echo "failed 0"
  fi
}

check_inference_load() {
  local rss_state rss_gb rss_detail mem_state mem_gb active=0

  read -r rss_state rss_gb rss_detail <<<"$(measure_inference_rss_gb)"
  read -r mem_state mem_gb <<<"$(measure_memavailable_gb)"

  export NIGHTSHIFT_MEMAVAIL_GB="$mem_gb"
  [[ "$mem_state" == "measured" ]] || export NIGHTSHIFT_MEMAVAIL_GB="unknown"

  if [[ "$rss_state" != "measured" ]]; then
    export NIGHTSHIFT_GUARD_STATE="failed"
    export NIGHTSHIFT_GUARD_REASON="$rss_detail"
    export NIGHTSHIFT_INFERENCE_RSS_GB="unknown"
    # Deliberately NOT 0. NIGHTSHIFT_INFERENCE_ACTIVE is only meaningful when the
    # state is `measured`; leaving it unset here means a consumer that forgets to
    # read the state gets an empty value rather than a confident "no inference".
    unset NIGHTSHIFT_INFERENCE_ACTIVE 2>/dev/null || true
    unset NIGHTSHIFT_TASK_FILTER 2>/dev/null || true
    echo "[inference_guard] MEASUREMENT FAILED: $rss_detail"
    echo "[inference_guard] The process channel could not be read, so 'no inference' is NOT"
    echo "[inference_guard] an available conclusion. MemAvailable second channel: ${NIGHTSHIFT_MEMAVAIL_GB}GB."
    echo "[inference_guard] Callers MUST refuse to launch (NIGHTSHIFT_GUARD_STATE=failed)."
    return 1
  fi

  export NIGHTSHIFT_GUARD_STATE="measured"
  export NIGHTSHIFT_GUARD_REASON=""
  export NIGHTSHIFT_INFERENCE_RSS_GB="$rss_gb"

  if (( rss_gb >= INFERENCE_RAM_THRESHOLD_GB )); then
    active=1
    echo "[inference_guard] Inference active: measured ${rss_gb}GB RSS ($rss_detail)"
  fi
  if [[ "$mem_state" == "measured" ]] && (( mem_gb < MIN_MEMAVAIL_GB )); then
    active=1
    echo "[inference_guard] Inference active by the MemAvailable channel: ${mem_gb}GB free"
    echo "[inference_guard]   (< ${MIN_MEMAVAIL_GB}GB). This channel is argv-independent: it"
    echo "[inference_guard]   catches a renamed or relocated inference binary the pattern misses."
  fi
  if [[ "$mem_state" != "measured" ]]; then
    echo "[inference_guard] WARNING: /proc/meminfo MemAvailable unreadable — the second,"
    echo "[inference_guard]   argv-independent channel is DOWN; only the process channel voted."
  fi

  if (( active == 1 )); then
    export NIGHTSHIFT_INFERENCE_ACTIVE=1
    export NIGHTSHIFT_TASK_FILTER="$ANALYSIS_ONLY_TASKS"
    echo "[inference_guard] Restricting to analysis-only tasks: $ANALYSIS_ONLY_TASKS"
  else
    export NIGHTSHIFT_INFERENCE_ACTIVE=0
    unset NIGHTSHIFT_TASK_FILTER 2>/dev/null || true
    echo "[inference_guard] measured ${rss_gb}GB RSS ($rss_detail) < ${INFERENCE_RAM_THRESHOLD_GB}GB threshold;"
    echo "[inference_guard] MemAvailable ${NIGHTSHIFT_MEMAVAIL_GB}GB >= ${MIN_MEMAVAIL_GB}GB. All tasks eligible."
  fi
  return 0
}

# Run if sourced or executed directly. `|| true` keeps a `source` under `set -e`
# from aborting the caller before it can read NIGHTSHIFT_GUARD_STATE and print its
# own refusal — the state is the verdict, not this return code.
check_inference_load || true
