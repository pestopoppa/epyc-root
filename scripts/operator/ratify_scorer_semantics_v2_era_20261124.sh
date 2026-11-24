#!/bin/bash
# ratify_scorer_semantics_v2_era_20261124.sh — append ONE eval_quality instrument-era row
# (E21-eval-scorer-semantics-v2-quality) to epyc-orchestrator/orchestration/instrument_eras.yaml.
#
#   Review:   bash ratify_scorer_semantics_v2_era_20261124.sh --show
#   Dry-run:  bash ratify_scorer_semantics_v2_era_20261124.sh --dry-run   (writes nothing)
#   Apply:    bash ratify_scorer_semantics_v2_era_20261124.sh --apply
#
# WHY THIS NEEDS RATIFICATION. The era registry is human-amendment-only
# (agents/shared/MEASUREMENT_POLICY.md -> Consolidated apply-time ratification). The change
# this row fences is ALREADY on origin/main (epyc-orchestrator 4110ed1c) and was
# operator-approved on 2026-11-24 ("land now as a new era"). This script records the
# boundary; it changes no scorer, pool or flag.
#
# WHAT --apply DOES: refuses unless (a) the scorer carries SCORER_SEMANTICS_VERSION =
# strict_finals_v2_20261124 in $ORCH_ROOT, (b) the era id is absent, (c) the era file has no
# uncommitted edits; then appends one row before `known_dead_instrument_items:`, re-parses
# the YAML, and prints the pathspec commit command.
# WHAT IT DOES NOT DO: stage or commit, touch autopilot_state.json, start/stop/reload anything.
set -euo pipefail

ORCH_ROOT="${ORCH_ROOT:-/mnt/raid0/llm/epyc-orchestrator}"
ERAS="${ORCH_ROOT}/orchestration/instrument_eras.yaml"
SCORER="${ORCH_ROOT}/scripts/benchmark/debug_scorer.py"
ERA_ID="E21-eval-scorer-semantics-v2-quality"
BOUNDARY="2026-11-24T11:46:39Z"   # commit time of epyc-orchestrator 4110ed1c on origin/main
SCORER_MARK='SCORER_SEMANTICS_VERSION = "strict_finals_v2_20261124"'

usage() { echo "usage: $0 [--show|--dry-run|--apply]" >&2; exit 2; }
[[ $# -eq 1 ]] || usage

era_row() {
    cat <<'ROW'
  - id: E21-eval-scorer-semantics-v2-quality
    from: "2026-11-24T11:46:39Z"
    scope: eval_quality
    scorer_semantics_version: strict_finals_v2_20261124
    note: >
      EV-SCORER-FUZZ-1 fix boxes, landed together (operator 2026-11-24: "land now as a new
      era"; epyc-orchestrator 4110ed1c). debug_scorer.py semantics v2:
      (1) SCORER-MV-GOLDWRAP: math_verify wraps a bare-LaTeX gold in $...$ before parse
      (3\sqrt{13} no longer reads as 3; MATH-500 gold coverage 0.88 -> 1.00).
      (2) SCORER-MV-STRICT-FINAL: math_verify requires a committed final (\boxed{}, <answer>
      or ####) and every committed final must verify against gold; prose-only and
      contradictory completions score False. <answer> tags are now READ: v1 parsed the whole
      completion and took the last expression in prose, ignoring the tag the models emit.
      (3) SCORER-EM-CONTRADICTORY: exact_match rejects conflicting structured finals (v1: first
      <answer> tag won but last \boxed{} won). Bare-last-line fallback unchanged.
      (4) SCORER-EM-FLOAT-TOL: exact_match numbers compare exactly at the gold's stated decimal
      precision; only float64 rendering noise (16+ significant digits, relative 1e-15) is
      tolerated (v1: absolute 1e-6).
      Rows carry details.scorer_semantics_version == strict_finals_v2_20261124 (absent = pre-v2)
      — era-label by that key where present, by timestamp otherwise.
      RECONCILIATION (history is NOT rescored or edited; era-label, then apply the verb):
      pre-boundary math_verify quality is DEFLATED on the math suite. Deterministic replay of
      the banked E7c EV-11 re-baseline (orchestration/reports/
      eval_tower_math_rebaseline_E7c_replay_scorer_v2, no inference; the v1-scorer replay
      reproduces every banked verdict): worker_general 0.7301 -> 0.8999 (312 F->T, 3 T->F),
      worker_math 0.6982 -> 0.8620 (301 F->T, 3 T->F), n=1819 each. Pre-boundary math quality
      is demote-to-prior; cross-boundary comparisons replay stored answers through the v2
      scorer (scripts/benchmark/replay_math_baseline_scorer.py). exact_match suites move only on
      contradictory-final and sub-1e-6-drift answers. B7 golden scorer corpus: 0 verdict changes.
      Fuzz: orchestrator artifacts/scorer_fuzz/report.md (schema v2, cases digest 502c54e2869e).

ROW
}

check_common() {
    [[ -f "${ERAS}" ]] || { echo "REFUSED: no file at ${ERAS}" >&2; exit 1; }
    [[ -f "${SCORER}" ]] || { echo "REFUSED: no file at ${SCORER}" >&2; exit 1; }
    grep -qF "${SCORER_MARK}" "${SCORER}" || { echo "REFUSED: scorer v2 (${SCORER_MARK}) not present in ${SCORER}; sync ${ORCH_ROOT} to origin/main (git merge --ff-only) first." >&2; exit 1; }
    if grep -q "id: ${ERA_ID}" "${ERAS}"; then echo "REFUSED: ${ERA_ID} already present in ${ERAS}." >&2; exit 1; fi
    git -C "${ORCH_ROOT}" diff --quiet -- orchestration/instrument_eras.yaml || { echo "REFUSED: ${ERAS} has uncommitted edits." >&2; exit 1; }
}

append_row() {  # $1 = target yaml file
    python3 - "$1" "$(era_row)" "${ERA_ID}" <<'PY'
import sys, yaml
path, row, era_id = sys.argv[1:4]
text = open(path, encoding="utf-8").read()
anchor = "\nknown_dead_instrument_items:"
if text.count(anchor) != 1:
    sys.exit(f"REFUSED: expected exactly one '{anchor.strip()}' anchor in {path}")
text = text.replace(anchor, "\n" + row.rstrip("\n") + "\n" + anchor, 1)
open(path, "w", encoding="utf-8").write(text)
d = yaml.safe_load(open(path, encoding="utf-8"))
rows = [e for e in d["eras"] if e.get("id") == era_id]
assert len(rows) == 1 and rows[0]["scope"] == "eval_quality", rows
assert rows[0]["scorer_semantics_version"] == "strict_finals_v2_20261124", rows
print("row parses:", rows[0]["id"], rows[0]["from"], rows[0]["scope"])
PY
}

case "$1" in
    --show)
        echo "Target (human-amendment-only era registry): ${ERAS}"
        echo "Boundary: ${BOUNDARY}"
        echo; era_row ;;
    --dry-run)
        check_common
        tmp="$(mktemp)"; trap 'rm -f "${tmp}"' EXIT
        cp "${ERAS}" "${tmp}"
        append_row "${tmp}"
        echo "DRY-RUN OK: preconditions hold and the row appends + parses. Nothing written to ${ERAS}."
        ;;
    --apply)
        check_common
        append_row "${ERAS}"
        echo "Applied to ${ERAS}. NOTHING IS STAGED. Commit (pathspec-limited) from the orchestrator tree:"
        echo "  git -C ${ORCH_ROOT} commit -m 'RATIFIED: era ${ERA_ID} (scorer semantics v2, EV-SCORER-FUZZ-1, 2026-11-24)' -- orchestration/instrument_eras.yaml"
        ;;
    *) usage ;;
esac
