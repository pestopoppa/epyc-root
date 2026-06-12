# Frontier F1 — Define the Demand Side: a Real-Task Corpus as the Eval Distribution

**Status**: SPEC'D, not started (created from the Fable 5 strategic-frontiers review)
**Created**: 2026-06-12
**Priority**: MED — start passive capture anytime
**Spec**: [fable5-findings-07-strategic-frontiers.md](fable5-findings-07-strategic-frontiers.md) §F1 — read it before claiming any waypoint
**Related**: [unified-trace-memory-service.md](unified-trace-memory-service.md) (capture substrate, BUILT); [fable5-findings-01-impl-plan.md](fable5-findings-01-impl-plan.md) Phase 2 (promotion evals); workload model in [fable5-findings-04-impl-plan.md](fable5-findings-04-impl-plan.md) §D

## Why

Everything in the project is supply-side: the eval distribution is public
benchmarks, ~77% of traffic is the harness testing itself, and Hermes is
priority-LOW. So "maximize quality AND speed" has no referent, routing
optimality is undefined, and the autopilot grinds noise on questions nobody
needs answered. The actual recurring workload is already visible in `progress/`
(research intake, deep-dives, code review, bench analysis, handoff hygiene,
wrap-ups) — capture it passively and turn it into the eval suite that makes
quality gains *felt*.

## Waypoints

- [ ] **W1 — task taxonomy** (1 day, no code): `orchestration/workload_model.yaml` gains `task_classes:` with per-class volume estimates from 30 days of `progress/` + Hermes logs — acceptance: volumes counted from logs, not guessed.
- [ ] **W2 — passive capture** (2–3 days): `task_record` event in the trace service (`{task_id, class, prompt_ref, route_taken, wall_s, tokens, outcome}`; implicit + one-keystroke explicit outcome capture); deliverables: ingest patch + `scripts/tasks/harvest_tasks.py` → `benchmarks/prompts/real_tasks.jsonl` — acceptance: ≥100 records with class+outcome after 2 weeks of normal use.
- [ ] **W3 — real-suite v1** (2 days): curate 50 tasks across classes into a YAML suite via the `YAML_ONLY_SUITES` hook in `dataset_adapter_modules/registry.py`; reference answers where deterministic, EV-9-style rubric (`scoring_method: llm_judge`) where not — acceptance: suite runs through `eval_tower` with per-question ledger capture, per MEASUREMENT.md P-QUAL-PROMO.
- [ ] **W4 — wire into decisions** (1 day): promotion evals (findings-01 Phase 2.4) include a real-suite slice; routing per-class regret (DAR-1 replay) reported against `task_classes` — acceptance: both reporting paths emit per-class real-task numbers.

## Gates & pitfalls

- Do NOT let the autopilot optimize against the real suite until n is large enough — it enters as audit/promotion material first (power discipline, findings-01).
- Rubric (`llm_judge`) items stay OUT of the autopilot gate — audit/promotion only.
- Personal data stays local — exclude real-task records from anything published under F6.
- Classes will be imbalanced — report per-class, never pooled.

## Reporting

On completion of each waypoint: tick here, one-line progress entry, update master index row. W2 acceptance requires a 2-week soak — checkpoint the ingest patch landing separately from the ≥100-record gate.
