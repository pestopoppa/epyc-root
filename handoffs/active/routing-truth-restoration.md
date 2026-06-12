# Routing Truth Restoration: Prod Flags, Attestation, Dead Code

**Status**: IN PROGRESS — W1-W5 landed and live-attested/deployed 2026-06-12; W6-W8 remain
**Created**: 2026-06-12
**Priority**: NOW/HIGH — master-index N3; every runtime-flag A/B under 6-worker uvicorn has measured a 5/6-unmutated system
**Spec**: [fable5-findings-02-impl-plan.md](fable5-findings-02-impl-plan.md) Phases 0–1 + [fable5-findings-02-routing-decision-architecture.md](fable5-findings-02-routing-decision-architecture.md) §2/§4 — read both before claiming any waypoint
**Related**: [decision-aware-routing.md](decision-aware-routing.md) (DAR-1 replay executes there), [learned-routing-controller.md](learned-routing-controller.md) (the dead MLP fast-path), [running-state-attestation.md](running-state-attestation.md) (system-wide ATTESTATION generator — this handoff owns ONLY the flags endpoint)

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
- [ ] **W6 — zero-caller deletions** (~1 day): `get_confidence_routing` + helpers (`chat_routing.py:283-448`), `HybridRouter.route_3way` (`hybrid_router.py:587-699`), `dispatch_swarm_fanout` (if no handoff claims it within the month) — proof in spec §4; un-set `ORCHESTRATOR_ROUTING_CLASSIFIER` until weights exist (stop the boot-warning lie). Expected −1.5–2K LoC + test files.
- [ ] **W7 — shadow-telemetry decision**: Trinity/difficulty/URE shadows log to non-persisted INFO (outputs not found on disk) — either route shadow events into `logs/progress/*.jsonl` (the file QScorer already mines) or stop running them per-request; shadow without a ratification path is pure cost. Rides master-index N10.
- [ ] **W8 — Phase 1 measurement** (1–2 days): DAR-1 regret replay on last-7-days traffic — executes via [decision-aware-routing.md](decision-aware-routing.md); link, do not duplicate. Plus `_try_cheap_first` accept/reject counters into progress JSONL (currently unobservable). Gate: regret ≥5% of requests opens Phase 3 (cascade); <5% freezes routing expansion indefinitely (re-run quarterly). Prediction on record: <5%.

## Gates & pitfalls

- W1 blocks only W2; W3–W7 are parallelizable today. W8's counter half depends on W7; the replay runs on existing logs.
- Long-dormant flags ARE new code: never enable wave-2 flags together; one observation window each.
- Attestation results must be journaled WITH each autopilot flag trial — otherwise flag experiments remain unmeasurable (findings-01 §3.4).
- Use `orchestrator_stack.py reload` for any restart — never manual PID kills.
- Record the W8 verdict either way: it gates the entire routing-expansion cluster (master-index gate table) and the Phase-3 tail of model-capability-descriptors.

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

## Reporting

Tick waypoints + one-line progress entry; delete master-index row N3 on completion (W8 verdict also updates the routing-expansion gate-cluster row); numbers via MEASUREMENT.md §2 claim grammar.
