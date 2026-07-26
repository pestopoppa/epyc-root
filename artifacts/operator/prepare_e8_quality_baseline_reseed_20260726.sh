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
from datetime import datetime, timezone
from pathlib import Path
import sys


def fail(message: str) -> None:
    raise SystemExit(message)


def finite_number(value: object, label: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        fail(f"{label} must be finite")


def post_boundary_timestamp(value: object, label: str) -> None:
    if not isinstance(value, str) or not value:
        fail(f"{label} must be a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        fail(f"{label} is not ISO-8601")
    if parsed.tzinfo is None or parsed.astimezone(timezone.utc).timestamp() < 1785004723.0:
        fail(f"{label} predates the E8 boundary")


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
record_keys = {"tier", "path", "sha256", "protocol_id", "core_id", "n", "timestamp", "era", "instrument", "quality"}
source_by_tier: dict[str, dict] = {}
for record in records:
    if not isinstance(record, dict) or set(record) != record_keys:
        fail("each source record must declare exactly the full-pool source contract")
    tier = record["tier"]
    if tier not in (1, 2) or tier in seen_tiers:
        fail("source records must contain exactly one each for tiers 1 and 2")
    seen_tiers.add(tier)
    if record["instrument"] != "dedicated_full_pool_tier_baseline":
        fail("numeric-derived or non-full-pool source records are forbidden")
    if record["era"] != "E8" or not all(isinstance(record[key], str) and record[key] for key in ("protocol_id", "core_id")):
        fail("source record protocol/core/timestamp/era is incomplete")
    post_boundary_timestamp(record["timestamp"], "source record timestamp")
    if not isinstance(record["n"], int) or record["n"] <= 0:
        fail("source record n must be a positive integer")
    finite_number(record["quality"], "source record quality")
    source = Path(record["path"])
    if not source.is_file():
        fail(f"source artifact is missing: {source}")
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if record["sha256"] != actual:
        fail(f"source artifact hash mismatch: {source}")
    try:
        summary = json.loads(source.read_text())
    except json.JSONDecodeError as exc:
        fail(f"source artifact is not JSON: {exc}")
    required_summary = {"tier", "core_id", "n", "quality", "per_suite_quality", "per_suite_counts", "era", "decision_grade"}
    if not isinstance(summary, dict) or set(summary) != required_summary:
        fail("source summary must declare exactly tier/core/n/quality/per-suite/era/decision-grade fields")
    if summary["decision_grade"] is not True:
        fail("source summary is not decision-grade")
    if (summary["tier"], summary["core_id"], summary["n"], summary["era"]) != (tier, record["core_id"], record["n"], "E8"):
        fail("source summary does not match declared tier/core/n/era")
    finite_number(summary["quality"], "source summary quality")
    if summary["quality"] != record["quality"]:
        fail("source summary quality does not match declared source quality")
    if not isinstance(summary["per_suite_quality"], dict) or not isinstance(summary["per_suite_counts"], dict):
        fail("source summary per-suite fields must be objects")
    source_by_tier[str(tier)] = {"record": record, "summary": summary}
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
if set(baseline["baselines_by_tier"] or {}) != {"1", "2"}:
    fail("tier baselines must cover exactly tiers 1 and 2")
for field in ("per_suite_quality_by_tier", "per_suite_counts_by_tier"):
    if not isinstance(baseline[field], dict) or set(baseline[field]) != {"1", "2"}:
        fail(f"{field} must cover exactly tiers 1 and 2")
if set(replacement["quality_history_by_tier"] or {}) != {"1", "2"} or set(replacement["quality_history_provenance_by_tier"] or {}) != {"1", "2"}:
    fail("quality history and MAD provenance must cover exactly tiers 1 and 2")
for tier in ("1", "2"):
    finite_number((baseline["baselines_by_tier"] or {}).get(tier), f"tier {tier} baseline")
    summary = source_by_tier[tier]["summary"]
    record = source_by_tier[tier]["record"]
    if baseline["baselines_by_tier"][tier] != record["quality"]:
        fail(f"tier {tier} baseline does not match source quality")
    if baseline["per_suite_quality_by_tier"][tier] != summary["per_suite_quality"] or baseline["per_suite_counts_by_tier"][tier] != summary["per_suite_counts"]:
        fail(f"tier {tier} per-suite proposal does not match source summary")
    quality_map = baseline["per_suite_quality_by_tier"][tier]
    count_map = baseline["per_suite_counts_by_tier"][tier]
    if set(quality_map) != set(count_map):
        fail(f"tier {tier} per-suite quality/count keys differ")
    for suite, value in quality_map.items():
        finite_number(value, f"tier {tier} suite {suite} quality")
        if not isinstance(count_map[suite], int) or count_map[suite] < 0:
            fail(f"tier {tier} suite {suite} count must be nonnegative")
    history = replacement["quality_history_by_tier"][tier]
    if not isinstance(history, list) or not 3 <= len(history) <= 10:
        fail(f"tier {tier} quality history must contain 3-10 E8 observations")
    for index, value in enumerate(history):
        finite_number(value, f"tier {tier} history[{index}]")
    provenance = replacement["quality_history_provenance_by_tier"][tier]
    if not isinstance(provenance, list) or len(provenance) != len(history):
        fail(f"tier {tier} MAD provenance must match history length")
    allowed_cores = {item["record"]["core_id"] for item in source_by_tier.values()}
    for index, observation in enumerate(provenance):
        if not isinstance(observation, dict) or set(observation) != {"q", "ts", "era", "core_id"}:
            fail(f"tier {tier} MAD provenance has unexpected or missing fields")
        if observation["era"] != "E8" or observation["core_id"] not in allowed_cores:
            fail(f"tier {tier} MAD provenance is not tied to E8 source cores")
        post_boundary_timestamp(observation["ts"], f"tier {tier} MAD provenance timestamp")
        finite_number(observation["q"], f"tier {tier} MAD provenance quality")
        if observation["q"] != history[index]:
            fail(f"tier {tier} MAD provenance quality does not match history")
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
