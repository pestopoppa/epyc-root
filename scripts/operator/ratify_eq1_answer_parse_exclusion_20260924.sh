#!/bin/bash
# ratify_eq1_answer_parse_exclusion_20260924.sh — ONE operator-ratified
# eval_quality instrument-era boundary (E19) that now flips TWO independent
# debug_scorer.py flags together:
#
#   1. EXCLUDE_UNPARSEABLE_ANSWERS (EQ-1, TD-21.11..21.14): model-side
#      answer-parse-failure handling, DEFAULT-OFF (scored wrong) -> live
#      (excluded).
#   2. CONSTRAIN_JUDGE_OUTPUT (TD-21.9/21.10/21.15): LLM-judge OUTPUT SHAPE
#      (a schema-constrained, strictly-parsed verdict/rubric-score reply
#      instead of a free-text prefix-match/brace-slice fish), DEFAULT-OFF ->
#      live. TD-21.32: judge BINDING (which model) is untouched by either
#      flag — both are pure output-shape/parse-strictness changes against
#      whatever judge the existing LLM_JUDGE_ROLE/`_llm_judge_force_role`
#      seam already resolves to.
#
#   Bundled under ONE era row (not two) because both are eval-quality-
#   denominator-adjacent changes landing at the SAME 2026-09-24 review and
#   the same operator sign-off; see `era_row()` below for the combined note.
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
#   TD-21.9/21.10/21.15 (CONSTRAIN_JUDGE_OUTPUT) IS A SEPARATE CHANGE BUNDLED HERE, NOT A
#   RESTATEMENT OF THE ABOVE: it converts the LLM-judge sites (boolean equivalence verdict
#   at debug_scorer.py's orchestrator AND raw-llama-server branches; the autopilot rubric
#   judge's {"scores": {...}} reply in eval_tower.py) from a free-text
#   prefix-match/fence-strip-plus-brace-slice fish to a schema-constrained request plus a
#   strict parse (and, for the rubric judge only, ONE parse_with_repair extraction turn on
#   a miss, back to the SAME pinned judge role). This too changes live eval-quality numbers
#   -- a judge that used to have its free-text reply loosely fished now either parses
#   strictly or the row is excluded (boolean judge: ScoringUnavailableError -> scoring_failed,
#   the same always-excluded class as an unreachable judge; rubric judge: an extra repair
#   turn recovers some replies the old fisher missed, changing rubric_source's judge/
#   heuristic_fallback split) -- so it landed DEFAULT-OFF exactly like EQ-1, and is folded
#   into this same ratification rather than shipped as a second script, because both flags
#   review at the same 2026-09-24 boundary. ALWAYS-ON GUARD, independent of this flag:
#   debug_scorer.judge_parse_stats() counts every judge parse outcome (parsed / repaired /
#   unparseable) UNCONDITIONALLY, surfaced in EvalTower._aggregate as judge_parse_by_site /
#   judge_parse_unparseable_rate beside quality/accuracy on every trial -- the same
#   never-silent contract EQ-1's parse_failure_stats() already gives the model-side flag.
#
# WHAT --apply DOES
#
#   1. Refuses unless $ORCH_ROOT's checked-out HEAD contains EVERY commit in the single
#      TD21_COMMITS array below — both the EQ-1 (TD-21.11..21.14) commits and the judge
#      OUTPUT SHAPE (TD-21.9/21.10/21.15) commit (i.e. refuses until both branches have
#      actually been reviewed and merged into whatever branch that clone runs). Refuses
#      if AutoPilot is running (read-only /proc scan, never a name-pattern kill).
#   2. Flips, in $ORCH_ROOT/scripts/benchmark/debug_scorer.py, BOTH flags:
#        EXCLUDE_UNPARSEABLE_ANSWERS = False  ->  EXCLUDE_UNPARSEABLE_ANSWERS = True
#        CONSTRAIN_JUDGE_OUTPUT      = False  ->  CONSTRAIN_JUDGE_OUTPUT      = True
#      via anchor-based single-occurrence text replaces, each independently checked
#      (refuses if either sentinel is not found exactly once, so it can never silently
#      touch the wrong line, apply only one flag, or touch a stale file).
#   3. Appends ONE era row to $ORCH_ROOT/orchestration/instrument_eras.yaml, scope
#      eval_quality, id E19-eval-answer-parse-failure-excluded-quality (next free E-number
#      after E17/E18; this file's own convention is E-numbers, not a separate "EQ-"
#      series), stating the E17 tension, the always-on-rate guards for BOTH flags above,
#      the judge-shape paragraph, plus a
#      RECONCILIATION note.
#   4. RATIFICATION-SENTINEL TEST UPDATE (the RTG-09 lesson: a "default-off contract"
#      test left unchanged after its own flag flips is stale the moment the flip lands --
#      RTG-09's own test_default_config_reward_is_byte_identical_with_and_without_duration
#      needed a post-hoc rename into test_pre_e18_config_reward_is_byte_identical_..., plus
#      a new test_scoring_config_defaults_are_ratified, after E18 actually landed). This
#      script does that update ITSELF, in the SAME apply, via its own anchor-based
#      single-occurrence replace on BOTH sentinel tests:
#      $ORCH_ROOT/tests/unit/test_debug_scorer_td21_parse_exclusion.py's
#      `#EQ1_RATIFICATION_TEST_SENTINEL` line and its paired assertion, AND
#      $ORCH_ROOT/tests/unit/test_td21_judge_output_shape.py's
#      `#CJO1_RATIFICATION_TEST_SENTINEL` line and its paired assertion, so the post-flip
#      test run below is never stale by construction for either flag.
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
# IDEMPOTENCY. Sentinel-checked, per flag: a second --apply refuses immediately (either
# flag's old value already flipped, either test's sentinel already updated, or the era id
# already present), rather than double-applying or corrupting a file on a re-run. A
# half-applied state cannot occur: both flag flips, both test updates, and the era append
# are only attempted after ALL FOUR pre-flight sentinel checks (both flags, both tests)
# and both commit-ancestry checks pass.
#
# IF YOU DECLINE. Nothing breaks. TD-21.11..21.14's and TD-21.9/21.10/21.15's code stay on
# main (once merged) fully inert -- EXCLUDE_UNPARSEABLE_ANSWERS and CONSTRAIN_JUDGE_OUTPUT
# both stay False, and every converted site keeps its pre-conversion output for every
# input. The parse-failure-rate and judge-parse-outcome reporting (item 6 above) is
# UNCONDITIONAL and independent of this ratification -- it is already live and useful
# evidence for deciding whether to ratify at all.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ORCH_ROOT="${ORCH_ROOT:-/mnt/raid0/llm/epyc-orchestrator}"
SCORER="${ORCH_ROOT}/scripts/benchmark/debug_scorer.py"
ERAS="${ORCH_ROOT}/orchestration/instrument_eras.yaml"
TEST_FILE="${ORCH_ROOT}/tests/unit/test_debug_scorer_td21_parse_exclusion.py"
JUDGE_TEST_FILE="${ORCH_ROOT}/tests/unit/test_td21_judge_output_shape.py"
ERA_ID="E19-eval-answer-parse-failure-excluded-quality"
# ONE array, every commit this script's --apply requires to be present in $ORCH_ROOT's
# checked-out HEAD before either flag may flip:
#
#   EQ-1 (TD-21.11..21.14, td21/scorer branch, landed 2026-09-24): af8a4a1b lands the
#   four-site conversion DEFAULT-OFF; 940e0553 reverts the out-of-scope fish_json swap on
#   _is_valid_json, arm-keys the parse-failure counters, and wires the per-arm rate into
#   EvalTower._aggregate; ec412724 hardens the one SCORE-26 golden fixture that this flip
#   would otherwise make stale.
#
#   TD-21.9/21.10/21.15 (judge OUTPUT SHAPE, td21/judge branch, landed 2026-09-24):
#   62ab94ed lands debug_scorer.py's CONSTRAIN_JUDGE_OUTPUT flag +
#   _parse_judge_boolean_verdict (TD-21.9) + the raw-branch response_format forwarding
#   (TD-21.10) + judge_parse_stats, and eval_tower.py's RUBRIC_JUDGE_SCHEMA +
#   parse_with_repair wiring in _rubric_scores_for_answer (TD-21.15), all DEFAULT-OFF,
#   plus tests/unit/test_td21_judge_output_shape.py.
#
# Re-pinned 2026-09-24 to the landed epyc-orchestrator main SHA (62ab94ed).
TD21_COMMITS=(af8a4a1b 940e0553 ec412724 62ab94ed)
SENTINEL_OLD_FLAG='EXCLUDE_UNPARSEABLE_ANSWERS = False'
SENTINEL_NEW_FLAG='EXCLUDE_UNPARSEABLE_ANSWERS = True'
SENTINEL_OLD_TEST_MARK='#EQ1_RATIFICATION_TEST_SENTINEL: EXCLUDE_UNPARSEABLE_ANSWERS ships False'
SENTINEL_NEW_TEST_MARK='#EQ1_RATIFICATION_TEST_SENTINEL: EXCLUDE_UNPARSEABLE_ANSWERS ships True (ratified — see instrument_eras.yaml E19)'
SENTINEL_OLD_TEST_ASSERT='assert _SHIPPED_DEFAULT_ON_IMPORT is False'
SENTINEL_NEW_TEST_ASSERT='assert _SHIPPED_DEFAULT_ON_IMPORT is True'
SENTINEL_OLD_JUDGE_FLAG='CONSTRAIN_JUDGE_OUTPUT = False'
SENTINEL_NEW_JUDGE_FLAG='CONSTRAIN_JUDGE_OUTPUT = True'
SENTINEL_OLD_JUDGE_TEST_MARK='#CJO1_RATIFICATION_TEST_SENTINEL: CONSTRAIN_JUDGE_OUTPUT ships False'
SENTINEL_NEW_JUDGE_TEST_MARK='#CJO1_RATIFICATION_TEST_SENTINEL: CONSTRAIN_JUDGE_OUTPUT ships True (ratified — see instrument_eras.yaml E19)'
SENTINEL_OLD_JUDGE_TEST_ASSERT='assert _JUDGE_SHIPPED_DEFAULT_ON_IMPORT is False'
SENTINEL_NEW_JUDGE_TEST_ASSERT='assert _JUDGE_SHIPPED_DEFAULT_ON_IMPORT is True'

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

      JUDGE OUTPUT SHAPE (TD-21.9/21.10/21.15, bundled into this SAME boundary at the
      SAME 2026-09-24 review — a second era row was rejected as unnecessary fragmentation
      of one review's sign-off): debug_scorer.py's CONSTRAIN_JUDGE_OUTPUT flips 0->1
      alongside EXCLUDE_UNPARSEABLE_ANSWERS above. TD-21.32: this changes judge OUTPUT
      SHAPE only, never judge BINDING — every site still resolves the judge via the
      existing LLM_JUDGE_ROLE/_llm_judge_force_role seam untouched by this flag, so a
      later CJ-11 rebinding changes nothing here. Three sites move from a free-text
      fish to a schema-constrained, strictly-parsed request: (a) the boolean equivalence
      judge's orchestrator /chat branch keeps its existing output_schema={"type":
      "boolean"} wire payload but replaces the .lower().startswith(true) prefix-match
      parse (a "truely not equivalent" reply scored True before) with an exact
      true/false parse — an unparseable verdict now raises ScoringUnavailableError
      directly (a SCORER-side failure, NOT the model-side AnswerParseError above) and
      routes through the SAME scoring_failed/EXCLUDED path; (b) the raw llama-server
      override branch, which sent NO schema at all before this flag, now forwards the
      same schema as an OpenAI response_format envelope; (c) the autopilot rubric
      judge's {"scores": {dim: [0,1]}} reply (eval_tower.py's
      _rubric_scores_for_answer) is requested under rubric_scoring.RUBRIC_JUDGE_SCHEMA,
      and a reply the existing lenient fisher cannot parse at all now gets ONE
      parse_with_repair extraction turn back to the SAME judge role before that judge's
      contribution is dropped — recovering some replies the old fisher missed and
      shifting some rows from rubric_source="heuristic_fallback" to "judge". The
      heuristic-fallback path taken when EVERY configured rubric judge is still
      unparseable is UNCHANGED by this flag: it was already clearly marked
      (rubric_source) and already counted per-arm by the pre-existing SCORE-08
      rubric_source_counts rollup, so this boundary does not touch that policy.
      ALWAYS-ON GUARD (same contract as the parse_failure_stats guard above, live
      whether or not this flag is set): debug_scorer.judge_parse_stats() counts every
      judge parse outcome (parsed / repaired / unparseable) per site, and
      EvalTower._aggregate reports judge_parse_by_site / judge_parse_unparseable_count /
      judge_parse_total_count / judge_parse_unparseable_rate beside quality/accuracy on
      every trial.

      Implementation: epyc-orchestrator ${TD21_COMMITS[0]} + ${TD21_COMMITS[1]} +
      ${TD21_COMMITS[2]} (EQ-1) + ${TD21_COMMITS[3]} (judge output shape).
      RECONCILIATION: pre-boundary quality UNDERSTATES any arm/suite with a nonzero
      parse-failure rate relative to post-boundary (an unparseable row was counted wrong
      pre-boundary; it is excluded post-boundary) — treat pre-boundary quality as a
      prior only for suites/arms with a nonzero parse_failure_stats() count at scoring
      time, or re-score from stored answers. Separately, pre-boundary rubric-judge scores
      UNDERSTATE the judge-scored (vs heuristic-fallback) share of any arm/suite with a
      nonzero judge_parse_by_site["rubric_judge"]["unparseable"] count relative to
      post-boundary (a reply the repair turn would have recovered instead fell back to
      the deterministic heuristic pre-boundary) — treat pre-boundary rubric_source_counts
      as a prior under the same condition, or re-score from stored judge replies.

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
        echo "  ${TEST_FILE} (EQ-1 ratification-sentinel test update)"
        echo "  ${JUDGE_TEST_FILE} (judge-output-shape ratification-sentinel test update)"
        echo
        echo "== debug_scorer.py module flag flip: EQ-1 (model-side answer parse) =="
        echo "  ${SENTINEL_OLD_FLAG}"
        echo "    -> ${SENTINEL_NEW_FLAG}"
        echo
        echo "== debug_scorer.py module flag flip: judge OUTPUT SHAPE (TD-21.9/21.10/21.15) =="
        echo "  ${SENTINEL_OLD_JUDGE_FLAG}"
        echo "    -> ${SENTINEL_NEW_JUDGE_FLAG}"
        echo
        echo "== EQ-1 ratification-sentinel test update =="
        echo "  ${SENTINEL_OLD_TEST_MARK}"
        echo "    -> ${SENTINEL_NEW_TEST_MARK}"
        echo "  ${SENTINEL_OLD_TEST_ASSERT}"
        echo "    -> ${SENTINEL_NEW_TEST_ASSERT}"
        echo
        echo "== judge-output-shape ratification-sentinel test update =="
        echo "  ${SENTINEL_OLD_JUDGE_TEST_MARK}"
        echo "    -> ${SENTINEL_NEW_JUDGE_TEST_MARK}"
        echo "  ${SENTINEL_OLD_JUDGE_TEST_ASSERT}"
        echo "    -> ${SENTINEL_NEW_JUDGE_TEST_ASSERT}"
        echo
        echo "== ONE era row appended to the eras: list (boundary = apply time; covers BOTH flags) =="
        era_row "<apply-time UTC>"
        echo "== required commits in \${ORCH_ROOT} HEAD (EQ-1 + judge output shape) =="
        printf '  %s\n' "${TD21_COMMITS[@]}"
        echo "  (last entry is a placeholder — see the TD21_COMMITS comment above; --apply's"
        echo "   ancestry check will refuse until it is re-pinned to the real post-push SHA)"
        echo
        echo "After --apply: commit the orchestrator repo (printed then), and reload the"
        echo "orchestrator API/autopilot separately for the flip to take effect (not done here)."
        ;;
    --apply)
        [[ -f "${SCORER}" ]] || { echo "REFUSED: no file at ${SCORER}" >&2; exit 1; }
        [[ -f "${ERAS}" ]] || { echo "REFUSED: no file at ${ERAS}" >&2; exit 1; }
        [[ -f "${TEST_FILE}" ]] || { echo "REFUSED: no file at ${TEST_FILE}" >&2; exit 1; }
        [[ -f "${JUDGE_TEST_FILE}" ]] || { echo "REFUSED: no file at ${JUDGE_TEST_FILE}" >&2; exit 1; }

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
        old_judge_flag_count="$({ grep -oF "${SENTINEL_OLD_JUDGE_FLAG}" "${SCORER}" || true; } | wc -l | tr -d ' ')"
        new_judge_flag_count="$({ grep -oF "${SENTINEL_NEW_JUDGE_FLAG}" "${SCORER}" || true; } | wc -l | tr -d ' ')"
        if [[ "${old_judge_flag_count}" -eq 0 ]]; then
            if [[ "${new_judge_flag_count}" -gt 0 ]]; then
                echo "REFUSED: ${SCORER} already carries '${SENTINEL_NEW_JUDGE_FLAG}' — already applied." >&2
                exit 1
            fi
            echo "REFUSED: sentinel not found in ${SCORER}: ${SENTINEL_OLD_JUDGE_FLAG}" >&2
            exit 1
        fi
        if [[ "${old_judge_flag_count}" -ne 1 ]]; then
            echo "REFUSED: expected exactly one occurrence of '${SENTINEL_OLD_JUDGE_FLAG}' in ${SCORER}, found ${old_judge_flag_count}." >&2
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
        old_judge_mark_count="$({ grep -oF "${SENTINEL_OLD_JUDGE_TEST_MARK}" "${JUDGE_TEST_FILE}" || true; } | wc -l | tr -d ' ')"
        if [[ "${old_judge_mark_count}" -ne 1 ]]; then
            echo "REFUSED: expected exactly one occurrence of the ratification-sentinel mark in ${JUDGE_TEST_FILE}, found ${old_judge_mark_count}." >&2
            exit 1
        fi
        old_judge_assert_count="$({ grep -oF "${SENTINEL_OLD_JUDGE_TEST_ASSERT}" "${JUDGE_TEST_FILE}" || true; } | wc -l | tr -d ' ')"
        if [[ "${old_judge_assert_count}" -ne 1 ]]; then
            echo "REFUSED: expected exactly one occurrence of '${SENTINEL_OLD_JUDGE_TEST_ASSERT}' in ${JUDGE_TEST_FILE}, found ${old_judge_assert_count}." >&2
            exit 1
        fi

        for c in "${TD21_COMMITS[@]}"; do
            git -C "${ORCH_ROOT}" merge-base --is-ancestor "$c" HEAD 2>/dev/null || {
                echo "REFUSED: ${ORCH_ROOT} HEAD does not contain required commit $c (EQ-1 TD-21.11..21.14, or the" >&2
                echo "  judge-output-shape TD-21.9/21.10/21.15 commit)." >&2
                echo "  Merge/fast-forward td21/scorer and td21/judge into that clone's checked-out branch first," >&2
                echo "  or update TD21_COMMITS in this script if a branch was squash-merged under a new SHA (the" >&2
                echo "  the judge-output-shape entry must be the landed main SHA)." >&2
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
        git -C "${ORCH_ROOT}" diff --quiet -- tests/unit/test_td21_judge_output_shape.py || {
            echo "REFUSED: ${JUDGE_TEST_FILE} carries unstaged changes that are not this ratification:" >&2
            echo "  git -C ${ORCH_ROOT} diff -- tests/unit/test_td21_judge_output_shape.py" >&2
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

        python3 - "${SCORER}" "${SENTINEL_OLD_JUDGE_FLAG}" "${SENTINEL_NEW_JUDGE_FLAG}" <<'PY'
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

        python3 - "${JUDGE_TEST_FILE}" "${SENTINEL_OLD_JUDGE_TEST_MARK}" "${SENTINEL_NEW_JUDGE_TEST_MARK}" \
                                        "${SENTINEL_OLD_JUDGE_TEST_ASSERT}" "${SENTINEL_NEW_JUDGE_TEST_ASSERT}" <<'PY'
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
        echo "Running the TD-21.11..21.14 + TD-21.9/21.10/21.15 test suite against the now-flipped tree..."
        VENVPY="${ORCH_ROOT}/.venv/bin/python3"
        [[ -x "${VENVPY}" ]] || VENVPY="python3"
        "${VENVPY}" -m pytest \
            "${ORCH_ROOT}/tests/unit/test_debug_scorer_td21_parse_exclusion.py" \
            "${ORCH_ROOT}/tests/unit/test_td21_parse_failure_rate_reporting.py" \
            "${ORCH_ROOT}/tests/unit/test_debug_scorer_score25_26.py" \
            "${ORCH_ROOT}/tests/unit/test_b7_golden_corpus_pin.py" \
            "${ORCH_ROOT}/tests/unit/test_seeding_scoring.py" \
            "${ORCH_ROOT}/tests/unit/test_etr1_task_failed_scores_zero.py" \
            "${ORCH_ROOT}/tests/unit/test_td21_judge_output_shape.py" \
            "${ORCH_ROOT}/tests/unit/test_debug_scorer_nugget_judge_transport.py" \
            "${ORCH_ROOT}/tests/unit/test_rubric_scoring.py" -q || {
            echo "REFUSED (post-flip check): tests failed — inspect before committing anything." >&2
            exit 1
        }

        echo
        echo "Review, then commit the orchestrator repo from its own tree, pathspec-limited:"
        echo "  git -C ${ORCH_ROOT} diff -- scripts/benchmark/debug_scorer.py orchestration/instrument_eras.yaml tests/unit/test_debug_scorer_td21_parse_exclusion.py tests/unit/test_td21_judge_output_shape.py"
        echo "  git -C ${ORCH_ROOT} commit -m 'RATIFIED: EQ-1 answer-parse exclusion + judge output shape live; era ${ERA_ID} (2026-09-24)' -- scripts/benchmark/debug_scorer.py orchestration/instrument_eras.yaml tests/unit/test_debug_scorer_td21_parse_exclusion.py tests/unit/test_td21_judge_output_shape.py"
        echo
        echo "REQUIRED, NOT DONE HERE: the orchestrator API/autopilot process must be reloaded"
        echo "for this flip to take effect (uvicorn :8000 reload / stack reload). Reload"
        echo "ownership: the session that owns inference executes it at its own boundary"
        echo "(agents/shared/OPERATING_CONSTRAINTS.md -> Inference and Benchmarks)."
        ;;
    *) usage ;;
esac
