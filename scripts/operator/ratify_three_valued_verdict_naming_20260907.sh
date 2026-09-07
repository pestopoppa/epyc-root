#!/bin/bash
# ratify_three_valued_verdict_naming_20260907.sh — settle ONE naming drift across two repos.
#
#   Review:  bash scripts/operator/ratify_three_valued_verdict_naming_20260907.sh --show
#   Apply:   bash scripts/operator/ratify_three_valued_verdict_naming_20260907.sh --apply
#   Commit:  printed by --apply (TWO commits — this spans two repos)
#
# THE DRIFT. Two three-valued contracts exist for one state, in two repos:
#
#   epyc-orchestrator  orchestration/verification_report.schema.json  (RATIFIED, older)
#       outcome: [pass, fail, inconclusive]
#       inconclusive_reason: REQUIRED — but a free-text string with NO enum
#
#   epyc-root          scripts/benchmark/gate_verdict.py             (CJ-8, 2026-09-07)
#       VERDICTS: (pass, fail, out-of-coverage)
#       cause: REQUIRED, from a CLOSED 9-code registry, each naming a remedy
#
# `out-of-coverage` IS `inconclusive`. Two spellings for one state is standing drift: the day
# something serialises one and reads the other, the state silently becomes a fourth thing.
#
# WHAT THIS RATIFIES, and why it is not a coin-flip. The two contracts are complementary, and
# each already has what the other lacks — so this takes the better half of each rather than
# picking a winner:
#
#   1. `inconclusive` is the CANONICAL WIRE SPELLING. It is the already-ratified one, and
#      renaming a ratified cross-repo schema to match a one-day-old module would be backwards.
#      Anything crossing a repo or plane boundary, or landing in a stored artifact, says
#      `inconclusive`. `out-of-coverage` survives as gate-plane IN-CODE vocabulary only —
#      at that plane the useful thing to say is which items the checker never reached — and
#      `to_verification_outcome()` becomes the MANDATORY boundary translator, not optional
#      politeness. Two spellings are safe only while exactly one is on the wire.
#
#   2. `inconclusive_reason` GAINS THE CLOSED 9-CODE ENUM. This is the real repair and it flows
#      the other way. Today that field is free text, which means every producer invents its own
#      reason and nobody can count them — the exact defect that made `blocked = 0` uncountable
#      in the fan-out corpus this week. Each code names the subsystem to fix rather than the
#      subject to blame: `unparsed` says fix the extractor (a parse-failure rate read as a
#      quality gap is a scoring artifact), `no_reference` says fix the corpus join not the
#      model, `abstained` says the checker declined and that is not a negative label.
#
# WHY IT NEEDS YOU. `verification_report.schema.json` is a ratified cross-repo measurement-plane
# contract; closing a vocabulary on it changes what downstream producers may emit. That is a
# trust-boundary decision, not a refactor.
#
# IF YOU DECLINE. Nothing breaks today — `to_verification_outcome()` already interconverts, and
# CJ-8/CJ-9's tests lock the mapping. The cost of declining is that the free-text field stays
# uncountable and the two spellings stay co-equal, so the next producer picks one at random.
#
# WHAT THIS DOES NOT DO. It renames nothing in code, edits no test, and changes no verdict's
# behaviour. It adds an enum to one schema field and a ratification note to one module header.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ORCH="${REPO_ROOT}/repos/epyc-orchestrator"
PATCH="${REPO_ROOT}/artifacts/operator/three-valued-verdict-naming-20260907.patch"
SCHEMA_PATCH="/tmp/.ratify_three_valued_schema.$$.patch"
ROOT_PATCH="/tmp/.ratify_three_valued_root.$$.patch"
cleanup() { rm -f "${SCHEMA_PATCH}" "${ROOT_PATCH}"; }
trap cleanup EXIT

# The combined patch carries both repos' hunks; split on the second `diff --git`.
split_patch() {
    awk '/^diff --git a\/orchestration\//{f=1} /^diff --git a\/scripts\//{f=2}
         f==1{print > "'"${SCHEMA_PATCH}"'"} f==2{print > "'"${ROOT_PATCH}"'"}' "${PATCH}"
}

usage() { echo "usage: $0 [--show|--apply]" >&2; exit 2; }
[[ $# -eq 1 ]] || usage

case "$1" in
    --show)
        echo "Targets:"
        echo "  ${ORCH}/orchestration/verification_report.schema.json   (epyc-orchestrator)"
        echo "  ${REPO_ROOT}/scripts/benchmark/gate_verdict.py          (epyc-root)"
        echo "Amendment: ${PATCH}"
        echo
        cat "${PATCH}"
        ;;
    --apply)
        [[ -f "${PATCH}" ]] || { echo "REFUSED: no patch at ${PATCH}" >&2; exit 1; }
        split_patch

        # Preflight BOTH repos before touching either: a half-applied cross-repo naming
        # ratification is worse than an unapplied one, because the two halves are what make
        # the mapping total.
        git -C "${ORCH}" apply --check "${SCHEMA_PATCH}" \
            || { echo "REFUSED: schema hunk does not apply in epyc-orchestrator." >&2
                 echo "  Inspect: git -C ${ORCH} status --porcelain -- orchestration/" >&2; exit 1; }
        git -C "${REPO_ROOT}" apply --check "${ROOT_PATCH}" \
            || { echo "REFUSED: gate_verdict hunk does not apply in epyc-root." >&2
                 echo "  Inspect: git -C ${REPO_ROOT} status --porcelain -- scripts/benchmark/" >&2; exit 1; }

        git -C "${ORCH}" apply "${SCHEMA_PATCH}"
        git -C "${REPO_ROOT}" apply "${ROOT_PATCH}"
        echo "Applied to BOTH working trees. NOTHING IS STAGED."
        echo
        echo "Verify the enum landed and the schema still parses:"
        echo "  ${REPO_ROOT}/repos/epyc-orchestrator/.venv/bin/python -c \"import json; json.load(open('${ORCH}/orchestration/verification_report.schema.json')); print('schema parses')\""
        echo "  ${REPO_ROOT}/repos/epyc-orchestrator/.venv/bin/python -m pytest ${REPO_ROOT}/tests/benchmark/ -q"
        echo
        echo "Then TWO commits — these are two repos and must not be conflated:"
        echo
        echo "  git -C ${ORCH} add -- orchestration/verification_report.schema.json"
        echo "  git -C ${ORCH} commit -m 'RATIFIED: close the inconclusive_reason vocabulary to the 9-code cause registry (2026-09-07)'"
        echo
        echo "  git -C ${REPO_ROOT} add -- scripts/benchmark/gate_verdict.py"
        echo "  git -C ${REPO_ROOT} commit -m 'RATIFIED: inconclusive is the canonical wire spelling; out-of-coverage is gate-plane in-code only (2026-09-07)'"
        echo
        echo "Both trees are shared clones. Verify each staged diff shows ONLY this amendment"
        echo "before committing, and commit from the index rather than with a pathspec."
        ;;
    *) usage ;;
esac
