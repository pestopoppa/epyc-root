#!/bin/bash
# Operator ratification — P-AK-SEARCH-1-A3: let the loop remember.
#
# DECISION D1 of handoffs/active/autokernel-rebuild-program.md (INF-66).
#
# THIS SCRIPT IS NOT RUN BY AN AGENT. measurement/protocols/*.md sits inside the
# human-amendment-only trust boundary (invariant 15), and agent writes there are
# hook-blocked. It is staged here so the operator can read the amendment, decide,
# and apply it in one command.
#
#   Review:  bash scripts/operator/ratify_ak_search_1_a3_20260828.sh --show
#   Apply:   bash scripts/operator/ratify_ak_search_1_a3_20260828.sh --apply
#
# ---------------------------------------------------------------------------
# WHAT IS BEING AMENDED, AND WHY
#
# P-AK-SEARCH-1 denial 4 currently reads, in part:
#
#     "A later AutoKernel campaign MAY use a prior record for HYPOTHESIS FORMATION
#      ONLY — never to rank, bank, compose, or contribute to readiness."
#
# Choosing which hypothesis to attempt next IS ranking. So a planner that reads its
# own history to prioritise is, on a strict reading, non-conformant — which is very
# likely why the mechanism was never built.
#
# MEASURED CONSEQUENCE. Across 355 hypothesis-ledger events the loop fired
# HYPOTHESIS_RESOLVED zero times, ADOPTED zero, REOPENED zero. One bit-deposit
# rewrite of vec_dot_q5_0_q8_1_impl was re-proposed 38 times across 37 deployments,
# because every crash minted a fresh sealed deployment and reset the counters. The
# loop has no memory, and the protocol is one of the reasons.
#
# WHAT THE AMENDMENT GRANTS. Within a FIXED EPOCH — same anchor commit, same build
# recipe, same host state — a campaign may read prior campaigns' records to rank its
# own next attempt. Nothing else changes.
#
# WHAT IT DOES NOT GRANT. Every denial in "What this protocol does NOT authorize"
# stays verbatim: no banking, no composition authority, no readiness contribution, no
# promotion, no retro-certification. A search record still can never become a claim.
#
# THE MECHANISM THAT REPLACES THE PROHIBITION. Denial 4's stated rationale is that a
# later campaign re-derives its own calibration, so prior numbers are not comparable.
# That concern is now ENCODED rather than prohibited: every record carries the SHA-256
# of its epoch (controller/experiments.py::epoch_sha256), and recall marks a
# cross-epoch record `stale_epoch: true` / `comparable_measurement: false`. The record
# is still visible — knowing a mechanism was tried is formation — but its NUMBER is
# never presented as comparable.
#
# This is not invented here. It is AP-28's context-hash staleness, already running in
# orchestration/repl_memory/strategy_store.py, where DEFAULT_CONTEXT_FILES are hashed
# on every store() and entries from a different epoch take a validity penalty at
# retrieve() time.
#
# UNTIL THIS IS APPLIED, the store is built and wired but `ranking_authorized`
# defaults to False: records reach the planner for hypothesis formation and nothing
# computes an order of merit from them. Applying this amendment is what lets that
# flag be turned on.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROTOCOL="${REPO_ROOT}/measurement/protocols/kernel-research.md"
PATCH="${REPO_ROOT}/artifacts/operator/ak-search-1-a3-20260828.patch"

usage() {
    echo "usage: $0 [--show|--apply]" >&2
    exit 2
}

[[ $# -eq 1 ]] || usage

case "$1" in
    --show)
        echo "Protocol:  ${PROTOCOL}"
        echo "Amendment: ${PATCH}"
        echo
        if [[ -f "${PATCH}" ]]; then
            cat "${PATCH}"
        else
            echo "NOTE: the amendment text has not been drafted into ${PATCH} yet."
            echo "The operator drafts the exact clause; this script only stages the apply."
        fi
        ;;
    --apply)
        [[ -f "${PATCH}" ]] || {
            echo "REFUSED: no amendment patch at ${PATCH}" >&2
            exit 1
        }
        # Isolated staging: never a blanket `git add`. A human-only path must not
        # ride into a commit alongside anything else.
        git -C "${REPO_ROOT}" apply --cached "${PATCH}"
        echo "Staged. Review with: git -C ${REPO_ROOT} diff --cached -- measurement/protocols/kernel-research.md"
        echo "Then commit that path alone."
        ;;
    *) usage ;;
esac
