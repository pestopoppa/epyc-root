#!/bin/bash
# Human-only authorization for the final E8 c1 retry. This script never runs inference.
set -euo pipefail
export PATH="/usr/bin:/bin"

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
LOCK_HELD=0
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
EXPECTED_ORCH_COMMIT="6907582a0d67e6fded47b9350b87cb911c8d83b3"
EXPECTED_ORCH_TREE="db35e179b7b35f96d55b5ae755bdcf421dbe4d2b"
RUNNER_REL="scripts/benchmark/final_c1_retry.py"
EXPECTED_RUNNER_SHA256="0bc35b84399df7d7434de6b356f58545f28cea89bf164aaa85977d7954ce6295"
VALIDATOR_REL="scripts/benchmark/final_c1_validator.py"
EXPECTED_VALIDATOR_SHA256="b82c49cfa362d75496d5e925d58ae5b11d1d33c3d9d14a6f7f796a6c6bf4e977"

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

cleanup() {
    local status=$?
    trap - EXIT INT TERM HUP
    set +e
    [[ "$LOCK_HELD" != 1 ]] || rmdir -- "$LOCK"
    return "$status"
}

acquire_lock() {
    # mkdir(2) is an atomic no-replace operation and does not follow a symlink
    # at the target path. The private, empty directory is the shared lock.
    if ! mkdir -m 0700 -- "$LOCK"; then
        fail "canonical shared lock acquisition refused: $LOCK"
    fi
    LOCK_HELD=1
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    trap 'exit 129' HUP
    if [[ "$TEST_MODE" == 1 && "${E8_C1_TEST_HOLD_LOCK_SECONDS:-0}" != 0 ]]; then
        [[ "${E8_C1_TEST_HOLD_LOCK_SECONDS}" =~ ^[0-9]+([.][0-9]+)?$ ]] ||
            fail "invalid test-only lock hold duration"
        sleep "${E8_C1_TEST_HOLD_LOCK_SECONDS}"
    fi
}

release_lock() {
    rmdir -- "$LOCK" || fail "canonical shared lock could not be released: $LOCK"
    LOCK_HELD=0
}

verify_canonical_paths() {
    local production=0
    [[ "$TEST_MODE" == 1 ]] || production=1
    "$PYTHON" - "$SCRIPT_PATH" "$ROOT" "$EVIDENCE" "$(dirname -- "$RECEIPT")" \
        "$CANONICAL_ROOT" "$CANONICAL_EVIDENCE" "$production" <<'PY'
import os
import stat
import sys
from pathlib import Path

script, root, evidence, receipt_parent, canonical_root, canonical_evidence, production = sys.argv[1:]

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
if production == "1":
    expected_script = f"{canonical_root}/artifacts/operator/ratify_e8_final_c1_retry_amendment_20260728.sh"
    expected_parent = f"{canonical_root}/artifacts/operator"
    expected = {"script": expected_script, "root": canonical_root,
                "evidence": canonical_evidence, "receipt parent": expected_parent}
    actual = {"script": script, "root": root, "evidence": evidence,
              "receipt parent": receipt_parent}
    for label, wanted in expected.items():
        if actual[label] != wanted:
            raise SystemExit(f"production {label} differs from canonical path: {actual[label]}")
PY
}

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
    verify_canonical_paths
    verify_instrument_pins
    verify_failed_namespace
}

write_and_publish_receipt() {
    local test_hold="${E8_C1_TEST_HOLD_AFTER_CANDIDATE_SECONDS:-0}"
    local test_decoy="${E8_C1_TEST_REPLACE_CANDIDATE_WITH_SYMLINK:-0}"
    [[ "$TEST_MODE" == 1 ]] || { test_hold=0; test_decoy=0; }
    [[ "$test_hold" =~ ^[0-9]+([.][0-9]+)?$ ]] || fail "invalid test-only receipt hold duration"
    "$PYTHON" - "$LOCK" "$RECEIPT" "$EVIDENCE" "$EXPECTED_PLAN_SHA256" "$EXPECTED_PROPOSAL_SHA256" \
        "$EXPECTED_FAILURES_SHA256" "$EXPECTED_PLAN_TREE_SHA256" "$EXPECTED_PROPOSAL_TREE_SHA256" \
        "$EXPECTED_SOURCE_TREE_SHA256" "$EXPECTED_FAILED_SIDECARS" "$ORCH" "$EXPECTED_ORCH_COMMIT" "$EXPECTED_ORCH_TREE" \
        "$RUNNER_REL" "$EXPECTED_RUNNER_SHA256" "$VALIDATOR_REL" "$EXPECTED_VALIDATOR_SHA256" \
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

(lock_dir, receipt, evidence, plan_hash, proposal_hash, failures_hash, plan_tree, proposal_tree,
 source_tree, sidecars, orch, commit, tree, runner, runner_hash, validator, validator_hash,
 script, test_hold, test_decoy) = sys.argv[1:]
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
data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
decoded = json.loads(data)
if decoded["authorization"] != payload["authorization"] or decoded["non_authorizations"] != payload["non_authorizations"]:
    raise SystemExit("receipt schema round-trip differs")

nofollow = getattr(os, "O_NOFOLLOW", 0)
if not hasattr(os, "O_TMPFILE"):
    raise SystemExit("O_TMPFILE is unavailable; fail closed")
lockfd = os.open(lock_dir, os.O_RDONLY | os.O_DIRECTORY | nofollow)
parent, name = os.path.split(receipt)
dirfd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | nofollow)
fd = os.open(lock_dir, os.O_RDWR | os.O_TMPFILE, 0o600)
published = False
decoy = os.path.join(lock_dir, "receipt.candidate")
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
    os.close(lockfd)
    os.close(dirfd)
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
    acquire_lock
    verify_preflight
    # Detect any evidence mutation which occurred while this receipt was being
    # constructed. The namespace is read-only evidence; publication is denied
    # if its full canonical tree no longer agrees with the preflight binding.
    verify_failed_namespace
    # One trusted process creates an anonymous inode, writes and validates the
    # receipt, then publishes that held inode with linkat(AT_EMPTY_PATH).
    write_and_publish_receipt
    release_lock
    trap - EXIT INT TERM HUP
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
