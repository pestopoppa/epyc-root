# Frontier F1 — Define the Demand Side: a Real-Task Corpus as the Eval Distribution

**Status**: IN PROGRESS — W1 workload taxonomy branch-ready 2026-06-12; W2 passive capture next
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

- [x] **W1 — task taxonomy** (1 day, no code): branch-ready 2026-06-12 in `epyc-orchestrator` worktree `/mnt/raid0/llm/tmp/workload-model-worktree`, branch `feat/workload-model`, commit `2211e29` (`Add measured workload model`). Added `orchestration/workload_model.yaml` with `task_classes:` and measured 30-day volume estimates from 33 progress markdown files + 24 orchestrator progress JSONL logs; added `orchestration/reports/workload_model_source_counts_2026-06-12.md` as the source-count artifact. No durable Hermes runtime task ledger was found; the report records that absence instead of guessing. Acceptance: counts are measured, with caveats that progress sections are a proxy and runtime `task_started` events are harness-dominated.
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

## Checkpoints

- 2026-06-12 W1 verification: `uv run python` YAML parse asserted schema version, 7 task classes, and 247 classified progress sections; `git diff --check` clean. Measured progress-section shares: benchmark/eval/measurement 46 (18.6%), ops/deploy/process 45 (18.2%), code implementation 44 (17.8%), debug/root-cause 36 (14.6%), governance/docs/handoff 35 (14.2%), research/intake/deep-dive 26 (10.5%), planning/architecture review 15 (6.1%). Structured task log measured 49,297 `task_started` events and is explicitly treated as harness traffic pressure, not human demand.
