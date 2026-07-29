#!/bin/bash
# Human-only superseding authorization for the final E8 c1 retry. This script never runs inference.
set -euo pipefail
export PATH="/usr/bin:/bin"

SCRIPT_PATH="$(realpath -e -- "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
DEFAULT_ROOT="$(realpath -e -- "$SCRIPT_DIR/../..")"
TEST_MODE="${E8_C1_SUPERSEDING_TEST_MODE:-0}"
CANONICAL_ROOT="/mnt/raid0/llm/epyc-root"
CANONICAL_EVIDENCE="$CANONICAL_ROOT/artifacts/operator/e8_quality_baseline_v5_partial_r2_race_retry_20260728T202306Z"
ROOT="$DEFAULT_ROOT"
EVIDENCE="$CANONICAL_EVIDENCE"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
# The ratifier needs only the stdlib. Do not execute an interpreter reachable
# through the mutable orchestrator worktree while asserting no side effects.
PYTHON="/usr/bin/python3"
TRUST_LOCK="/run/lock/epyc-measurement-trust-boundary.lock"

if [[ "$TEST_MODE" == "1" ]]; then
    ROOT="${EPYC_ROOT:-$DEFAULT_ROOT}"
    EVIDENCE="${E8_C1_SUPERSEDING_EVIDENCE:-$CANONICAL_EVIDENCE}"
    ORCH="${EPYC_ORCHESTRATOR:-$ORCH}"
    PYTHON="${E8_C1_SUPERSEDING_PYTHON:-$PYTHON}"
    TRUST_LOCK="${E8_C1_SUPERSEDING_TRUST_LOCK:-$TRUST_LOCK}"
    # Test overrides must never be able to mint a receipt at a canonical path.
    [[ "$ROOT" != "$CANONICAL_ROOT" && "$EVIDENCE" != "$CANONICAL_EVIDENCE" ]] ||
        { printf 'ERROR: test mode refuses canonical root or evidence namespace.\n' >&2; exit 1; }
fi

RECEIPT="$ROOT/artifacts/operator/ratify_e8_final_c1_retry_superseding_20260729.json"
RECEIPT_PARENT="$(dirname -- "$RECEIPT")"
TOKEN="RATIFY-E8-FINAL-C1-RETRY-SUPERSEDING-20260729"
SUPERSEDED_RECEIPT="$ROOT/artifacts/operator/ratify_e8_final_c1_retry_amendment_20260728.json"
EXPECTED_SUPERSEDED_RECEIPT_SHA256="51aef2bd0431c8df5050f7985422d9712fc2d1494cfed1d7a3b1a54e5cab121e"
EXPECTED_SUPERSEDED_SCHEMA="epyc.operator_e8_quality_final_c1_retry_amendment.v1"
EXPECTED_SUPERSEDED_ATTESTATION="RATIFY-E8-FINAL-C1-RETRY-20260728"
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

# These reviewed pins bind the final-c1 runner, validator, wrapper, and state
# appliers. A human token must never authorize a different instrument.
EXPECTED_ORCH_COMMIT="243b56e9fa0f0f652d400c2716470b21158c7ae7"
EXPECTED_ORCH_TREE="95c5396e68eff5fb1624b9a0103131b3474d582a"
RUNNER_REL="scripts/benchmark/final_c1_retry.py"
EXPECTED_RUNNER_SHA256="b215e0aa34357224302543c2b49a5cf8e07a25d2d4dd28df5121131c63cef62b"
VALIDATOR_REL="scripts/benchmark/final_c1_validator.py"
EXPECTED_VALIDATOR_SHA256="b82c49cfa362d75496d5e925d58ae5b11d1d33c3d9d14a6f7f796a6c6bf4e977"
WRAPPER_REL="scripts/benchmark/operator_candidates/ratify_and_apply_e8_quality_baseline_v5.sh"
EXPECTED_WRAPPER_SHA256="fca5b8b0e663205e3525098e3997fec76b22533ef8dd7175745acc3e4fc1753c"
APPLIER_ADAPTER_REL="scripts/benchmark/operator_candidates/apply_e8_quality_baseline_state_v5_candidate.py"
EXPECTED_APPLIER_ADAPTER_SHA256="ab8ed499c98eedfb961f790ede2596649d8f6080317145f3b8203ab871080309"
CANONICAL_APPLIER_REL="artifacts/operator/apply_e8_quality_baseline_state.py"
EXPECTED_CANONICAL_APPLIER_SHA256="f1e0c0a88edaea5a66dda34ec9a938f8a20daa17491263a44ffff179623d3d61"

if [[ "$TEST_MODE" == "1" ]]; then
    EXPECTED_SUPERSEDED_RECEIPT_SHA256="${E8_C1_SUPERSEDING_EXPECTED_SUPERSEDED_RECEIPT_SHA256:-$EXPECTED_SUPERSEDED_RECEIPT_SHA256}"
    EXPECTED_PLAN_SHA256="${E8_C1_SUPERSEDING_EXPECTED_PLAN_SHA256:-$EXPECTED_PLAN_SHA256}"
    EXPECTED_PROPOSAL_SHA256="${E8_C1_SUPERSEDING_EXPECTED_PROPOSAL_SHA256:-$EXPECTED_PROPOSAL_SHA256}"
    EXPECTED_FAILURES_SHA256="${E8_C1_SUPERSEDING_EXPECTED_FAILURES_SHA256:-$EXPECTED_FAILURES_SHA256}"
    EXPECTED_PLAN_TREE_SHA256="${E8_C1_SUPERSEDING_EXPECTED_PLAN_TREE_SHA256:-$EXPECTED_PLAN_TREE_SHA256}"
    EXPECTED_PROPOSAL_TREE_SHA256="${E8_C1_SUPERSEDING_EXPECTED_PROPOSAL_TREE_SHA256:-$EXPECTED_PROPOSAL_TREE_SHA256}"
    EXPECTED_SOURCE_TREE_SHA256="${E8_C1_SUPERSEDING_EXPECTED_SOURCE_TREE_SHA256:-$EXPECTED_SOURCE_TREE_SHA256}"
    EXPECTED_FAILED_SIDECARS="${E8_C1_SUPERSEDING_EXPECTED_FAILED_SIDECARS:-$EXPECTED_FAILED_SIDECARS}"
    EXPECTED_ORCH_COMMIT="${E8_C1_SUPERSEDING_EXPECTED_ORCH_COMMIT:-$EXPECTED_ORCH_COMMIT}"
    EXPECTED_ORCH_TREE="${E8_C1_SUPERSEDING_EXPECTED_ORCH_TREE:-$EXPECTED_ORCH_TREE}"
    RUNNER_REL="${E8_C1_SUPERSEDING_RUNNER_REL:-$RUNNER_REL}"
    EXPECTED_RUNNER_SHA256="${E8_C1_SUPERSEDING_EXPECTED_RUNNER_SHA256:-$EXPECTED_RUNNER_SHA256}"
    VALIDATOR_REL="${E8_C1_SUPERSEDING_VALIDATOR_REL:-$VALIDATOR_REL}"
    EXPECTED_VALIDATOR_SHA256="${E8_C1_SUPERSEDING_EXPECTED_VALIDATOR_SHA256:-$EXPECTED_VALIDATOR_SHA256}"
    WRAPPER_REL="${E8_C1_SUPERSEDING_WRAPPER_REL:-$WRAPPER_REL}"
    EXPECTED_WRAPPER_SHA256="${E8_C1_SUPERSEDING_EXPECTED_WRAPPER_SHA256:-$EXPECTED_WRAPPER_SHA256}"
    APPLIER_ADAPTER_REL="${E8_C1_SUPERSEDING_APPLIER_ADAPTER_REL:-$APPLIER_ADAPTER_REL}"
    EXPECTED_APPLIER_ADAPTER_SHA256="${E8_C1_SUPERSEDING_EXPECTED_APPLIER_ADAPTER_SHA256:-$EXPECTED_APPLIER_ADAPTER_SHA256}"
    CANONICAL_APPLIER_REL="${E8_C1_SUPERSEDING_CANONICAL_APPLIER_REL:-$CANONICAL_APPLIER_REL}"
    EXPECTED_CANONICAL_APPLIER_SHA256="${E8_C1_SUPERSEDING_EXPECTED_CANONICAL_APPLIER_SHA256:-$EXPECTED_CANONICAL_APPLIER_SHA256}"
fi

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
sha256() { sha256sum -- "$1" | awk '{print $1}'; }
require_hash() { [[ "$(sha256 "$2")" == "$1" ]] || fail "SHA-256 mismatch for $2"; }
require_pin() { [[ "$1" =~ ^[0-9a-f]{40}$ || "$1" =~ ^[0-9a-f]{64}$ ]] || fail "unresolved or malformed instrument pin"; }
require_relpath() { [[ "$1" != /* && "$1" != *".."* && "$1" != __* ]] || fail "unresolved or unsafe instrument path"; }

acquire_trust_boundary_lock() {
    "$PYTHON" - "$TRUST_LOCK" <<'PY'
import os
import stat
import sys

path = sys.argv[1]
parent = os.path.dirname(path)
if not os.path.isabs(path) or os.path.realpath(parent) != parent:
    raise SystemExit(f"trust-boundary lock parent is not an exact path: {parent}")
fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o660)
try:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        raise SystemExit(f"trust-boundary lock is not a regular file: {path}")
    os.fsync(fd)
finally:
    os.close(fd)
parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
try:
    os.fsync(parent_fd)
finally:
    os.close(parent_fd)
PY
    exec 8<>"$TRUST_LOCK"
    /usr/bin/flock -n 8 ||
        fail "measurement trust-boundary lock is already held: $TRUST_LOCK"
    "$PYTHON" - "$TRUST_LOCK" "/proc/$$/fd/8" <<'PY'
import os
import stat
import sys

path, held_path = sys.argv[1:]
named = os.lstat(path)
held = os.stat(held_path)
if stat.S_ISLNK(named.st_mode) or not stat.S_ISREG(named.st_mode):
    raise SystemExit(f"trust-boundary lock path is not a regular file: {path}")
if (named.st_dev, named.st_ino) != (held.st_dev, held.st_ino):
    raise SystemExit("held trust-boundary lock inode differs from its canonical path")
PY
    if [[ "$TEST_MODE" == 1 && "${E8_C1_SUPERSEDING_TEST_HOLD_TRUST_LOCK_SECONDS:-0}" != 0 ]]; then
        [[ "${E8_C1_SUPERSEDING_TEST_HOLD_TRUST_LOCK_SECONDS}" =~ ^[0-9]+([.][0-9]+)?$ ]] ||
            fail "invalid test-only trust-lock hold duration"
        /usr/bin/sleep "${E8_C1_SUPERSEDING_TEST_HOLD_TRUST_LOCK_SECONDS}"
    fi
}

verify_canonical_paths() {
    local production=0
    [[ "$TEST_MODE" == 1 ]] || production=1
    "$PYTHON" - "$SCRIPT_PATH" "$ROOT" "$EVIDENCE" "$RECEIPT_PARENT" "$SUPERSEDED_RECEIPT" "$TRUST_LOCK" \
        "$CANONICAL_ROOT" "$CANONICAL_EVIDENCE" "$production" <<'PY'
import os
import stat
import sys
from pathlib import Path

script, root, evidence, receipt_parent, superseded_receipt, trust_lock, canonical_root, canonical_evidence, production = sys.argv[1:]

def reject_alias(label: str, value: str, kind: str) -> None:
    path = Path(value)
    if not path.is_absolute() or os.path.realpath(value) != value:
        raise SystemExit(f"{label} is not an exact resolved path: {value}")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        mode = os.lstat(current).st_mode
        if stat.S_ISLNK(mode):
            raise SystemExit(f"{label} contains a symlink component: {current}")
    mode = os.lstat(path).st_mode
    if kind == "file" and not stat.S_ISREG(mode):
        raise SystemExit(f"{label} is not a regular file: {value}")
    if kind == "dir" and not stat.S_ISDIR(mode):
        raise SystemExit(f"{label} is not a directory: {value}")

reject_alias("script", script, "file")
reject_alias("root", root, "dir")
reject_alias("evidence", evidence, "dir")
reject_alias("receipt parent", receipt_parent, "dir")
reject_alias("superseded receipt", superseded_receipt, "file")
reject_alias("trust-boundary lock", trust_lock, "file")
if production == "1":
    expected_script = f"{canonical_root}/artifacts/operator/ratify_e8_final_c1_retry_superseding_20260729.sh"
    expected_parent = f"{canonical_root}/artifacts/operator"
    expected_superseded_receipt = f"{canonical_root}/artifacts/operator/ratify_e8_final_c1_retry_amendment_20260728.json"
    expected = {"script": expected_script, "root": canonical_root,
                "evidence": canonical_evidence, "receipt parent": expected_parent,
                "superseded receipt": expected_superseded_receipt,
                "trust-boundary lock": "/run/lock/epyc-measurement-trust-boundary.lock"}
    actual = {"script": script, "root": root, "evidence": evidence,
              "receipt parent": receipt_parent, "superseded receipt": superseded_receipt,
              "trust-boundary lock": trust_lock}
    for label, wanted in expected.items():
        if actual[label] != wanted:
            raise SystemExit(f"production {label} differs from canonical path: {actual[label]}")
PY
}

verify_superseded_receipt() {
    [[ -f "$SUPERSEDED_RECEIPT" ]] || fail "superseded final-c1 receipt is absent: $SUPERSEDED_RECEIPT"
    require_hash "$EXPECTED_SUPERSEDED_RECEIPT_SHA256" "$SUPERSEDED_RECEIPT"
    "$PYTHON" - "$SUPERSEDED_RECEIPT" "$EXPECTED_SUPERSEDED_SCHEMA" "$EXPECTED_SUPERSEDED_ATTESTATION" <<'PY'
import json
import sys
from pathlib import Path

receipt = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
schema, attestation = sys.argv[2:]
if receipt.get("schema") != schema:
    raise SystemExit("superseded receipt schema differs")
if receipt.get("human_attestation") != attestation:
    raise SystemExit("superseded receipt attestation differs")
if receipt.get("status") != "ratified":
    raise SystemExit("superseded receipt is not ratified")
PY
}

verify_instrument_pins() {
    require_pin "$EXPECTED_ORCH_COMMIT"
    require_pin "$EXPECTED_ORCH_TREE"
    require_pin "$EXPECTED_RUNNER_SHA256"
    require_pin "$EXPECTED_VALIDATOR_SHA256"
    require_pin "$EXPECTED_WRAPPER_SHA256"
    require_pin "$EXPECTED_APPLIER_ADAPTER_SHA256"
    require_pin "$EXPECTED_CANONICAL_APPLIER_SHA256"
    require_relpath "$RUNNER_REL"
    require_relpath "$VALIDATOR_REL"
    require_relpath "$WRAPPER_REL"
    require_relpath "$APPLIER_ADAPTER_REL"
    require_relpath "$CANONICAL_APPLIER_REL"
    [[ -x "$PYTHON" ]] || fail "required trusted interpreter is unavailable: $PYTHON"
    [[ -d "$ORCH/.git" || -f "$ORCH/.git" ]] || fail "orchestrator is not a Git worktree: $ORCH"
    git -C "$ORCH" cat-file -e "${EXPECTED_ORCH_COMMIT}^{commit}" || fail "pinned orchestrator commit is unavailable"
    [[ "$(git -C "$ORCH" rev-parse "${EXPECTED_ORCH_COMMIT}^{tree}")" == "$EXPECTED_ORCH_TREE" ]] ||
        fail "pinned orchestrator tree differs"
    [[ "$(git -C "$ORCH" show "${EXPECTED_ORCH_COMMIT}:${RUNNER_REL}" | sha256sum | awk '{print $1}')" == "$EXPECTED_RUNNER_SHA256" ]] ||
        fail "pinned final-c1 runner hash differs"
    [[ "$(git -C "$ORCH" show "${EXPECTED_ORCH_COMMIT}:${VALIDATOR_REL}" | sha256sum | awk '{print $1}')" == "$EXPECTED_VALIDATOR_SHA256" ]] ||
        fail "pinned final-c1 validator hash differs"
    [[ "$(git -C "$ORCH" show "${EXPECTED_ORCH_COMMIT}:${WRAPPER_REL}" | sha256sum | awk '{print $1}')" == "$EXPECTED_WRAPPER_SHA256" ]] ||
        fail "pinned E8-v5 wrapper hash differs"
    [[ "$(git -C "$ORCH" show "${EXPECTED_ORCH_COMMIT}:${APPLIER_ADAPTER_REL}" | sha256sum | awk '{print $1}')" == "$EXPECTED_APPLIER_ADAPTER_SHA256" ]] ||
        fail "pinned E8-v5 applier adapter hash differs"
    require_hash "$EXPECTED_CANONICAL_APPLIER_SHA256" "$ROOT/$CANONICAL_APPLIER_REL"
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
        fail "production superseding ratifier must run from the canonical root: $CANONICAL_ROOT"
    [[ -d "$ROOT/.git" || -f "$ROOT/.git" ]] || fail "root is not a Git worktree: $ROOT"
    [[ ! -e "$RECEIPT" ]] || fail "final-c1 superseding ratifier receipt already exists: $RECEIPT"
    verify_canonical_paths
    verify_instrument_pins
    verify_failed_namespace
    verify_superseded_receipt
}

write_and_publish_receipt() {
    local test_hold="${E8_C1_SUPERSEDING_TEST_HOLD_AFTER_CANDIDATE_SECONDS:-0}"
    local test_decoy="${E8_C1_SUPERSEDING_TEST_REPLACE_CANDIDATE_WITH_SYMLINK:-0}"
    [[ "$TEST_MODE" == 1 ]] || { test_hold=0; test_decoy=0; }
    [[ "$test_hold" =~ ^[0-9]+([.][0-9]+)?$ ]] || fail "invalid test-only receipt hold duration"
    "$PYTHON" - "$RECEIPT_PARENT" "$RECEIPT" "$EVIDENCE" "$EXPECTED_PLAN_SHA256" "$EXPECTED_PROPOSAL_SHA256" \
        "$EXPECTED_FAILURES_SHA256" "$EXPECTED_PLAN_TREE_SHA256" "$EXPECTED_PROPOSAL_TREE_SHA256" \
        "$EXPECTED_SOURCE_TREE_SHA256" "$EXPECTED_FAILED_SIDECARS" "$ORCH" "$EXPECTED_ORCH_COMMIT" "$EXPECTED_ORCH_TREE" \
        "$RUNNER_REL" "$EXPECTED_RUNNER_SHA256" "$VALIDATOR_REL" "$EXPECTED_VALIDATOR_SHA256" \
        "$WRAPPER_REL" "$EXPECTED_WRAPPER_SHA256" "$APPLIER_ADAPTER_REL" "$EXPECTED_APPLIER_ADAPTER_SHA256" \
        "$CANONICAL_APPLIER_REL" "$EXPECTED_CANONICAL_APPLIER_SHA256" \
        "$SUPERSEDED_RECEIPT" "$EXPECTED_SUPERSEDED_RECEIPT_SHA256" "$EXPECTED_SUPERSEDED_SCHEMA" "$EXPECTED_SUPERSEDED_ATTESTATION" \
        "$SCRIPT_PATH" "$test_hold" "$test_decoy" <<'PY'
import ctypes
import errno
import hashlib
import json
import os
import stat
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

(candidate_dir, receipt, evidence, plan_hash, proposal_hash, failures_hash, plan_tree, proposal_tree,
 source_tree, sidecars, orch, commit, tree, runner, runner_hash, validator, validator_hash,
 wrapper, wrapper_hash, applier_adapter, applier_adapter_hash,
 canonical_applier, canonical_applier_hash, superseded_receipt, superseded_receipt_hash,
 superseded_schema, superseded_attestation, script, test_hold, test_decoy) = sys.argv[1:]
payload = {
    "schema": "epyc.operator_e8_quality_final_c1_retry_superseding.v1",
    "status": "ratified",
    "protocol_id": "e8_quality_full_pool_tier_baseline.v5/final-c1-retry",
    "ratified_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    "human_attestation": "RATIFY-E8-FINAL-C1-RETRY-SUPERSEDING-20260729",
    "supersedes": {
        "path": superseded_receipt,
        "sha256": superseded_receipt_hash,
        "schema": superseded_schema,
        "human_attestation": superseded_attestation,
    },
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
        "wrapper": {"path": wrapper, "sha256": wrapper_hash},
        "applier_adapter": {"path": applier_adapter, "sha256": applier_adapter_hash},
        "canonical_applier": {
            "path": canonical_applier,
            "sha256": canonical_applier_hash,
        },
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
data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
decoded = json.loads(data)
if decoded["authorization"] != payload["authorization"] or decoded["non_authorizations"] != payload["non_authorizations"]:
    raise SystemExit("receipt schema round-trip differs")

nofollow = getattr(os, "O_NOFOLLOW", 0)
if not hasattr(os, "O_TMPFILE"):
    raise SystemExit("O_TMPFILE is unavailable; fail closed")
candidate_dirfd = os.open(candidate_dir, os.O_RDONLY | os.O_DIRECTORY | nofollow)
parent, name = os.path.split(receipt)
dirfd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | nofollow)
fd = os.open(candidate_dir, os.O_RDWR | os.O_TMPFILE, 0o600)
published = False
decoy = os.path.join(candidate_dir, ".e8-final-c1-receipt.candidate")
try:
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 0:
        raise SystemExit("anonymous receipt inode is not an unlinked regular file")
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        view = view[written:]
    os.fsync(fd)
    written_state = os.fstat(fd)
    if (written_state.st_dev, written_state.st_ino, written_state.st_nlink) != (before.st_dev, before.st_ino, 0):
        raise SystemExit("anonymous receipt inode changed while writing")
    os.lseek(fd, 0, os.SEEK_SET)
    held_data = os.read(fd, len(data) + 1)
    if held_data != data:
        raise SystemExit("held receipt bytes differ before publication")
    if test_decoy == "1":
        os.symlink("/etc/passwd", decoy)
    if float(test_hold):
        time.sleep(float(test_hold))

    libc = ctypes.CDLL(None, use_errno=True)
    linkat = libc.linkat
    linkat.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    linkat.restype = ctypes.c_int
    at_empty_path = 0x1000
    if linkat(fd, b"", dirfd, os.fsencode(name), at_empty_path) != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise SystemExit(f"receipt destination already exists: {receipt}")
        raise OSError(error, os.strerror(error), receipt)
    published = True
    after = os.fstat(fd)
    final = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
    os.lseek(fd, 0, os.SEEK_SET)
    final_data = os.read(fd, after.st_size + 1)
    if (after.st_dev, after.st_ino, after.st_nlink) != (before.st_dev, before.st_ino, 1):
        raise SystemExit("published receipt inode or link count differs")
    if not stat.S_ISREG(final.st_mode) or (final.st_dev, final.st_ino) != (after.st_dev, after.st_ino):
        raise SystemExit("published receipt does not name the held candidate inode")
    if final_data != data:
        raise SystemExit("held receipt content changed during publication")
    os.fsync(dirfd)
except BaseException:
    if published:
        try:
            final = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
            held = os.fstat(fd)
            if (final.st_dev, final.st_ino) == (held.st_dev, held.st_ino):
                os.unlink(name, dir_fd=dirfd)
                os.fsync(dirfd)
        except (FileNotFoundError, OSError):
            pass
    raise
finally:
    try:
        os.unlink(decoy)
    except FileNotFoundError:
        pass
    os.close(candidate_dirfd)
    os.close(dirfd)
    os.close(fd)
PY
}

plan() {
    verify_preflight
    printf '%s\n' \
        'E8 final-c1 retry superseding ratifier is preflight-valid.' \
        'Authorization is limited to sequential ordinals 97 then 279 at the unchanged 300s timeout.' \
        'The ratifier starts no inference and changes no state or lineup.'
}

attest() {
    verify_preflight
    verify_preflight
    # Detect any evidence mutation which occurred while this receipt was being
    # constructed. The namespace is read-only evidence; publication is denied
    # if its full canonical tree no longer agrees with the preflight binding.
    verify_failed_namespace
    # One trusted process creates an anonymous inode, writes and validates the
    # receipt, then publishes that held inode with linkat(AT_EMPTY_PATH).
    write_and_publish_receipt
    printf 'E8 final-c1 retry superseding ratifier receipt created:\n%s\n' "$RECEIPT"
    sha256sum -- "$RECEIPT"
}

acquire_trust_boundary_lock

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
