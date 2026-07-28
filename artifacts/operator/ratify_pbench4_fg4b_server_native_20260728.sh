#!/bin/bash
# Human-only P-BENCH-4 amendment. It never starts inference or edits a registry.
set -euo pipefail

SCRIPT_PATH="$(realpath -e -- "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
DEFAULT_ROOT="$(realpath -e -- "$SCRIPT_DIR/../..")"
TEST_MODE="${P_BENCH_4_TEST_MODE:-0}"
ROOT="$DEFAULT_ROOT"
RESEARCH="/mnt/raid0/llm/epyc-inference-research"
RUNNER_ROOT="/mnt/raid0/llm/worktrees/fg4b-optimized-server-20260728"

if [[ "$TEST_MODE" == "1" ]]; then
    ROOT="${EPYC_ROOT:-$DEFAULT_ROOT}"
    RESEARCH="${EPYC_RESEARCH:-$RESEARCH}"
    RUNNER_ROOT="${P_BENCH_4_RUNNER_ROOT:-$RUNNER_ROOT}"
    [[ "$ROOT" != "/mnt/raid0/llm/epyc-root" ]] || {
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
EXPECTED_RESEARCH_COMMIT="877ee0654bb01be319a771b503bb31cbc1729dda"
EXPECTED_RESEARCH_TREE="e7bfcb66f51cca11901a09e095f3e2befa9ee15f"
EXPECTED_RUNNER_SHA256="11364fe3197b91554c9b44a7aa2b80403c1e01f7646474f4e3269dc0a2953980"
EXPECTED_AMENDMENT_SHA256="acaab021fd79a7489d661eaa684692ca685ad46e3be20914d6d5225d6907b033"
EXPECTED_MEASUREMENT_SHA256="6c894c302aa4ad868cd66ad36814fded1937cb84d097724feffc25f6f1468e88"
EXPECTED_AMENDED_MEASUREMENT_SHA256="f70ca12987af826a24442b17fdfe78033d8ca793b50648bdeb384f3c106329b1"
EXPECTED_CHANGELOG_SHA256="24b045465050d693941d4a8381a8e222c386b94261cc13d29722b40f034cee9a"
EXPECTED_AMENDED_CHANGELOG_SHA256="b02611a16a91c84638d5e9e9eaa0103b39172659d452452f893e56aefd7e1cae"

if [[ "$TEST_MODE" == "1" ]]; then
    EXPECTED_RESEARCH_COMMIT="${P_BENCH_4_EXPECTED_RESEARCH_COMMIT:-$EXPECTED_RESEARCH_COMMIT}"
    EXPECTED_RESEARCH_TREE="${P_BENCH_4_EXPECTED_RESEARCH_TREE:-$EXPECTED_RESEARCH_TREE}"
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
    require_pin "$EXPECTED_RUNNER_SHA256"
    require_pin "$EXPECTED_AMENDMENT_SHA256"
    require_pin "$EXPECTED_MEASUREMENT_SHA256"
    require_pin "$EXPECTED_AMENDED_MEASUREMENT_SHA256"
    require_pin "$EXPECTED_CHANGELOG_SHA256"
    require_pin "$EXPECTED_AMENDED_CHANGELOG_SHA256"
}

verify_preflight() {
    verify_pins
    [[ -d "$ROOT/.git" || -f "$ROOT/.git" ]] || fail "root is not a Git worktree: $ROOT"
    [[ -f "$MEASUREMENT" && -f "$CHANGELOG" && -f "$AMENDMENT" ]] ||
        fail "protocol source files are missing below $ROOT"
    [[ -d "$RESEARCH/.git" || -f "$RESEARCH/.git" ]] ||
        fail "research is not a Git worktree: $RESEARCH"
    [[ -d "$RUNNER_ROOT/.git" || -f "$RUNNER_ROOT/.git" ]] ||
        fail "hardened runner is not an exact Git worktree: $RUNNER_ROOT"
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
    require_hash "$EXPECTED_RUNNER_SHA256" "$RUNNER_ROOT/$RUNNER_REL"
}

validate_receipt_with_authoritative_runner() {
    local receipt=$1
    /usr/bin/python3 - "$RUNNER_ROOT/$RUNNER_REL" "$receipt" <<'PY'
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
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    tx="$(mktemp -d "$TX_PARENT/.pbench4-${stamp}.XXXXXX")"
    measurement_candidate="$tx/MEASUREMENT.md.candidate"
    changelog_candidate="$tx/CHANGELOG.md.candidate"
    receipt_candidate="$tx/receipt.json.candidate"
    receipt_final="$ROOT/artifacts/operator/ratify_pbench4_fg4b_server_native_${stamp}.json"
    [[ ! -e "$receipt_final" ]] || fail "receipt destination already exists: $receipt_final"
    install -m 0600 -- "$MEASUREMENT" "$tx/MEASUREMENT.md.before"
    install -m 0600 -- "$CHANGELOG" "$tx/CHANGELOG.md.before"
    candidate_measurement >"$measurement_candidate"
    candidate_changelog >"$changelog_candidate"
    require_hash "$EXPECTED_AMENDED_MEASUREMENT_SHA256" "$measurement_candidate"
    require_hash "$EXPECTED_AMENDED_CHANGELOG_SHA256" "$changelog_candidate"
    write_receipt "$receipt_candidate" "$reviewer" "$(date -u --iso-8601=seconds)"

    local measurement_replaced=0 changelog_replaced=0 receipt_published=0
    rollback() {
        local status=$?
        trap - ERR INT TERM
        if [[ "$receipt_published" == 1 ]]; then
            rm -f -- "$receipt_final" || true
        fi
        if [[ "$changelog_replaced" == 1 ]]; then
            mv -f -- "$tx/CHANGELOG.md.before" "$CHANGELOG"
        fi
        if [[ "$measurement_replaced" == 1 ]]; then
            mv -f -- "$tx/MEASUREMENT.md.before" "$MEASUREMENT"
        fi
        exit "$status"
    }
    trap rollback ERR INT TERM
    mv -f -- "$measurement_candidate" "$MEASUREMENT"
    measurement_replaced=1
    if [[ "$TEST_MODE" == 1 && "${P_BENCH_4_TEST_FAIL_AFTER_MEASUREMENT:-0}" == 1 ]]; then
        false
    fi
    mv -f -- "$changelog_candidate" "$CHANGELOG"
    changelog_replaced=1
    validate_receipt_with_authoritative_runner "$receipt_candidate"
    mv -- "$receipt_candidate" "$receipt_final"
    receipt_published=1
    if [[ "$TEST_MODE" == 1 && "${P_BENCH_4_TEST_FAIL_AFTER_RECEIPT:-0}" == 1 ]]; then
        false
    fi
    printf 'ratified %s\n' "$stamp" >"$tx/COMPLETE"
    measurement_replaced=0
    changelog_replaced=0
    receipt_published=0
    trap - ERR INT TERM
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
