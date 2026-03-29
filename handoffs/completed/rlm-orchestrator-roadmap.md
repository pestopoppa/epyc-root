# RLM-Orchestrator Roadmap (Post-Orchestration Stabilization)

**Created**: 2026-01-13
**Updated**: 2026-02-19
**Status**: ARCHIVED (2026-03-29)
**Archived**: 2026-03-29
**Archive reason**: R1-R6 all complete. Phase 7 (hyperparameter tuning) superseded by `autopilot-continuous-optimization.md` (2026-03-08), which implements continuous multi-species optimization with Pareto archive, safety gates, and staged rollout — a superset of what Phase 7 envisioned. Follow-on tasks 1-4 extracted to `routing-and-optimization-index.md` § P9. Task 5 (feature vetting) superseded by autopilot safety gates. Task 6 references `01-fast-rlm-budget-controls.md` which never existed — the underlying work (budget propagation) was completed as R1/D2. D1 context compaction superseded by `context-folding-progressive.md`. MemRL distillation (2026-03-05 section) is complementary to `routing-intelligence.md` Phase 2. Section 5 doc edit spec references stale chapter numbers (pre-renumbering) — verify against actual files before using.
**Primary Goal**: close remaining orchestration/runtime gaps with implementation-ready tasks for next session
**Related**:
- `handoffs/archived/programmatic-tool-chaining.md`
- `handoffs/archived/inference-lock-starvation-bug.md`
- `docs/reference/agent-config/ORCHESTRATION_DEBUG_PLAYBOOK.md`

---

## 1) Current State Snapshot (What Is Already Done)

### 2026-02-18 incremental update (R1 started)

- Added shared request-budget diagnostics surface in API responses (`budget_diagnostics`).
- Unified timeout clamping through `LLMPrimitives` request budget helpers across:
  - single-call paths,
  - streaming paths,
  - caching/model-server backend calls,
  - worker-pool batch timeout wrapping.
- `/chat` pipeline now attaches per-request budget telemetry to all mode responses.
- Added integration-level API proof that finalized `/chat` responses include `budget_diagnostics` from primitives (without heavy inference dependency).
- Added direct `LLMPrimitives` unit coverage for budget clamping behavior in request context (deadline and no-deadline paths).
- This closes the first implementation slice of R1; remaining R1 work is strict end-to-end coverage and additional integration proof under contention.

### 2026-02-19 incremental update (R1 contention evidence add-on)

- Ran a fresh 5-seed contention-debug sweep (`seed=76..80`) with API-only preflight relaunch per run:
  - command: `ORCHESTRATOR_UVICORN_WORKERS=6 ORCHESTRATOR_FRONTDOOR_TRACE=1 ORCHESTRATOR_DELEGATION_TRACE=1 ORCHESTRATOR_DELEGATION_TOTAL_MAX_SECONDS=55 ORCHESTRATOR_DELEGATION_SPECIALIST_MAX_SECONDS=25 ORCHESTRATOR_INFERENCE_LOCK_TIMEOUT_EXCLUSIVE_S=45 ORCHESTRATOR_INFERENCE_LOCK_TIMEOUT_SHARED_S=45 timeout 220 python3 scripts/benchmark/seed_specialist_routing.py --3way --suites simpleqa --sample-size 1 --no-pool --seed <N> --timeout 90 --preflight`
- Evidence outcomes:
  - lock-holder cleanup remained clean in all five runs:
    - `LOCK_HOLDERS seed=76 pids=none`
    - `LOCK_HOLDERS seed=77 pids=none`
    - `LOCK_HOLDERS seed=78 pids=none`
    - `LOCK_HOLDERS seed=79 pids=none`
    - `LOCK_HOLDERS seed=80 pids=none`
  - bounded timeout/error branches still occurred (`rc=124` on seeds 78, 79), but with explicit timeout-erase handling and no stale lock retention.
  - non-timeout runs stayed bounded (`rc=0` on seeds 76, 77, 80) with delegation diagnostics populated.
- R1 implication:
  - deadline/lock budget hardening appears operationally stable under this sweep (no stale-abandoned lock evidence),
  - remaining R1 gap is deeper response-level diagnostics completeness for pre-delegation abort branches and broader integration-proof depth, not lock cleanup correctness.

### 2026-02-19 incremental update (R1 diagnostics completeness patch)

- Updated REPL-mode delegation diagnostics to avoid ambiguous empty break reasons when delegation never starts:
  - `src/api/routes/chat_pipeline/repl_executor.py`
  - `_build_delegation_diagnostics(...)` now emits a canonical delegated-shape payload even with zero delegation events:
    - `loops`, `phases_count`, `break_reason`, `cap_reached`, `effective_max_loops`, `reentrant_depth`,
      `report_handles_count`, `report_handles`, `delegation_inference_hops`, `avg_prompt_ms`, `avg_gen_ms`
  - Added break-reason inference from error text for pre-start failures:
    - `pre_delegation_abort`, `pre_delegation_lock_timeout`, `request_cancelled`, `deadline_exceeded`, `request_timeout`.
- Validation:
  - targeted unit tests passed:
    - `tests/unit/test_repl_executor.py::TestExecutionTimeout::test_repl_execution_timeout`
    - `tests/unit/test_repl_executor.py::TestBasicREPLExecution::test_llm_call_exception_returns_error`

- Root-cause fix (not just fallback inference):
  - `src/api/routes/chat_delegation.py::_run_architect_decision(...)` now classifies architect Phase-A inference failures into stable reasons (`pre_delegation_lock_timeout`, `request_timeout`, `request_cancelled`, `deadline_exceeded`, `pre_delegation_architect_error`).
  - `_architect_delegated_answer_inner(...)` now propagates this reason into `stats.break_reason` on early Phase-A failure instead of returning generic error text with empty diagnostics.
  - Additional root-cause closure: when `llm_call` returns an inline `"[ERROR: ...]"` string (instead of raising), Phase-A now treats it as a failure (not a direct `D|` answer) and maps reason via `_classify_failure_reason(...)`.
  - backward-compatible tuple unpacking retained for existing tests/mocks that still return the legacy 3-tuple from `_run_architect_decision`.
- Validation (root-cause path):
  - `tests/unit/test_architect_delegation.py::TestArchitectDelegatedAnswer::test_pre_delegation_architect_lock_timeout_sets_break_reason`
  - `tests/unit/test_architect_delegation.py::TestArchitectDelegatedAnswer::test_pre_delegation_error_string_sets_break_reason`
  - `tests/integration/test_chat_pipeline.py::TestChatEndpoint::test_delegated_pre_start_lock_timeout_sets_break_reason`
  - live runtime contention probe (two concurrent `/chat` calls) now yields delegated response diagnostics with:
    - `break_reason=pre_delegation_lock_timeout`
    - `loops=0`
    - `answer="[ERROR: Architect delegation failed]"`

### 2026-02-19 incremental update (R1 breadth-proof add-on, seeds 86-90)

- Ran an additional 5-seed contention-debug sweep outside sandbox (preflight requires socket checks):
  - command template:
    - `ORCHESTRATOR_UVICORN_WORKERS=6 ORCHESTRATOR_FRONTDOOR_TRACE=1 ORCHESTRATOR_DELEGATION_TRACE=1 ORCHESTRATOR_DELEGATION_TOTAL_MAX_SECONDS=55 ORCHESTRATOR_DELEGATION_SPECIALIST_MAX_SECONDS=25 ORCHESTRATOR_INFERENCE_LOCK_TIMEOUT_EXCLUSIVE_S=45 ORCHESTRATOR_INFERENCE_LOCK_TIMEOUT_SHARED_S=45 timeout 220 python3 scripts/benchmark/seed_specialist_routing.py --3way --suites simpleqa --sample-size 1 --no-pool --seed <N> --timeout 90 --preflight`
- Outcomes:
  - `seed=86`: `rc=0`, `elapsed_s=189`, `LOCK_HOLDERS=none`
  - `seed=87`: `rc=0`, `elapsed_s=117`, `LOCK_HOLDERS=none`
  - `seed=88`: `rc=0`, `elapsed_s=133`, `LOCK_HOLDERS=none`
  - `seed=89`: `rc=0`, `elapsed_s=161`, `LOCK_HOLDERS=none`
  - `seed=90`: `rc=0`, `elapsed_s=156`, `LOCK_HOLDERS=none`
- Diagnostics observations:
  - delegated diagnostics remained populated in architect paths (`break_reason=specialist_report` in successful delegation loops),
  - no stale-abandoned heavy lock holder observed across the full sequence.
- Implication:
  - R1 contention breadth evidence is strengthened (now two separate 5-run sweeps with clean lock-holder state),
  - remaining D2 closure work is contract-level completeness across every internal call surface, not contention lock hygiene.

### 2026-02-19 incremental update (R1 contract-completeness closure)

- Closed the remaining D2 contract gap by making request context propagation explicit in all threaded/async batch call surfaces:
  - `src/llm_primitives/primitives.py`
    - `llm_batch_async(...)` now binds current contextvars for each executor task via `_bind_current_context(...)`.
  - `src/llm_primitives/inference.py`
    - `_real_batch(...)` threadpool submissions now run under copied context (`contextvars.copy_context().run(...)`).
    - `_fallback_batch(...)` threadpool submissions now run under copied context as well.
- Why this matters:
  - request-local `task_id` / `deadline_s` attribution is now deterministic through executor boundaries,
  - budget clamp + lock telemetry attribution remains consistent even when batch fan-out crosses thread/executor edges.
- Validation:
  - `tests/unit/test_llm_primitives.py::test_llm_batch_async_propagates_request_context_to_executor_threads`
  - `tests/unit/test_llm_primitives.py::test_llm_batch_propagates_request_context_to_threadpool_calls`
  - plus existing request-context tests in same module (`4 passed` targeted run).
- R1 result:
  - root-cause diagnostics completeness fixed,
  - contention breadth evidence captured (two 5-run sweeps),
  - call-surface context propagation contract now explicit across batch async/threadpool paths.

### 2026-02-18 incremental update (R2 started)

- Added canonical wave-level chain telemetry emission in REPL chain diagnostics:
  - `wave_timeline[]` entries now carry:
    - `wave_index`
    - `tools`
    - `mode_used`
    - `elapsed_ms`
    - `fallback_to_seq`
    - `parallel_mutations_enabled`
- Response summarization path now normalizes/backs-fills `wave_timeline` for compatibility even when only legacy `waves` count exists.
- ClaudeDebugger prompt rendering now includes wave timeline lines (per-chain `wave#...` rows), improving chain-loop diagnosis granularity.
- Added integration-level API proof that `/chat` REPL responses surface normalized `tool_chains.wave_timeline` payloads (not only unit-level coverage).
- R2 closure note supersedes this baseline; optional UI polish remains non-blocking.

### 2026-02-19 incremental update (R2 visualization closure)

- Enhanced debugger rendering from flat chain lines to explicit timeline blocks:
  - delegation phase timeline rows now render from `delegation_diagnostics.phases[]` (`loop`, `phase`, `elapsed_ms`, `decision/target/mode/turns`),
  - wave timeline blocks are now explicitly grouped under each chain (`wave_timeline:` header + per-wave rows).
- This closes the missing visualization depth called out in Phase 8 without changing response schema contracts.
- Validation:
  - `tests/unit/test_claude_debugger.py::test_prompt_includes_tool_chain_wave_diagnostics`
  - `tests/unit/test_claude_debugger.py::test_prompt_includes_delegation_phase_timeline`
  - `tests/unit/test_claude_debugger.py::test_prompt_includes_wave_timeline_header_for_multi_wave`
  - Result: `3 passed`.
- R2 status:
  - canonical wave schema emission: complete,
  - debugger timeline rendering: complete,
  - integration proof for surfaced chain diagnostics: complete.
  - optional Gradio/UI visual polish remains explicitly non-blocking.

### 2026-02-18 incremental update (R3 started)

- Added feature-gated depth-aware role override support in `LLMPrimitives`:
  - new feature flag: `depth_model_overrides`
  - env override map support via `ORCHESTRATOR_LLM_DEPTH_ROLE_OVERRIDES`
  - safe fallback to requested role when override target backend is unavailable
- Added explicit config-level wiring for depth-role overrides:
  - `LLMConfig.depth_role_overrides`
  - `ORCHESTRATOR_LLM_DEPTH_ROLE_OVERRIDES` loaded into config and consumed by primitives (env fallback preserved for compatibility).
- Depth semantics:
  - caller depth (root) keeps requested role
  - nested depth uses configured override map (default depth-1 baseline mapping when enabled)
- Added unit coverage for enabled/disabled behavior and feature-summary integration.
- R3 closure note below supersedes this baseline rollout-tuning placeholder.

### 2026-02-19 incremental update (R3 rollout-tuning evidence closure)

- Captured live ON/OFF rollout evidence for depth overrides on the delegated architect path:
  - **OFF probe** (`DEPTH_MODEL_OVERRIDES=0`):
    - `mode=delegated`, `routed_to=architect_coding`, `error_code=None`, `elapsed≈32.8s`
    - `budget_diagnostics.depth_override_enabled=False`
    - `break_reason=specialist_report`, `loops=1`, `delegation_inference_hops=1`
  - **ON probe** (`DEPTH_MODEL_OVERRIDES=1`):
    - `mode=delegated`, `routed_to=architect_coding`, `error_code=None`, `elapsed≈45.8s`
    - `budget_diagnostics.depth_override_enabled=True`
    - `break_reason=specialist_report`, `loops=1`, `delegation_inference_hops=1`
- Interpretation:
  - feature gating and runtime telemetry toggles are verified in live requests,
  - delegated path remains stable/bounded in both modes,
  - existing deterministic mapping + guardrail behavior remains covered by unit suite (`test_primitives_extended` + `test_llm_primitives`).
- R3 status: rollout-tuning evidence requirement is now satisfied for this roadmap cycle.

### 2026-02-19 incremental update (R4 started)

- Formalized checkpoint protocol boundary for REPL restore:
  - added explicit checkpoint payload `protocol_version` in `Checkpoint` serialization,
  - added protocol constants + normalize function in `src/session/protocol.py`:
    - required restore fields,
    - optional restore fields,
    - compatibility modes (`exact`, `legacy_upgrade`, `forward_downgrade`),
    - diagnostics for dropped/required-missing fields.
- `/chat` REPL restore path now uses normalization before `repl.restore(...)` and emits protocol diagnostics in response payload:
  - `session_persistence.restore_protocol`.
- Added migration/compat tests for missing/legacy and forward/newer payload versions:
  - `tests/unit/test_session_models.py`
  - `tests/unit/test_session_protocol.py`
  - `tests/integration/test_chat_pipeline.py::test_session_restore_protocol_compat_diagnostics`
- Protocol behavior documented in chapter/playbook docs:
  - `docs/chapters/20-session-persistence.md`
  - `docs/reference/agent-config/ORCHESTRATION_DEBUG_PLAYBOOK.md`
- Remaining R4 work is optional deeper migration policy (if/when protocol v2 is introduced) and broader contention-run evidence bundling with other open roadmap tracks.

### 2026-02-19 incremental update (Phase 6 load-validation closure)

- Completed targeted validation of early-failure detection surfaces:
  - unit-level monitor/integration suite:
    - `python3 -m pytest -n 0 tests/unit/test_chat_pipeline_stages.py tests/unit/test_stages.py tests/unit/test_generation_monitor.py -k "generation_monitor or early_abort" -q`
    - result: `47 passed`.
  - live concurrent load probe with monitor explicitly enabled (`GENERATION_MONITOR=1`):
    - 4 parallel `/chat` requests (real-mode direct, `timeout_s=90`) under API reload profile,
    - outcomes: 2 successful responses, 2 explicit bounded `504` lock-timeout responses, no silent hangs.
- Interpretation:
  - early-failure monitor path remains active and regression-free in covered unit/integration paths,
  - under live concurrent load, failures surfaced as explicit bounded errors (not stalled/opaque behavior).
- Phase 6 status: validation evidence requirement satisfied for this roadmap cycle.

### 2026-02-19 incremental update (R6 completed)

- Completed safe-default enablement set for this roadmap cycle:
  - `session_compaction` switched to default-on for `get_features(production=True)`.
  - `depth_model_overrides` switched to default-on for `get_features(production=True)` after guardrail hardening.
- Added rollout guardrails for depth overrides:
  - max-depth cap (`LLMConfig.depth_override_max_depth`, registry default `3`)
  - worker-only override targets
  - backend-availability fallback preserving requested role
  - skip telemetry (`depth_override_skip_events`, `depth_override_skip_reasons`)
- Added explicit rollback and validation guidance in docs:
  - rollback env: `ORCHESTRATOR_SESSION_COMPACTION=0`
  - rollback env: `ORCHESTRATOR_DEPTH_MODEL_OVERRIDES=0`
  - smoke-check guidance in playbook/architecture docs.
- Kept higher-risk flags default-off with rationale:
  - `content_cache`, `model_fallback`, `structured_tool_output`,
  - `side_effect_tracking` / `approval_gates`.
- Updated candidate matrix for next enablement wave (remaining default-off candidates):
  1. `model_fallback` (requires fallback-quality guardrails under induced backend faults),
  2. `structured_tool_output` (requires tool-consumer compatibility sweep),
  3. `content_cache` (requires cache-correctness + invalidation confidence),
  4. `side_effect_tracking`/`approval_gates` (requires policy+UX validation).
- R6 closure evidence:
  - targeted unit validation passed (`194 passed`)
  - live seeded smoke (`seed=75`) remained bounded and lock-clean.

### 2026-02-19 incremental update (R5 completed)

- Ran 5 consecutive contention-debug seeded probes (`seed=70..74`) using:
  - `seed_specialist_routing.py --3way --suites simpleqa --sample-size 1 --no-pool --timeout 90 --preflight`
  - orchestrator API reload/profile path only (`reload orchestrator --profile contention-debug`), without full stack restart.
- Evidence outcomes:
  - post-run heavy lock holder check was clean in all 5 runs:
    - `LOCK_HOLDERS ... pids=none` for seeds 70, 71, 72, 73, 74
  - delegated architect hops remained bounded (roughly 16-26s in these runs)
  - one run (`seed=73`) hit bounded `SELF:repl` infra timeout path (`~88.7s`, `rc=124`) but still released lock cleanly (no stale holder).
- Conclusion:
  - stale-abandoned inference-lock behavior was not observed across the 5-run sequence under contention-debug profile.
  - residual risk remains around occasional infra timeout branches, but they are bounded and do not leak lock ownership.

### Core orchestration/runtime work completed recently

- Inference lock starvation hardening is in place:
  - request-tagged lock telemetry + holder attribution (`src/inference_lock.py`)
  - lock wait timeouts + cancellation/deadline awareness (`src/inference_lock.py`)
- Delegation loop stabilization is in place:
  - explicit break reasons (`specialist_timeout`, `specialist_report`, `wall_clock_budget`)
  - specialist report rescue paths
  - bounded delegation loops with guard rails (`src/api/routes/chat_delegation.py`)
- Artifact-backed delegated report hydration is implemented:
  - persisted handles + summary pointer path (`src/delegation_reports.py`, `src/api/routes/chat_delegation.py`)
  - REPL + API retrieval (`fetch_report(...)`, `GET /chat/delegation-report/{report_id}`)
- Programmatic tool chaining phases 1-3 are implemented:
  - deferred tool result handling
  - `allowed_callers` policy + chain diagnostics (`tool_chains`)
  - cross-request REPL globals persistence with `session_id` checkpoints
- Worker runtime alignment is implemented:
  - `worker_coder` is active semantic coding worker
  - `worker_code` kept as compatibility alias
  - stack/role mapping aligned (`scripts/server/orchestrator_stack.py`, routing/config docs)
- API lifecycle operability improved:
  - `orchestrator_stack.py reload orchestrator --profile contention-debug`
  - reload-state serialization robustness in stack launcher

### Notes on RLM deltas vs current code

- D1 context compaction: effectively implemented as session compaction in graph execution (`src/graph/helpers.py`, feature `session_compaction`). **Further context management work superseded by `handoffs/active/context-folding-progressive.md`** — progressive 4-phase upgrade from single-level compaction to two-tier condensation with process reward telemetry, informed by Context-Folding (intake-154), AgentFold (intake-155), MemAgent (intake-156), and ReSum (intake-157).
- D2 budget propagation: partially implemented (delegation and lock/deadline paths), not yet end-to-end through all sub-LM calls.
- D3 depth-based model override: implemented with config/env/registry wiring, worker-only + max-depth guardrails, and production default-on rollout (`get_features(production=True)`).
- D4 persistence protocol: versioned protocol boundary and restore compatibility diagnostics implemented; future protocol-version migrations remain optional.
- D5/D6 (external MCP service + sandbox isolation modes): still deferred and non-blocking for current local orchestrator quality goals.

---

## 2) Reconciled Status Matrix

| Track | Previous Label | Actual Code State | Updated Status |
|---|---|---|---|
| Phase 1 Backend completion | Complete | Complete, in active use | ✅ Done |
| Phase 2 RLM enhancements | Complete | Complete for recursion/async/cost + forced exploration lineage | ✅ Done |
| Phase 3 Escalation integration | Complete | Complete + additional delegation loop hardening | ✅ Done |
| Phase 4 Formalizer | Complete | Complete (feature-flagged) | ✅ Done |
| Phase 5 Tool/script completion | Complete | Complete + expanded chaining model | ✅ Done |
| Phase 6 Early failure detection | Ready | Generation monitor integrated and now validated under targeted tests + live concurrent probe | ✅ Done |
| Phase 7 Hyperparameter tuning | Ready/Blocked | Benchmark ecosystem exists; contention evidence artifact now captured for lock/delegation stability | 🟡 Partial (tuning still open) |
| Phase 8 Trajectory visualization | Low | Complete for API+debugger surfaces (wave schema + timeline rendering + integration proof); optional Gradio polish is non-blocking | ✅ Done |
| D1 context compaction | High, pending | Implemented under `session_compaction` flow | ✅ Done (needs docs alignment) |
| D2 budget propagation | High, pending | Contract now explicit across single + stream + batch + async/threadpool paths; contention evidence captured | ✅ Done |
| D3 depth model override | Medium | Implemented with guardrails + registry/config wiring + production default-on, plus live ON/OFF rollout evidence | ✅ Done |
| D4 versioned persistence protocol | Medium design | Protocol/version boundary + compatibility diagnostics implemented | ✅ Done (v1 boundary) |
| D5 RLM-as-MCP-service | Low | Not pursued | ⏸ Deferred |
| D6 isolation modes (Docker/Modal/E2B) | Low | Not pursued | ⏸ Deferred |

---

## 3) Outstanding Tasks For Next Implementation Session

Priority order is based on impact to latency stability and orchestration correctness.

### R1 (Highest): End-to-end budget/deadline propagation across sub-LM paths

Status: ✅ Completed (2026-02-19).

Implemented:
- shared request-budget context + diagnostics in `LLMPrimitives`,
- timeout clamp + lock deadline propagation across single-call, streaming, batch, and worker-pool paths,
- delegated pre-start diagnostics root-cause fixes (`break_reason` propagation),
- explicit contextvars propagation across executor/threadpool batch surfaces,
- contention-depth operational evidence (two 5-seed sweeps, lock holders clean).

Residual optional work (non-blocking):
- additional high-volume perf characterization of budget clipping frequency by role/backends.

### R2: Complete trajectory visualization track (Phase 8 closure)

Status: ✅ Completed (2026-02-19).

Implemented:
- canonical per-wave response schema in `tool_chains.wave_timeline`,
- debugger timeline rendering for both tool-chain waves and delegation phases,
- integration proof that `/chat` responses surface normalized chain diagnostics.

Residual optional work (non-blocking):
- additional visual polish in deprecated `src/gradio_ui.py` if that UI path is revived.

### R3: Depth-aware model override (targeted optimization)

Status: ✅ Completed (2026-02-19).

Implemented:
- depth-aware role override map + feature gate + config/registry wiring,
- max-depth + worker-only + backend-availability guardrails,
- response telemetry fields for rollout inspection,
- live ON/OFF probe evidence on delegated architect path with bounded outcomes,
- deterministic mapping and guardrail test coverage in unit suites.

Residual optional work (non-blocking):
- further role-map fine-tuning only if future benchmark quality deltas warrant it.

### R4: Formalize persistence protocol boundary (D4 hardening)

**Problem**: persistence works, but interface contract is implicit.

**Target files**:
- `src/session/models.py`
- `src/session/protocol.py`
- `src/api/routes/chat_pipeline/repl_executor.py`

**Spec**:
- Define explicit versioned checkpoint protocol document + code comments:
  - required fields
  - optional fields
  - forward/backward-compat behavior
- Add migration and restore tests for missing/older versions.

**Acceptance criteria**:
- Restore path handles version absent/older/newer gracefully with explicit diagnostics.
- Protocol documented in chapter docs (see doc plan below).

### R5: Phase-closure evidence collection under contention

**Problem**: several tracks are implemented but lack fresh, bundled evidence artifacts for closure.

**Spec**:
- Run contention/delegation sweep with `contention-debug` profile.
- Capture 5+ consecutive runs showing no stale-abandoned lock holders and bounded delegated latency.
- Store results in progress log and optionally benchmark results notes.

**Acceptance criteria**:
- Evidence includes command lines, timings, break reasons, and residual risk notes.
- ✅ Completed on 2026-02-19 (5-run sweep with lock-holder telemetry, see incremental update above).

### R6 (Last): Safe-to-enable-by-default feature-set review

**Problem**: multiple implemented features remain OFF by production default; we need a risk-ranked enablement pass instead of ad-hoc toggling.

**Target files**:
- `src/features.py`
- `docs/reference/agent-config/ORCHESTRATION_DEBUG_PLAYBOOK.md`
- `docs/chapters/10-orchestration-architecture.md`

**Spec**:
- Build a shortlist of low-risk, high-value flags to enable by default in production.
- For each candidate flag, capture:
  - expected benefit
  - rollback toggle/env var
  - known regression risk and required smoke checks
- Keep high-risk items OFF by default with explicit rationale in docs.

**Acceptance criteria**:
- `get_features(production=True)` defaults updated only for approved safe set.
- Documentation lists enabled-by-default rationale and rollback path per changed flag.
- ✅ Completed on 2026-02-19:
  - safe set promoted: `session_compaction`, `depth_model_overrides`
  - higher-risk features remain default-off with documented rationale and rollback.

---

### 2026-03-05 incremental update (MemRL Distillation Pipeline)

- Implemented ColBERT-Zero Track 2: routing classifier distilled from episodic memory Q-values.
- New feature flag: `routing_classifier` (`ORCHESTRATOR_ROUTING_CLASSIFIER`). Default off — enable after A/B test.
- `EpisodicStore.get_all_memories()` added — bulk retrieval method needed by `routing_graph.py:135` and the training pipeline.
- Files: `routing_classifier.py`, `extract_training_data.py`, `train_routing_classifier.py`, `ab_test_classifier.py` (NEW); `episodic_store.py`, `retriever.py`, `features.py`, `reset_episodic_memory.sh` (MODIFIED).
- Reset-safe: weights auto-deleted on memory reset, handoff auto-created for retraining.
- 25 new tests. See `docs/reference/agent-config/MEMRL_DISTILLATION_DESIGN.md`.

## 4) Follow-On Tasks Recommended (Post-Roadmap)

1. Add a lightweight delegation SLO report job (daily summary from logs): p50/p95 delegation latency, timeout rate, report-handle emission rate.
2. Add chain-execution anomaly detection in debugger (flag frequent fallback-to-seq or repeated wave stalls).
3. Remove legacy `worker_code` naming in docs/prompts/constants once compatibility window is officially closed.
4. Evaluate safe partial shared-result cache for repeated delegated subtasks (content-hash keyed report snippets).
5. Systematize feature vetting and default-on promotion:
   - define a single risk/benefit scoring rubric for candidate flags,
   - require a standard evidence pack per flag (targeted tests + bounded live probe + rollback drill),
   - enforce staged rollout gates (`off` -> `shadow` -> `default-on`) with explicit pass/fail criteria recorded in roadmap/progress/changelog.
6. **Extend budget controls with recursion depth + call count limits** — continues R1/D2 budget propagation work. Adds formal recursion depth caps (prevent infinite escalation loops), per-worker call count budgets, and per-task aggregate token envelopes. Tracked in `handoffs/active/01-fast-rlm-budget-controls.md` (research source: [Fast-RLM](https://github.com/avbiswas/fast-rlm)).

---

## 5) Documentation Edit Specification (For Next Session)

These edits should happen alongside R1-R4 implementation PRs.

### Required chapter updates

- `docs/chapters/10-orchestration-architecture.md`
  - Add section: request-budget propagation contract and diagnostics fields.
  - Clarify session compaction as D1 closure.
- `docs/chapters/18-escalation-and-routing.md`
  - Add delegation break-reason taxonomy and timeout semantics.
  - Add depth-aware model override behavior if R3 ships.
- `docs/chapters/22-tool-registry.md`
  - Expand wave diagnostics format (`tool_chains` schema details).
- `docs/chapters/26-claude-debugger.md`
  - Document wave-level visualization semantics and troubleshooting path.
- `docs/chapters/29-programmatic-tool-chaining.md`
  - Add “operational hardening” appendix linking to budget propagation and persistence protocol versioning.

### Agent knowledge/playbook updates

- `docs/reference/agent-config/ORCHESTRATION_DEBUG_PLAYBOOK.md`
  - Add budget-propagation debugging checklist and expected diagnostics.
- `agents/shared/WORKFLOWS.md`
  - Keep handoff closure workflow in sync with actual lifecycle requirements.

### Tracker updates required with each closure step

- `coordination/BLOCKED_TASKS.md`
- `handoffs/README.md` (if active/archived transitions occur)
- `CHANGELOG.md`

---

## 6) Verification Commands (Next Session Starter Pack)

```bash
# 1) Validate roadmap-targeted tests
python3 -m pytest tests/unit/test_primitives_extended.py tests/unit/test_repl_executor.py tests/unit/test_architect_delegation.py -v

# 2) Validate chaining + persistence integration
python3 -m pytest tests/integration/test_chat_pipeline.py -k "tool_chains or session_persistence or delegation_report" -v

# 3) Reload with contention profile
python3 scripts/server/orchestrator_stack.py reload orchestrator --profile contention-debug

# 4) Seed probe (single-sample sanity)
ORCHESTRATOR_FRONTDOOR_TRACE=1 ORCHESTRATOR_DELEGATION_TRACE=1 \
python3 scripts/benchmark/seed_specialist_routing.py --3way --suites simpleqa --sample-size 1 --no-pool --preflight
```

---

## 7) Handoff Lifecycle Notes

This handoff remains active because Phase 7 hyperparameter tuning is still open.
When all open items above are complete:

1. Extract final findings to docs chapters.
2. Update blocked/task trackers and changelog with closure evidence.
3. Archive this handoff from `handoffs/active/` to `handoffs/archived/`.

## Research Intake Update — 2026-03-16

### New Related Research
- **[intake-153] "Recursive Language Models"** (arxiv:2512.24601)
  - Relevance: This IS the foundational RLM paper — now has standalone intake entry
  - Key technique: Symbolic recursion via REPL environment offloading
  - Reported results: GPT-5 RLM 91.3% BrowseComp+; RLM-Qwen3-8B 32% CodeQA with 1K fine-tune samples
  - Delta from current approach: EPYC implements 80% of RLM; remaining gaps are async sub-calls and forced exploration validation

- **[intake-154] "Context-Folding"** (arxiv:2510.11967)
  - Relevance: 10x context reduction via procedural branching — more aggressive than session_compaction
  - Key technique: FoldGRPO (RL with process rewards for task decomposition)
  - Reported results: 10x active context reduction, matches ReAct on Deep Research/SWE
  - Delta: RL-driven fold decisions vs our rule-based compaction; process rewards could improve MemRL routing

- **[intake-155] "AgentFold"** (arxiv:2510.24699)
  - Relevance: Two-level condensation (granular + deep) for long-horizon web agents
  - Key technique: Retrospective consolidation — cognitive-inspired proactive context management
  - Reported results: 36.2% BrowseComp with 30B-A3B model, surpasses 671B models
  - Delta: SFT-only (no RL), two-tier compression vs our single-level compaction

- **[intake-157] "ReSum"** (arxiv:2509.13313)
  - Relevance: Periodic summarization for web search agents — closest match to session_compaction
  - Key technique: ReSum-GRPO with advantage broadcasting across summary boundaries
  - Reported results: +8.2% over ReAct with RL training; 33.3% BrowseComp-zh
  - Delta: Advantage broadcasting solves credit assignment across summary points — applicable to our session log
