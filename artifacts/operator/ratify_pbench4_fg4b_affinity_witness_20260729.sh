#!/bin/bash
# Human-only P-BENCH-4 affinity amendment. It never starts inference or mutates a registry.
set -euo pipefail
export PATH="/usr/bin:/bin"

SCRIPT_PATH="$(realpath -e -- "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
DEFAULT_ROOT="$(realpath -e -- "$SCRIPT_DIR/../..")"
TEST_MODE="${P_BENCH_4_AFFINITY_TEST_MODE:-0}"
ROOT="$DEFAULT_ROOT"
RESEARCH="/mnt/raid0/llm/epyc-inference-research"
RUNNER_ROOT="/mnt/raid0/llm/worktrees/fg4b-optimized-server-20260728"
TRUST_LOCK="/run/lock/epyc-measurement-trust-boundary.lock"
PYTHON="/usr/bin/python3"

if [[ "$TEST_MODE" == "1" ]]; then
    ROOT="${EPYC_ROOT:-$ROOT}"
    RESEARCH="${EPYC_RESEARCH:-$RESEARCH}"
    RUNNER_ROOT="${P_BENCH_4_AFFINITY_RUNNER_ROOT:-$RUNNER_ROOT}"
    TRUST_LOCK="${P_BENCH_4_AFFINITY_TRUST_LOCK:-$TRUST_LOCK}"
fi

AMENDMENT="$ROOT/artifacts/operator/pbench4_fg4b_affinity_witness_amendment_20260729.md"
MEASUREMENT="$ROOT/MEASUREMENT.md"
CHANGELOG="$ROOT/CHANGELOG.md"
PRIOR_RECEIPT_REL="artifacts/operator/ratify_pbench4_fg4b_server_native_20260729T055435Z.json"
PRIOR_RECEIPT="$ROOT/$PRIOR_RECEIPT_REL"
TX_PARENT="$ROOT/artifacts/operator/pbench4_fg4b_affinity_transactions"
RUNNER_REL="scripts/benchmark/fg4b_a4_cpu_optimized_reanchor.py"
MARKER="## P-BENCH-4 affinity-witness superseding amendment (FG-4b)"
TOKEN="RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729"

EXPECTED_REPOSITORY="https://github.com/pestopoppa/epyc-inference-research.git"
EXPECTED_COMMIT="006801b96de6a427a5c73a380fe5ff15260d33be"
EXPECTED_TREE="60554ceb49ef26b9d685d61d8816d0650957f027"
EXPECTED_RUNNER_SHA256="e77415acf226e67d0fcf09652e24a19a70bc9a5bdad9df5da6d66b6bd0538de9"
EXPECTED_AMENDMENT_SHA256="a90499fcc5232c9d9c0039ad8a83e37b9a693be9a03072e7b9c30bdb52463ac1"
EXPECTED_MEASUREMENT_SHA256="49ec1495e8b812614d0cafa35c6ed450bff96482610c644893f8009f7ce2d651"
EXPECTED_AMENDED_MEASUREMENT_SHA256="9c78ab20ea8855ebcf90512b18c30070ee0ded5ef3636a9a900855e180429423"
EXPECTED_CHANGELOG_SHA256="b523e9c917538463899ac3d68d88754580d6195e6408e00f6b412c20a67243fc"
EXPECTED_AMENDED_CHANGELOG_SHA256="8dcaa7c142f09b387ba06bb0ecd10057c3406842a8253d8e3592699ba81adf70"
EXPECTED_PRIOR_RECEIPT_SHA256="8da155e451f94720878d1fc7ffc53c190d8eabb96b106b15ffb32794528c154e"

if [[ "$TEST_MODE" == "1" ]]; then
    EXPECTED_REPOSITORY="${P_BENCH_4_AFFINITY_EXPECTED_REPOSITORY:-$EXPECTED_REPOSITORY}"
    EXPECTED_COMMIT="${P_BENCH_4_AFFINITY_EXPECTED_COMMIT:-$EXPECTED_COMMIT}"
    EXPECTED_TREE="${P_BENCH_4_AFFINITY_EXPECTED_TREE:-$EXPECTED_TREE}"
    EXPECTED_RUNNER_SHA256="${P_BENCH_4_AFFINITY_EXPECTED_RUNNER_SHA256:-$EXPECTED_RUNNER_SHA256}"
    EXPECTED_AMENDMENT_SHA256="${P_BENCH_4_AFFINITY_EXPECTED_AMENDMENT_SHA256:-$EXPECTED_AMENDMENT_SHA256}"
    EXPECTED_MEASUREMENT_SHA256="${P_BENCH_4_AFFINITY_EXPECTED_MEASUREMENT_SHA256:-$EXPECTED_MEASUREMENT_SHA256}"
    EXPECTED_AMENDED_MEASUREMENT_SHA256="${P_BENCH_4_AFFINITY_EXPECTED_AMENDED_MEASUREMENT_SHA256:-$EXPECTED_AMENDED_MEASUREMENT_SHA256}"
    EXPECTED_CHANGELOG_SHA256="${P_BENCH_4_AFFINITY_EXPECTED_CHANGELOG_SHA256:-$EXPECTED_CHANGELOG_SHA256}"
    EXPECTED_AMENDED_CHANGELOG_SHA256="${P_BENCH_4_AFFINITY_EXPECTED_AMENDED_CHANGELOG_SHA256:-$EXPECTED_AMENDED_CHANGELOG_SHA256}"
    EXPECTED_PRIOR_RECEIPT_SHA256="${P_BENCH_4_AFFINITY_EXPECTED_PRIOR_RECEIPT_SHA256:-$EXPECTED_PRIOR_RECEIPT_SHA256}"
fi

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
sha256() { sha256sum -- "$1" | awk '{print $1}'; }
require_hash() { [[ -f "$2" ]] && [[ "$(sha256 "$2")" == "$1" ]] || fail "SHA-256 mismatch for $2"; }

usage() { printf 'usage: %s --validate-only | --attest %s\n' "$0" "$TOKEN" >&2; }
case "${1:-}" in
    --validate-only) [[ $# == 1 ]] || { usage; exit 2; }; MODE="validate" ;;
    --attest) [[ $# == 2 && "$2" == "$TOKEN" ]] || { usage; exit 2; }; MODE="attest" ;;
    *) usage; exit 2 ;;
esac

[[ "$PATH" == "/usr/bin:/bin" && -x "$PYTHON" ]] || fail "trusted execution path is invalid"
[[ "$TEST_MODE" == "1" || "$ROOT" == "/mnt/raid0/llm/epyc-root" ]] || fail "production root is not canonical"
[[ "$TEST_MODE" == "1" || "$RESEARCH" == "/mnt/raid0/llm/epyc-inference-research" ]] || fail "production research is not canonical"
[[ "$TEST_MODE" == "1" || "$RUNNER_ROOT" == "/mnt/raid0/llm/worktrees/fg4b-optimized-server-20260728" ]] || fail "production runner is not canonical"
[[ -d "$ROOT/.git" || -f "$ROOT/.git" ]] || fail "root is not a Git worktree"
[[ -d "$RESEARCH/.git" || -f "$RESEARCH/.git" ]] || fail "research is not a Git worktree"
[[ -d "$RUNNER_ROOT/.git" || -f "$RUNNER_ROOT/.git" ]] || fail "runner is not a Git worktree"
[[ -f "$MEASUREMENT" && -f "$CHANGELOG" && -f "$AMENDMENT" ]] || fail "amendment files are missing"
require_hash "$EXPECTED_AMENDMENT_SHA256" "$AMENDMENT"
require_hash "$EXPECTED_PRIOR_RECEIPT_SHA256" "$PRIOR_RECEIPT"
git -C "$RESEARCH" cat-file -e "${EXPECTED_COMMIT}^{commit}" || fail "pinned runner commit is unavailable"
[[ "$(git -C "$RESEARCH" rev-parse "${EXPECTED_COMMIT}^{tree}")" == "$EXPECTED_TREE" ]] || fail "pinned runner tree differs"
[[ "$(git -C "$RESEARCH" show "${EXPECTED_COMMIT}:${RUNNER_REL}" | sha256sum | awk '{print $1}')" == "$EXPECTED_RUNNER_SHA256" ]] || fail "pinned runner hash differs"
[[ "$(git -C "$RUNNER_ROOT" rev-parse HEAD)" == "$EXPECTED_COMMIT" ]] || fail "runner worktree is not at the pinned commit"
[[ -z "$(git -C "$RUNNER_ROOT" status --porcelain --untracked-files=all)" ]] || fail "runner worktree is dirty"
[[ "$(git -C "$RUNNER_ROOT" remote get-url origin)" == "$EXPECTED_REPOSITORY" ]] || fail "runner repository differs"
require_hash "$EXPECTED_RUNNER_SHA256" "$RUNNER_ROOT/$RUNNER_REL"

mkdir -p -- "$(dirname -- "$TRUST_LOCK")"
exec 8<>"$TRUST_LOCK"
/usr/bin/flock -n 8 || fail "measurement trust-boundary lock is already held: $TRUST_LOCK"

"$PYTHON" - "$MODE" "$ROOT" "$MEASUREMENT" "$CHANGELOG" "$AMENDMENT" "$TX_PARENT" \
    "$RUNNER_ROOT/$RUNNER_REL" "$EXPECTED_REPOSITORY" "$EXPECTED_COMMIT" "$EXPECTED_TREE" \
    "$EXPECTED_RUNNER_SHA256" "$EXPECTED_MEASUREMENT_SHA256" "$EXPECTED_CHANGELOG_SHA256" \
    "$EXPECTED_AMENDED_MEASUREMENT_SHA256" "$EXPECTED_AMENDED_CHANGELOG_SHA256" \
    "$PRIOR_RECEIPT_REL" "$EXPECTED_PRIOR_RECEIPT_SHA256" "$TOKEN" <<'PY'
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

(mode, root, measurement, changelog, amendment, tx_parent, runner_path, repository,
 commit, tree, runner_sha256, measurement_sha256, changelog_sha256,
 amended_measurement_sha256, amended_changelog_sha256,
 prior_receipt, prior_sha256, token) = sys.argv[1:]
root = Path(root)
measurement = Path(measurement)
changelog = Path(changelog)
amendment = Path(amendment)
tx_parent = Path(tx_parent)
runner_path = Path(runner_path)
entry = ("- Ratified the P-BENCH-4 FG-4b affinity-witness superseding amendment; it binds stable all-thread request-boundary snapshots to the hardened runner and retains the prior receipt as superseded provenance.\n").encode()

def fsync_path(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fsync(fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
        os.close(fd)

def fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def replace(path: Path, data: bytes) -> None:
    temporary = path.parent / f".pbench4-affinity-{os.getpid()}-{path.name}"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)
    fsync_path(path)

def remove_receipt(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"receipt is not a regular file: {path}")
    path.unlink()
    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)

def fault(point: str) -> None:
    if os.environ.get("P_BENCH_4_AFFINITY_TEST_FAULT") == point:
        os.kill(os.getpid(), signal.SIGKILL)

def contract() -> dict:
    return {
        "protocol_id": "FG-4b/A4-CPU-optimized-server-v1", "metric": "llama-server timings.predicted_per_second", "metric_direction": "higher_is_better",
        "model": "/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf", "binary": "/mnt/raid0/llm/llama.cpp/build/bin/llama-server",
        "cpu_list": "0-47,96-143", "physical_regions": ["q0", "q1"], "threads": 96, "ctx": 32768, "ubatch": 8192, "np": 1,
        "native_mtp_draft_max": 4, "n_predict": 512, "ignore_eos": True, "required_finish_reason": "length", "measured_reps": 5,
        "aggregation": ["median", "median_absolute_deviation"], "warmup": {"tokens": 64, "consecutive_samples": 3, "relative_tolerance": 0.05, "max_attempts": 8},
        "cold_cache_preparation": {"sync": True, "drop_caches": 3, "after_clean_host_gate": True, "before_server_start": True},
        "per_request_witness": {"exclusive_inference_process_tree": True, "thread_affinity": {"observation": "stable /proc task snapshots immediately before and after each request; not continuous scheduler tracing", "snapshot_tid_set_unchanged": True, "expected_cpu_list": "0-47,96-143", "thread_union_exact": True, "no_thread_outside_expected": True, "worker_thread_union_exact": True, "before_after_witness_exact": True}},
        "durable_publish": "fsync_files_and_staging_dir_then_parent_before_and_after_atomic_rename",
    }

def receipt(human_path: Path, reviewed_at: str) -> dict:
    value = contract()
    return {"schema": "epyc.fg4b_a4_cpu_optimized_server_protocol_review.v1", "status": "ratified", "protocol_id": value["protocol_id"], "reviewer": token, "reviewed_at": reviewed_at,
            "instrument_sha256": runner_sha256, "instrument": {"repository": repository, "repository_commit": commit, "repository_tree": tree, "path": "scripts/benchmark/fg4b_a4_cpu_optimized_reanchor.py"},
            "human_amendment": {"path": str(human_path), "sha256": amended_measurement_sha256}, "contract": value,
            "supersedes": {"receipt_path": prior_receipt, "receipt_sha256": prior_sha256, "status": "superseded_provenance_only"}}

def validate(path: Path) -> None:
    spec = importlib.util.spec_from_file_location("pbench4_affinity_runner", runner_path)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load pinned FG-4b runner")
    runner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runner
    spec.loader.exec_module(runner)
    runner.validate_protocol_attestation(path)

def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    fsync_path(path)

def recover_pending() -> None:
    if not tx_parent.exists():
        return
    for tx in sorted(tx_parent.glob(".pbench4-affinity-*")):
        if (tx / "COMPLETE").exists():
            continue
        journal_path = tx / "transaction.json"
        if not journal_path.is_file():
            raise SystemExit(f"unfinished affinity transaction lacks a journal: {tx}")
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        if journal.get("schema") != "epyc.pbench4_fg4b_affinity_transaction.v1":
            raise SystemExit(f"unfinished affinity transaction has an unknown schema: {tx}")
        destination = Path(str(journal.get("receipt") or ""))
        if destination.parent != root / "artifacts/operator" or destination.is_symlink():
            raise SystemExit(f"unfinished affinity transaction has an unsafe receipt path: {tx}")
        before_measurement = (tx / "MEASUREMENT.md.before").read_bytes()
        before_changelog = (tx / "CHANGELOG.md.before").read_bytes()
        candidate_measurement = (tx / "MEASUREMENT.md.candidate").read_bytes()
        candidate_changelog = (tx / "CHANGELOG.md.candidate").read_bytes()
        after = (journal.get("measurement_after"), journal.get("changelog_after"))
        current = (hashlib.sha256(measurement.read_bytes()).hexdigest(), hashlib.sha256(changelog.read_bytes()).hexdigest())
        before = (hashlib.sha256(before_measurement).hexdigest(), hashlib.sha256(before_changelog).hexdigest())
        if before != (journal.get("measurement_before"), journal.get("changelog_before")):
            raise SystemExit(f"unfinished affinity transaction has corrupt preimages: {tx}")
        if (hashlib.sha256(candidate_measurement).hexdigest(), hashlib.sha256(candidate_changelog).hexdigest()) != after:
            raise SystemExit(f"unfinished affinity transaction has corrupt candidates: {tx}")
        first_replace = (after[0], before[1])
        second_replace = (before[0], after[1])
        if destination.exists():
            if not destination.is_file():
                raise SystemExit(f"unfinished affinity transaction has an unsafe receipt destination: {tx}")
            if current == before:
                replace(measurement, candidate_measurement)
                replace(changelog, candidate_changelog)
                current = after
            if current == after:
                try:
                    validate(destination)
                except BaseException:
                    remove_receipt(destination)
                    replace(measurement, before_measurement)
                    replace(changelog, before_changelog)
                    write_json(tx / "COMPLETE", {"state": "rolled-back-invalid-receipt"})
                else:
                    write_json(tx / "COMPLETE", {"state": "committed-recovered"})
                continue
            raise SystemExit(f"unfinished affinity transaction has unrecognized receipt policy state: {tx}")
        if current == after:
            replace(measurement, before_measurement)
            fault("recovery_after_first_restore")
            replace(changelog, before_changelog)
        elif current == first_replace or current == second_replace:
            replace(measurement, before_measurement)
            fault("recovery_after_first_restore")
            replace(changelog, before_changelog)
        elif current != before:
            raise SystemExit(f"unfinished affinity transaction has unrecognized policy state: {tx}")
        write_json(tx / "COMPLETE", {"state": "rolled-back-recovered"})

recover_pending()
measurement_before = measurement.read_bytes()
changelog_before = changelog.read_bytes()
if b"## P-BENCH-4 affinity-witness superseding amendment (FG-4b)" in measurement_before:
    raise SystemExit("affinity amendment marker is already present; refuse duplicate application")
if subprocess.run(["git", "-C", str(root), "diff", "--quiet", "--", "MEASUREMENT.md", "CHANGELOG.md"], check=False).returncode:
    raise SystemExit("policy preimages have unstaged changes")
if subprocess.run(["git", "-C", str(root), "diff", "--cached", "--quiet", "--", "MEASUREMENT.md", "CHANGELOG.md"], check=False).returncode:
    raise SystemExit("policy preimages have staged changes")
if hashlib.sha256(measurement_before).hexdigest() != measurement_sha256:
    raise SystemExit("MEASUREMENT.md preimage hash differs")
if hashlib.sha256(changelog_before).hexdigest() != changelog_sha256:
    raise SystemExit("CHANGELOG.md preimage hash differs")
measurement_candidate = measurement_before + b"\n" + amendment.read_bytes()
changelog_candidate = changelog_before + b"\n" + entry
if hashlib.sha256(measurement_candidate).hexdigest() != amended_measurement_sha256:
    raise SystemExit("candidate MEASUREMENT.md hash differs")
if hashlib.sha256(changelog_candidate).hexdigest() != amended_changelog_sha256:
    raise SystemExit("candidate CHANGELOG.md hash differs")

with tempfile.TemporaryDirectory() as temporary:
    candidate_path = Path(temporary) / "MEASUREMENT.md.candidate"
    candidate_path.write_bytes(measurement_candidate)
    probe = Path(temporary) / "receipt.json"
    write_json(probe, receipt(candidate_path, "2026-07-29T00:00:00+00:00"))
    validate(probe)

if mode == "validate":
    print("preflight-valid")
    raise SystemExit(0)

stamp = os.environ.get("P_BENCH_4_AFFINITY_TEST_STAMP") or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
if len(stamp) != 16 or not stamp.endswith("Z") or not stamp[:8].isdigit() or not stamp[9:15].isdigit() or stamp[8] != "T":
    raise SystemExit("invalid receipt timestamp")
destination = root / "artifacts/operator" / f"ratify_pbench4_fg4b_affinity_witness_{stamp}.json"
if destination.exists():
    raise SystemExit("receipt destination already exists")
tx_parent.mkdir(parents=True, exist_ok=True)
fsync_directory(tx_parent)
tx = Path(tempfile.mkdtemp(prefix=f".pbench4-affinity-{stamp}.", dir=tx_parent))
fsync_directory(tx_parent)
(tx / "MEASUREMENT.md.before").write_bytes(measurement_before)
(tx / "CHANGELOG.md.before").write_bytes(changelog_before)
(tx / "MEASUREMENT.md.candidate").write_bytes(measurement_candidate)
(tx / "CHANGELOG.md.candidate").write_bytes(changelog_candidate)
for path in tx.iterdir():
    fsync_path(path)
journal = {"schema": "epyc.pbench4_fg4b_affinity_transaction.v1", "state": "prepared", "receipt": str(destination), "measurement_before": hashlib.sha256(measurement_before).hexdigest(), "measurement_after": amended_measurement_sha256, "changelog_before": hashlib.sha256(changelog_before).hexdigest(), "changelog_after": amended_changelog_sha256}
write_json(tx / "transaction.json", journal)
try:
    staged_receipt = tx / "receipt.json"
    write_json(staged_receipt, receipt(measurement, datetime.now(UTC).isoformat().replace("+00:00", "+00:00")))
    replace(measurement, measurement_candidate)
    fault("after_first_policy_replace")
    replace(changelog, changelog_candidate)
    fault("after_both_policy_replaces")
    validate(staged_receipt)
    data = staged_receipt.read_bytes()
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
    try:
        partial = os.environ.get("P_BENCH_4_AFFINITY_TEST_FAULT") == "after_partial_receipt_create"
        view = memoryview(b"partial" if partial else data)
        while view:
            view = view[os.write(fd, view):]
        os.fsync(fd)
        fault("after_partial_receipt_create")
    finally:
        os.close(fd)
    fsync_path(destination)
    fault("after_valid_receipt_publish_before_complete")
    write_json(tx / "COMPLETE", {"state": "committed"})
except BaseException:
    raise
print(f"ratified: {destination}")
PY
