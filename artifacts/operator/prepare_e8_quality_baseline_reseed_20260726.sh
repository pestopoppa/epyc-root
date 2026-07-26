#!/bin/bash
# Read-only preflight for the human-only E8 quality-baseline reseed.
# The eventual apply transaction must consume a source-hashed full-pool evidence
# manifest; this script never writes baseline values or alters the E8 hold.
set -euo pipefail

ROOT="${EPYC_ROOT:-/mnt/raid0/llm/epyc-root}"
ORCH="${EPYC_ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
PYTHON="${EPYC_PYTHON:-$ORCH/.venv/bin/python}"
STATE="$ORCH/orchestration/autopilot_state.json"
JOURNAL="$ORCH/orchestration/autopilot_journal.jsonl"
EVIDENCE="$ROOT/artifacts/operator/e8_quality_baseline_evidence_20260726.json"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

numeric_trial_count() {
    (cd "$ORCH"; "$PYTHON" - "$STATE" <<'PY'
import json
import sys
sys.path.insert(0, "scripts/autopilot")
from autopilot import _frontier_rerun_completed_numeric_trials
from experiment_journal import ExperimentJournal

state = json.load(open(sys.argv[1], encoding="utf-8"))
marker = state.get("frontier_rerun_required") or {}
print(_frontier_rerun_completed_numeric_trials(marker, ExperimentJournal()))
PY
    )
}

validate_preflight() {
    [[ -x "$PYTHON" && -f "$STATE" && -f "$JOURNAL" ]] || fail 'AutoPilot state or journal prerequisite is missing'
    jq -e '
        .active_instrument_eras.eval_quality == "E8" and
        .baseline_state.eval_quality_era != "E8" and
        .e8_quality_rebaseline.status == "hold_open"
    ' "$STATE" >/dev/null || fail 'E8 quality hold is not open against a pre-E8 baseline'
    local completed required
    completed="$(numeric_trial_count)"
    required="$(jq -er '.frontier_rerun_required.min_numeric_trials' "$STATE")"
    (( completed >= required && required >= 16 )) ||
        fail "E8 numeric rerun is incomplete ($completed/$required); no quality baseline may be applied"
    [[ -f "$EVIDENCE" ]] || fail "E8 full-pool evidence manifest is not staged: $EVIDENCE"
    jq -e '
        .schema == "epyc.e8_quality_baseline_evidence.v1" and
        .eval_quality_era == "E8" and
        (.source_hashes | type == "object" and length >= 2) and
        (.replacement_baseline_state | type == "object") and
        .replacement_baseline_state.eval_quality_era == "E8"
    ' "$EVIDENCE" >/dev/null || fail 'evidence manifest is not a source-hashed E8 full-pool baseline proposal'
}

plan() {
    cat <<'EOF'
E8 quality-baseline reseed preparation
- retain the E8 quality hold until 16 or more E8 numeric trials have completed
- require dedicated full-pool tier evidence, source hashes, and an E8-stamped replacement baseline
- use a separate human-reviewed atomic apply transaction after evidence review
- never derive quality baseline values from numeric trials

Recorded alternatives: deriving baseline values from numeric trials was rejected as confounded;
holding the gate indefinitely remains the fail-closed fallback if full-pool evidence is unavailable.
EOF
}

case "${1:-}" in
    --plan) [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only'; plan ;;
    --validate-only) [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only'; validate_preflight; printf 'E8 quality baseline reseed preflight passed; no files changed.\n' ;;
    *) fail 'usage: --plan|--validate-only' ;;
esac
