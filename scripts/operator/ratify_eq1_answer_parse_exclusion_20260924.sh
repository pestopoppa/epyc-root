#!/bin/bash
# ratify_eq1_answer_parse_exclusion_20260924.sh — flip debug_scorer's model-side
# answer-parse-failure handling from DEFAULT-OFF (scored wrong) to live (excluded), as
# ONE operator-ratified eval_quality instrument-era boundary.
#
#   Review:  bash scripts/operator/ratify_eq1_answer_parse_exclusion_20260924.sh --show
#   Apply:   bash scripts/operator/ratify_eq1_answer_parse_exclusion_20260924.sh --apply
#   Commit:  printed by --apply (orchestrator repo)
#
# WHY THIS NEEDS RATIFICATION (not just a code merge)
#
#   TD-21.11..21.14 (handoffs/active/typed-decision-plane.md; artifacts/audits/
#   td-json-consumer-audit-20260924.md J-03/J-05/J-06/J-07) converts four debug_scorer.py
#   sites (multiple_choice, f1_list, structural_exact_match, exact_match's last-resort
#   fallback) so each can tell "the model's answer could not be parsed into the required
#   shape" apart from "parsed and simply wrong". Today the former silently scores `False`
#   -- WRONG, IN the quality denominator -- indistinguishable from a genuine wrong answer,
#   with no counter. The code change makes that distinguishable and, when
#   EXCLUDE_UNPARSEABLE_ANSWERS is True, routes the former through
#   seeding_scoring.score_answer_or_error's EXISTING exclusion path (the same one an
#   unreachable judge or a malformed gold already uses): AnswerParseError -> disposition
#   scoring_failed -> EXCLUDED from the quality denominator, in both the seeding harness
#   and eval_tower's _score_generation (same shared function).
#
#   That is a live eval-quality-denominator change -- exactly the class of change
#   E17-eval-task-failed-scores-zero-quality (ETR-1) exists to fence -- so it landed
#   DEFAULT-OFF pending this ratification, and the era boundary must land at the SAME
#   moment as the flip, never as a silent default change in a merged commit.
#
#   THE TENSION THIS RATIFICATION ACCEPTS (flagged at 2026-09-24 main-session review, not
#   quietly resolved by this script): this boundary runs the OPPOSITE direction from E17.
#   E17 pulled a failure class (task_failed) INTO the quality denominator specifically so
#   a config that fails more could not shrink its own denominator instead of being
#   penalized. This boundary pulls a DIFFERENT failure class (a model's unparseable
#   output) OUT of the denominator -- the same shape of leniency E17 forbids for
#   agent/config failures, now applied to a parsing failure. The two eras are independent
#   (E17 governs rows that already carry a structural `error`; a model-side parse failure
#   carries none today), but the operator ratifying this one is accepting that a model
#   which cannot produce parseable output is measured as "not measured" rather than
#   "wrong". THE GUARD AGAINST THIS REOPENING E17's HOLE, already live and NOT gated
#   behind this flag: debug_scorer.parse_failure_stats() counts every parse failure
#   UNCONDITIONALLY (via _record_parse_failure, at all four sites, regardless of
#   EXCLUDE_UNPARSEABLE_ANSWERS), and EvalTower._aggregate reports
#   parse_failure_count / parse_failure_by_method / parse_failure_rate in `details`
#   beside quality/accuracy on every trial, bucketed per arm so concurrent arms never mix
#   counts (see debug_scorer.py's _PARSE_FAILURE_COUNTS module comment). A model/config
#   that games this exclusion by producing more unparseable output instead of more wrong
#   answers is visible in the SAME report as its inflated quality number -- never silent.
#   Per the 2026-07-20 standing rule (architect-model-selection-bench.md): a nonzero
#   parse_failure_rate makes that arm's quality number a prior, not standalone evidence.
#
# WHAT --apply DOES
#
#   1. Refuses unless $ORCH_ROOT's checked-out HEAD contains ALL THREE TD-21.11..21.14
#      commits below (i.e. refuses until td21/scorer has actually been reviewed and
#      merged into whatever branch that clone runs). Refuses if AutoPilot is running
#      (read-only /proc scan, never a name-pattern kill).
#   2. Flips, in $ORCH_ROOT/scripts/benchmark/debug_scorer.py:
#        EXCLUDE_UNPARSEABLE_ANSWERS = False  ->  EXCLUDE_UNPARSEABLE_ANSWERS = True
#      via an anchor-based single-occurrence text replace (refuses if the sentinel is not
#      found exactly once, so it can never silently touch the wrong line or a stale file).
#   3. Appends an era row to $ORCH_ROOT/orchestration/instrument_eras.yaml, scope
#      eval_quality, id E19-eval-answer-parse-failure-excluded-quality (next free E-number
#      after E17/E18; this file's own convention is E-numbers, not a separate "EQ-"
#      series), stating the E17 tension and the always-on-rate guard above, plus a
#      RECONCILIATION note.
#   4. RATIFICATION-SENTINEL TEST UPDATE (the RTG-09 lesson: a "default-off contract"
#      test left unchanged after its own flag flips is stale the moment the flip lands --
#      RTG-09's own test_default_config_reward_is_byte_identical_with_and_without_duration
#      needed a post-hoc rename into test_pre_e18_config_reward_is_byte_identical_..., plus
#      a new test_scoring_config_defaults_are_ratified, after E18 actually landed). This
#      script does that update ITSELF, in the SAME apply, via its own anchor-based
#      single-occurrence replace on
#      $ORCH_ROOT/tests/unit/test_debug_scorer_td21_parse_exclusion.py's
#      `#EQ1_RATIFICATION_TEST_SENTINEL` line and its paired assertion, so the post-flip
#      test run below is never stale by construction.
#   5. Stamps the boundary at APPLY time (not at code-review time), matching E17/E18's own
#      convention.
#   6. Runs the debug_scorer / eval_tower TD-21 test suite AGAINST THE NOW-FLIPPED TREE and
#      refuses (before printing commit instructions) if it fails.
#   7. Prints, but does NOT run, the commit command for the orchestrator repo. NOTHING IS
#      STAGED OR COMMITTED by this script.
#
# WHAT --apply DOES NOT DO
#
#   Does not commit, does not push, does not reload or restart anything, does not touch
#   the SCORE-25/26 golden-fixture file (test_debug_scorer_score25_26.py) or the B7
#   golden-corpus pin -- both were already hardened (TD-21.13 commit) to force
#   EXCLUDE_UNPARSEABLE_ANSWERS=False explicitly around the one input they carry that
#   would otherwise depend on this flag, so they stay byte-for-byte regardless of this
#   flip and need no post-flip update. The orchestrator API/autopilot process must be
#   reloaded separately for the flip to take effect once committed -- this script prints
#   that requirement and stops; per agents/shared/OPERATING_CONSTRAINTS.md ("Reload
#   ownership"), the session that owns inference executes that reload at its own boundary,
#   never this script.
#
# IDEMPOTENCY. Sentinel-checked: a second --apply refuses immediately (old value already
# flipped, or the era id is already present), rather than double-applying or corrupting
# a file on a re-run.
#
# IF YOU DECLINE. Nothing breaks. TD-21.11..21.14's code stays on main (once merged) fully
# inert -- EXCLUDE_UNPARSEABLE_ANSWERS stays False and every one of the four scorers keeps
# its pre-TD-21.11..21.14 output for every input. The parse-failure-rate reporting (item 6
# above) is UNCONDITIONAL and independent of this ratification -- it is already live and
# useful evidence for deciding whether to ratify at all.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ORCH_ROOT="${ORCH_ROOT:-/mnt/raid0/llm/epyc-orchestrator}"
SCORER="${ORCH_ROOT}/scripts/benchmark/debug_scorer.py"
ERAS="${ORCH_ROOT}/orchestration/instrument_eras.yaml"
TEST_FILE="${ORCH_ROOT}/tests/unit/test_debug_scorer_td21_parse_exclusion.py"
ERA_ID="E19-eval-answer-parse-failure-excluded-quality"
# The TD-21.11..21.14 commits on the epyc-orchestrator td21/scorer branch (landed
# 2026-09-24): af8a4a1b lands the four-site conversion DEFAULT-OFF; 940e0553 reverts the
# out-of-scope fish_json swap on _is_valid_json, arm-keys the parse-failure counters, and
# wires the per-arm rate into EvalTower._aggregate; ec412724 hardens the one SCORE-26
# golden fixture that this flip would otherwise make stale.
TD21_COMMITS=(af8a4a1b 940e0553 ec412724)
SENTINEL_OLD_FLAG='EXCLUDE_UNPARSEABLE_ANSWERS = False'
SENTINEL_NEW_FLAG='EXCLUDE_UNPARSEABLE_ANSWERS = True'
SENTINEL_OLD_TEST_MARK='#EQ1_RATIFICATION_TEST_SENTINEL: EXCLUDE_UNPARSEABLE_ANSWERS ships False'
SENTINEL_NEW_TEST_MARK='#EQ1_RATIFICATION_TEST_SENTINEL: EXCLUDE_UNPARSEABLE_ANSWERS ships True (ratified — see instrument_eras.yaml E19)'
SENTINEL_OLD_TEST_ASSERT='assert _SHIPPED_DEFAULT_ON_IMPORT is False'
SENTINEL_NEW_TEST_ASSERT='assert _SHIPPED_DEFAULT_ON_IMPORT is True'

usage() { echo "usage: $0 [--show|--apply]" >&2; exit 2; }
[[ $# -eq 1 ]] || usage

era_row() {  # $1 = boundary timestamp
    cat <<EOF
  - id: ${ERA_ID}
    from: "$1"
    scope: eval_quality
    note: >
      TD-21.11..21.14 answer-parse-failure-exclusion boundary (operator ratification
      2026-09-24, handoffs/active/typed-decision-plane.md; artifacts/audits/
      td-json-consumer-audit-20260924.md J-03/J-05/J-06/J-07). debug_scorer.py's
      multiple_choice / f1_list / structural_exact_match / exact_match scorers flip
      EXCLUDE_UNPARSEABLE_ANSWERS 0->1: a model-side answer that cannot be parsed into
      the scoring method's required shape now raises AnswerParseError, which
      seeding_scoring.score_answer_or_error converts to an EXCLUDED scoring_failed row
      (the same path an unreachable judge or a malformed gold already uses) instead of
      scoring it False/WRONG. Before this boundary such rows were IN the quality
      denominator scored wrong; after, they are OUT. Rows carry no separate policy key
      of their own (unlike E17's quality_denominator_policy) — era-label by timestamp,
      or by details.parse_failure_count/parse_failure_rate being present and nonzero on
      arms scored after this boundary (added in the SAME implementation below).

      TENSION WITH E17 (deliberate, flagged at 2026-09-24 review, not resolved by this
      note): this boundary runs the OPPOSITE direction from
      E17-eval-task-failed-scores-zero-quality, which pulled a failure class
      (task_failed) INTO the denominator specifically so a config that fails more could
      not shrink its own denominator instead of being penalized. This boundary pulls a
      DIFFERENT failure class (unparseable model output) OUT of the denominator — the
      same shape of leniency E17 forbids for agent/config failures, applied here to a
      parsing failure instead. The two are independent: E17 governs rows that already
      carry a structural error; a model-side parse failure carries none today, so
      nothing routed it through disposition classification before TD-21.11..21.14
      existed. GUARD AGAINST GAMING (why this is ratifiable despite the tension):
      debug_scorer.parse_failure_stats() counts every parse failure UNCONDITIONALLY —
      independent of this flag — and EvalTower._aggregate reports parse_failure_count /
      parse_failure_by_method / parse_failure_rate in details beside quality/accuracy on
      EVERY trial, bucketed per eval_batch_id so concurrent arms never mix counts. A
      model/config that games this exclusion by producing more unparseable output
      instead of more wrong answers is visible in the SAME report as its inflated
      quality number, never silently — per the 2026-07-20 standing rule
      (architect-model-selection-bench.md), a nonzero parse_failure_rate makes that
      arm's quality a prior, not standalone evidence.

      Implementation: epyc-orchestrator ${TD21_COMMITS[0]} + ${TD21_COMMITS[1]} +
      ${TD21_COMMITS[2]}. RECONCILIATION: pre-boundary quality UNDERSTATES any arm/suite
      with a nonzero parse-failure rate relative to post-boundary (an unparseable row
      was counted wrong pre-boundary; it is excluded post-boundary) — treat pre-boundary
      quality as a prior only for suites/arms with a nonzero parse_failure_stats() count
      at scoring time, or re-score from stored answers.

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
        echo "Targets (eval_quality instrument-era boundary, human-amendment-only):"
        echo "  ${SCORER}"
        echo "  ${ERAS}"
        echo "  ${TEST_FILE} (ratification-sentinel test update)"
        echo
        echo "== debug_scorer.py module flag flip =="
        echo "  ${SENTINEL_OLD_FLAG}"
        echo "    -> ${SENTINEL_NEW_FLAG}"
        echo
        echo "== ratification-sentinel test update =="
        echo "  ${SENTINEL_OLD_TEST_MARK}"
        echo "    -> ${SENTINEL_NEW_TEST_MARK}"
        echo "  ${SENTINEL_OLD_TEST_ASSERT}"
        echo "    -> ${SENTINEL_NEW_TEST_ASSERT}"
        echo
        echo "== era row appended to the eras: list (boundary = apply time) =="
        era_row "<apply-time UTC>"
        echo "== required TD-21.11..21.14 commits in \${ORCH_ROOT} HEAD =="
        printf '  %s\n' "${TD21_COMMITS[@]}"
        echo
        echo "After --apply: commit the orchestrator repo (printed then), and reload the"
        echo "orchestrator API/autopilot separately for the flip to take effect (not done here)."
        ;;
    --apply)
        [[ -f "${SCORER}" ]] || { echo "REFUSED: no file at ${SCORER}" >&2; exit 1; }
        [[ -f "${ERAS}" ]] || { echo "REFUSED: no file at ${ERAS}" >&2; exit 1; }
        [[ -f "${TEST_FILE}" ]] || { echo "REFUSED: no file at ${TEST_FILE}" >&2; exit 1; }

        old_flag_count="$({ grep -oF "${SENTINEL_OLD_FLAG}" "${SCORER}" || true; } | wc -l | tr -d ' ')"
        new_flag_count="$({ grep -oF "${SENTINEL_NEW_FLAG}" "${SCORER}" || true; } | wc -l | tr -d ' ')"
        if [[ "${old_flag_count}" -eq 0 ]]; then
            if [[ "${new_flag_count}" -gt 0 ]]; then
                echo "REFUSED: ${SCORER} already carries '${SENTINEL_NEW_FLAG}' — already applied." >&2
                exit 1
            fi
            echo "REFUSED: sentinel not found in ${SCORER}: ${SENTINEL_OLD_FLAG}" >&2
            exit 1
        fi
        if [[ "${old_flag_count}" -ne 1 ]]; then
            echo "REFUSED: expected exactly one occurrence of '${SENTINEL_OLD_FLAG}' in ${SCORER}, found ${old_flag_count}." >&2
            exit 1
        fi
        if grep -q "id: ${ERA_ID}" "${ERAS}"; then
            echo "REFUSED: ${ERA_ID} already present in ${ERAS}." >&2
            exit 1
        fi
        old_mark_count="$({ grep -oF "${SENTINEL_OLD_TEST_MARK}" "${TEST_FILE}" || true; } | wc -l | tr -d ' ')"
        if [[ "${old_mark_count}" -ne 1 ]]; then
            echo "REFUSED: expected exactly one occurrence of the ratification-sentinel mark in ${TEST_FILE}, found ${old_mark_count}." >&2
            exit 1
        fi
        old_assert_count="$({ grep -oF "${SENTINEL_OLD_TEST_ASSERT}" "${TEST_FILE}" || true; } | wc -l | tr -d ' ')"
        if [[ "${old_assert_count}" -ne 1 ]]; then
            echo "REFUSED: expected exactly one occurrence of '${SENTINEL_OLD_TEST_ASSERT}' in ${TEST_FILE}, found ${old_assert_count}." >&2
            exit 1
        fi

        for c in "${TD21_COMMITS[@]}"; do
            git -C "${ORCH_ROOT}" merge-base --is-ancestor "$c" HEAD 2>/dev/null || {
                echo "REFUSED: ${ORCH_ROOT} HEAD does not contain TD-21.11..21.14 commit $c." >&2
                echo "  Merge/fast-forward td21/scorer into that clone's checked-out branch first," >&2
                echo "  or update TD21_COMMITS in this script if the branch was squash-merged under a new SHA." >&2
                exit 1; }
        done

        live="$(autopilot_pids)"
        if [[ -n "${live// /}" ]]; then
            echo "REFUSED: AutoPilot is running (pid ${live}) on code that may predate this boundary." >&2
            echo "  Stop it first (full-stack rule: stop autopilot before the stack), then re-run." >&2
            exit 1
        fi

        git -C "${ORCH_ROOT}" diff --quiet -- scripts/benchmark/debug_scorer.py || {
            echo "REFUSED: ${SCORER} carries unstaged changes that are not this ratification:" >&2
            echo "  git -C ${ORCH_ROOT} diff -- scripts/benchmark/debug_scorer.py" >&2
            exit 1; }
        git -C "${ORCH_ROOT}" diff --quiet -- orchestration/instrument_eras.yaml || {
            echo "REFUSED: ${ERAS} carries unstaged changes; inspect them first." >&2
            exit 1; }
        git -C "${ORCH_ROOT}" diff --quiet -- tests/unit/test_debug_scorer_td21_parse_exclusion.py || {
            echo "REFUSED: ${TEST_FILE} carries unstaged changes that are not this ratification:" >&2
            echo "  git -C ${ORCH_ROOT} diff -- tests/unit/test_debug_scorer_td21_parse_exclusion.py" >&2
            exit 1; }

        boundary="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

        python3 - "${SCORER}" "${SENTINEL_OLD_FLAG}" "${SENTINEL_NEW_FLAG}" <<'PY'
import sys
path, old_v, new_v = sys.argv[1:4]
text = open(path, encoding="utf-8").read()
if text.count(old_v) != 1:
    sys.exit(f"REFUSED: expected exactly one occurrence of {old_v!r} in {path}, found {text.count(old_v)}")
text = text.replace(old_v, new_v, 1)
open(path, "w", encoding="utf-8").write(text)
PY

        python3 - "${TEST_FILE}" "${SENTINEL_OLD_TEST_MARK}" "${SENTINEL_NEW_TEST_MARK}" \
                                  "${SENTINEL_OLD_TEST_ASSERT}" "${SENTINEL_NEW_TEST_ASSERT}" <<'PY'
import sys
path, old_m, new_m, old_a, new_a = sys.argv[1:6]
text = open(path, encoding="utf-8").read()
if text.count(old_m) != 1:
    sys.exit(f"REFUSED: expected exactly one occurrence of {old_m!r} in {path}, found {text.count(old_m)}")
if text.count(old_a) != 1:
    sys.exit(f"REFUSED: expected exactly one occurrence of {old_a!r} in {path}, found {text.count(old_a)}")
text = text.replace(old_m, new_m, 1).replace(old_a, new_a, 1)
open(path, "w", encoding="utf-8").write(text)
PY

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

        echo "Applied to ${ORCH_ROOT} (boundary ${boundary}). NOTHING IS STAGED."
        echo
        echo "Running the TD-21.11..21.14 test suite against the now-flipped tree..."
        VENVPY="${ORCH_ROOT}/.venv/bin/python3"
        [[ -x "${VENVPY}" ]] || VENVPY="python3"
        "${VENVPY}" -m pytest \
            "${ORCH_ROOT}/tests/unit/test_debug_scorer_td21_parse_exclusion.py" \
            "${ORCH_ROOT}/tests/unit/test_td21_parse_failure_rate_reporting.py" \
            "${ORCH_ROOT}/tests/unit/test_debug_scorer_score25_26.py" \
            "${ORCH_ROOT}/tests/unit/test_b7_golden_corpus_pin.py" \
            "${ORCH_ROOT}/tests/unit/test_seeding_scoring.py" \
            "${ORCH_ROOT}/tests/unit/test_etr1_task_failed_scores_zero.py" -q || {
            echo "REFUSED (post-flip check): tests failed — inspect before committing anything." >&2
            exit 1
        }

        echo
        echo "Review, then commit the orchestrator repo from its own tree, pathspec-limited:"
        echo "  git -C ${ORCH_ROOT} diff -- scripts/benchmark/debug_scorer.py orchestration/instrument_eras.yaml tests/unit/test_debug_scorer_td21_parse_exclusion.py"
        echo "  git -C ${ORCH_ROOT} commit -m 'RATIFIED: EQ-1 answer-parse-failure exclusion live; era ${ERA_ID} (2026-09-24)' -- scripts/benchmark/debug_scorer.py orchestration/instrument_eras.yaml tests/unit/test_debug_scorer_td21_parse_exclusion.py"
        echo
        echo "REQUIRED, NOT DONE HERE: the orchestrator API/autopilot process must be reloaded"
        echo "for this flip to take effect (uvicorn :8000 reload / stack reload). Reload"
        echo "ownership: the session that owns inference executes it at its own boundary"
        echo "(agents/shared/OPERATING_CONSTRAINTS.md -> Inference and Benchmarks)."
        ;;
    *) usage ;;
esac
