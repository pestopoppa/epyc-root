# Frontier F1 — Define the Demand Side: a Real-Task Corpus as the Eval Distribution

**Status**: IN PROGRESS — W1 workload taxonomy branch-ready 2026-06-12; W2 offline harvester + dedupe branch-ready 2026-06-13; passive progress-logger `task_record.v1` embedding live in `ade1cdd`; operator verdict path + 2-week soak still open
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
- [ ] **W2 — passive capture** (2–3 days): `task_record` event in the trace service (`{task_id, class, prompt_ref, route_taken, wall_s, tokens, outcome}`; implicit + one-keystroke explicit outcome capture); deliverables: ingest patch + `scripts/tasks/harvest_tasks.py` → `benchmarks/prompts/real_tasks.jsonl` — acceptance: ≥100 records with class+outcome after 2 weeks of normal use. **Offline harvester branch-ready 2026-06-13**: `feat/task-record-harvester` commits `40bde0d` and `90c6f59` add `scripts/tasks/harvest_tasks.py`, prompt-dedupe mode, and tests. It reads existing orchestrator progress JSONL and optional F2 `lab_task_record.v1` logs, emits `real_task_record.v1` rows with local-private prompt refs/text, inferred class/outcome, route, wall time, synthetic/eligibility flags, duplicate-collapsed evidence when enabled, and a `task_harvest_manifest.v1`. **Passive live capture substrate landed 2026-06-14** in `ade1cdd`: `progress_logger.py` embeds passive `task_record.v1` payloads inside existing terminal `task_completed` / `task_failed` progress events, without adding a new event type or changing routing/execution behavior. Payloads capture opportunistic `{task_id, class, prompt_ref, route_taken, wall_s, tokens, outcome}` values with local hash refs (`progress-text-sha256:*`) instead of raw prompt text; terminal completions without a prior start omit `task_record_v1`, so early failures are not fabricated as completed task records. Remaining W2 acceptance: explicit operator verdict path, token completeness as traffic accrues, and 2-week soak.
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
- 2026-06-13 W2 offline harvester checkpoint: `feat/task-record-harvester` commit `40bde0d`. Validation: `python3 -m py_compile scripts/tasks/harvest_tasks.py tests/unit/test_task_harvester.py` passed; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_task_harvester.py` -> 3 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/tasks/harvest_tasks.py tests/unit/test_task_harvester.py` passed; `git diff --cached --check` passed. Smoke over 2026-06-12..2026-06-13 progress logs plus F2 shadow-batch dry-run task records wrote 831 rows under `/mnt/raid0/llm/tmp/f1-real-tasks-smoke-20260613`: 831 written, 275 taxonomy-class, 202 training-eligible after synthetic filtering, 138 synthetic-like, outcomes 797 success / 34 failure. This is a corpus-builder scaffold, not W2 completion; the manifest keeps the harness-dominated runtime mix from being mistaken for real operator demand.
- 2026-06-13 W2 duplicate-collapse checkpoint: `feat/task-record-harvester` commit `90c6f59` adds opt-in `--dedupe-prompt`, preserving `duplicate_count`, `duplicate_task_ids`, `route_attempts`, `duplicate_outcomes`, and capped source refs. Validation: `python3 -m py_compile scripts/tasks/harvest_tasks.py tests/unit/test_task_harvester.py` passed; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_task_harvester.py` -> 4 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/tasks/harvest_tasks.py tests/unit/test_task_harvester.py` passed; `git diff --cached --check` passed. Dedupe smoke over the same no-inference input wrote 165 rows under `/mnt/raid0/llm/tmp/f1-real-tasks-dedupe-smoke-20260613`, collapsing 666 duplicate prompt records while preserving evidence: 69 taxonomy-class, 54 training-eligible, 23 synthetic-like, outcomes 164 success / 1 failure.
- 2026-06-14 W2 passive live-capture substrate landed live as `ade1cdd` (`Embed passive task records in progress logs`). `orchestration/repl_memory/progress_logger.py` now embeds `task_record.v1` payloads into existing terminal progress lifecycle events (`task_completed` / `task_failed`) without adding a new `EventType` or changing routing/execution behavior. Captured fields are `{task_id, class, prompt_ref, route_taken, wall_s, tokens, outcome}`; prompt/outcome details use local hash refs such as `progress-text-sha256:*`, not raw prompt text. Completion without a prior start omits `task_record_v1`, preventing fabricated completed records for early failures. Validation: `python3 -m py_compile orchestration/repl_memory/progress_logger.py tests/unit/test_progress_logger_task_record.py`; `uv run ruff check ...`; `git diff --check`; `uv run pytest -q tests/unit/test_progress_logger_task_record.py tests/unit/test_pipeline_routing.py tests/unit/test_trajectory_extractor.py tests/unit/test_replay_engine.py tests/unit/test_q_scorer.py` -> 157 passed, 3 existing SWIG deprecation warnings.
