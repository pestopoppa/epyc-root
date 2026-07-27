#!/bin/bash
# Human-only E8 baseline-state apply wrapper. The runner remains evidence-only.
set -euo pipefail

ROOT="${EPYC_ROOT:-/mnt/raid0/llm/epyc-root}"
ORCH="${EPYC_ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
PYTHON="${EPYC_PYTHON:-$ORCH/.venv/bin/python}"
EVIDENCE="${E8_QUALITY_BASELINE_EVIDENCE:-$ROOT/artifacts/operator/e8_quality_baseline_evidence_20260726/e8_quality_baseline_evidence.json}"
CANONICAL_EVIDENCE="$ROOT/artifacts/operator/e8_quality_baseline_evidence_20260726/e8_quality_baseline_evidence.json"
INTEGRITY="$ROOT/artifacts/operator/e8_quality_baseline_state_apply_integrity_20260726.json"
EXPECTED_INTEGRITY_SHA256="f037d76f6994f58ba3ba2df570b468301ffb51dae94fad6da1e1f658c10a7a07"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

verify_integrity() {
    [[ -f "$INTEGRITY" ]] || fail "missing detached apply-integrity root: $INTEGRITY"
    [[ "$(sha256sum -- "$INTEGRITY" | awk '{print $1}')" == "$EXPECTED_INTEGRITY_SHA256" ]] ||
        fail 'detached apply-integrity root hash mismatch'
    jq -e '
        .schema == "epyc.operator_e8_quality_baseline_state_apply_integrity.v1" and
        (.artifacts | type == "object") and
        (.artifacts | keys == [
          "artifacts/operator/apply_e8_quality_baseline_state.py",
          "artifacts/operator/prepare_e8_quality_baseline_reseed_20260726.sh"
        ])
    ' "$INTEGRITY" >/dev/null || fail 'detached apply-integrity root schema mismatch'
    local relative expected actual
    for relative in \
        artifacts/operator/apply_e8_quality_baseline_state.py \
        artifacts/operator/prepare_e8_quality_baseline_reseed_20260726.sh; do
        expected="$(jq -er --arg path "$relative" '.artifacts[$path]' "$INTEGRITY")" ||
            fail "missing integrity pin for $relative"
        [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || fail "malformed integrity pin for $relative"
        actual="$(sha256sum -- "$ROOT/$relative" | awk '{print $1}')" ||
            fail "cannot hash reviewed artifact $relative"
        [[ "$actual" == "$expected" ]] || fail "reviewed artifact hash mismatch: $relative"
    done
}

verify_integrity

exec "$PYTHON" "$ROOT/artifacts/operator/apply_e8_quality_baseline_state.py" \
    --state "$ORCH/orchestration/autopilot_state.json" \
    --evidence "$EVIDENCE" \
    --canonical-evidence "$CANONICAL_EVIDENCE" \
    --validator "$ROOT/artifacts/operator/prepare_e8_quality_baseline_reseed_20260726.sh" \
    --transaction-dir "$ROOT/artifacts/operator/e8_quality_baseline_state_apply_20260726" \
    --attestation "$ROOT/artifacts/operator/ratify_e8_quality_baseline_state_apply_20260726.json" \
    "$@"
