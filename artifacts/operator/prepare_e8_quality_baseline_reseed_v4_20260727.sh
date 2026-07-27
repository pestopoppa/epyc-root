#!/bin/bash
# Read-only v4 candidate-evidence validator for the consolidated E8 transaction.
set -euo pipefail

ROOT="/mnt/raid0/llm/epyc-root"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
PYTHON="$ORCH/.venv/bin/python"
MAP="$ROOT/artifacts/operator/e8_context_replacement_map_candidate_relaxed_20260727.json"
COVERAGE="$ROOT/artifacts/operator/e8_quality_context_coverage_v4_r2_20260727.json"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[[ $# -eq 2 && "$1" == "--validate-evidence" ]] ||
    fail 'usage: prepare_e8_quality_baseline_reseed_v4_20260727.sh --validate-evidence EVIDENCE'
EVIDENCE="$2"
[[ -x "$PYTHON" && -f "$EVIDENCE" && -f "$MAP" && -f "$COVERAGE" ]] ||
    fail 'v4 evidence-validator prerequisite is missing'

PYTHONOPTIMIZE=0 "$PYTHON" - "$EVIDENCE" "$MAP" "$COVERAGE" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

def fail(message):
    raise SystemExit(f"ERROR: {message}")

def load(path, label):
    try:
        value = json.loads(path.read_text())
    except Exception as exc:
        fail(f"{label} is unreadable: {exc}")
    if not isinstance(value, dict):
        fail(f"{label} is not an object")
    return value

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

evidence_path, map_path, coverage_path = map(Path, sys.argv[1:])
evidence = load(evidence_path, "evidence")
mapping = load(map_path, "replacement map")
coverage = load(coverage_path, "coverage report")
if sha(map_path) != "168ec8bd82e97deaf76943c65ba0c923848a5bda1ee14d4ce9bedcf2a3f12b95":
    fail("replacement map hash differs")
if sha(coverage_path) != "7ef88865c5aa7315143b19cc3d40c153c59e981db7eba9bcbb2ab6ea774fe983":
    fail("coverage report hash differs")
if evidence.get("schema") != "epyc.e8_quality_baseline_evidence.v2":
    fail("evidence schema differs")
candidate_ref = evidence.get("protocol_candidate")
if not isinstance(candidate_ref, dict):
    fail("candidate protocol reference is missing")
candidate_path = Path(str(candidate_ref.get("path", "")))
if not candidate_path.is_file() or candidate_ref.get("sha256") != sha(candidate_path):
    fail("candidate protocol identity differs")
candidate = load(candidate_path, "candidate protocol")
protocol = candidate.get("protocol")
if candidate.get("schema") != "epyc.e8_quality_baseline_protocol_proposal.v3" or not isinstance(protocol, dict):
    fail("candidate protocol schema differs")
if protocol.get("protocol_id") != "e8_quality_full_pool_tier_baseline.v4":
    fail("candidate protocol id differs")
expected_map = {
    "path": str(map_path.resolve()),
    "sha256": sha(map_path),
    "schema": "epyc.e8_context_replacement_map.v2",
}
if protocol.get("context_replacement_map") != expected_map:
    fail("candidate protocol map binding differs")
replacements = mapping.get("replacements")
overflows = coverage.get("overflows")
if not isinstance(replacements, list) or not isinstance(overflows, list):
    fail("map/coverage rows are malformed")
if len(replacements) != 16 or len(overflows) != 16:
    fail("map/coverage count differs")
if {row.get("old_id") for row in replacements} != {row.get("qid") for row in overflows}:
    fail("map does not cover exact overflow identities")

records = evidence.get("source_records")
if not isinstance(records, list) or len(records) != 2:
    fail("evidence must contain T1 and T2 records")
seen = set()
for record in records:
    if not isinstance(record, dict) or record.get("tier") not in (1, 2):
        fail("source record tier differs")
    tier = record["tier"]
    if tier in seen:
        fail("source record tier is duplicated")
    seen.add(tier)
    declared = protocol.get("tiers", {}).get(str(tier), {})
    if (
        record.get("protocol_id") != protocol["protocol_id"]
        or record.get("n") != declared.get("n")
        or record.get("question_vector_sha256") != declared.get("vector_sha256")
    ):
        fail(f"T{tier} record differs from candidate protocol")
    summary_path = Path(str(record.get("path", "")))
    summary = load(summary_path, f"T{tier} summary")
    observations = summary.get("observations")
    if summary.get("decision_grade") is not True or not isinstance(observations, list) or len(observations) != 3:
        fail(f"T{tier} summary is not three clean observations")
if seen != {1, 2}:
    fail("source records do not cover T1 and T2")

seal_path = evidence_path.parent / "run_seal.json"
seal = load(seal_path, "run seal")
if seal.get("status") != "complete" or seal.get("manifest_sha256") != sha(evidence_path):
    fail("run seal does not bind complete evidence")
if seal.get("protocol_candidate_sha256") != sha(candidate_path):
    fail("run seal candidate hash differs")
bundle = seal.get("bundle_sha256")
if not isinstance(bundle, dict) or not bundle:
    fail("run seal bundle is missing")
if bundle.get(str(candidate_path)) != sha(candidate_path):
    fail("candidate protocol is not an exact sealed bundle member")
for record in records:
    source_path = Path(str(record.get("path", "")))
    source_sha = sha(source_path) if source_path.is_file() else None
    if record.get("sha256") != source_sha or bundle.get(str(source_path)) != source_sha:
        fail(f"T{record.get('tier')} source record is not an exact sealed bundle member")
for path_text, expected in bundle.items():
    path = Path(path_text)
    if not path.is_file() or sha(path) != expected:
        fail(f"sealed bundle member differs: {path}")
print("v4 E8 candidate evidence validation passed")
PY
