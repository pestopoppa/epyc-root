# 2026-09-16 — sub-reviewer (reviewer control plane, zero-inference)

This session ran no inference and managed no processes. All code is in `epyc-orchestrator` on branch
`sub/reviewer-artifacts-20260916` (worktree `/mnt/raid0/llm/worktrees/sub-reviewer-epyc-orchestrator`),
based on `main@92bbeb06`. Nothing has been merged or pushed.

## RA-12 — immutable machine-review envelope (`afa4e107`)
- `orchestration/machine_review_envelope.schema.json` (validate_ir kind `review_envelope`) and
  `src/proactive_delegation/review_envelope.py`.
- The binding covers source/candidate hash+version, reviewer model+quant, prompt bundle hash,
  pipeline version and review-schema version. The review body is signed with the binding digest.
  Stale envelopes are kept as history and never contribute objections. Objections are
  `unverified_lead` and never corroboration.
- Frozen regression fixture `tests/fixtures/review_envelope/` pairs an old review signed for
  abstract v1 with the current abstract v2; every splice is refused.
  `tests/test_review_envelope.py`: 37 tests, 5/5 mutants killed.

## RA-9 — dual-gold schema + gold-sanity gate (`e242a156`)
- `orchestration/gold_annotation.schema.json` (kind `gold_annotation`),
  `src/proactive_delegation/gold_annotations.py` and `src/proactive_delegation/gold_sanity.py`.
- `status: invalid` decoys provide the negative-control axis, and `false_accept_rate()` states its
  denominator. The gate order is inject, then gold, then native runner, then a retry at a strictly
  higher temperature, and only then the 3-sample judge. A config without retry is refused, and there
  is no retry-prompt parameter.
- `tests/test_gold_annotations.py`: 45 tests, 13/13 mutants killed. This is the single schema for
  both `reviewer-typed-artifacts.md` and `security-review-skill.md`; both handoffs record where it lives.

## Stale tests fixed (`70e2662d`)
- 4 verification_report tests failed on main because ratified commit `8b740065` closed
  `inconclusive_reason` while two fixtures still used free text. The fixtures now use `timeout` and
  `checker_error`.

## RM-5 — bias-robustness probe set, zero-inference half (`9a00184b`)
- `src/proactive_delegation/bias_probes.py` and `tests/test_bias_probes.py` (19 tests, 9/9 mutants
  killed). The box stays open because the run is RM-4 inference.

## Triage
- RC-10 cannot start offline: the ledger has no score-token distribution. Note added under RC-10.
- Belief kernel: README source row and task SC76 added (negative-control FA rate; stale envelopes
  emit zero rows).
- Related suites: 330 passed, 1 skipped, 2 xfailed. `index_state.py --check` reports only the stale
  generated rollup, which is expected after the ticks.
