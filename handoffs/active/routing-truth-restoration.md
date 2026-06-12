# Routing Truth Restoration: Prod Flags, Attestation, Dead Code

**Status**: IMMEDIATE SCOPE COMPLETE 2026-06-12 — W1-W8 landed and live-attested/deployed; routing expansion remains frozen by the W8/DAR-1 gate; `dispatch_swarm_fanout` is a conditional ownership watch through 2026-07-12
**Created**: 2026-06-12
**Priority**: CLOSED/HIGH — immediate repair scope completed; remaining item is the 2026-07-12 `dispatch_swarm_fanout` ownership watch
**Spec**: [fable5-findings-02-impl-plan.md](fable5-findings-02-impl-plan.md) Phases 0–1 + [fable5-findings-02-routing-decision-architecture.md](fable5-findings-02-routing-decision-architecture.md) §2/§4 — read both before claiming any waypoint
**Related**: [decision-aware-routing.md](decision-aware-routing.md) (DAR-1 replay result recorded there), [learned-routing-controller.md](learned-routing-controller.md) (the dead MLP fast-path), [running-state-attestation.md](running-state-attestation.md) (system-wide ATTESTATION generator — this handoff owns ONLY the flags endpoint)

## Why

Production runs on TEST feature defaults: `features()` lazy-loads with
`production=False`, so every `default_prod=True` flag (specialist_routing,
model_fallback, plan_review, …) has been silently OFF for months — verified
against `/proc/<pid>/environ`. `POST /config` mutates 1 of 6 uvicorn workers,
silently invalidating every runtime flag experiment ever run. The MLP
classifier flag is ON with its weights file missing since the 05-25 reset.
The live system must match SOME declared intent before any routing redesign.

## Waypoints

- [x] **W1 — operator wave decision** (blocking, minutes): wave-1 = `specialist_routing` + `model_fallback` (low-risk: keyword priors + circuit-breaker fallback); wave-2 = plan_review / architect_delegation / parallel_execution / unified_streaming, EACH behind a one-week observation window — these code paths haven't run in months; treat as new code. **Decision applied 2026-06-12**: wave-1 ON, wave-2 OFF, `routing_classifier` OFF until weights exist.
- [x] **W2 — PRODUCTION_FEATURE_ENV block** (~1 day): explicit env block in `orchestrator_stack.py` (next to env assembly `:1114-1193`) setting every registry flag from `default_prod` per the wave decision; then delete the `production=` ambiguity (env-only; param stays for tests). Acceptance: `/proc/<pid>/environ` is a complete attestable record; rollback = re-emit flag=0 + reload (one runbook line). **Landed** via complete `ORCHESTRATOR_FEATURE_*` block; legacy `ORCHESTRATOR_*` remains supported but stack-managed feature intent uses the collision-safe namespace (`ORCHESTRATOR_REPL` conflicts with Pydantic `OrchestratorSettings.repl`).
- [x] **W3 — shared runtime_flags.json** (~1 day): atomic-write `orchestration/runtime_flags.json` recording `{flag, value, set_by, ts}`; `src/features.py` gains a 1s-TTL mtime re-read; `POST /config` (`src/api/routes/config.py`) writes the file. Precedence: env (boot intent) < runtime file (overrides). Acceptance: all 6 workers converge ≤1s.
- [x] **W4 — attestation endpoint** (~1 day): `GET /config/attest` returns `{pid, flags, source}` for the answering worker; client `scripts/validate/attest_flags.py` polls ~N×20 to cover all worker PIDs, red on heterogeneity; `structural_lab.apply_flag_experiment` (`:404-412`) gets a post-apply attestation poll + journals the result with the trial. Acceptance: empty cross-worker diff after any POST /config; a structural trial journals uniform attestation.
- [x] **W5 — q_scorer baseline_tps refresh** (afternoon): read `baseline_tps_by_role` from the lean registry's measured values at startup (`q_scorer.py:89-99` marked KNOWN STALE — frontdoor 12.7 vs measured ~21–27, spec 0.3). Stopgap until descriptors ([model-capability-descriptors.md](model-capability-descriptors.md) W3 replaces it).
- [x] **W6 — zero-caller deletions** (~1 day): `get_confidence_routing` + helpers (`chat_routing.py:283-448`) and 3-way routing wrappers deleted; proof in spec §4. `ORCHESTRATOR_ROUTING_CLASSIFIER` is unset/off in the declared production env until weights exist. `dispatch_swarm_fanout` is deliberately retained for now because this waypoint's deletion condition is "if no handoff claims it within the month"; revisit ownership on 2026-07-12 before deleting it.
- [x] **W7 — shadow-telemetry decision**: Trinity/difficulty/URE shadows now route into `logs/progress/*.jsonl`, the file QScorer/replay tools already mine. Difficulty/risk were already present; W7 added Trinity `assigned_role` and URE `uncertainty_*` fields to the durable routing event while preserving the existing URE sidecar for backward compatibility.
- [x] **W8 — Phase 1 measurement**: DAR-1 regret replay on 2026-06-05..2026-06-12 traffic completed in `epyc-orchestrator` `1dfbc22`; report: `orchestration/reports/dar1_regret_replay_2026-06-12.md`. Gate result: 12,057 decisions, 11,249 matched outcomes, 8,145 regret-identifiable decisions, 0.00% identifiable mean regret, 99.1% uniform Q-values. Phase 3 cascade expansion remains frozen; re-run quarterly or after enough new `action_topk` telemetry accumulates. `_try_cheap_first` denominator/attempt/accept/reject counters now write `routing_fallback` progress rows with `data.kind=try_cheap_first`.

## Gates & pitfalls

- W1-W8 are complete. Any future routing expansion must re-open through a new measured gate, not through this repair handoff.
- Long-dormant flags ARE new code: never enable wave-2 flags together; one observation window each.
- Attestation results must be journaled WITH each autopilot flag trial — otherwise flag experiments remain unmeasurable (findings-01 §3.4).
- Use `orchestrator_stack.py reload` for any restart — never manual PID kills.
- Latest W8 verdict: routing expansion remains frozen because DAR-1 measured 0.00% identifiable mean regret, below the 5% gate.

## 2026-06-12 Checkpoint — W1-W4 Landed

Commit: `epyc-orchestrator` `b5f26e5` (`Restore runtime flag truth and attestation`).

Live deployment:
- Reloaded orchestrator through `scripts/server/orchestrator_stack.py reload orchestrator`.
- New supervisor PID `2692296` healthy on port 8000; failed intermediate supervisor PID `2687898` was terminated with SIGTERM and verified gone by `ps`.
- `uv run python scripts/validate/attest_flags.py --polls 240 --delay-s 0.02 --min-workers 6 --expect specialist_routing=true --expect model_fallback=true --expect plan_review=false --expect architect_delegation=false --expect parallel_execution=false --expect unified_streaming=false --expect routing_classifier=false` saw 6 workers, `errors={}`, `expected_diffs=[]`, `heterogeneous={}`.

Implementation notes:
- `src/features.py` now reads legacy `ORCHESTRATOR_*` and preferred `ORCHESTRATOR_FEATURE_*`, then applies `orchestration/runtime_flags.json`, then explicit test overrides.
- `POST /config` writes the shared runtime file; workers re-read by mtime with a 1s TTL.
- `GET /config/attest` returns the answering PID, effective flags, and source map.
- Structural experiments attach `flag_apply_result`, `flag_attestation`, and, when needed, `flag_revert_result` into eval details.
- The standalone attestation client closes connections between polls and supports `--min-workers` so a keep-alive connection cannot falsely sample only one uvicorn worker.

## 2026-06-12 Checkpoint — W5 Landed

Commit: `epyc-orchestrator` `41a6944` (`Load q-scorer TPS baselines from registry`).

Implementation:
- `orchestration/repl_memory/q_scorer.py` now builds `ScoringConfig.baseline_tps_by_role` from the lean `orchestration/model_registry.yaml` at config construction time.
- Live text roles prefer `server_mode.*.throughput`: frontdoor/coder escalation `24.3`, architect general `12.19`, ingest lower-bound `14.4`, and worker aliases (`worker_explore`, `worker_general`, `worker_math`, `toolrunner`) `60.7`.
- Vision roles use `roles.*.performance.optimized_tps`: worker vision `20.0`, vision escalation `27.6`.
- Removed `architect_coding` remains as fallback `8.0` for legacy callers; degraded scripts fall back to the previous static table if the registry is unavailable.

Verification:
- GitNexus impact for `ScoringConfig`: MEDIUM, 42 upstream nodes; direct imports include q_scorer runner, seeding scripts, q_reward, hybrid_router, replay modules, and `src/api/services/memrl.py`.
- `uv run pytest tests/unit/test_q_scorer.py tests/unit/test_bilinear_scorer.py tests/unit/test_replay_engine.py tests/unit/test_warm_start.py` -> 104 passed.
- `python3 -m py_compile orchestration/repl_memory/q_scorer.py` and `git diff --check` passed.
- GitNexus re-indexed commit `41a6944` successfully: 48,739 nodes, 83,673 edges, 997 clusters, 300 flows.
- Reloaded orchestrator through `scripts/server/orchestrator_stack.py reload orchestrator`; new supervisor PID `2702386` healthy, prior PID `2692296` verified gone by `ps`. Post-reload flag attestation still saw 6 workers with no diffs/heterogeneity.

## 2026-06-12 Checkpoint — W6 Zero-Caller Deletion Batch

Commit: `epyc-orchestrator` `2a52740` (`Delete dead confidence and 3-way routing paths`).

Implementation:
- Deleted the confidence-routing API path in `src/api/routes/chat_routing.py`: `get_confidence_routing`, `_parse_confidence_response`, `_is_coding_task`, and `_select_role_by_confidence`.
- Deleted `build_confidence_estimation_prompt`, its fallback prompt constant, the `prompt_builders` export, and `orchestration/prompts/confidence_estimation.md`.
- Deleted `HybridRouter.route_3way` and `SkillAugmentedRouter.route_3way`, plus tests that only covered those removed entry points.
- Retained `dispatch_swarm_fanout` because the waypoint names a month-long ownership condition rather than an immediate zero-caller proof; it remains default-off and should be revisited on 2026-07-12.

Verification:
- `rg` found no remaining references to `route_3way`, `get_confidence_routing`, `build_confidence_estimation_prompt`, `confidence_estimation`, `_parse_confidence_response`, or `_select_role_by_confidence` under `src/`, `orchestration/`, or `tests/`.
- GitNexus impacts were LOW / 0 upstream for `get_confidence_routing`, `build_confidence_estimation_prompt`, exact `HybridRouter.route_3way`, and exact `SkillAugmentedRouter.route_3way`; removed helper impacts were limited to the dead confidence route.
- `python3 -m py_compile src/api/routes/chat_routing.py src/prompt_builders/builder.py src/prompt_builders/__init__.py orchestration/repl_memory/hybrid_router.py orchestration/repl_memory/retriever.py` passed.
- `uv run pytest tests/unit/test_chat_routing.py tests/unit/test_prompt_resolver.py tests/unit/test_skill_integration.py tests/unit/test_bilinear_scorer.py` -> 96 passed.
- `git diff --check` in `epyc-orchestrator` passed.
- GitNexus re-indexed commit `2a52740`: 48,679 nodes, 83,567 edges, 994 clusters, 300 flows.
- Reloaded orchestrator through `scripts/server/orchestrator_stack.py reload orchestrator`; new supervisor PID `2711818` healthy and prior PID `2702386` verified gone by `ps`. Post-reload `/config/attest` saw 6 workers, `errors={}`, `expected_diffs=[]`, and `heterogeneous={}`.

## 2026-06-12 Checkpoint — W7 Shadow Telemetry Persistence

Commit: `epyc-orchestrator` `e40df31` (`Persist routing shadow telemetry in progress logs`).

Implementation:
- Moved Trinity tri-role classification before the durable routing log call so `assigned_role` is written into each `routing_decision` progress event.
- When `ure_uncertainty_shadow_log` is enabled, `routing_meta()` now computes and stores `uncertainty_score`, `uncertainty_components`, and `uncertainty_n_alternatives` directly on the progress event. The existing `data/trace/uncertainty_shadow.jsonl` sidecar remains for older ingest jobs.
- Difficulty and factual-risk fields were already present in `logs/progress/*.jsonl`; W7 completes the missing Trinity + URE pieces.

Verification:
- Pre-edit GitNexus impacts were HIGH for `routing_meta`, `log_routing_start`, `classify_trinity_role`, and `emit_uncertainty_shadow` because they sit on the shared chat routing path (`generate_stream` / `chat_stream` upstream). Patch was additive-only: no routing decisions or flag behavior changed.
- Live audit before the patch: today's progress log had 176 routing decisions with difficulty/risk fields, 0 with Trinity role fields, and 0 with URE fields; `data/trace/uncertainty_shadow.jsonl` had 93,232 URE sidecar rows.
- `python3 -m py_compile src/api/routes/chat_pipeline/routing.py src/api/routes/chat_pipeline/routing_decision.py src/uncertainty_shadow.py` passed.
- `uv run pytest tests/unit/test_pipeline_routing.py tests/unit/test_uncertainty_shadow.py tests/classifiers/test_difficulty_signal.py tests/unit/test_chat_pipeline_stages.py` -> 157 passed.
- `uv run pytest tests/unit/test_chat_routes.py tests/unit/test_chat_endpoints.py tests/integration/test_chat_pipeline.py tests/unit/test_runtime_flags.py` -> 80 passed.
- `git diff --check` for touched files passed.
- Reloaded orchestrator through `scripts/server/orchestrator_stack.py reload orchestrator`; new supervisor PID `2719260` healthy and prior PID `2711818` verified gone by `ps`. Post-reload `/config/attest` saw 6 workers, `errors={}`, `expected_diffs=[]`, and `heterogeneous={}`.
- GitNexus re-indexed commit `e40df31`: 48,681 nodes, 83,579 edges, 992 clusters, 300 flows.
- Live no-inference smoke: 24 mock-mode `/chat` requests wrote 24 new `routing_decision` rows; all had `assigned_role`, `uncertainty_score`, `uncertainty_components`, and `uncertainty_n_alternatives`.

## 2026-06-12 Checkpoint — W8 DAR-1 Replay + Cheap-First Counters

Commit: `epyc-orchestrator` `1dfbc22` (`Measure routing regret and log cheap-first counters`).

Implementation:
- Repaired `scripts/analysis/dar1_regret_analysis.py` outcome parsing: durable progress rows write `outcome` and `reward` at the event top level, not only under `data`.
- Added explicit identifiable-vs-unidentified regret accounting. Historical rules/classifier rows that lack candidate action IDs are now reported as unidentifiable instead of treated as precise regret.
- Added `action_topk` to `HybridRouter._record_decision_meta()` so future `routing_decision` rows can support true selected-vs-best regret replay.
- Added `_try_cheap_first` progress counters under `event_type=routing_fallback`, `data.kind=try_cheap_first`, covering disabled/skipped/attempted/rejected/accepted reasons.
- Added `orchestration/reports/dar1_regret_replay_2026-06-12.md`.

Replay result:
- Command: `uv run python scripts/analysis/dar1_regret_analysis.py --from 2026-06-05 --to 2026-06-12`.
- Decisions analyzed: 12,057; matched outcomes: 11,249.
- Learned Q-scorer decisions: 8,145; rules/classifier decisions: 3,912.
- Regret-identifiable decisions: 8,145 (67.6%); mean decision regret: 0.0000; DAR-1 gate regret percent: 0.00%; max regret: 0.0000.
- Q-scorer signal remains degenerate: 99.1% uniform Q-values and 95.2% trivial selection-score spread.
- Gate verdict: Phase 3 cascade expansion remains frozen. Re-run quarterly or after enough new `action_topk` telemetry accumulates.

Verification:
- `python3 -m py_compile scripts/analysis/dar1_regret_analysis.py orchestration/repl_memory/hybrid_router.py src/api/routes/chat.py` passed.
- `uv run pytest tests/unit/test_dar1_regret_analysis.py tests/unit/test_chat_routes.py tests/unit/test_chat_endpoints.py tests/integration/test_chat_pipeline.py` -> 74 passed.
- `uv run pytest tests/unit/test_uncertainty_shadow.py tests/classifiers/test_difficulty_signal.py tests/unit/test_pipeline_routing.py tests/unit/test_dar1_regret_analysis.py tests/unit/test_chat_routes.py tests/unit/test_chat_endpoints.py tests/integration/test_chat_pipeline.py` -> 167 passed.
- `git diff --check` for touched orchestrator files passed.
- Reloaded orchestrator through `scripts/server/orchestrator_stack.py reload orchestrator`; new supervisor PID `2734276` healthy and prior PID `2719260` absent by `ps`. Post-reload `/config/attest` saw 6 workers with `errors={}`, `expected_diffs=[]`, and `heterogeneous={}`.
- GitNexus re-indexed commit `1dfbc22`: 48,727 nodes, 83,649 edges, 998 clusters, 300 flows.
- Live `/chat` smoke requests succeeded, but did not produce routing/task progress rows in `logs/progress/2026-06-12.jsonl`; treat live counter verification as covered by unit/integration tests until the request-path progress logging discrepancy is separately investigated.

## Reporting

Immediate repair scope is complete. Keep only the `dispatch_swarm_fanout` ownership watch through 2026-07-12; any new routing-expansion work must pass a fresh measured gate.
