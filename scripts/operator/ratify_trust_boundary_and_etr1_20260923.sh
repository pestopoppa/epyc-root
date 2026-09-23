#!/bin/bash
# ratify_trust_boundary_and_etr1_20260923.sh — two operator rulings of 2026-09-23 on the
# human-only measurement paths, applied as ONE command.
#
#   Review:  bash scripts/operator/ratify_trust_boundary_and_etr1_20260923.sh --show
#   Apply:   bash scripts/operator/ratify_trust_boundary_and_etr1_20260923.sh --apply
#   Commit:  printed by --apply (two repos)
#
# THE TWO RULINGS
#
#   1. NIB2-59 — the agent digest is inside the trust boundary. agents/shared/MEASUREMENT_POLICY.md
#      calls itself human-amendment-only and every past edit to it was a RATIFIED commit, but
#      MEASUREMENT.md §5 listed the boundary without it. §5 now names it. No rule changes.
#
#   2. ETR-1 — agent/config-caused eval failures (`task_failed`) score 0 inside the quality
#      denominator; platform failures (`infra_failed`, `scoring_failed`) stay excluded. The code
#      is already on epyc-orchestrator main (44d0d4a0 + 927380a5) and stamps every aggregate with
#      `quality_denominator_policy: task_failed_scores_zero_v1`. What needs you: the §5 clause, a
#      CHANGELOG line, and the era row E17-eval-task-failed-scores-zero-quality (scope
#      eval_quality) in orchestration/instrument_eras.yaml — the era registry is human-only.
#
# WHAT THE ERA ROW DOES. The eval_quality era guard fences every quality row before the
# boundary as a PRIOR (kept, excluded from quality decisions). That is the point: pre-E17
# quality dropped failed rows, so it overstates any configuration that fails. The boundary is
# stamped at APPLY time, so apply only when the code that implements it will be what runs next:
# this script refuses unless the orchestrator clone contains both ETR-1 commits and no AutoPilot
# is running.
#
# IF YOU DECLINE. Nothing breaks. The ETR-1 code is live on main either way, and its rows are
# self-describing; without the era row the quality plane simply mixes pre- and post-ETR-1 rows.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ORCH_ROOT="${ORCH_ROOT:-/mnt/raid0/llm/epyc-orchestrator}"
PATCH="${REPO_ROOT}/artifacts/operator/measurement-trust-boundary-etr1-20260923.patch"
ERAS="${ORCH_ROOT}/orchestration/instrument_eras.yaml"
ERA_ID="E17-eval-task-failed-scores-zero-quality"
ETR1_COMMITS=(44d0d4a0 927380a5)
SENTINEL="Quality denominator (ETR-1)"

usage() { echo "usage: $0 [--show|--apply]" >&2; exit 2; }
[[ $# -eq 1 ]] || usage

era_row() {  # $1 = boundary timestamp
    cat <<EOF
  - id: ${ERA_ID}
    from: "$1"
    scope: eval_quality
    note: >
      ETR-1 quality-denominator boundary (operator ruling 2026-09-23; MEASUREMENT.md §5).
      Agent/config-caused failures (disposition task_failed) score 0 and stay in the
      quality denominator; infra_failed / scoring_failed stay excluded. Before this
      boundary both were dropped, so pre-E17 quality overstates any configuration that
      fails. Rows carry details.quality_denominator_policy == task_failed_scores_zero_v1
      (absent = pre-E17) — era-label by that key where present, by timestamp otherwise.
      Implementation: epyc-orchestrator 44d0d4a0 + 927380a5. RECONCILIATION: pre-boundary
      quality is a prior only; rebuild the frontier from post-boundary trials, or
      re-aggregate stored per-question rows where their disposition was persisted.

EOF
}

# Read-only /proc scan for a running AutoPilot (never a name-pattern tool; nothing is signalled).
autopilot_pids() {
    local d cmd
    for d in /proc/[0-9]*; do
        cmd="$(tr '\0' ' ' < "${d}/cmdline" 2>/dev/null || true)"
        [[ "$cmd" == *"autopilot.py"*" start"* ]] && printf '%s ' "${d#/proc/}"
    done
    return 0
}

case "$1" in
    --show)
        echo "Targets (all HUMAN-AMENDMENT-ONLY):"
        echo "  ${REPO_ROOT}/MEASUREMENT.md"
        echo "  ${ERAS}"
        echo
        echo "== MEASUREMENT.md amendment (${PATCH}) =="
        cat "${PATCH}"
        echo
        echo "== era row appended to the eras: list (boundary = apply time) =="
        era_row "<apply-time UTC>"
        ;;
    --apply)
        [[ -f "${PATCH}" ]] || { echo "REFUSED: no patch at ${PATCH}" >&2; exit 1; }
        if grep -q "${SENTINEL}" "${REPO_ROOT}/MEASUREMENT.md"; then
            echo "REFUSED: MEASUREMENT.md already carries '${SENTINEL}' — already applied." >&2; exit 1
        fi
        if grep -q "id: ${ERA_ID}" "${ERAS}"; then
            echo "REFUSED: ${ERA_ID} already present in ${ERAS}." >&2; exit 1
        fi
        for c in "${ETR1_COMMITS[@]}"; do
            git -C "${ORCH_ROOT}" merge-base --is-ancestor "$c" HEAD 2>/dev/null || {
                echo "REFUSED: ${ORCH_ROOT} HEAD does not contain ETR-1 commit $c." >&2
                echo "  Fast-forward that clone first, so the next AutoPilot runs the policy this era names." >&2
                exit 1; }
        done
        live="$(autopilot_pids)"
        if [[ -n "${live// /}" ]]; then
            echo "REFUSED: AutoPilot is running (pid ${live}) on code that may predate ETR-1." >&2
            echo "  Stop it first (full-stack rule: stop autopilot before the stack), then re-run." >&2
            exit 1
        fi
        for t in MEASUREMENT.md; do
            git -C "${REPO_ROOT}" diff --quiet -- "$t" || {
                echo "REFUSED: ${t} carries unstaged changes that are not this amendment:" >&2
                echo "  git -C ${REPO_ROOT} diff -- ${t}" >&2; exit 1; }
        done
        git -C "${ORCH_ROOT}" diff --quiet -- orchestration/instrument_eras.yaml || {
            echo "REFUSED: ${ERAS} carries unstaged changes; inspect them first." >&2; exit 1; }
        git -C "${REPO_ROOT}" apply --check "${PATCH}" || {
            echo "REFUSED: the MEASUREMENT.md amendment no longer applies cleanly; regenerate it." >&2; exit 1; }

        boundary="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        git -C "${REPO_ROOT}" apply "${PATCH}"
        python3 - "${ERAS}" "$(era_row "${boundary}")" <<'PY'
import sys
path, row = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
anchor = "\nknown_dead_instrument_items:"
if text.count(anchor) != 1:
    sys.exit(f"REFUSED: expected exactly one '{anchor.strip()}' anchor in {path}")
text = text.replace(anchor, "\n" + row.rstrip("\n") + "\n" + anchor, 1)
open(path, "w", encoding="utf-8").write(text)
PY
        python3 -c "import sys,yaml; d=yaml.safe_load(open(sys.argv[1])); assert any(e.get('id')==sys.argv[2] for e in d['eras'])" "${ERAS}" "${ERA_ID}" \
            || { echo "ERROR: era file failed to parse after the append — inspect ${ERAS}" >&2; exit 1; }

        echo "Applied to both working trees (boundary ${boundary}). NOTHING IS STAGED."
        echo
        echo "Review, then commit each repo from its own tree, pathspec-limited:"
        echo "  git -C ${REPO_ROOT} diff -- MEASUREMENT.md"
        echo "  git -C ${REPO_ROOT} commit -m 'RATIFIED: NIB2-59 digest inside the trust boundary; ETR-1 task_failed scores 0 (2026-09-23)' -- MEASUREMENT.md"
        echo "  git -C ${ORCH_ROOT} diff -- orchestration/instrument_eras.yaml"
        echo "  git -C ${ORCH_ROOT} commit -m 'RATIFIED: era ${ERA_ID} (ETR-1, 2026-09-23)' -- orchestration/instrument_eras.yaml"
        echo "Then push both (root through scripts/coordination/serialized_push.py)."
        ;;
    *) usage ;;
esac
