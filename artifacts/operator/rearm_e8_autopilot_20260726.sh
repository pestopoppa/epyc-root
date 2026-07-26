#!/bin/bash
# Restart AutoPilot after the separately ratified E8 quality fence. This never
# reloads or directly edits the production stack, lineup, era registry, or
# trust-boundary state; AutoPilot itself will write its normal runtime state.
set -euo pipefail

ROOT="${EPYC_ROOT:-/mnt/raid0/llm/epyc-root}"
ORCH="${EPYC_ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
PROD="${EPYC_PROD:-/mnt/raid0/llm/llama.cpp}"
PYTHON="$ORCH/.venv/bin/python"
ATTESTATION="$ROOT/artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.json"
STATE="$ORCH/orchestration/autopilot_state.json"
ERAS="$ORCH/orchestration/instrument_eras.yaml"
SUPPRESSION="kv_compaction"
MAX_TRIALS="${AUTOPILOT_E8_MAX_TRIALS:-3000}"
RUN_DIR="$ROOT/artifacts/autopilot/e8-rearm-$(date -u +%Y%m%dT%H%M%SZ)"
CHILD_DISCOVERY_TIMEOUT_S="${AUTOPILOT_E8_CHILD_DISCOVERY_TIMEOUT_S:-30}"
STABILITY_WINDOW_S="${AUTOPILOT_E8_STABILITY_WINDOW_S:-10}"

cleanup_armed=0
supervisor_pid=""
child_pid=""
source_max_epoch=0

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

validate_frozen_stack() {
    [[ "$(git -C "$PROD" branch --show-current)" == "production-consolidated-v8" ]] || fail 'production branch is not frozen v8'
    [[ "$(git -C "$PROD" rev-parse HEAD)" == "67a433bf45a8a091d83b4ea0b32ff0735fd51800" ]] || fail 'production head is not frozen v8'
    git -C "$PROD" diff --quiet || fail 'production tree has tracked modifications'
    git -C "$PROD" diff --cached --quiet || fail 'production index has staged modifications'
    curl -fsS --max-time 10 http://127.0.0.1:8000/health |
        jq -e '.status == "ok" and .models_loaded == 6 and ([.backend_probes[] | select(.ok == true)] | length == 6) and ([.backend_probes[]] | length == 6)' >/dev/null ||
        fail 'current frozen-v8 API lineup is not healthy 6/6'
    ! pgrep -f '[s]cripts/autopilot/autopilot.py start' >/dev/null || fail 'AutoPilot child is already running'
    ! pgrep -f '[s]cripts/autopilot/autopilot_supervisor.py' >/dev/null || fail 'AutoPilot supervisor is already running'
}

validate_attestation() {
    [[ -f "$ATTESTATION" ]] || fail 'E8 quality-fence attestation is absent'
    jq -e --arg eras "$(sha256sum "$ERAS" | awk '{print $1}')" --arg state "$(sha256sum "$STATE" | awk '{print $1}')" '
        .decision == "RATIFY-E8-AUTOPILOT-QUALITY-FENCE" and
        .quality_era.id == "E8" and
        .required_autopilot_env.AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES == "kv_compaction" and
        .sha256.instrument_eras == $eras and .sha256.autopilot_state == $state
    ' "$ATTESTATION" >/dev/null || fail 'E8 attestation does not match current state and registry'
    jq -e '.active_instrument_eras.eval_quality == "E8" and .quality_epoch_ts == 1785004723.0 and .quality_exclude_before_ts == 1785004723.0 and .baseline_state.eval_quality_era == "E7-eval-instrument"' "$STATE" >/dev/null ||
        fail 'state is not the expected E8 quality-hold posture'
    local attested_orchestrator_head current_orchestrator_head
    attested_orchestrator_head="$(jq -er '.repository_heads.epyc_orchestrator' "$ATTESTATION")"
    current_orchestrator_head="$(git -C "$ORCH" rev-parse HEAD)"
    [[ "$current_orchestrator_head" == "$attested_orchestrator_head" ]] ||
        fail "orchestrator HEAD $current_orchestrator_head does not match attested $attested_orchestrator_head"
    # The human transaction intentionally appends the attested E8 registry row
    # without committing it. Its exact current hash was checked above; every
    # other tracked orchestrator path must remain clean before launch.
    git -C "$ORCH" diff --quiet -- . ':(exclude)orchestration/instrument_eras.yaml' ||
        fail 'orchestrator tree has tracked modifications outside the attested era registry'
    git -C "$ORCH" diff --cached --quiet -- . ':(exclude)orchestration/instrument_eras.yaml' ||
        fail 'orchestrator index has staged modifications outside the attested era registry'
}

snapshot_prelaunch() {
    mkdir -p "$RUN_DIR"
    uv_cmd=(uv run python scripts/server/orchestrator_stack.py status)
    ( cd "$ORCH"; "${uv_cmd[@]}" ) >"$RUN_DIR/stack-before.txt"
    curl -fsS http://127.0.0.1:8000/health | jq . >"$RUN_DIR/api-health-before.json"
    stat -c '%n %Y %y' "$ORCH/scripts/autopilot/autopilot.py" "$ORCH/scripts/autopilot/actions.py" "$ORCH/scripts/autopilot/controller_io.py" >"$RUN_DIR/autopilot-source-mtimes.txt"
    source_max_epoch="$(awk 'BEGIN { max = 0 } { if ($2 > max) max = $2 } END { print max }' "$RUN_DIR/autopilot-source-mtimes.txt")"
    git -C "$ORCH" rev-parse HEAD >"$RUN_DIR/orchestrator-head.txt"
    (
        export AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES="$SUPPRESSION"
        cd "$ORCH"
        "$PYTHON" - <<'PY'
from scripts.autopilot.start_fable_authority_daemon import authority_env
import json
env = authority_env()
assert env["AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES"] == "kv_compaction"
print(json.dumps({"AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES": env["AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES"]}))
PY
    ) >"$RUN_DIR/suppression-env-check.json"
}

process_alive() {
    [[ -n "${1:-}" ]] && kill -0 "$1" 2>/dev/null
}

process_start_epoch() {
    local pid="$1" ticks boot_hz boot_epoch
    ticks="$(awk '{print $22}' "/proc/$pid/stat")" || return 1
    boot_hz="$(getconf CLK_TCK)" || return 1
    boot_epoch="$(awk '/^btime / { print $2 }' /proc/stat)" || return 1
    awk -v boot="$boot_epoch" -v ticks="$ticks" -v hz="$boot_hz" 'BEGIN { printf "%.3f\n", boot + (ticks / hz) }'
}

verify_child_suppression() {
    tr '\0' '\n' <"/proc/$child_pid/environ" |
        rg '^AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES=kv_compaction$' >"$RUN_DIR/child-suppression-env.txt"
}

terminate_pid() {
    local pid="$1" attempts=0
    process_alive "$pid" || return 0
    kill -TERM "$pid" 2>/dev/null || true
    while process_alive "$pid" && (( attempts < 5 )); do
        sleep 1
        ((attempts += 1))
    done
    if process_alive "$pid"; then
        kill -KILL "$pid" 2>/dev/null || true
        attempts=0
        while process_alive "$pid" && (( attempts < 5 )); do
            sleep 1
            ((attempts += 1))
        done
    fi
    ! process_alive "$pid"
}

terminate_matching_processes() {
    local pattern="$1" pid
    local -a pids=()
    mapfile -t pids < <(pgrep -f "$pattern" || true)
    for pid in "${pids[@]}"; do
        terminate_pid "$pid" || printf 'ERROR: PID %s remained live after SIGKILL.\n' "$pid" >&2
    done
}

cleanup_after_failed_start() {
    local status=$? discovered_child discovered_supervisor
    trap - EXIT
    if (( cleanup_armed == 1 )); then
        discovered_child="$child_pid"
        discovered_supervisor="$supervisor_pid"
        [[ -n "$discovered_child" ]] || discovered_child="$(pgrep -f '[s]cripts/autopilot/autopilot.py start' | head -n 1 || true)"
        [[ -n "$discovered_supervisor" ]] || discovered_supervisor="$(pgrep -f '[s]cripts/autopilot/autopilot_supervisor.py' | head -n 1 || true)"
        printf 'E8 AutoPilot launch verification failed; terminating supervisor=%s child=%s.\n' "$discovered_supervisor" "$discovered_child" >&2
        terminate_pid "$discovered_supervisor" || printf 'ERROR: supervisor PID %s remained live after SIGKILL.\n' "$discovered_supervisor" >&2
        terminate_matching_processes '[s]cripts/autopilot/autopilot_supervisor.py'
        terminate_pid "$discovered_child" || printf 'ERROR: child PID %s remained live after SIGKILL.\n' "$discovered_child" >&2
        terminate_matching_processes '[s]cripts/autopilot/autopilot.py start'
        ! pgrep -f '[s]cripts/autopilot/autopilot_supervisor.py' >/dev/null || fail 'AutoPilot supervisor remained live after cleanup'
        ! pgrep -f '[s]cripts/autopilot/autopilot.py start' >/dev/null || fail 'AutoPilot child remained live after cleanup'
    fi
    exit "$status"
}

await_child() {
    local elapsed=0
    while (( elapsed < CHILD_DISCOVERY_TIMEOUT_S )); do
        child_pid="$(pgrep -f '[s]cripts/autopilot/autopilot.py start' | head -n 1 || true)"
        if process_alive "$child_pid"; then
            return 0
        fi
        sleep 1
        ((elapsed += 1))
    done
    return 1
}

verify_live_launch() {
    local supervisor_start child_start elapsed=0
    process_alive "$supervisor_pid" || fail 'authority launcher supervisor exited before verification'
    process_alive "$child_pid" || fail 'AutoPilot child exited before verification'
    supervisor_start="$(process_start_epoch "$supervisor_pid")" || fail 'could not read supervisor start epoch'
    child_start="$(process_start_epoch "$child_pid")" || fail 'could not read child start epoch'
    awk -v start="$supervisor_start" -v source="$source_max_epoch" 'BEGIN { exit !(start >= source) }' ||
        fail "supervisor predates current AutoPilot sources ($supervisor_start < $source_max_epoch)"
    awk -v start="$child_start" -v source="$source_max_epoch" 'BEGIN { exit !(start >= source) }' ||
        fail "child predates current AutoPilot sources ($child_start < $source_max_epoch)"
    printf '{"source_max_epoch":%s,"supervisor_start_epoch":%s,"child_start_epoch":%s}\n' \
        "$source_max_epoch" "$supervisor_start" "$child_start" >"$RUN_DIR/process-start-epochs.json"
    verify_child_suppression || fail 'AutoPilot child did not inherit kv_compaction suppression'
    while (( elapsed < STABILITY_WINDOW_S )); do
        sleep 1
        process_alive "$supervisor_pid" || fail 'authority launcher supervisor exited during stability window'
        process_alive "$child_pid" || fail 'AutoPilot child exited during stability window'
        verify_child_suppression || fail 'AutoPilot child lost kv_compaction suppression during stability window'
        ((elapsed += 1))
    done
    ps -o pid=,lstart=,etimes=,args= -p "$supervisor_pid" -p "$child_pid" >"$RUN_DIR/process-starts.txt"
}

monitor() {
    ( cd "$ORCH"; "$PYTHON" - <<'PY'
import json
import sys
sys.path.insert(0, "scripts/autopilot")
from autopilot import _frontier_rerun_completed_numeric_trials, _frontier_rerun_min_trials
from experiment_journal import ExperimentJournal

with open("orchestration/autopilot_state.json", encoding="utf-8") as handle:
    state = json.load(handle)
marker = state.get("frontier_rerun_required") or {}
journal = ExperimentJournal()
completed = _frontier_rerun_completed_numeric_trials(marker, journal) if marker else 0
required = _frontier_rerun_min_trials(marker) if marker else 0
print(json.dumps({
    "trial_counter": state.get("trial_counter"),
    "quality_hold": state.get("e8_quality_rebaseline"),
    "active_eval_quality_era": (state.get("active_instrument_eras") or {}).get("eval_quality"),
    "baseline_eval_quality_era": (state.get("baseline_state") or {}).get("eval_quality_era"),
    "frontier_rerun_required": bool(marker.get("required")),
    "frontier_numeric_trials_completed": completed,
    "frontier_numeric_trials_required": required,
    "frontier_numeric_trials_remaining": max(0, required - completed),
}, indent=2, sort_keys=True))
PY
    )
}

start() {
    validate_frozen_stack
    validate_attestation
    snapshot_prelaunch
    cleanup_armed=1
    trap cleanup_after_failed_start EXIT
    (
        export AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES="$SUPPRESSION"
        cd "$ORCH"
        uv run python scripts/autopilot/start_fable_authority_daemon.py --max-trials "$MAX_TRIALS"
    ) >"$RUN_DIR/launch.json"
    supervisor_pid="$(jq -er '.pid' "$RUN_DIR/launch.json")"
    await_child || fail "authority launcher did not leave a live AutoPilot child within ${CHILD_DISCOVERY_TIMEOUT_S}s"
    verify_live_launch
    monitor >"$RUN_DIR/e8-progress-after-start.json"
    cleanup_armed=0
    trap - EXIT
    printf 'AutoPilot E8 rearm launched. Provenance: %s\n' "$RUN_DIR"
}

main() {
    case "${1:-}" in
        --dry-run)
            [[ $# -eq 1 ]] || fail 'usage: --dry-run|--start|--monitor'
            validate_frozen_stack
            snapshot_prelaunch
            (
                export AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES="$SUPPRESSION"
                cd "$ORCH"
                uv run python scripts/autopilot/start_fable_authority_daemon.py --max-trials "$MAX_TRIALS" --dry-run
            ) >"$RUN_DIR/launcher-dry-run.json"
            printf 'E8 AutoPilot rearm dry-run passed. Evidence: %s\n' "$RUN_DIR"
            ;;
        --start) [[ $# -eq 1 ]] || fail 'usage: --dry-run|--start|--monitor'; start ;;
        --monitor) [[ $# -eq 1 ]] || fail 'usage: --dry-run|--start|--monitor'; monitor ;;
        *) fail 'usage: --dry-run|--start|--monitor' ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
