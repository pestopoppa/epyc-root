#!/bin/bash
# Autonomous E8 v4 collection plus one evidence-bound human apply transaction.
set -euo pipefail

ROOT="/mnt/raid0/llm/epyc-root"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
RESEARCH="/mnt/raid0/llm/epyc-inference-research"
PYTHON="$ORCH/.venv/bin/python"
RUNNER="$ORCH/scripts/benchmark/run_e8_quality_baseline_reseed.py"
CANDIDATE_DIR="$ROOT/artifacts/operator/e8_quality_baseline_candidate_v4_20260727"
EVIDENCE="$CANDIDATE_DIR/e8_quality_baseline_evidence.json"
STATE_REVIEW="$CANDIDATE_DIR/state_candidate_review.json"
RECEIPT="$ROOT/artifacts/operator/ratify_e8_quality_baseline_context_apply_v4_20260727.json"
MAP="$ROOT/artifacts/operator/e8_context_replacement_map_candidate_relaxed_20260727.json"
COVERAGE="$ROOT/artifacts/operator/e8_quality_context_coverage_v4_r2_20260727.json"
VALIDATOR="$ROOT/artifacts/operator/prepare_e8_quality_baseline_reseed_v4_20260727.sh"
APPLIER="$ROOT/artifacts/operator/apply_e8_quality_baseline_state.py"
ATTESTATION="$ROOT/artifacts/operator/ratify_e8_quality_baseline_state_apply_v4_20260727.json"
TRANSACTION_BASE="$ROOT/artifacts/operator/e8_quality_baseline_state_apply_v4_20260727"
INTEGRITY="$ROOT/artifacts/operator/e8_quality_baseline_v4_integrity_20260727.json"
INTEGRITY_SHA256="1be17ddb8d8039a8c88542f9c2274771ffd5bdf19a3a25bf78d4b9644510efbc"
TOKEN="ATTEST-E8-CONTEXT-FEASIBILITY-AND-BASELINE-APPLY-20260727"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
sha() { sha256sum -- "$1" | awk '{print $1}'; }

verify_integrity() {
    [[ -x "$PYTHON" ]] || fail "repo venv interpreter is unavailable: $PYTHON"
    [[ "$(readlink -f -- "$ROOT")" == "$ROOT" ]] || fail 'canonical epyc-root realpath differs'
    [[ "$(readlink -f -- "$ORCH")" == "$ORCH" ]] || fail 'canonical orchestrator realpath differs'
    [[ "$(readlink -f -- "$RESEARCH")" == "$RESEARCH" ]] || fail 'canonical research realpath differs'
    [[ "$(readlink -f -- "$PYTHON")" == "$(readlink -f -- "$ORCH/.venv/bin/python")" ]] ||
        fail 'canonical orchestrator venv interpreter differs'
    [[ -f "$INTEGRITY" && "$(sha "$INTEGRITY")" == "$INTEGRITY_SHA256" ]] ||
        fail 'detached v4 integrity root differs'
    PYTHONOPTIMIZE=0 "$PYTHON" - "$INTEGRITY" "$ROOT" <<'PY'
import hashlib, json
from pathlib import Path
import sys
manifest, root = Path(sys.argv[1]), Path(sys.argv[2])
value = json.loads(manifest.read_text())
if value.get("schema") != "epyc.e8_quality_baseline_v4_integrity.v1":
    raise SystemExit("ERROR: integrity schema differs")
artifacts = value.get("artifacts")
if not isinstance(artifacts, dict) or not artifacts:
    raise SystemExit("ERROR: integrity artifact map is missing")
for relative, expected in artifacts.items():
    path = Path(relative)
    if not path.is_absolute():
        path = root / path
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit(f"ERROR: reviewed v4 artifact differs: {relative}")
PY
}

validate_candidate() {
    [[ -f "$EVIDENCE" ]] || fail "candidate evidence is absent; run --collect first"
    bash "$VALIDATOR" --validate-evidence "$EVIDENCE"
}

stage_state_review() {
    PYTHONOPTIMIZE=0 "$PYTHON" - "$ORCH/orchestration/autopilot_state.json" "$EVIDENCE" "$VALIDATOR" "$APPLIER" "$STATE_REVIEW" <<'PY'
import importlib.util
import json
import os
from pathlib import Path
import sys

state_path, evidence, validator, applier_path, output = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location("e8_v4_applier", applier_path)
if spec is None or spec.loader is None:
    raise SystemExit("ERROR: cannot import reviewed state applier")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
environment = dict(os.environ)
environment["PYTHONOPTIMIZE"] = "0"
payload = module.state_candidate_review_payload(
    state_path,
    evidence,
    validator,
    lambda: module.run_evidence_validator(validator, evidence, environment),
)
serialized = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
if output.exists():
    if output.read_bytes() != serialized:
        raise SystemExit("ERROR: existing state-candidate review differs from current pre-state/evidence")
else:
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(fd, serialized)
        os.fsync(fd)
    finally:
        os.close(fd)
    directory_fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
PY
}

validate_state_review() {
    [[ -f "$STATE_REVIEW" ]] || fail 'state-candidate review is absent; run --collect first'
    PYTHONOPTIMIZE=0 "$PYTHON" - "$STATE_REVIEW" "$EVIDENCE" "$VALIDATOR" "$ORCH/orchestration/autopilot_state.json" "$APPLIER" "$RECEIPT" <<'PY'
import importlib.util
import os
from pathlib import Path
import sys
review_path, evidence, validator, state, applier_path, receipt = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location("e8_v4_review_validator", applier_path)
if spec is None or spec.loader is None:
    raise SystemExit("ERROR: cannot import reviewed state applier")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
environment = dict(os.environ)
environment["PYTHONOPTIMIZE"] = "0"
try:
    module.validate_state_candidate_review(
        review_path,
        state,
        evidence,
        validator,
        lambda: module.run_evidence_validator(validator, evidence, environment),
        allow_applied=receipt.is_file(),
    )
except module.ApplyError as exc:
    raise SystemExit(f"ERROR: {exc}") from exc
PY
}

applier() {
    local action="$1" transaction="$2"
    local bindings expected_pre expected_candidate
    if [[ "$action" == "--validate-only" ]]; then
        expected_pre="$(jq -er '.pre_state_sha256' "$STATE_REVIEW")"
        expected_candidate="$(jq -er '.candidate_state_sha256' "$STATE_REVIEW")"
    else
        bindings="$(validate_receipt)"
        read -r expected_pre expected_candidate <<<"$bindings"
        [[ "$expected_pre" =~ ^[0-9a-f]{64}$ && "$expected_candidate" =~ ^[0-9a-f]{64}$ ]] ||
            fail 'validated receipt did not return reviewed state hashes'
    fi
    local -a command=(
        "$PYTHON" "$APPLIER"
        --state "$ORCH/orchestration/autopilot_state.json" \
        --evidence "$EVIDENCE" \
        --canonical-evidence "$EVIDENCE" \
        --validator "$VALIDATOR" \
        --transaction-dir "$transaction" \
        --attestation "$ATTESTATION" \
        --expected-pre-state-sha256 "$expected_pre" \
        --expected-candidate-state-sha256 "$expected_candidate"
    )
    if [[ "$action" == "--validate-only" ]]; then
        command+=("$action")
    else
        command+=("$action" "$TOKEN")
    fi
    E8_BASELINE_APPLY_TOKEN="$TOKEN" PYTHONOPTIMIZE=0 "${command[@]}"
}

validate_resume_state() {
    PYTHONOPTIMIZE=0 "$PYTHON" - "$TRANSACTION_BASE" "$ATTESTATION" "$EVIDENCE" <<'PY'
import hashlib, json
from pathlib import Path
import sys
base, attestation, evidence = map(Path, sys.argv[1:])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
allowed = {"prepared", "applying", "failed", "rolled_back", "committed"}
states = []
for path in sorted(base.parent.glob(base.name + "-attempt-*")):
    journal = path / "transaction.json"
    if not journal.is_file():
        raise SystemExit(f"ERROR: transaction attempt lacks journal: {path}")
    value = json.loads(journal.read_text())
    state = value.get("state")
    if state not in allowed:
        raise SystemExit(f"ERROR: transaction attempt has unknown state {state}: {path}")
    if (
        value.get("schema") != "epyc.e8_quality_baseline_state_apply_transaction.v1"
        or value.get("evidence", {}).get("sha256") != sha(evidence)
    ):
        raise SystemExit(f"ERROR: transaction attempt evidence binding differs: {path}")
    record = value.get("state_file", {})
    backup = Path(str(record.get("backup", "")))
    candidate = path / "autopilot_state.json.candidate"
    if (
        not backup.is_file()
        or sha(backup) != record.get("pre_sha256")
    ):
        raise SystemExit(f"ERROR: transaction attempt recovery files differ: {path}")
    live = Path(str(record.get("destination", "")))
    live_sha = sha(live)
    if candidate.is_file() and sha(candidate) != record.get("candidate_sha256"):
        raise SystemExit(f"ERROR: transaction candidate copy differs: {path}")
    if (
        not candidate.is_file()
        and live_sha != record.get("candidate_sha256")
        and state not in {"rolled_back"}
    ):
        raise SystemExit(f"ERROR: consumed candidate is not recoverable from live state: {path}")
    if state == "committed" and live_sha != record.get("candidate_sha256"):
        raise SystemExit(f"ERROR: committed transaction differs from live state: {path}")
    if state == "rolled_back" and live_sha != record.get("pre_sha256"):
        raise SystemExit(f"ERROR: rolled-back transaction differs from live state: {path}")
    if state in {"prepared", "applying", "failed"} and live_sha not in {
        record.get("pre_sha256"), record.get("candidate_sha256")
    }:
        raise SystemExit(f"ERROR: incomplete transaction is not recoverable: {path}")
    states.append(state)
if attestation.exists() and "committed" not in states:
    raise SystemExit("ERROR: apply attestation exists without a committed journal")
if "committed" in states:
    print("committed")
elif any(state in {"prepared", "applying", "failed"} for state in states):
    print("recoverable")
else:
    print("fresh")
PY
}

validate_receipt() {
    [[ -f "$RECEIPT" ]] || fail "combined receipt is absent: $RECEIPT"
    PYTHONOPTIMIZE=0 "$PYTHON" - "$RECEIPT" "$EVIDENCE" "$MAP" "$COVERAGE" "$INTEGRITY" "$STATE_REVIEW" "$TOKEN" "$ROOT" "$ORCH" "$RESEARCH" <<'PY'
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys

receipt, evidence, mapping, coverage, integrity, review = map(Path, sys.argv[1:7])
token, root, orch, research = sys.argv[7:]
value = json.loads(receipt.read_text())
expected_keys = {
    "schema",
    "decision",
    "ratified_at",
    "evidence",
    "evidence_sha256",
    "protocol_candidate",
    "protocol_candidate_sha256",
    "protocol_id",
    "replacement_map_sha256",
    "coverage_report_sha256",
    "integrity_root_sha256",
    "state_candidate_review",
    "state_candidate_review_sha256",
    "pre_state_sha256",
    "candidate_state_sha256",
    "exact_state_diff",
    "validation_result",
    "source_pool_tier_relaxation_accepted",
    "repository_heads",
}
if set(value) != expected_keys:
    raise SystemExit("ERROR: existing combined receipt has the wrong exact key set")
if (
    value["schema"] != "epyc.operator_e8_quality_baseline_context_apply.v1"
    or value["decision"] != token
):
    raise SystemExit("ERROR: existing combined receipt decision differs")
ratified_at = value["ratified_at"]
if not isinstance(ratified_at, str):
    raise SystemExit("ERROR: existing combined receipt timestamp is not a string")
try:
    parsed_at = datetime.fromisoformat(ratified_at.replace("Z", "+00:00"))
except ValueError as exc:
    raise SystemExit("ERROR: existing combined receipt timestamp is not ISO-8601") from exc
if parsed_at.tzinfo is None or parsed_at.astimezone(timezone.utc) < datetime(
    2026, 7, 25, 18, 38, 43, tzinfo=timezone.utc
):
    raise SystemExit("ERROR: existing combined receipt timestamp predates E8")

evidence_value = json.loads(evidence.read_text())
candidate = Path(evidence_value["protocol_candidate"]["path"])
review_value = json.loads(review.read_text())
expected_heads = {
    name: subprocess.check_output(
        ["git", "-C", path, "rev-parse", "HEAD"], text=True
    ).strip()
    for name, path in {
        "epyc_root": root,
        "epyc_orchestrator": orch,
        "epyc_inference_research": research,
    }.items()
}
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
expected = {
    "evidence": str(evidence.resolve()),
    "evidence_sha256": sha(evidence),
    "protocol_candidate": str(candidate.resolve()),
    "protocol_candidate_sha256": sha(candidate),
    "protocol_id": "e8_quality_full_pool_tier_baseline.v4",
    "replacement_map_sha256": sha(mapping),
    "coverage_report_sha256": sha(coverage),
    "integrity_root_sha256": sha(integrity),
    "state_candidate_review": str(review.resolve()),
    "state_candidate_review_sha256": sha(review),
    "pre_state_sha256": review_value["pre_state_sha256"],
    "candidate_state_sha256": review_value["candidate_state_sha256"],
    "exact_state_diff": review_value["exact_state_diff"],
    "validation_result": review_value["validation_result"],
    "source_pool_tier_relaxation_accepted": True,
    "repository_heads": expected_heads,
}
for key, expected_value in expected.items():
    if value[key] != expected_value:
        raise SystemExit(
            f"ERROR: existing combined receipt field differs from reviewed inputs: {key}"
        )
print(value["pre_state_sha256"], value["candidate_state_sha256"])
PY
}

collect() {
    verify_integrity
    if [[ -f "$EVIDENCE" ]]; then
        validate_candidate
        stage_state_review
        printf 'Existing E8 v4 candidate evidence is complete: %s\n' "$EVIDENCE"
        return
    fi
    [[ ! -e "$CANDIDATE_DIR" ]] ||
        fail "candidate directory exists without valid evidence: $CANDIDATE_DIR"
    PYTHONOPTIMIZE=0 "$PYTHON" "$RUNNER" --collect-candidate --output-dir "$CANDIDATE_DIR"
    validate_candidate
    stage_state_review
    printf 'E8 v4 candidate evidence collected: %s\n' "$EVIDENCE"
}

validate_only() {
    verify_integrity
    validate_candidate
    validate_state_review
    local resume_state
    resume_state="$(validate_resume_state)"
    if pgrep -f '[s]cripts/autopilot/autopilot.py start|[s]cripts/autopilot/autopilot_supervisor.py' >/dev/null; then
        fail 'AutoPilot is active; final apply prerequisite is not satisfied'
    fi
    if [[ -e "$RECEIPT" ]]; then
        validate_receipt >/dev/null
    fi
    if [[ "$resume_state" == "fresh" ]]; then
        applier --validate-only "${TRANSACTION_BASE}-attempt-validate"
    fi
    printf 'E8 v4 final apply prevalidation passed; no writes, inference, stop, or state apply performed.\n'
}

mint_receipt() {
    if [[ -e "$RECEIPT" ]]; then
        validate_receipt >/dev/null
        return
    fi
    local tmp
    tmp="$(mktemp "${RECEIPT}.tmp.XXXXXX")"
    trap 'rm -f -- "$tmp"' RETURN
    PYTHONOPTIMIZE=0 "$PYTHON" - "$EVIDENCE" "$MAP" "$COVERAGE" "$INTEGRITY" "$STATE_REVIEW" "$ORCH/orchestration/autopilot_state.json" "$VALIDATOR" "$APPLIER" "$RECEIPT" "$tmp" "$TOKEN" "$ROOT" "$ORCH" "$RESEARCH" <<'PY'
import hashlib, importlib.util, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys
(
    evidence,
    mapping,
    coverage,
    integrity,
    review_path,
    state,
    validator,
    applier_path,
    output,
    tmp,
) = map(Path, sys.argv[1:11])
token, root, orch, research = sys.argv[11:]
ev = json.loads(evidence.read_text())
spec = importlib.util.spec_from_file_location("e8_v4_receipt_minter", applier_path)
if spec is None or spec.loader is None:
    raise SystemExit("ERROR: cannot import reviewed state applier")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
environment = dict(os.environ)
environment["PYTHONOPTIMIZE"] = "0"
try:
    review, review_sha256 = module.validate_state_candidate_review(
        review_path,
        state,
        evidence,
        validator,
        lambda: module.run_evidence_validator(validator, evidence, environment),
    )
except module.ApplyError as exc:
    raise SystemExit(f"ERROR: {exc}") from exc
candidate_path = Path(ev["protocol_candidate"]["path"])
candidate = json.loads(candidate_path.read_text())
payload = {
    "schema": "epyc.operator_e8_quality_baseline_context_apply.v1",
    "decision": token,
    "ratified_at": datetime.now(timezone.utc).isoformat(),
    "evidence": str(evidence.resolve()),
    "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    "protocol_candidate": str(candidate_path.resolve()),
    "protocol_candidate_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
    "protocol_id": candidate["protocol"]["protocol_id"],
    "replacement_map_sha256": hashlib.sha256(mapping.read_bytes()).hexdigest(),
    "coverage_report_sha256": hashlib.sha256(coverage.read_bytes()).hexdigest(),
    "integrity_root_sha256": hashlib.sha256(integrity.read_bytes()).hexdigest(),
    "state_candidate_review": str(review_path.resolve()),
    "state_candidate_review_sha256": review_sha256,
    "pre_state_sha256": review["pre_state_sha256"],
    "candidate_state_sha256": review["candidate_state_sha256"],
    "exact_state_diff": review["exact_state_diff"],
    "validation_result": review["validation_result"],
    "source_pool_tier_relaxation_accepted": True,
    "repository_heads": {
        name: subprocess.check_output(["git", "-C", path, "rev-parse", "HEAD"], text=True).strip()
        for name, path in {"epyc_root": root, "epyc_orchestrator": orch, "epyc_inference_research": research}.items()
    },
}
with tmp.open("x") as handle:
    handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    handle.flush()
    os.fchmod(handle.fileno(), 0o600)
    os.fsync(handle.fileno())
try:
    module.verify_state_review_pin(review_path, review_sha256)
except module.ApplyError as exc:
    raise SystemExit(f"ERROR: {exc}") from exc
os.link(tmp, output)
directory_fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
try:
    os.fsync(directory_fd)
finally:
    os.close(directory_fd)
PY
    rm -f -- "$tmp"
    trap - RETURN
}

apply_final() {
    validate_only
    mint_receipt
    local transaction state attempt
    for transaction in "${TRANSACTION_BASE}"-attempt-*; do
        [[ -d "$transaction" ]] || continue
        state="$(jq -er '.state' "$transaction/transaction.json")"
        if [[ "$state" == "committed" ]]; then
            applier --recover "$transaction"
            printf 'E8 v4 state apply already committed and attested.\n'
            return
        fi
        if [[ "$state" != "rolled_back" ]]; then
            applier --recover "$transaction"
        fi
    done
    attempt=1
    while [[ -e "${TRANSACTION_BASE}-attempt-${attempt}" ]]; do
        attempt=$((attempt + 1))
    done
    applier --attest "${TRANSACTION_BASE}-attempt-${attempt}"
    printf 'E8 v4 evidence-bound state apply completed: %s\n' "$ATTESTATION"
}

case "${1:-}" in
    --collect)
        [[ $# -eq 1 ]] || fail 'usage: --collect|--validate-only|--attest TOKEN'
        collect
        ;;
    --validate-only)
        [[ $# -eq 1 ]] || fail 'usage: --collect|--validate-only|--attest TOKEN'
        validate_only
        ;;
    --attest)
        [[ $# -eq 2 && "$2" == "$TOKEN" ]] ||
            fail "usage: --attest $TOKEN"
        apply_final
        ;;
    *) fail 'usage: --collect|--validate-only|--attest TOKEN' ;;
esac
