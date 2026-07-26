#!/bin/bash
# Restart AutoPilot after the separately ratified E8 quality fence. This never
# reloads or edits the production stack, lineup, era registry, or state values.
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
}

snapshot_prelaunch() {
    mkdir -p "$RUN_DIR"
    uv_cmd=(uv run python scripts/server/orchestrator_stack.py status)
    ( cd "$ORCH"; "${uv_cmd[@]}" ) >"$RUN_DIR/stack-before.txt"
    curl -fsS http://127.0.0.1:8000/health | jq . >"$RUN_DIR/api-health-before.json"
    stat -c '%n %Y %y' "$ORCH/scripts/autopilot/autopilot.py" "$ORCH/scripts/autopilot/actions.py" "$ORCH/scripts/autopilot/controller_io.py" >"$RUN_DIR/autopilot-source-mtimes.txt"
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
    (
        export AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES="$SUPPRESSION"
        cd "$ORCH"
        uv run python scripts/autopilot/start_fable_authority_daemon.py --max-trials "$MAX_TRIALS"
    ) >"$RUN_DIR/launch.json"
    local supervisor_pid child_pid
    supervisor_pid="$(jq -er '.pid' "$RUN_DIR/launch.json")"
    sleep 2
    child_pid="$(pgrep -f '[s]cripts/autopilot/autopilot.py start' | head -n 1 || true)"
    [[ -n "$child_pid" ]] || fail 'authority launcher did not leave a live AutoPilot child'
    ps -o pid=,lstart=,etimes=,args= -p "$supervisor_pid" -p "$child_pid" >"$RUN_DIR/process-starts.txt"
    tr '\0' '\n' <"/proc/$child_pid/environ" | rg '^AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES=kv_compaction$' >"$RUN_DIR/child-suppression-env.txt" ||
        fail 'AutoPilot child did not inherit kv_compaction suppression'
    monitor >"$RUN_DIR/e8-progress-after-start.json"
    printf 'AutoPilot E8 rearm launched. Provenance: %s\n' "$RUN_DIR"
}

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
