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
ROOT="$DEFAULT_ROOT"
RESEARCH="$CANONICAL_RESEARCH"
RUNNER_ROOT="$CANONICAL_RUNNER_ROOT"

if [[ "$TEST_MODE" == "1" ]]; then
    ROOT="${EPYC_ROOT:-$DEFAULT_ROOT}"
    RESEARCH="${EPYC_RESEARCH:-$RESEARCH}"
    RUNNER_ROOT="${P_BENCH_4_RUNNER_ROOT:-$RUNNER_ROOT}"
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
EXPECTED_RESEARCH_COMMIT="c00f2937a48439f5f00e527176e854a94333a8db"
EXPECTED_RESEARCH_TREE="fcf651b2cfb21cfaf2cb5c2cf75768bbda037532"
EXPECTED_REPOSITORY="https://github.com/pestopoppa/epyc-inference-research.git"
EXPECTED_RUNNER_SHA256="f2983a10f6af3290f254c16a7681762a074bafb71fc12df68dbfbcc83043a1b9"
EXPECTED_AMENDMENT_SHA256="ca2b9ff9d255f927ceddf3f5b8e43b1b50f9a99b27a84a948ebcac8549daaf8a"
EXPECTED_MEASUREMENT_SHA256="de54442522068b127606f3455608187c065061e222559fb63a8488928924f387"
EXPECTED_AMENDED_MEASUREMENT_SHA256="93d864e757eff51c0edae560e9aaa1809dd37f74b9fb922485c1c59a81638b52"
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
    "$PYTHON" - "$SCRIPT_PATH" "$ROOT" "$RESEARCH" "$RUNNER_ROOT" "$CANONICAL_ROOT" \
        "$CANONICAL_RESEARCH" "$CANONICAL_RUNNER_ROOT" "$production" "$PATH" <<'PY'
import os
import stat
import sys
from pathlib import Path

script, root, research, runner_root, canonical_root, canonical_research, canonical_runner, production, path = sys.argv[1:]

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
if path != "/usr/bin:/bin":
    raise SystemExit(f"ratifier PATH is not fixed: {path}")
if production == "1":
    expected_script = f"{canonical_root}/artifacts/operator/ratify_pbench4_fg4b_server_native_20260728.sh"
    expected = {
        "script": expected_script,
        "root": canonical_root,
        "research": canonical_research,
        "runner root": canonical_runner,
    }
    actual = {"script": script, "root": root, "research": research, "runner root": runner_root}
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
    [[ "$reviewer" =~ ^[A-Za-z0-9._:@+-]{1,128}$ ]] ||
        fail "attestation must be 1-128 safe ASCII characters"
    verify_preflight
    mkdir -p -- "$TX_PARENT"
    exec 9<"$SCRIPT_PATH"
    flock -n 9 || fail "another P-BENCH-4 transaction holds the script lock"
    # Re-check every protected input after the operator has supplied the token.
    verify_preflight
    stamp="${P_BENCH_4_TEST_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
    [[ "$TEST_MODE" != 1 || "$stamp" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] ||
        fail "invalid test-only receipt timestamp"
    tx="$(mktemp -d "$TX_PARENT/.pbench4-${stamp}.XXXXXX")"
    measurement_candidate="$tx/MEASUREMENT.md.candidate"
    changelog_candidate="$tx/CHANGELOG.md.candidate"
    receipt_candidate="$tx/receipt.json.candidate"
    receipt_final="$ROOT/artifacts/operator/ratify_pbench4_fg4b_server_native_${stamp}.json"
    install -m 0600 -- "$MEASUREMENT" "$tx/MEASUREMENT.md.before"
    install -m 0600 -- "$CHANGELOG" "$tx/CHANGELOG.md.before"
    candidate_measurement >"$measurement_candidate"
    candidate_changelog >"$changelog_candidate"
    require_hash "$EXPECTED_AMENDED_MEASUREMENT_SHA256" "$measurement_candidate"
    require_hash "$EXPECTED_AMENDED_CHANGELOG_SHA256" "$changelog_candidate"
    write_receipt "$receipt_candidate" "$reviewer" "$(date -u --iso-8601=seconds)"
    fsync_file_and_parent "$measurement_candidate"
    fsync_file_and_parent "$changelog_candidate"
    fsync_file_and_parent "$receipt_candidate"

    local measurement_replaced=0 changelog_replaced=0
    rollback() {
        local status=${1:-$?}
        trap - ERR INT TERM HUP
        if [[ -e "$receipt_final" ]] && validate_receipt_with_authoritative_runner "$receipt_final"; then
            # A durable valid receipt is the commit record. Never retract it or
            # its bound policy files after publication.
            exit "$status"
        fi
        if [[ "$changelog_replaced" == 1 ]]; then
            mv -f -- "$tx/CHANGELOG.md.before" "$CHANGELOG"
            fsync_file_and_parent "$CHANGELOG"
        fi
        if [[ "$measurement_replaced" == 1 ]]; then
            mv -f -- "$tx/MEASUREMENT.md.before" "$MEASUREMENT"
            fsync_file_and_parent "$MEASUREMENT"
        fi
        exit "$status"
    }
    trap rollback ERR INT TERM HUP
    mv -f -- "$measurement_candidate" "$MEASUREMENT"
    fsync_file_and_parent "$MEASUREMENT"
    measurement_replaced=1
    if [[ "$TEST_MODE" == 1 && "${P_BENCH_4_TEST_FAIL_AFTER_MEASUREMENT:-0}" == 1 ]]; then
        false
    fi
    mv -f -- "$changelog_candidate" "$CHANGELOG"
    fsync_file_and_parent "$CHANGELOG"
    changelog_replaced=1
    validate_receipt_with_authoritative_runner "$receipt_candidate"
    publish_receipt_no_replace "$receipt_candidate" "$receipt_final" || rollback "$?"
    if [[ "$TEST_MODE" == 1 && "${P_BENCH_4_TEST_FAIL_AFTER_RECEIPT:-0}" == 1 ]]; then
        false
    fi
    printf 'ratified %s\n' "$stamp" >"$tx/COMPLETE"
    measurement_replaced=0
    changelog_replaced=0
    trap - ERR INT TERM HUP
    printf 'Ratified P-BENCH-4. Receipt: %s\n' "$receipt_final"
}

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
