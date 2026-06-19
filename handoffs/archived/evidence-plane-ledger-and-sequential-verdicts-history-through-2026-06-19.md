# Evidence Plane Ledger And Sequential Verdicts — History Through 2026-06-19

Historical ledger only; current work lives in `../active/evidence-plane-ledger-and-sequential-verdicts.md`.

## Scope

This ledger preserves the completed implementation chronology compacted out of the active N2/W4/W6/W7 handoff during the 2026-06-19 wrap-up. It is evidence for what landed, not the dispatch surface for future agents.

## Completed Implementation

| Area | Commit(s) | Result |
|------|-----------|--------|
| W1 per-question vectors | `22a3874a` | Stable qid/outcome vectors are journaled through `EvalResult.question_results` and AutoPilot `eval_details.question_results`. |
| W2 paired replay | `9f6fc8e`, `d21bbee` | `scripts/autopilot/paired_stats.py` supports summary/McNemar/config-vs-baseline and folds append-only supersession events before replay. |
| W3 sequential verdict math | `7e6ac9c` | Pure capped-Kelly e-process module with deterministic null simulation false-positive rate `0.00551` at alpha `0.05`. |
| W4 default-off gate mechanism | `eab6a32` | `SafetyGate` can compute advisory sequential quality/rate verdicts behind `AUTOPILOT_SEQ_VERDICT`; flag off preserves legacy behavior. |
| W4 AutoPilot shadow wiring | `9f89b5d` | AutoPilot threads per-question evidence, task-rate, baseline profile, prior observations, candidate/core ids into the gate and journals top-level `seq` blocks. |
| W4 baseline/fresh-eval finalization | `8f5f78b`, `8824d4d`, `c2a656d`, `1161243` | Baseline-reference cadence, one fresh promotion eval, update-baseline finalization, and pre-dispatch checks are wired without granting authority before readiness. |
| W4 cached verdict repair | `fd8340f` | Central seq-aware gate calls can upgrade an early cached legacy pass when seq evidence is available without double-counting MAD/consecutive-failure side effects. |
| W4 fallback reselection | `be7f488` | Planner/AutoPilot fallback seed actions search measured unblacklisted alternatives instead of looping on blacklisted defaults. |
| W4 action-local gate threading | `29ed546` | Mutation/structural revert checks preserve the legacy one-argument path when seq is off and supply seq inputs when seq is on. |
| W4 failed-trial denominator repair | `0024cf3` | Failed safety checks now journal advisory seq blocks when seq inputs exist, so trusted failed vectors can move `seq_shadow_rows`. Trial 888 verified the denominator moved from `4` to `5`. |
| W5 planner evidence | `0bc1f32` | Planner gets read-only evidence power and sequential candidate status context after Pareto geometry. |
| W6 readiness artifacts | `d446f68`, `42b65f5` | Readiness reporting exists and can emit durable Markdown/JSON artifacts via CLI. |
| W7 critic/game layer | `41c5c71`, `7492cf5`, `8e4b1ec`, `4b09661`, `749d38f` | Critic prompt gets bounded measurement context, production eval sampling is server-clamped, gaming alarms are read-only, species budgets use PEAF information gain, and compact per-question provenance reaches planner/critic context without prompt/answer leakage. |

## Latest Durable Evidence

The latest durable readiness snapshot before compaction was `seq_readiness_20260619T140002Z`:

- `cutover_ready=false`
- trusted vector trials `57 / 120`
- raw vector trials `64`
- untrusted vector trials `7`
- sequential shadow rows `5 / 30`
- flip-rate `100%` over only 5 rows

The bounded repair run exited at trial counter `889`; Python PID `3548349` was verified gone. This means the blocker after 2026-06-19 is evidence volume, not missing default-off mechanism.

## Validation Reference

Focused validations recorded in progress logs include:

- sequential verdict and paired replay tests through the W3/W4 bring-up;
- W4 adjacent gates over `test_safety_gate_sequential_verdict.py`, `test_autopilot_sequential_wiring.py`, `test_safety_gate_mad.py`, `test_safety_gate_baseline_eligibility.py`, `test_autopilot_actions.py`, and `test_seq_readiness_report.py`;
- W7 planner/eval/audit tests including planner coordinator, eval tower, audit block report, and planner evidence suites;
- GitNexus refreshes after high-risk AutoPilot/eval edits.

See `progress/2026-06/2026-06-19.md` for the full per-commit chronology and validation commands.
