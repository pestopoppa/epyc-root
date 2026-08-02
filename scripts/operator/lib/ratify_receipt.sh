#!/bin/bash
# Shared receipt hooks for operator ratification scripts.
#
# MEASUREMENT.md §5 requires the human to sign ONCE over a consolidated bundle:
# protocol + evidence hashes + validation results + exact state diff. Source this
# file and bracket the amendment with two calls:
#
#     source "$ROOT/scripts/operator/lib/ratify_receipt.sh"
#     receipt_capture MEASUREMENT.md CHANGELOG.md          # BEFORE the edit
#     ... apply the amendment ...
#     receipt_emit <ratification-id> <protocol-id> [--protocol-new]
#
# Evidence and validation come from the environment so a historical script can be
# re-run with the citations it should always have carried:
#
#     RATIFY_EVIDENCE="data/<campaign> data/<campaign>/results.tsv"
#     RATIFY_NO_EVIDENCE_REASON="editorial erratum; no new measurement"
#     RATIFY_VALIDATION="scripts/validate/check_claims_grammar.sh MEASUREMENT.md"
#     RATIFY_OPERATOR="<name>"
#
# `receipt_emit` returns non-zero on REFUSED (1) or COULD-NOT-CHECK (2). It does
# NOT roll the amendment back — the receipt is the record the human reads before
# committing, and a refused receipt means: do not commit this.

: "${ROOT:=/workspace}"
RECEIPT_TOOL="$ROOT/scripts/operator/ratification_receipt.py"
RECEIPT_PRE_STATE="${RECEIPT_PRE_STATE:-}"

receipt_capture() {
    if [ ! -f "$RECEIPT_TOOL" ]; then
        echo "COULD-NOT-CHECK: $RECEIPT_TOOL is missing; MEASUREMENT.md §5 requires a" >&2
        echo "  consolidated receipt and none can be produced. Refusing to amend." >&2
        return 2
    fi
    RECEIPT_PRE_STATE="$(mktemp -t ratify-pre-XXXXXX.json)"
    local args=()
    local f
    for f in "$@"; do args+=(--state "$f"); done
    python3 "$RECEIPT_TOOL" capture --repo-root "$ROOT" "${args[@]}" --out "$RECEIPT_PRE_STATE"
}

receipt_emit() {
    local rid="$1"; shift
    local pid="$1"; shift
    if [ -z "${RECEIPT_PRE_STATE:-}" ] || [ ! -f "$RECEIPT_PRE_STATE" ]; then
        echo "COULD-NOT-CHECK: no pre-amendment snapshot, so no exact state diff exists." >&2
        echo "  Call receipt_capture BEFORE applying the amendment." >&2
        return 2
    fi
    local args=(emit --repo-root "$ROOT" --pre "$RECEIPT_PRE_STATE"
                --ratification-id "$rid" --protocol-id "$pid")
    local item
    for item in ${RATIFY_EVIDENCE:-}; do args+=(--evidence "$item"); done
    if [ -n "${RATIFY_NO_EVIDENCE_REASON:-}" ]; then
        args+=(--no-evidence-reason "$RATIFY_NO_EVIDENCE_REASON")
    fi
    if [ -n "${RATIFY_VALIDATION:-}" ]; then
        args+=(--validation "$RATIFY_VALIDATION")
    fi
    if [ -n "${RATIFY_OPERATOR:-}" ]; then
        args+=(--operator "$RATIFY_OPERATOR")
    fi
    args+=("$@")
    python3 "$RECEIPT_TOOL" "${args[@]}"
}
