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
EVIDENCE="${E8_QUALITY_BASELINE_EVIDENCE:-$ROOT/artifacts/operator/e8_quality_baseline_evidence_20260726.json}"

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
    validate_evidence "$EVIDENCE"
}

validate_evidence() {
    local evidence="$1"
    [[ -f "$evidence" ]] || fail "E8 full-pool evidence manifest is not staged: $evidence"
    "$PYTHON" - "$evidence" <<'PY'
import hashlib
import json
import math
from pathlib import Path
import sys


def fail(message: str) -> None:
    raise SystemExit(message)


def finite_number(value: object, label: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        fail(f"{label} must be finite")


manifest_path = Path(sys.argv[1])
try:
    manifest = json.loads(manifest_path.read_text())
except (OSError, json.JSONDecodeError) as exc:
    fail(f"cannot read evidence manifest: {exc}")
if not isinstance(manifest, dict):
    fail("evidence manifest must be an object")
if set(manifest) != {"schema", "eval_quality_era", "source_records", "replacement"}:
    fail("evidence manifest has unexpected or missing top-level keys")
if manifest["schema"] != "epyc.e8_quality_baseline_evidence.v1" or manifest["eval_quality_era"] != "E8":
    fail("evidence manifest is not an E8 quality-baseline proposal")
records = manifest["source_records"]
if not isinstance(records, list) or len(records) != 2:
    fail("evidence manifest requires exactly two tier source records")
seen_tiers: set[int] = set()
record_keys = {"tier", "path", "sha256", "protocol_id", "core_id", "n", "timestamp", "era", "instrument"}
for record in records:
    if not isinstance(record, dict) or set(record) != record_keys:
        fail("each source record must declare exactly the full-pool source contract")
    tier = record["tier"]
    if tier not in (1, 2) or tier in seen_tiers:
        fail("source records must contain exactly one each for tiers 1 and 2")
    seen_tiers.add(tier)
    if record["instrument"] != "dedicated_full_pool_tier_baseline":
        fail("numeric-derived or non-full-pool source records are forbidden")
    if record["era"] != "E8" or not all(isinstance(record[key], str) and record[key] for key in ("protocol_id", "core_id", "timestamp")):
        fail("source record protocol/core/timestamp/era is incomplete")
    if not isinstance(record["n"], int) or record["n"] <= 0:
        fail("source record n must be a positive integer")
    source = Path(record["path"])
    if not source.is_file():
        fail(f"source artifact is missing: {source}")
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if record["sha256"] != actual:
        fail(f"source artifact hash mismatch: {source}")
if seen_tiers != {1, 2}:
    fail("source records must cover tiers 1 and 2")

replacement = manifest["replacement"]
if not isinstance(replacement, dict) or set(replacement) != {
    "baseline_state", "quality_history_by_tier", "quality_history_provenance_by_tier"
}:
    fail("replacement may contain only quality baseline/history/MAD fields")
baseline = replacement["baseline_state"]
allowed_baseline = {"eval_quality_era", "baselines_by_tier", "per_suite_quality_by_tier", "per_suite_counts_by_tier"}
if not isinstance(baseline, dict) or set(baseline) != allowed_baseline:
    fail("replacement baseline_state contains non-quality fields or is incomplete")
if baseline["eval_quality_era"] != "E8":
    fail("replacement baseline must be stamped E8")
for tier in ("1", "2"):
    finite_number((baseline["baselines_by_tier"] or {}).get(tier), f"tier {tier} baseline")
    if not isinstance((replacement["quality_history_by_tier"] or {}).get(tier), list) or not replacement["quality_history_by_tier"][tier]:
        fail(f"tier {tier} quality history is missing")
    for index, value in enumerate(replacement["quality_history_by_tier"][tier]):
        finite_number(value, f"tier {tier} history[{index}]")
    provenance = (replacement["quality_history_provenance_by_tier"] or {}).get(tier)
    if not isinstance(provenance, list) or not provenance:
        fail(f"tier {tier} MAD provenance is missing")
    for observation in provenance:
        if not isinstance(observation, dict) or observation.get("era") != "E8":
            fail(f"tier {tier} MAD provenance is not E8-stamped")
        finite_number(observation.get("q"), f"tier {tier} MAD provenance quality")
PY
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
    --plan) [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--validate-evidence PATH'; plan ;;
    --validate-only) [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--validate-evidence PATH'; validate_preflight; printf 'E8 quality baseline reseed preflight passed; no files changed.\n' ;;
    --validate-evidence) [[ $# -eq 2 ]] || fail 'usage: --plan|--validate-only|--validate-evidence PATH'; validate_evidence "$2"; printf 'E8 quality evidence contract passed; no files changed.\n' ;;
    *) fail 'usage: --plan|--validate-only|--validate-evidence PATH' ;;
esac
