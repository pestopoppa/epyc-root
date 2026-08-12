#!/bin/bash
# run_wrapper.sh — Nightshift runner with inference guard
#
# This script is called by the systemd timer/service instead of
# `nightshift run` directly. It checks inference load and adjusts
# which tasks nightshift can run.
#
# Usage:
#   scripts/nightshift/run_wrapper.sh [extra nightshift args...]
#
# Environment:
#   NIGHTSHIFT_MAX_PROJECTS  — max projects per run (default: 3)
#   NIGHTSHIFT_MAX_TASKS     — max tasks per project (default: 2)
#   NIGHTSHIFT_INFERENCE_THRESHOLD_GB — RAM threshold for inference detection (default: 200)
#   NIGHTSHIFT_ATTESTATION_MAX_AGE_S — refresh running-state attestation after this age (default: 14400)
#   NIGHTSHIFT_LAB_SHADOW_ENABLED — run self-running-lab shadow jobs when quiet (default: 1)
#   NIGHTSHIFT_LAB_SHADOW_MAX_JOBS — max lab shadow jobs per quiet run (default: 2)
#   NIGHTSHIFT_LAB_ACTIVE_SAFE_ENABLED — run read-only deterministic lab jobs even when inference is active (default: 1)
#   NIGHTSHIFT_LAB_ACTIVE_SAFE_MAX_JOBS — max active-safe lab jobs per run (default: 4)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORKTREE="/mnt/raid0/llm/epyc-root-nightshift"
LOG_DIR="$PROJECT_ROOT/logs/nightshift"
DISABLE_FLAG="$PROJECT_ROOT/.nightshift_disabled"

mkdir -p "$LOG_DIR"

LOGFILE="$LOG_DIR/$(date +%Y-%m-%d_%H%M%S).log"

refresh_attestation_if_stale() {
  if [[ "${NIGHTSHIFT_ATTESTATION_REFRESH:-1}" == "0" ]]; then
    echo "[wrapper] Attestation refresh disabled (NIGHTSHIFT_ATTESTATION_REFRESH=0)"
    return 0
  fi

  local orch_root="${ORCHESTRATOR_ROOT:-/mnt/raid0/llm/epyc-orchestrator}"
  local script="$orch_root/scripts/attest/generate_attestation.py"
  local latest="$orch_root/orchestration/attestation/latest.json"
  local max_age="${NIGHTSHIFT_ATTESTATION_MAX_AGE_S:-14400}"

  if [[ ! -f "$script" ]]; then
    echo "[wrapper] Attestation refresh skipped: missing $script"
    return 0
  fi

  local now
  now="$(date +%s)"
  local mtime=0
  if [[ -f "$latest" ]]; then
    mtime="$(stat -c %Y "$latest" 2>/dev/null || echo 0)"
  fi
  local age=$((now - mtime))
  if (( age < max_age )); then
    echo "[wrapper] Attestation fresh (${age}s < ${max_age}s), skipping refresh"
    return 0
  fi

  echo "[wrapper] Refreshing running-state attestation (age=${age}s, max=${max_age}s)"
  local rc=0
  (
    cd "$orch_root"
    uv run python scripts/attest/generate_attestation.py \
      --trigger nightshift_4h \
      --flag-polls "${NIGHTSHIFT_ATTESTATION_FLAG_POLLS:-120}" \
      --flag-min-workers "${NIGHTSHIFT_ATTESTATION_MIN_WORKERS:-6}"
  ) || rc=$?
  if [[ "$rc" == "0" || "$rc" == "1" ]]; then
    echo "[wrapper] Attestation refresh wrote artifact (rc=$rc)"
    return 0
  fi
  echo "[wrapper] WARNING: attestation refresh failed (rc=$rc)"
  return 0
}

autopilot_running() {
  pgrep -f 'scripts/autopilot/autopilot.py start' >/dev/null 2>&1
}

run_lab_active_safe() {
  if [[ "${NIGHTSHIFT_LAB_ACTIVE_SAFE_ENABLED:-1}" == "0" ]]; then
    echo "[wrapper] Lab active-safe run disabled (NIGHTSHIFT_LAB_ACTIVE_SAFE_ENABLED=0)"
    return 0
  fi

  local orch_root="${ORCHESTRATOR_ROOT:-/mnt/raid0/llm/epyc-orchestrator}"
  local runner="$orch_root/scripts/lab/run_shadow_jobs.py"
  if [[ ! -f "$runner" ]]; then
    echo "[wrapper] Lab active-safe skipped: missing $runner"
    return 0
  fi

  echo "[wrapper] Running self-running-lab active-safe deterministic jobs"
  local rc=0
  (
    cd "$orch_root"
    uv run python scripts/lab/run_shadow_jobs.py \
      --schedule nightly \
      --active-safe-only \
      --max-jobs "${NIGHTSHIFT_LAB_ACTIVE_SAFE_MAX_JOBS:-4}" \
      --execute-command \
      --continue-on-error \
      --timeout-s "${NIGHTSHIFT_LAB_ACTIVE_SAFE_TIMEOUT_S:-120}"
  ) || rc=$?
  if [[ "$rc" == "0" ]]; then
    echo "[wrapper] Lab active-safe run complete"
    return 0
  fi
  echo "[wrapper] WARNING: lab active-safe run failed (rc=$rc); continuing nightshift"
  return 0
}

run_lab_shadow_if_quiet() {
  if [[ "${NIGHTSHIFT_LAB_SHADOW_ENABLED:-1}" == "0" ]]; then
    echo "[wrapper] Lab shadow run disabled (NIGHTSHIFT_LAB_SHADOW_ENABLED=0)"
    return 0
  fi

  if [[ "${NIGHTSHIFT_INFERENCE_ACTIVE:-0}" == "1" ]]; then
    echo "[wrapper] Lab shadow skipped: inference is active (${NIGHTSHIFT_INFERENCE_RSS_GB:-unknown}GB RSS)"
    return 0
  fi

  if autopilot_running; then
    echo "[wrapper] Lab shadow skipped: AutoPilot is active"
    return 0
  fi

  local orch_root="${ORCHESTRATOR_ROOT:-/mnt/raid0/llm/epyc-orchestrator}"
  local runner="$orch_root/scripts/lab/run_shadow_jobs.py"
  if [[ ! -f "$runner" ]]; then
    echo "[wrapper] Lab shadow skipped: missing $runner"
    return 0
  fi

  echo "[wrapper] Running self-running-lab nightly shadow jobs"
  local rc=0
  (
    cd "$orch_root"
    uv run python scripts/lab/run_shadow_jobs.py \
      --schedule nightly \
      --quiet-window-only \
      --max-jobs "${NIGHTSHIFT_LAB_SHADOW_MAX_JOBS:-2}" \
      --execute-chat \
      --continue-on-error \
      --timeout-s "${NIGHTSHIFT_LAB_SHADOW_TIMEOUT_S:-300}"
  ) || rc=$?
  if [[ "$rc" == "0" ]]; then
    echo "[wrapper] Lab shadow run complete"
    return 0
  fi
  echo "[wrapper] WARNING: lab shadow run failed (rc=$rc); continuing nightshift"
  return 0
}

{
  echo "=== Nightshift Run: $(date -Iseconds) ==="
  echo "Project root: $PROJECT_ROOT"
  echo "Worktree: $WORKTREE"

  # Global kill switch: allow disabling nightshift without touching systemd.
  # Either set NIGHTSHIFT_DISABLED=1 or create .nightshift_disabled file.
  if [[ "${NIGHTSHIFT_DISABLED:-0}" == "1" || -f "$DISABLE_FLAG" ]]; then
    echo "[wrapper] NIGHTSHIFT DISABLED — skipping run"
    echo "[wrapper] To re-enable: unset NIGHTSHIFT_DISABLED and remove $DISABLE_FLAG"
    exit 0
  fi

  # 0. Ensure worktree exists, then sync to latest main (best effort).
  if [[ ! -d "$WORKTREE" ]]; then
    echo "[wrapper] Worktree missing at $WORKTREE. Attempting self-heal..."
    # Clear stale worktree metadata entries first.
    git -C "$PROJECT_ROOT" worktree prune 2>/dev/null || true

    # Try origin/main first, then local main, then HEAD.
    git -C "$PROJECT_ROOT" fetch origin main 2>/dev/null || true
    git -C "$PROJECT_ROOT" worktree add --detach "$WORKTREE" origin/main 2>/dev/null ||
      git -C "$PROJECT_ROOT" worktree add --detach "$WORKTREE" main 2>/dev/null ||
      git -C "$PROJECT_ROOT" worktree add --detach "$WORKTREE" HEAD 2>/dev/null || true
  fi

  if [[ ! -d "$WORKTREE" ]]; then
    echo "[wrapper] ERROR: could not create worktree at $WORKTREE"
    echo "[wrapper] Manual fix: git -C $PROJECT_ROOT worktree prune && git -C $PROJECT_ROOT worktree add --detach $WORKTREE HEAD"
    exit 1
  fi

  echo "[wrapper] Syncing worktree to latest main..."
  git -C "$WORKTREE" fetch origin main 2>/dev/null || true
  git -C "$WORKTREE" checkout --detach origin/main 2>/dev/null ||
    git -C "$WORKTREE" checkout --detach main 2>/dev/null || true
  echo "[wrapper] Worktree at: $(git -C "$WORKTREE" rev-parse --short HEAD)"

  # 0.8. Keep running-state attestation fresh for AutoPilot trial-trust gates.
  refresh_attestation_if_stale

  # 1. Check inference load
  source "$SCRIPT_DIR/inference_guard.sh"

  # AUD-7 (2026-08-12): REFUSE TO LAUNCH ON AN UNMEASURED HOST.
  #
  # The guard used to fail OPEN: a missing pgrep, argv drift, a renamed binary or a
  # /proc read error all summed to 0GB and printed "No heavy inference detected",
  # after which this wrapper launched a full agent workload on top of a live 200GB
  # inference run. The guard is now three-valued and says so; the only correct
  # response to `failed` is to stop. An unmeasured host is not a quiet host.
  if [[ "${NIGHTSHIFT_GUARD_STATE:-failed}" != "measured" ]]; then
    echo "[wrapper] ==================================================================="
    echo "[wrapper] REFUSING TO RUN: the inference guard could not MEASURE this host."
    echo "[wrapper]   state  : ${NIGHTSHIFT_GUARD_STATE:-<unset — guard did not run>}"
    echo "[wrapper]   reason : ${NIGHTSHIFT_GUARD_REASON:-<none reported>}"
    echo "[wrapper]   memavail: ${NIGHTSHIFT_MEMAVAIL_GB:-unknown}GB"
    echo "[wrapper] Nightshift would otherwise launch an agent workload that could land on"
    echo "[wrapper] top of a live multi-hundred-GB inference run. 'Cannot tell' is not 'idle'."
    echo "[wrapper] Fix the measurement (is pgrep present? has the server binary been"
    echo "[wrapper] renamed? is /proc readable?) and re-run."
    echo "[wrapper] ==================================================================="
    exit 4
  fi

  # 1.5. Feed F2 self-running lab jobs. Active-safe deterministic monitors run
  # even during live AutoPilot/llama serving; model-backed jobs remain quiet-window
  # only and write review queue artifacts in epyc-orchestrator.
  run_lab_active_safe
  run_lab_shadow_if_quiet

  # 2. Build nightshift command
  MAX_PROJECTS="${NIGHTSHIFT_MAX_PROJECTS:-3}"
  MAX_TASKS="${NIGHTSHIFT_MAX_TASKS:-2}"

  NIGHTSHIFT_CMD=(
    nightshift run
    --yes
    --max-projects "$MAX_PROJECTS"
    --max-tasks "$MAX_TASKS"
  )

  # If inference is active, run only on this project with analysis-only tasks
  if [[ "${NIGHTSHIFT_INFERENCE_ACTIVE:-0}" == "1" ]]; then
    echo "[wrapper] Inference mode: limiting to analysis-only tasks on this project"
    IFS=',' read -ra TASKS <<<"$NIGHTSHIFT_TASK_FILTER"
    for task in "${TASKS[@]}"; do
      echo "[wrapper] Running analysis task: $task"
      nightshift run --yes --project "$WORKTREE" --task "$task" "$@" 2>&1 || {
        echo "[wrapper] Task $task failed or skipped (budget/cooldown), continuing..."
      }
    done
  else
    echo "[wrapper] Full mode: running all eligible tasks"
    "${NIGHTSHIFT_CMD[@]}" "$@" 2>&1
  fi

  echo "=== Nightshift Run Complete: $(date -Iseconds) ==="
# AUD-7: the braces run in a SUBSHELL because of the pipe, so an `exit` inside them
# is the subshell's status, not this script's. Capture it — otherwise the guard's
# refusal above would exit 4 into a pipeline whose visible status is tee's 0, and
# the systemd unit (or any caller) would record a clean run.
} 2>&1 | tee "$LOGFILE" || wrapper_rc=$?
wrapper_rc="${wrapper_rc:-0}"

# Prune logs older than 30 days
find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true

exit "$wrapper_rc"
