#!/bin/bash
# Human-only authorization for the final E8 c1 retry. This script never runs inference.
set -euo pipefail

SCRIPT_PATH="$(realpath -e -- "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
DEFAULT_ROOT="$(realpath -e -- "$SCRIPT_DIR/../..")"
TEST_MODE="${E8_C1_AMENDMENT_TEST_MODE:-0}"
CANONICAL_ROOT="/mnt/raid0/llm/epyc-root"
CANONICAL_EVIDENCE="$CANONICAL_ROOT/artifacts/operator/e8_quality_baseline_v5_partial_r2_race_retry_20260728T202306Z"
ROOT="$DEFAULT_ROOT"
EVIDENCE="$CANONICAL_EVIDENCE"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
# The ratifier needs only the stdlib. Do not execute an interpreter reachable
# through the mutable orchestrator worktree while asserting no side effects.
PYTHON="/usr/bin/python3"

if [[ "$TEST_MODE" == "1" ]]; then
    ROOT="${EPYC_ROOT:-$DEFAULT_ROOT}"
    EVIDENCE="${E8_C1_EVIDENCE:-$CANONICAL_EVIDENCE}"
    ORCH="${EPYC_ORCHESTRATOR:-$ORCH}"
    PYTHON="${E8_C1_PYTHON:-$PYTHON}"
    # Test overrides must never be able to mint a receipt at a canonical path.
    [[ "$ROOT" != "$CANONICAL_ROOT" && "$EVIDENCE" != "$CANONICAL_EVIDENCE" ]] ||
        { printf 'ERROR: test mode refuses canonical root or evidence namespace.\n' >&2; exit 1; }
fi

RECEIPT="$ROOT/artifacts/operator/ratify_e8_final_c1_retry_amendment_20260728.json"
LOCK="$ROOT/artifacts/operator/.e8_final_c1_retry_amendment.lock"
TOKEN="RATIFY-E8-FINAL-C1-RETRY-20260728"
PLAN_REL="partial_r2_plan.json"
PROPOSAL_REL="recovery_proposal.json"
FAILURES_REL="generation_failed_attempts.T2.r2.jsonl"

# The three evidence digests bind the immutable failed race namespace. The
# source-tree values are recorded by the failed plan/proposal themselves.
EXPECTED_PLAN_SHA256="81198338c01a8532e6134333e9fdcca33a9061c54eadbfaed5745c8b032184fc"
EXPECTED_PROPOSAL_SHA256="3b15e3ce5025cd758422f468fdf029269bf9a2fed4b7132798a99f2d2925eeb8"
EXPECTED_FAILURES_SHA256="3bf22a12c91a3639992d7db782664a4ed1f580147bf7aacd2cfdb9f69d748385"
EXPECTED_PLAN_TREE_SHA256="92241f793c254dcf71dfca452f8cc50416d2fb1410698584b514ff3c14c5571a"
EXPECTED_PROPOSAL_TREE_SHA256="b821900094e866027d9a1561b21d91eb09f6a02ff92b8d91b133df57c7d5ce2d"
EXPECTED_SOURCE_TREE_SHA256="7f4eb0d380765914c26c887af599df7979152248ef57b5cdd9b824614eee7514"
EXPECTED_FAILED_SIDECARS="97:a550c07752f8dedc0fdf5c4582b587c90f3b624405ed1454f628e523c100cae9,279:a41be1b012bb33475a5d8c9fd2e810c5b6dab651d123e3006f07cfc3f7fc835e"

# These are deliberately unresolved until the owning orchestrator integration
# supplies its reviewed final-c1 runner and validator pins. A human token must
# never authorize an unpinned instrument.
EXPECTED_ORCH_COMMIT="__ORCHESTRATOR_COMMIT_TO_BE_SUPPLIED__"
EXPECTED_ORCH_TREE="__ORCHESTRATOR_TREE_TO_BE_SUPPLIED__"
RUNNER_REL="__FINAL_C1_RUNNER_PATH_TO_BE_SUPPLIED__"
EXPECTED_RUNNER_SHA256="__FINAL_C1_RUNNER_SHA256_TO_BE_SUPPLIED__"
VALIDATOR_REL="__FINAL_C1_VALIDATOR_PATH_TO_BE_SUPPLIED__"
EXPECTED_VALIDATOR_SHA256="__FINAL_C1_VALIDATOR_SHA256_TO_BE_SUPPLIED__"

if [[ "$TEST_MODE" == "1" ]]; then
    EXPECTED_PLAN_SHA256="${E8_C1_EXPECTED_PLAN_SHA256:-$EXPECTED_PLAN_SHA256}"
    EXPECTED_PROPOSAL_SHA256="${E8_C1_EXPECTED_PROPOSAL_SHA256:-$EXPECTED_PROPOSAL_SHA256}"
    EXPECTED_FAILURES_SHA256="${E8_C1_EXPECTED_FAILURES_SHA256:-$EXPECTED_FAILURES_SHA256}"
    EXPECTED_PLAN_TREE_SHA256="${E8_C1_EXPECTED_PLAN_TREE_SHA256:-$EXPECTED_PLAN_TREE_SHA256}"
    EXPECTED_PROPOSAL_TREE_SHA256="${E8_C1_EXPECTED_PROPOSAL_TREE_SHA256:-$EXPECTED_PROPOSAL_TREE_SHA256}"
    EXPECTED_SOURCE_TREE_SHA256="${E8_C1_EXPECTED_SOURCE_TREE_SHA256:-$EXPECTED_SOURCE_TREE_SHA256}"
    EXPECTED_FAILED_SIDECARS="${E8_C1_EXPECTED_FAILED_SIDECARS:-$EXPECTED_FAILED_SIDECARS}"
    EXPECTED_ORCH_COMMIT="${E8_C1_EXPECTED_ORCH_COMMIT:-$EXPECTED_ORCH_COMMIT}"
    EXPECTED_ORCH_TREE="${E8_C1_EXPECTED_ORCH_TREE:-$EXPECTED_ORCH_TREE}"
    RUNNER_REL="${E8_C1_RUNNER_REL:-$RUNNER_REL}"
    EXPECTED_RUNNER_SHA256="${E8_C1_EXPECTED_RUNNER_SHA256:-$EXPECTED_RUNNER_SHA256}"
    VALIDATOR_REL="${E8_C1_VALIDATOR_REL:-$VALIDATOR_REL}"
    EXPECTED_VALIDATOR_SHA256="${E8_C1_EXPECTED_VALIDATOR_SHA256:-$EXPECTED_VALIDATOR_SHA256}"
fi

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
sha256() { sha256sum -- "$1" | awk '{print $1}'; }
require_hash() { [[ "$(sha256 "$2")" == "$1" ]] || fail "SHA-256 mismatch for $2"; }
require_pin() { [[ "$1" =~ ^[0-9a-f]{40}$ || "$1" =~ ^[0-9a-f]{64}$ ]] || fail "unresolved or malformed instrument pin"; }
require_relpath() { [[ "$1" != /* && "$1" != *".."* && "$1" != __* ]] || fail "unresolved or unsafe instrument path"; }

verify_instrument_pins() {
    require_pin "$EXPECTED_ORCH_COMMIT"
    require_pin "$EXPECTED_ORCH_TREE"
    require_pin "$EXPECTED_RUNNER_SHA256"
    require_pin "$EXPECTED_VALIDATOR_SHA256"
    require_relpath "$RUNNER_REL"
    require_relpath "$VALIDATOR_REL"
    [[ -x "$PYTHON" ]] || fail "required trusted interpreter is unavailable: $PYTHON"
    [[ -d "$ORCH/.git" || -f "$ORCH/.git" ]] || fail "orchestrator is not a Git worktree: $ORCH"
    git -C "$ORCH" cat-file -e "${EXPECTED_ORCH_COMMIT}^{commit}" || fail "pinned orchestrator commit is unavailable"
    [[ "$(git -C "$ORCH" rev-parse "${EXPECTED_ORCH_COMMIT}^{tree}")" == "$EXPECTED_ORCH_TREE" ]] ||
        fail "pinned orchestrator tree differs"
    [[ "$(git -C "$ORCH" show "${EXPECTED_ORCH_COMMIT}:${RUNNER_REL}" | sha256sum | awk '{print $1}')" == "$EXPECTED_RUNNER_SHA256" ]] ||
        fail "pinned final-c1 runner hash differs"
    [[ "$(git -C "$ORCH" show "${EXPECTED_ORCH_COMMIT}:${VALIDATOR_REL}" | sha256sum | awk '{print $1}')" == "$EXPECTED_VALIDATOR_SHA256" ]] ||
        fail "pinned final-c1 validator hash differs"
}

verify_failed_namespace() {
    [[ -d "$EVIDENCE" ]] || fail "failed race evidence namespace is absent: $EVIDENCE"
    [[ -f "$EVIDENCE/$PLAN_REL" && -f "$EVIDENCE/$PROPOSAL_REL" && -f "$EVIDENCE/$FAILURES_REL" ]] ||
        fail "failed race evidence namespace is incomplete"
    require_hash "$EXPECTED_PLAN_SHA256" "$EVIDENCE/$PLAN_REL"
    require_hash "$EXPECTED_PROPOSAL_SHA256" "$EVIDENCE/$PROPOSAL_REL"
    require_hash "$EXPECTED_FAILURES_SHA256" "$EVIDENCE/$FAILURES_REL"
    "$PYTHON" - "$EVIDENCE" "$EVIDENCE/$PLAN_REL" "$EVIDENCE/$PROPOSAL_REL" "$EVIDENCE/$FAILURES_REL" \
        "$EXPECTED_PLAN_TREE_SHA256" "$EXPECTED_PROPOSAL_TREE_SHA256" "$EXPECTED_SOURCE_TREE_SHA256" \
        "$EXPECTED_FAILED_SIDECARS" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
plan = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
proposal = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
failure_rows = [json.loads(line) for line in Path(sys.argv[4]).read_text(encoding="utf-8").splitlines() if line]
expected_plan_tree, expected_proposal_tree, expected_source_tree, expected_sidecars = sys.argv[5:]
expected = {int(pair.split(":", 1)[0]): pair.split(":", 1)[1] for pair in expected_sidecars.split(",")}
source_hashes = {}
for path in sorted(root.rglob("*")):
    if path.is_symlink():
        raise SystemExit(f"failed-race source tree contains symlink: {path}")
    if path.is_file():
        source_hashes[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif not path.is_dir():
        raise SystemExit(f"failed-race source tree contains non-regular entry: {path}")
source_tree = hashlib.sha256(json.dumps(source_hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
if source_tree != expected_source_tree:
    raise SystemExit("failed-race canonical source tree differs")
if plan.get("schema") != "epyc.e8_quality_v5_partial_r2_race_retry_plan.v1":
    raise SystemExit("unexpected failed-race plan schema")
if plan.get("generation_ordinals") != [97, 203, 279] or plan.get("race_retry_ordinals") != [97, 203, 279]:
    raise SystemExit("failed-race plan ordinal set differs")
if plan.get("generation_concurrency") != 3 or plan.get("failed_source_tree_sha256") != expected_plan_tree:
    raise SystemExit("failed-race plan tree or concurrency differs")
if proposal.get("schema") != "epyc.e8_quality_v5_partial_r2_race_retry_proposal.v1":
    raise SystemExit("unexpected failed-race proposal schema")
if proposal.get("output_namespace") != str(root):
    raise SystemExit("failed-race proposal namespace differs")
if proposal.get("source_tree_sha256") != expected_proposal_tree or proposal.get("generation_concurrency") != 3:
    raise SystemExit("failed-race proposal tree or concurrency differs")
if len(failure_rows) != 1 or failure_rows[0].get("disposition") != "failed_closed_no_automatic_retry":
    raise SystemExit("failed-race failure disposition differs")
actual = {row.get("ordinal"): row.get("sidecar_sha256") for row in failure_rows[0].get("failures", [])}
if actual != expected:
    raise SystemExit("failed-race timeout sidecars differ")
PY
}

verify_preflight() {
    [[ "$TEST_MODE" == "1" || "$ROOT" == "$CANONICAL_ROOT" ]] ||
        fail "production amendment must run from the canonical root: $CANONICAL_ROOT"
    [[ -d "$ROOT/.git" || -f "$ROOT/.git" ]] || fail "root is not a Git worktree: $ROOT"
    [[ ! -e "$RECEIPT" ]] || fail "final-c1 amendment receipt already exists: $RECEIPT"
    verify_instrument_pins
    verify_failed_namespace
}

write_receipt() {
    local candidate=$1
    "$PYTHON" - "$candidate" "$EVIDENCE" "$EXPECTED_PLAN_SHA256" "$EXPECTED_PROPOSAL_SHA256" \
        "$EXPECTED_FAILURES_SHA256" "$EXPECTED_PLAN_TREE_SHA256" "$EXPECTED_PROPOSAL_TREE_SHA256" \
        "$EXPECTED_SOURCE_TREE_SHA256" "$EXPECTED_FAILED_SIDECARS" "$ORCH" "$EXPECTED_ORCH_COMMIT" "$EXPECTED_ORCH_TREE" \
        "$RUNNER_REL" "$EXPECTED_RUNNER_SHA256" "$VALIDATOR_REL" "$EXPECTED_VALIDATOR_SHA256" \
        "$SCRIPT_PATH" <<'PY'
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

(out, evidence, plan_hash, proposal_hash, failures_hash, plan_tree, proposal_tree, source_tree, sidecars,
 orch, commit, tree, runner, runner_hash, validator, validator_hash, script) = sys.argv[1:]
payload = {
    "schema": "epyc.operator_e8_quality_final_c1_retry_amendment.v1",
    "status": "ratified",
    "protocol_id": "e8_quality_full_pool_tier_baseline.v5/final-c1-retry",
    "ratified_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    "human_attestation": "RATIFY-E8-FINAL-C1-RETRY-20260728",
    "amendment_script": {"path": script, "sha256": hashlib.sha256(Path(script).read_bytes()).hexdigest()},
    "failed_race_evidence": {
        "namespace": evidence,
        "canonical": True,
        "files": {"partial_r2_plan.json": plan_hash, "recovery_proposal.json": proposal_hash,
                  "generation_failed_attempts.T2.r2.jsonl": failures_hash},
        "recorded_trees": {"plan_failed_source_tree_sha256": plan_tree,
                           "proposal_source_tree_sha256": proposal_tree},
        "failed_timeout_sidecars": sidecars,
    },
    "source": {"path": evidence, "tree_sha256": source_tree},
    "instrument": {
        "repository": orch,
        "commit": commit,
        "tree": tree,
        "ratifier_interpreter": "/usr/bin/python3",
        "runner": {"path": runner, "sha256": runner_hash},
        "validator": {"path": validator, "sha256": validator_hash},
    },
    "authorization": {
        "tier": 2,
        "repetition": 2,
        "ordinals": [97, 279],
        "qids": ["leval_codeU_269", "leval_review_summ_382"],
        "order": "sequential",
        "generation_concurrency": 1,
        "request_timeout_s": 300,
        "region_claim_regions": ["q3"],
        "runtime_preconditions": ["held_q3_claim", "clean_runtime_watcher"],
        "success_disposition": "clean_rows_continue_existing_clean_500_finalizer",
        "repeated_failure_disposition": "terminal_failed_no_admission",
        "no_auto_retry": True,
        "no_timeout_increase": True,
    },
    "non_authorizations": {"no_state_write": True, "no_lineup_mutation": True,
                           "no_inference_by_ratifier": True},
}
Path(out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

durable_fsync() {
    "$PYTHON" - "$1" <<'PY'
import os
import sys

path = sys.argv[1]
fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY if os.path.isdir(path) else os.O_RDONLY)
try:
    os.fsync(fd)
finally:
    os.close(fd)
PY
}

plan() {
    verify_preflight
    printf '%s\n' \
        'E8 final-c1 retry amendment is preflight-valid.' \
        'Authorization is limited to sequential ordinals 97 then 279 at the unchanged 300s timeout.' \
        'The ratifier starts no inference and changes no state or lineup.'
}

attest() {
    verify_preflight
    mkdir -p -- "$(dirname -- "$RECEIPT")"
    exec 9>"$LOCK"
    flock -n 9 || fail "another final-c1 amendment transaction holds the canonical shared lock"
    verify_preflight
    local candidate
    candidate="$(mktemp "${RECEIPT}.candidate.XXXXXX")"
    trap 'rm -f -- "$candidate"' EXIT
    write_receipt "$candidate"
    "$PYTHON" - "$candidate" <<'PY'
import json
import sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload["authorization"]["ordinals"] == [97, 279]
assert payload["authorization"]["qids"] == ["leval_codeU_269", "leval_review_summ_382"]
assert payload["authorization"]["order"] == "sequential"
assert payload["authorization"]["generation_concurrency"] == 1
assert payload["authorization"]["request_timeout_s"] == 300
assert payload["authorization"]["success_disposition"] == "clean_rows_continue_existing_clean_500_finalizer"
assert payload["authorization"]["repeated_failure_disposition"] == "terminal_failed_no_admission"
assert payload["authorization"]["no_auto_retry"] is True
assert payload["authorization"]["no_timeout_increase"] is True
assert payload["non_authorizations"] == {"no_state_write": True, "no_lineup_mutation": True,
                                          "no_inference_by_ratifier": True}
PY
    durable_fsync "$candidate"
    # Detect any evidence mutation which occurred while this receipt was being
    # constructed. The namespace is read-only evidence; publication is denied
    # if its full canonical tree no longer agrees with the preflight binding.
    verify_failed_namespace
    # link(2) has no overwrite mode, unlike `mv -n` whose no-op may still exit
    # successfully. The candidate and final receipt are in the same directory.
    ln -- "$candidate" "$RECEIPT" || fail "receipt destination already exists: $RECEIPT"
    durable_fsync "$(dirname -- "$RECEIPT")"
    rm -f -- "$candidate"
    trap - EXIT
    printf 'E8 final-c1 retry amendment receipt created:\n%s\n' "$RECEIPT"
    sha256sum -- "$RECEIPT"
}

case "${1:-}" in
    --plan|--validate-only)
        [[ $# -eq 1 ]] || fail "usage: $0 --plan|--validate-only|--attest $TOKEN"
        plan
        ;;
    --attest)
        [[ $# -eq 2 && "$2" == "$TOKEN" ]] || fail "usage: $0 --attest $TOKEN"
        attest
        ;;
    *) fail "usage: $0 --plan|--validate-only|--attest $TOKEN" ;;
esac
