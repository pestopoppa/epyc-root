#!/bin/bash
# Human-only P-BENCH-4 amendment. It never starts inference or edits a registry.
set -euo pipefail
export PATH="/usr/bin:/bin"

SCRIPT_PATH="$(realpath -e -- "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
DEFAULT_ROOT="$(realpath -e -- "$SCRIPT_DIR/../..")"
TEST_MODE="${P_BENCH_4_TEST_MODE:-0}"
CANONICAL_ROOT="/mnt/raid0/llm/epyc-root"
CANONICAL_RESEARCH="/mnt/raid0/llm/epyc-inference-research"
CANONICAL_RUNNER_ROOT="/mnt/raid0/llm/worktrees/fg4b-optimized-server-20260728"
PYTHON="/usr/bin/python3"
TRUST_LOCK="/run/lock/epyc-measurement-trust-boundary.lock"
ACTIVE_TX=""
ROOT="$DEFAULT_ROOT"
RESEARCH="$CANONICAL_RESEARCH"
RUNNER_ROOT="$CANONICAL_RUNNER_ROOT"

if [[ "$TEST_MODE" == "1" ]]; then
    ROOT="${EPYC_ROOT:-$DEFAULT_ROOT}"
    RESEARCH="${EPYC_RESEARCH:-$RESEARCH}"
    RUNNER_ROOT="${P_BENCH_4_RUNNER_ROOT:-$RUNNER_ROOT}"
    TRUST_LOCK="${P_BENCH_4_TRUST_LOCK:-$TRUST_LOCK}"
    [[ "$ROOT" != "$CANONICAL_ROOT" ]] || {
        printf 'ERROR: test mode refuses the canonical root.\n' >&2
        exit 1
    }
fi

AMENDMENT="$ROOT/artifacts/operator/pbench4_fg4b_server_native_protocol_amendment_20260728.md"
MEASUREMENT="$ROOT/MEASUREMENT.md"
CHANGELOG="$ROOT/CHANGELOG.md"
TX_PARENT="$ROOT/artifacts/operator/pbench4_fg4b_server_native_transactions"
RUNNER_REL="scripts/benchmark/fg4b_a4_cpu_optimized_reanchor.py"
PROTOCOL_MARKER="## P-BENCH-4 — Single-instance server-native speculative decode (FG-4b)"
ATTEST_TOKEN="RATIFY-P-BENCH-4-FG4B-20260728"

# These pins bind the runner's reviewed `protocol_contract()` and reject the
# retired three-sample source before any human-owned file is changed.
EXPECTED_RESEARCH_COMMIT="73dcf194fc5c6a23a098ecc34bcef03e38430f0a"
EXPECTED_RESEARCH_TREE="d2e2b6f21cbdb57ca85986099642047fb83fad2c"
EXPECTED_REPOSITORY="https://github.com/pestopoppa/epyc-inference-research.git"
EXPECTED_RUNNER_SHA256="b77cdf9d90d010146c79a09114947fa24919f65e97cd35519ca76b085a24f19d"
EXPECTED_AMENDMENT_SHA256="028adc0fb2b72d71fa0dd3ace5ef3d82d08779a4c3c21fd0b561c92762a695fe"
EXPECTED_MEASUREMENT_SHA256="de54442522068b127606f3455608187c065061e222559fb63a8488928924f387"
EXPECTED_AMENDED_MEASUREMENT_SHA256="49ec1495e8b812614d0cafa35c6ed450bff96482610c644893f8009f7ce2d651"
EXPECTED_CHANGELOG_SHA256="96b6311233d9a4d771d205ff45bb3eca912834eaf241906f2f9adfce0a3de436"
EXPECTED_AMENDED_CHANGELOG_SHA256="b523e9c917538463899ac3d68d88754580d6195e6408e00f6b412c20a67243fc"

if [[ "$TEST_MODE" == "1" ]]; then
    EXPECTED_RESEARCH_COMMIT="${P_BENCH_4_EXPECTED_RESEARCH_COMMIT:-$EXPECTED_RESEARCH_COMMIT}"
    EXPECTED_RESEARCH_TREE="${P_BENCH_4_EXPECTED_RESEARCH_TREE:-$EXPECTED_RESEARCH_TREE}"
    EXPECTED_REPOSITORY="${P_BENCH_4_EXPECTED_REPOSITORY:-$EXPECTED_REPOSITORY}"
    EXPECTED_RUNNER_SHA256="${P_BENCH_4_EXPECTED_RUNNER_SHA256:-$EXPECTED_RUNNER_SHA256}"
    EXPECTED_AMENDMENT_SHA256="${P_BENCH_4_EXPECTED_AMENDMENT_SHA256:-$EXPECTED_AMENDMENT_SHA256}"
    EXPECTED_MEASUREMENT_SHA256="${P_BENCH_4_EXPECTED_MEASUREMENT_SHA256:-$EXPECTED_MEASUREMENT_SHA256}"
    EXPECTED_AMENDED_MEASUREMENT_SHA256="${P_BENCH_4_EXPECTED_AMENDED_MEASUREMENT_SHA256:-$EXPECTED_AMENDED_MEASUREMENT_SHA256}"
    EXPECTED_CHANGELOG_SHA256="${P_BENCH_4_EXPECTED_CHANGELOG_SHA256:-$EXPECTED_CHANGELOG_SHA256}"
    EXPECTED_AMENDED_CHANGELOG_SHA256="${P_BENCH_4_EXPECTED_AMENDED_CHANGELOG_SHA256:-$EXPECTED_AMENDED_CHANGELOG_SHA256}"
fi

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
sha256() { sha256sum -- "$1" | awk '{print $1}'; }
require_hash() {
    local expected=$1 path=$2 actual
    actual="$(sha256 "$path")"
    [[ "$actual" == "$expected" ]] || fail "SHA-256 mismatch for $path"
}
require_pin() {
    [[ "$1" =~ ^[0-9a-f]{40}$ || "$1" =~ ^[0-9a-f]{64}$ ]] ||
        fail "unresolved or malformed candidate pin"
}
require_relpath() {
    [[ "$1" != /* && "$1" != *".."* && "$1" != __* ]] ||
        fail "unresolved or unsafe runner path"
}

changelog_entry() {
    printf '%s\n' \
        '- Ratified `P-BENCH-4` for prospective FG-4b single-instance server-native speculative decode; it pins the reviewed runner contract and preserves prior FG-4b observations as non-decision-grade.'
}

candidate_measurement() {
    cat -- "$MEASUREMENT"
    printf '\n'
    cat -- "$AMENDMENT"
}

candidate_changelog() {
    cat -- "$CHANGELOG"
    printf '\n'
    changelog_entry
}

verify_pins() {
    require_pin "$EXPECTED_RESEARCH_COMMIT"
    require_pin "$EXPECTED_RESEARCH_TREE"
    [[ -n "$EXPECTED_REPOSITORY" ]] || fail "unresolved runner repository"
    require_pin "$EXPECTED_RUNNER_SHA256"
    require_pin "$EXPECTED_AMENDMENT_SHA256"
    require_pin "$EXPECTED_MEASUREMENT_SHA256"
    require_pin "$EXPECTED_AMENDED_MEASUREMENT_SHA256"
    require_pin "$EXPECTED_CHANGELOG_SHA256"
    require_pin "$EXPECTED_AMENDED_CHANGELOG_SHA256"
}

verify_canonical_paths() {
    local production=0
    [[ "$TEST_MODE" == "1" ]] || production=1
    "$PYTHON" - "$SCRIPT_PATH" "$ROOT" "$RESEARCH" "$RUNNER_ROOT" "$TRUST_LOCK" \
        "$CANONICAL_ROOT" "$CANONICAL_RESEARCH" "$CANONICAL_RUNNER_ROOT" "$production" "$PATH" <<'PY'
import os
import stat
import sys
from pathlib import Path

script, root, research, runner_root, trust_lock, canonical_root, canonical_research, canonical_runner, production, path = sys.argv[1:]

def verify_path(label: str, value: str, kind: str) -> None:
    candidate = Path(value)
    if not candidate.is_absolute() or os.path.realpath(value) != value:
        raise SystemExit(f"{label} is not an exact resolved path: {value}")
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current /= part
        if stat.S_ISLNK(os.lstat(current).st_mode):
            raise SystemExit(f"{label} contains a symlink component: {current}")
    mode = os.lstat(candidate).st_mode
    if kind == "file" and not stat.S_ISREG(mode):
        raise SystemExit(f"{label} is not a regular file: {value}")
    if kind == "dir" and not stat.S_ISDIR(mode):
        raise SystemExit(f"{label} is not a directory: {value}")

verify_path("script", script, "file")
verify_path("root", root, "dir")
verify_path("research", research, "dir")
verify_path("runner root", runner_root, "dir")
verify_path("trust-boundary lock", trust_lock, "file")
if path != "/usr/bin:/bin":
    raise SystemExit(f"ratifier PATH is not fixed: {path}")
if production == "1":
    expected_script = f"{canonical_root}/artifacts/operator/ratify_pbench4_fg4b_server_native_20260728.sh"
    expected = {
        "script": expected_script,
        "root": canonical_root,
        "research": canonical_research,
        "runner root": canonical_runner,
        "trust-boundary lock": "/run/lock/epyc-measurement-trust-boundary.lock",
    }
    actual = {"script": script, "root": root, "research": research,
              "runner root": runner_root, "trust-boundary lock": trust_lock}
    for label, wanted in expected.items():
        if actual[label] != wanted:
            raise SystemExit(f"production {label} differs from canonical path: {actual[label]}")
PY
}

verify_preflight() {
    verify_pins
    require_relpath "$RUNNER_REL"
    [[ "$TEST_MODE" == "1" || "$ROOT" == "$CANONICAL_ROOT" ]] ||
        fail "production ratifier must run from the canonical root: $CANONICAL_ROOT"
    [[ "$PATH" == "/usr/bin:/bin" ]] || fail "ratifier PATH is not fixed"
    [[ -x "$PYTHON" ]] || fail "trusted interpreter is unavailable: $PYTHON"
    [[ -d "$ROOT/.git" || -f "$ROOT/.git" ]] || fail "root is not a Git worktree: $ROOT"
    [[ -f "$MEASUREMENT" && -f "$CHANGELOG" && -f "$AMENDMENT" ]] ||
        fail "protocol source files are missing below $ROOT"
    [[ -d "$RESEARCH/.git" || -f "$RESEARCH/.git" ]] ||
        fail "research is not a Git worktree: $RESEARCH"
    [[ -d "$RUNNER_ROOT/.git" || -f "$RUNNER_ROOT/.git" ]] ||
        fail "hardened runner is not an exact Git worktree: $RUNNER_ROOT"
    verify_canonical_paths
    ! grep -Fqx "$PROTOCOL_MARKER" "$MEASUREMENT" ||
        fail "P-BENCH-4 marker is already present; refuse a duplicate or partial amendment"
    git -C "$ROOT" diff --quiet -- MEASUREMENT.md CHANGELOG.md ||
        fail "MEASUREMENT.md or CHANGELOG.md has unstaged changes"
    git -C "$ROOT" diff --cached --quiet -- MEASUREMENT.md CHANGELOG.md ||
        fail "MEASUREMENT.md or CHANGELOG.md has staged changes"
    require_hash "$EXPECTED_MEASUREMENT_SHA256" "$MEASUREMENT"
    require_hash "$EXPECTED_CHANGELOG_SHA256" "$CHANGELOG"
    require_hash "$EXPECTED_AMENDMENT_SHA256" "$AMENDMENT"
    git -C "$RESEARCH" cat-file -e "${EXPECTED_RESEARCH_COMMIT}^{commit}" ||
        fail "pinned hardened-runner commit is unavailable"
    [[ "$(git -C "$RESEARCH" rev-parse "${EXPECTED_RESEARCH_COMMIT}^{tree}")" == "$EXPECTED_RESEARCH_TREE" ]] ||
        fail "pinned hardened-runner tree differs"
    local runner_hash
    runner_hash="$(git -C "$RESEARCH" show "${EXPECTED_RESEARCH_COMMIT}:${RUNNER_REL}" | sha256sum | awk '{print $1}')" ||
        fail "pinned hardened-runner path is unavailable"
    [[ "$runner_hash" == "$EXPECTED_RUNNER_SHA256" ]] ||
        fail "pinned hardened-runner hash differs"
    [[ "$(git -C "$RUNNER_ROOT" rev-parse HEAD)" == "$EXPECTED_RESEARCH_COMMIT" ]] ||
        fail "hardened runner worktree is not at the pinned commit"
    [[ -z "$(git -C "$RUNNER_ROOT" status --porcelain --untracked-files=all)" ]] ||
        fail "hardened runner worktree is dirty"
    [[ "$(git -C "$RUNNER_ROOT" remote get-url origin)" == "$EXPECTED_REPOSITORY" ]] ||
        fail "hardened runner repository differs"
    require_hash "$EXPECTED_RUNNER_SHA256" "$RUNNER_ROOT/$RUNNER_REL"
}

validate_receipt_with_authoritative_runner() {
    local receipt=$1
    "$PYTHON" - "$RUNNER_ROOT/$RUNNER_REL" "$receipt" <<'PY'
import importlib.util
import sys
from pathlib import Path

runner_path = Path(sys.argv[1])
receipt_path = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("pbench4_authoritative_runner", runner_path)
if spec is None or spec.loader is None:
    raise SystemExit("cannot load the pinned FG-4b runner")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)
runner.validate_protocol_attestation(receipt_path)
PY
}

write_receipt() {
    local receipt=$1 reviewer=$2 reviewed_at=$3
    cat >"$receipt" <<EOF
{
  "schema": "epyc.fg4b_a4_cpu_optimized_server_protocol_review.v1",
  "status": "ratified",
  "protocol_id": "FG-4b/A4-CPU-optimized-server-v1",
  "reviewer": "$reviewer",
  "reviewed_at": "$reviewed_at",
  "instrument_sha256": "$EXPECTED_RUNNER_SHA256",
  "instrument": {
    "repository": "$EXPECTED_REPOSITORY",
    "repository_commit": "$EXPECTED_RESEARCH_COMMIT",
    "repository_tree": "$EXPECTED_RESEARCH_TREE",
    "path": "$RUNNER_REL"
  },
  "human_amendment": {
    "path": "$MEASUREMENT",
    "sha256": "$EXPECTED_AMENDED_MEASUREMENT_SHA256"
  },
  "contract": {
    "protocol_id": "FG-4b/A4-CPU-optimized-server-v1",
    "metric": "llama-server timings.predicted_per_second",
    "metric_direction": "higher_is_better",
    "model": "/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf",
    "binary": "/mnt/raid0/llm/llama.cpp/build/bin/llama-server",
    "cpu_list": "0-47,96-143",
    "physical_regions": ["q0", "q1"],
    "threads": 96,
    "ctx": 32768,
    "ubatch": 8192,
    "np": 1,
    "native_mtp_draft_max": 4,
    "n_predict": 512,
    "ignore_eos": true,
    "required_finish_reason": "length",
    "measured_reps": 5,
    "aggregation": ["median", "median_absolute_deviation"],
    "warmup": {
      "tokens": 64,
      "consecutive_samples": 3,
      "relative_tolerance": 0.05,
      "max_attempts": 8
    },
    "cold_cache_preparation": {
      "sync": true,
      "drop_caches": 3,
      "after_clean_host_gate": true,
      "before_server_start": true
    },
    "per_request_witness": {
      "exclusive_inference_process_tree": true,
      "exact_live_affinity": "0-47,96-143"
    },
    "durable_publish": "fsync_files_and_staging_dir_then_parent_before_and_after_atomic_rename"
  },
  "pre_ratification_runner": {
    "commit": "919e83a249ed9060d0608305700e6eeddb8daa71",
    "status": "explicitly_nonconforming_not_retro_certified"
  }
}
EOF
}

fsync_file_and_parent() {
    "$PYTHON" - "$1" <<'PY'
import os
import stat
import sys

path = sys.argv[1]
nofollow = getattr(os, "O_NOFOLLOW", 0)
fd = os.open(path, os.O_RDONLY | nofollow)
parent_fd = os.open(os.path.dirname(path), os.O_RDONLY | os.O_DIRECTORY | nofollow)
try:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        raise SystemExit(f"not a regular file: {path}")
    os.fsync(fd)
    os.fsync(parent_fd)
finally:
    os.close(parent_fd)
    os.close(fd)
PY
}

fsync_directory() {
    "$PYTHON" - "$1" <<'PY'
import os
import sys

fd = os.open(sys.argv[1], os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0))
try:
    os.fsync(fd)
finally:
    os.close(fd)
PY
}

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
    /usr/bin/flock -n 8 || fail "measurement trust-boundary lock is already held: $TRUST_LOCK"
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
    if [[ "$TEST_MODE" == 1 && "${P_BENCH_4_TEST_HOLD_TRUST_LOCK_SECONDS:-0}" != 0 ]]; then
        [[ "${P_BENCH_4_TEST_HOLD_TRUST_LOCK_SECONDS}" =~ ^[0-9]+([.][0-9]+)?$ ]] ||
            fail "invalid test-only trust-lock hold duration"
        /usr/bin/sleep "${P_BENCH_4_TEST_HOLD_TRUST_LOCK_SECONDS}"
    fi
}

write_transaction_journal() {
    local tx=$1 receipt=$2
    "$PYTHON" - "$tx/transaction.json" "$tx" "$receipt" "$MEASUREMENT" "$CHANGELOG" \
        "$EXPECTED_MEASUREMENT_SHA256" "$EXPECTED_AMENDED_MEASUREMENT_SHA256" \
        "$EXPECTED_CHANGELOG_SHA256" "$EXPECTED_AMENDED_CHANGELOG_SHA256" \
        "$EXPECTED_RESEARCH_COMMIT" "$EXPECTED_RESEARCH_TREE" "$EXPECTED_RUNNER_SHA256" <<'PY'
import json
import os
import stat
import sys
from datetime import UTC, datetime

(journal_path, tx, receipt, measurement, changelog, measurement_before,
 measurement_after, changelog_before, changelog_after, commit, tree, runner_hash) = sys.argv[1:]
payload = {
    "schema": "epyc.pbench4_fg4b_ratification_transaction.v1",
    "state": "prepared",
    "prepared_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    "receipt": receipt,
    "instrument": {"commit": commit, "tree": tree, "sha256": runner_hash},
    "files": {
        "measurement": {
            "path": measurement,
            "preimage": "MEASUREMENT.md.before",
            "preimage_sha256": measurement_before,
            "candidate_sha256": measurement_after,
        },
        "changelog": {
            "path": changelog,
            "preimage": "CHANGELOG.md.before",
            "preimage_sha256": changelog_before,
            "candidate_sha256": changelog_after,
        },
    },
}
data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
nofollow = getattr(os, "O_NOFOLLOW", 0)
fd = os.open(journal_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow, 0o600)
try:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        raise SystemExit("transaction journal is not a regular file")
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        view = view[written:]
    os.fsync(fd)
finally:
    os.close(fd)
dir_fd = os.open(tx, os.O_RDONLY | os.O_DIRECTORY | nofollow)
try:
    os.fsync(dir_fd)
finally:
    os.close(dir_fd)
PY
}

read_transaction_journal() {
    local tx=$1
    "$PYTHON" - "$tx/transaction.json" "$tx" "$MEASUREMENT" "$CHANGELOG" \
        "$ROOT/artifacts/operator" <<'PY'
import json
import os
import re
import sys
from pathlib import Path

journal_path, tx, measurement, changelog, operator = sys.argv[1:]
payload = json.loads(Path(journal_path).read_text(encoding="utf-8"))
if payload.get("schema") != "epyc.pbench4_fg4b_ratification_transaction.v1" or payload.get("state") != "prepared":
    raise SystemExit("unexpected P-BENCH-4 transaction journal schema or state")
files = payload.get("files")
if not isinstance(files, dict):
    raise SystemExit("transaction journal lacks file identities")
expected = {
    "measurement": (measurement, "MEASUREMENT.md.before"),
    "changelog": (changelog, "CHANGELOG.md.before"),
}
values = []
receipt = str(payload.get("receipt") or "")
receipt_path = Path(receipt)
if receipt_path.parent != Path(operator) or not re.fullmatch(
    r"ratify_pbench4_fg4b_server_native_[0-9]{8}T[0-9]{6}Z[.]json",
    receipt_path.name,
):
    raise SystemExit("transaction journal receipt path is unsafe")
values.append(receipt)
for key in ("measurement", "changelog"):
    record = files.get(key)
    if not isinstance(record, dict):
        raise SystemExit(f"transaction journal lacks {key} identity")
    path, preimage = expected[key]
    if record.get("path") != path or record.get("preimage") != preimage:
        raise SystemExit(f"transaction journal {key} path differs")
    for hash_key in ("preimage_sha256", "candidate_sha256"):
        value = str(record.get(hash_key) or "")
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise SystemExit(f"transaction journal {key} {hash_key} is malformed")
        values.append(value)
for value in values:
    print(value)
PY
}

restore_transaction_preimages() {
    local tx=$1 measurement_hash=$2 changelog_hash=$3
    "$PYTHON" - "$tx/MEASUREMENT.md.before" "$MEASUREMENT" "$measurement_hash" \
        "$tx/CHANGELOG.md.before" "$CHANGELOG" "$changelog_hash" <<'PY'
import hashlib
import os
import stat
import sys

nofollow = getattr(os, "O_NOFOLLOW", 0)

def restore(preimage: str, destination: str, expected_hash: str) -> None:
    source_fd = os.open(preimage, os.O_RDONLY | nofollow)
    try:
        source_stat = os.fstat(source_fd)
        if not stat.S_ISREG(source_stat.st_mode):
            raise SystemExit(f"transaction preimage is not regular: {preimage}")
        chunks = []
        while True:
            chunk = os.read(source_fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        data = b"".join(chunks)
    finally:
        os.close(source_fd)
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise SystemExit(f"transaction preimage hash differs: {preimage}")
    parent = os.path.dirname(destination)
    temporary = os.path.join(parent, f".pbench4-restore-{os.getpid()}-{os.path.basename(destination)}")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow, source_stat.st_mode & 0o777)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, destination)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | nofollow)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)

restore(sys.argv[1], sys.argv[2], sys.argv[3])
restore(sys.argv[4], sys.argv[5], sys.argv[6])
PY
}

mark_transaction_complete() {
    local tx=$1 disposition=$2 receipt=$3
    "$PYTHON" - "$tx" "$disposition" "$receipt" <<'PY'
import json
import os
import sys
from datetime import UTC, datetime

tx, disposition, receipt = sys.argv[1:]
if disposition not in {"committed", "rolled_back"}:
    raise SystemExit("invalid transaction disposition")
data = (json.dumps({
    "schema": "epyc.pbench4_fg4b_ratification_completion.v1",
    "completed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    "disposition": disposition,
    "receipt": receipt,
}, indent=2, sort_keys=True) + "\n").encode()
candidate = os.path.join(tx, f".COMPLETE.{os.getpid()}")
nofollow = getattr(os, "O_NOFOLLOW", 0)
fd = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow, 0o600)
try:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        view = view[written:]
    os.fsync(fd)
finally:
    os.close(fd)
os.replace(candidate, os.path.join(tx, "COMPLETE"))
dir_fd = os.open(tx, os.O_RDONLY | os.O_DIRECTORY | nofollow)
try:
    os.fsync(dir_fd)
finally:
    os.close(dir_fd)
PY
}

recover_transaction() {
    local tx=$1 receipt measurement_before measurement_after changelog_before changelog_after
    local -a journal
    [[ -d "$tx" && ! -L "$tx" ]] || fail "unsafe P-BENCH-4 transaction directory: $tx"
    if [[ -e "$tx/COMPLETE" ]]; then
        [[ -f "$tx/COMPLETE" && ! -L "$tx/COMPLETE" ]] ||
            fail "unsafe P-BENCH-4 completion marker: $tx/COMPLETE"
        return
    fi
    if [[ ! -e "$tx/transaction.json" ]]; then
        # The journal is published before either policy mutation. An orphan
        # without it therefore has no live state to recover.
        mark_transaction_complete "$tx" "rolled_back" ""
        return
    fi
    [[ -f "$tx/transaction.json" && ! -L "$tx/transaction.json" ]] ||
        fail "unsafe P-BENCH-4 transaction journal: $tx/transaction.json"
    mapfile -t journal < <(read_transaction_journal "$tx")
    [[ "${#journal[@]}" == 5 ]] || fail "incomplete P-BENCH-4 transaction journal: $tx"
    receipt="${journal[0]}"
    measurement_before="${journal[1]}"
    measurement_after="${journal[2]}"
    changelog_before="${journal[3]}"
    changelog_after="${journal[4]}"

    if [[ -f "$receipt" && ! -L "$receipt" ]] &&
        [[ "$(sha256 "$MEASUREMENT")" == "$measurement_after" ]] &&
        [[ "$(sha256 "$CHANGELOG")" == "$changelog_after" ]] &&
        validate_receipt_with_authoritative_runner "$receipt" >/dev/null 2>&1; then
        mark_transaction_complete "$tx" "committed" "$receipt"
        printf 'Recovered committed P-BENCH-4 transaction: %s\n' "$tx"
        return
    fi

    restore_transaction_preimages "$tx" "$measurement_before" "$changelog_before"
    [[ "$(sha256 "$MEASUREMENT")" == "$measurement_before" ]] ||
        fail "recovered MEASUREMENT.md does not match its journaled preimage"
    [[ "$(sha256 "$CHANGELOG")" == "$changelog_before" ]] ||
        fail "recovered CHANGELOG.md does not match its journaled preimage"
    mark_transaction_complete "$tx" "rolled_back" "$receipt"
    printf 'Recovered rolled-back P-BENCH-4 transaction: %s\n' "$tx"
}

recover_pending_transactions() {
    local tx
    [[ -e "$TX_PARENT" ]] || return 0
    [[ -d "$TX_PARENT" && ! -L "$TX_PARENT" ]] ||
        fail "unsafe P-BENCH-4 transaction parent: $TX_PARENT"
    for tx in "$TX_PARENT"/.pbench4-*; do
        [[ -e "$tx" ]] || break
        recover_transaction "$tx"
    done
}

publish_receipt_no_replace() {
    "$PYTHON" - "$1" "$2" <<'PY'
import ctypes
import errno
import os
import stat
import sys

candidate, receipt = sys.argv[1:]
nofollow = getattr(os, "O_NOFOLLOW", 0)
candidate_fd = os.open(candidate, os.O_RDONLY | nofollow)
parent, name = os.path.split(receipt)
parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | nofollow)
receipt_fd = None
published = False
try:
    source = os.fstat(candidate_fd)
    if not stat.S_ISREG(source.st_mode) or source.st_nlink != 1:
        raise SystemExit("receipt candidate is not a private regular file")
    chunks = []
    while True:
        chunk = os.read(candidate_fd, 1024 * 1024)
        if not chunk:
            break
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise SystemExit("receipt candidate is empty")
    if not hasattr(os, "O_TMPFILE"):
        raise SystemExit("O_TMPFILE is unavailable; receipt publication fails closed")
    receipt_fd = os.open(parent, os.O_RDWR | os.O_TMPFILE, 0o600)
    before = os.fstat(receipt_fd)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 0:
        raise SystemExit("anonymous receipt inode is not an unlinked regular file")
    view = memoryview(data)
    while view:
        written = os.write(receipt_fd, view)
        view = view[written:]
    os.fsync(receipt_fd)
    os.lseek(receipt_fd, 0, os.SEEK_SET)
    if os.read(receipt_fd, len(data) + 1) != data:
        raise SystemExit("receipt bytes differ before publication")
    libc = ctypes.CDLL(None, use_errno=True)
    linkat = libc.linkat
    linkat.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    linkat.restype = ctypes.c_int
    if linkat(receipt_fd, b"", parent_fd, os.fsencode(name), 0x1000) != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise SystemExit(f"receipt destination already exists: {receipt}")
        raise OSError(error, os.strerror(error), receipt)
    published = True
    final = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    held = os.fstat(receipt_fd)
    if not stat.S_ISREG(final.st_mode) or (final.st_dev, final.st_ino) != (held.st_dev, held.st_ino):
        raise SystemExit("receipt destination does not name the held inode")
    os.fsync(parent_fd)
except BaseException:
    if published:
        try:
            final = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            held = os.fstat(receipt_fd)
            if (final.st_dev, final.st_ino) == (held.st_dev, held.st_ino):
                os.unlink(name, dir_fd=parent_fd)
                os.fsync(parent_fd)
        except (FileNotFoundError, OSError):
            pass
    raise
finally:
    if receipt_fd is not None:
        os.close(receipt_fd)
    os.close(parent_fd)
    os.close(candidate_fd)
PY
}

plan() {
    verify_preflight
    printf '%s\n' \
        'P-BENCH-4 proposal is preflight-valid.' \
        "Runner: $EXPECTED_RESEARCH_COMMIT ($EXPECTED_RUNNER_SHA256)" \
        "Amendment: $AMENDMENT ($EXPECTED_AMENDMENT_SHA256)" \
        'No registry, inference, or process state will be changed.'
}

apply_amendment() {
    local reviewer=$1 stamp tx measurement_candidate changelog_candidate receipt_candidate receipt_final
    local test_hold_after_measurement=0 test_hold_after_receipt=0
    [[ "$reviewer" =~ ^[A-Za-z0-9._:@+-]{1,128}$ ]] ||
        fail "attestation must be 1-128 safe ASCII characters"
    verify_preflight
    mkdir -p -- "$TX_PARENT"
    fsync_directory "$TX_PARENT"
    stamp="${P_BENCH_4_TEST_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
    [[ "$TEST_MODE" != 1 || "$stamp" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] ||
        fail "invalid test-only receipt timestamp"
    tx="$(mktemp -d "$TX_PARENT/.pbench4-${stamp}.XXXXXX")"
    measurement_candidate="$tx/MEASUREMENT.md.candidate"
    changelog_candidate="$tx/CHANGELOG.md.candidate"
    receipt_candidate="$tx/receipt.json.candidate"
    receipt_final="$ROOT/artifacts/operator/ratify_pbench4_fg4b_server_native_${stamp}.json"
    fsync_directory "$TX_PARENT"
    install -m 0600 -- "$MEASUREMENT" "$tx/MEASUREMENT.md.before"
    install -m 0600 -- "$CHANGELOG" "$tx/CHANGELOG.md.before"
    fsync_file_and_parent "$tx/MEASUREMENT.md.before"
    fsync_file_and_parent "$tx/CHANGELOG.md.before"
    candidate_measurement >"$measurement_candidate"
    candidate_changelog >"$changelog_candidate"
    require_hash "$EXPECTED_AMENDED_MEASUREMENT_SHA256" "$measurement_candidate"
    require_hash "$EXPECTED_AMENDED_CHANGELOG_SHA256" "$changelog_candidate"
    write_receipt "$receipt_candidate" "$reviewer" "$(date -u --iso-8601=seconds)"
    fsync_file_and_parent "$measurement_candidate"
    fsync_file_and_parent "$changelog_candidate"
    fsync_file_and_parent "$receipt_candidate"
    write_transaction_journal "$tx" "$receipt_final"

    cleanup_transaction() {
        local status=$?
        trap - EXIT INT TERM HUP
        set +e
        if [[ -n "${ACTIVE_TX:-}" ]]; then
            recover_transaction "$ACTIVE_TX" || status=1
        fi
        exit "$status"
    }
    ACTIVE_TX="$tx"
    trap cleanup_transaction EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    trap 'exit 129' HUP
    if [[ "$TEST_MODE" == 1 ]]; then
        test_hold_after_measurement="${P_BENCH_4_TEST_HOLD_AFTER_MEASUREMENT_SECONDS:-0}"
        test_hold_after_receipt="${P_BENCH_4_TEST_HOLD_AFTER_RECEIPT_SECONDS:-0}"
        [[ "$test_hold_after_measurement" =~ ^[0-9]+([.][0-9]+)?$ ]] ||
            fail "invalid test-only post-measurement hold"
        [[ "$test_hold_after_receipt" =~ ^[0-9]+([.][0-9]+)?$ ]] ||
            fail "invalid test-only post-receipt hold"
    fi

    mv -f -- "$measurement_candidate" "$MEASUREMENT"
    [[ "$test_hold_after_measurement" == 0 ]] || /usr/bin/sleep "$test_hold_after_measurement"
    fsync_file_and_parent "$MEASUREMENT"
    if [[ "$TEST_MODE" == 1 && "${P_BENCH_4_TEST_FAIL_AFTER_MEASUREMENT:-0}" == 1 ]]; then
        false
    fi
    mv -f -- "$changelog_candidate" "$CHANGELOG"
    fsync_file_and_parent "$CHANGELOG"
    validate_receipt_with_authoritative_runner "$receipt_candidate"
    publish_receipt_no_replace "$receipt_candidate" "$receipt_final"
    [[ "$test_hold_after_receipt" == 0 ]] || /usr/bin/sleep "$test_hold_after_receipt"
    if [[ "$TEST_MODE" == 1 && "${P_BENCH_4_TEST_FAIL_AFTER_RECEIPT:-0}" == 1 ]]; then
        false
    fi
    mark_transaction_complete "$tx" "committed" "$receipt_final"
    ACTIVE_TX=""
    trap - EXIT INT TERM HUP
    printf 'Ratified P-BENCH-4. Receipt: %s\n' "$receipt_final"
}

acquire_trust_boundary_lock
recover_pending_transactions

case "${1:-}" in
    --plan|--validate-only)
        [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--attest TOKEN'
        plan
        ;;
    --attest)
        [[ $# -eq 2 && "$2" == "$ATTEST_TOKEN" ]] ||
            fail "usage: --attest $ATTEST_TOKEN"
        apply_amendment "$2"
        ;;
    *)
        fail "usage: --plan|--validate-only|--attest $ATTEST_TOKEN"
        ;;
esac
