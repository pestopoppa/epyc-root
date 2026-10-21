#!/bin/bash
# ratify_ev19_corpus_era_20261021.sh — append ONE eval_quality instrument-era row
# (E20-eval-corpus-ev19-quality) to epyc-orchestrator/orchestration/instrument_eras.yaml.
#
#   Review:   bash scripts/operator/ratify_ev19_corpus_era_20261021.sh --show
#   Dry-run:  bash scripts/operator/ratify_ev19_corpus_era_20261021.sh --dry-run   (writes nothing)
#   Apply:    bash scripts/operator/ratify_ev19_corpus_era_20261021.sh --apply
#
# WHY THIS NEEDS RATIFICATION. The era registry is human-amendment-only
# (agents/shared/MEASUREMENT_POLICY.md -> Consolidated apply-time ratification). The two
# changes this row fences are ALREADY LIVE and were operator-approved on 2026-10-21
# ("Swap now, new era" / "Accept variants" / "Go"):
#   1. live question pool swapped to corpus-ev19-20261021 (sha256 f8b53663...), 15:19:42Z;
#   2. f1_list scorer: normalised bare-None abstention accepted (orchestrator dd5bcf06).
# This script records that boundary; it changes no scorer, pool or flag.
#
# WHAT --apply DOES: refuses unless (a) the live pool's sha256 is the expected one, (b) the
# scorer fix is present in $ORCH_ROOT, (c) the era id is absent; then appends one row before
# `known_dead_instrument_items:`, re-parses the YAML, and prints the pathspec commit command.
# WHAT IT DOES NOT DO: stage or commit, touch autopilot_state.json, start/stop/reload
# anything. The era-advance path writes active_instrument_eras at the next AutoPilot start.
set -euo pipefail

ORCH_ROOT="${ORCH_ROOT:-/mnt/raid0/llm/epyc-orchestrator}"
RESEARCH_ROOT="${RESEARCH_ROOT:-/mnt/raid0/llm/epyc-inference-research}"
ERAS="${ORCH_ROOT}/orchestration/instrument_eras.yaml"
SCORER="${ORCH_ROOT}/scripts/benchmark/debug_scorer.py"
POOL="${RESEARCH_ROOT}/benchmarks/prompts/question_pool.jsonl"
POOL_SHA="f8b536632b0d95feee339333f46247125def384b6d36d65b39711155825d7f0a"
OLD_POOL_SHA="64218c27e07400acf3b10a3cac05a410d5ee67814f353788ab75a19c84dde584"
ERA_ID="E20-eval-corpus-ev19-quality"
BOUNDARY="2026-10-21T15:19:42Z"   # moment the live pool was renamed into place
SCORER_MARK="_normalize_abstention_candidate"

usage() { echo "usage: $0 [--show|--dry-run|--apply]" >&2; exit 2; }
[[ $# -eq 1 ]] || usage

era_row() {
    cat <<ROW
  - id: ${ERA_ID}
    from: "${BOUNDARY}"
    scope: eval_quality
    corpus_version: corpus-ev19-20261021
    pool_sha256: ${POOL_SHA}
    prior_pool_sha256: ${OLD_POOL_SHA}   # backup: question_pool.jsonl.pre-corpus-ev19-20261021 beside the live pool
    note: >
      EV-19 corpus fix + tulving_episodic none-variant scorer. Operator 2026-10-21:
      "Swap now, new era" (swap the live pool to the fixed corpus), "Accept variants"
      (accept "- None" / "None." / "Answer: None" on tulving_episodic controls), final "Go".
      (1) CORPUS corpus-ev19-20261021 (research 795cf9626, ledger benchmarks/prompts/corpus_revisions.json):
      mmlu_pro 12,032 rows re-derived so scoring_config carries choices A-J (the live pool had
      scoring_config={} on all, so the 2,053 rows with gold I/J, 17.1%, could never pass);
      livecodebench 2,360 -> 704 rows with executable oracles (1,656 without a validated oracle
      EXCLUDED; the old substring oracle "def " passed any Python answer); real_suite_v1 1.0 -> 1.1
      (0007 executable oracle; 0006, 0034 not scorable).
      (2) SCORER debug_scorer._score_f1_list (orchestrator dd5bcf06): a reply that is, as a WHOLE, a
      bare abstention is correct on an empty-gold control, modulo leading bullet, "Answer:" prefix,
      trailing punctuation, case and whitespace. "None" inside a longer answer, or a reply naming
      events, still fails. Affects the 182 of 456 tulving_episodic empty-gold rows only.
      RECONCILIATION (history is NOT rescored or edited; era-label, then apply the verb):
      pre-boundary mmlu_pro quality is DEFLATED (ceiling ~0.83 of true; demote-to-prior);
      pre-boundary livecodebench quality is INFLATED toward the cap and is not a code-ability
      measure (demote-to-prior; most journaled trials predate this by months); pre-boundary
      real_suite_v1 carries a <=6% upward bias; pre-boundary tulving_episodic stands (the
      corpus was never defective), but a "- None"-style reply that scored false before scores
      true after, so a cross-boundary tulving delta needs a replay of stored answers.
      Sample sizes shift (livecodebench pool 2,360 -> 704): era-label by this id before any
      cross-boundary frontier or baseline comparison. Details:
      epyc-orchestrator data/autopilot/corpus_fix_ev19_history_impact.md.
      KNOWN RESIDUAL (not fixed here, EV-19 full-pool self-check v2): 22 of 11,214 "thinking"
      ARC rows carry gold "1"/"2"/"3" with empty choices; the scorer REFUSES them (excluded from
      the denominator, never scored wrong). Every other suite self-checks 0 wrong.

ROW
}

check_common() {
    [[ -f "${ERAS}" ]] || { echo "REFUSED: no file at ${ERAS}" >&2; exit 1; }
    [[ -f "${SCORER}" ]] || { echo "REFUSED: no file at ${SCORER}" >&2; exit 1; }
    grep -q "${SCORER_MARK}" "${SCORER}" || { echo "REFUSED: scorer fix (${SCORER_MARK}) not present in ${SCORER}; sync ${ORCH_ROOT} to origin/main (git merge --ff-only) first." >&2; exit 1; }
    if grep -q "id: ${ERA_ID}" "${ERAS}"; then echo "REFUSED: ${ERA_ID} already present in ${ERAS}." >&2; exit 1; fi
    live="$(sha256sum "${POOL}" | cut -d' ' -f1)"
    [[ "${live}" == "${POOL_SHA}" ]] || { echo "REFUSED: live pool sha ${live} != ${POOL_SHA}" >&2; exit 1; }
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
assert len(rows) == 1 and rows[0]["scope"] == "eval_quality" and rows[0]["corpus_version"] == "corpus-ev19-20261021", rows
print("row parses:", rows[0]["id"], rows[0]["from"], rows[0]["scope"])
PY
}

case "$1" in
    --show)
        echo "Target (human-amendment-only era registry): ${ERAS}"
        echo "Live pool: ${POOL}"
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
        echo "  git -C ${ORCH_ROOT} commit -m 'RATIFIED: era ${ERA_ID} (EV-19 corpus-ev19-20261021 + tulving none-variants, 2026-10-21)' -- orchestration/instrument_eras.yaml"
        ;;
    *) usage ;;
esac
