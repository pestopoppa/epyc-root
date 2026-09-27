#!/bin/bash
# Refuse to ratify without a typed, human operator name.
#
# A ratification receipt is the record that a HUMAN performed an amendment of the
# measurement trust boundary. Until 2026-09-27 every ratifier resolved the signer as
# "${RATIFY_OPERATOR:-${USER:-unknown}}", so an unset name silently became the login
# account: RATIFY-TRUST-BOUNDARY-RECEIPTS-FIX-20260926 recorded `operator: "node"`,
# the container account agents run as. That is agent-written consent on a
# human-amendment-only path.
#
# Source this file and call ratify_require_operator before the first write:
#
#     source "$(dirname "${BASH_SOURCE[0]}")/lib/ratify_operator.sh"
#     [ "$MODE" != "apply" ] || ratify_require_operator
#
# It validates $RATIFY_OPERATOR (or the name passed as $1) and EXITS THE CALLING SCRIPT
# with 65 when the name is unset, a system account (node, root, ...), equal to the
# invoking login (`id -un` / $USER), or an agent/session id. On success it exports
# RATIFY_OPERATOR as the trimmed name. The rules live in ONE place:
# scripts/operator/ratification_receipt.py `operator_problem` (`check-operator`).

_RATIFY_OPERATOR_TOOL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/ratification_receipt.py"

ratify_require_operator() {
    local name="${1-${RATIFY_OPERATOR:-}}"
    local checked
    if [ ! -f "$_RATIFY_OPERATOR_TOOL" ]; then
        echo "REFUSING: $_RATIFY_OPERATOR_TOOL is missing, so the operator name cannot be checked." >&2
        exit 65
    fi
    if ! checked="$(python3 "$_RATIFY_OPERATOR_TOOL" check-operator "$name")"; then
        echo "REFUSING: a ratification must carry the name of the human who ran it." >&2
        echo "  Run it yourself from a terminal as: RATIFY_OPERATOR='<your name>' bash <script> --apply" >&2
        exit 65
    fi
    RATIFY_OPERATOR="$checked"
    export RATIFY_OPERATOR
}
