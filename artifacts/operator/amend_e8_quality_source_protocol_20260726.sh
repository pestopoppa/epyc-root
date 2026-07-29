#!/bin/bash
# Human-only E8 scorer-source/protocol amendment. Never invoked by AutoPilot.
set -euo pipefail

ROOT="${EPYC_ROOT:-/mnt/raid0/llm/epyc-root}"
RESEARCH="${EPYC_RESEARCH:-/mnt/raid0/llm/epyc-inference-research}"
ORCH="${EPYC_ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
RESEARCH_PYTHON="${EPYC_RESEARCH_PYTHON:-$RESEARCH/.venv/bin/python}"
ORCH_PYTHON="${EPYC_ORCH_PYTHON:-$ORCH/.venv/bin/python}"
POOL_PYTHON="${EPYC_POOL_PYTHON:-/mnt/raid0/llm/opendataloader-bench/.venv/bin/python}"
HF_HOME_PIN="${EPYC_E8_HF_HOME:-$RESEARCH/benchmarks/prompts/pool_rebuild_a3_20260721/_hfmerge}"
VL_PREFIX="${EPYC_E8_VL_PREFIX:-$ORCH/benchmarks/images/vl}"
SCRIPT="$ROOT/artifacts/operator/amend_e8_quality_source_protocol_20260726.sh"
HELPER="$ROOT/artifacts/operator/e8_quality_source_amendment.py"
DECISION="$ROOT/artifacts/operator/e8_quality_source_protocol_amendment_20260726.md"
MANIFEST_DEFAULT="$ROOT/artifacts/operator/e8_quality_source_protocol_amendment_manifest_20260726.json"
MANIFEST="${E8_AMENDMENT_MANIFEST:-$MANIFEST_DEFAULT}"
TOKEN="AMEND-E8-QUALITY-SCORER-SOURCE-20260726"
RECOVERY_TOKEN="RECOVER-E8-QUALITY-SOURCE-20260726"
# Detached integrity root: this reviewed wrapper pins the manifest; the
# manifest pins downstream executable/support artifacts and omits this wrapper.
MANIFEST_SHA256="2f01ff86d100cd53f2cb214c8cde6c140a0bc12d98eeab28e572b0b83d84ce39"
TX_PARENT="$ROOT/artifacts/operator/e8_quality_source_amendment_transactions"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
sha256() { sha256sum -- "$1" | awk '{print $1}'; }

verify_integrity_root() {
    local expected="$MANIFEST_SHA256"
    if [[ "${E8_AMENDMENT_TEST_MODE:-0}" == 1 ]]; then
        [[ "$ROOT" != "/mnt/raid0/llm/epyc-root" ]] ||
            fail "test mode refuses the canonical root"
        expected="${E8_AMENDMENT_MANIFEST_SHA256:-}"
        [[ "$expected" =~ ^[0-9a-f]{64}$ ]] ||
            fail "test mode requires E8_AMENDMENT_MANIFEST_SHA256"
    else
        [[ "$MANIFEST" == "$MANIFEST_DEFAULT" ]] ||
            fail "manifest override is test-only"
    fi
    [[ -f "$MANIFEST" ]] || fail "amendment manifest is missing: $MANIFEST"
    [[ "$(sha256 "$MANIFEST")" == "$expected" ]] ||
        fail "amendment manifest SHA-256 mismatch"
}

plan() {
    [[ -f "$DECISION" ]] || fail "decision bundle is missing: $DECISION"
    sed -n '1,180p' "$DECISION"
}

helper() {
    "$ORCH_PYTHON" -c 'import httpx, yaml' ||
        fail "orchestrator control interpreter lacks required httpx/yaml dependencies: $ORCH_PYTHON"
    "$ORCH_PYTHON" "$HELPER" \
        --root "$ROOT" \
        --research "$RESEARCH" \
        --orchestrator "$ORCH" \
        --research-python "$RESEARCH_PYTHON" \
        --orchestrator-python "$ORCH_PYTHON" \
        --pool-python "$POOL_PYTHON" \
        --hf-home "$HF_HOME_PIN" \
        --vl-prefix "$VL_PREFIX" \
        --manifest "$MANIFEST" \
        "$@"
}

validate_only() {
    helper --validate-only
}

attest() {
    [[ $# -eq 1 && "$1" == "$TOKEN" ]] || fail "usage: --attest $TOKEN"
    [[ "$MANIFEST" == "$MANIFEST_DEFAULT" ]] ||
        fail "operator attestation refuses a manifest override"
    mkdir -p -- "$TX_PARENT"
    # Lock the reviewed script inode without creating or modifying a lock file.
    exec 9<"$SCRIPT"
    flock -n 9 || fail "another E8 source amendment transaction holds the lock"
    local stamp tx
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    tx="$TX_PARENT/${stamp}-$$"
    helper --apply --transaction-root "$tx"
}

recover() {
    [[ $# -eq 3 && "$2" == "--attest" && "$3" == "$RECOVERY_TOKEN" ]] ||
        fail "usage: --recover TRANSACTION --attest $RECOVERY_TOKEN"
    exec 9<"$SCRIPT"
    flock -n 9 || fail "another E8 source amendment transaction holds the lock"
    local transaction canonical_parent
    transaction="$(realpath -e -- "$1")" ||
        fail "recovery transaction does not exist"
    canonical_parent="$(realpath -e -- "$TX_PARENT")" ||
        fail "canonical transaction root does not exist"
    [[ "$(dirname -- "$transaction")" == "$canonical_parent" ]] ||
        fail "recovery transaction is outside the canonical transaction root"
    helper --recover "$transaction"
}

verify_integrity_root

case "${1:-}" in
    --plan)
        [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--attest TOKEN'
        plan
        ;;
    --validate-only)
        [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--attest TOKEN'
        validate_only
        ;;
    --attest)
        shift
        attest "$@"
        ;;
    --recover)
        shift
        recover "$@"
        ;;
    *)
        fail 'usage: --plan|--validate-only|--attest TOKEN|--recover TRANSACTION --attest TOKEN'
        ;;
esac
