# Handoff: Infra Seeding Regression + CPU-Exclusive Inference Plan

## Context
Recent MemRL seeding runs show a massive infra regression: sequential 600s timeouts across all roles (SELF:direct, SELF:repl, ARCHITECT), with 0 tokens. Pattern indicates the API event loop is blocked by sync LLM calls in async handlers. Additional weak spots include missing slot cleanup in 3-way mode, health checks that do not detect backend hangs, and lack of a global serialization lock for heavy models in a CPU-only environment. This handoff documents a comprehensive stabilization plan.

## Evidence (stored data)
From `benchmarks/results/eval/3way_20260206_093823.jsonl`:
- First all-infra timeout: `2026-02-06T09:39:20Z` (arc_MCAS_2004_9_5)
- After that: 40-minute questions (4 roles x 600s) until partial recovery at ~11:13Z
- `architect_coding` times out persistently even when others succeed
- Second collapse starts ~12:24Z, persists through 17:04Z

## Confirmed Root Cause
**Event loop blocking** due to synchronous LLM calls inside async request handlers:
- `_execute_direct`, `_execute_delegated`, `_execute_react`, `_execute_repl`, `_execute_proactive` call `primitives.llm_call()` (sync HTTP)
- When a heavy request stalls (e.g., architect_coding), the loop blocks for 600s
- Requests queue at TCP level; clients time out before processing

## Additional Weak Spots
- **No heavy-model serialization**: heavy roles can run concurrently, which is invalid for CPU-only, full-thread inference.
- **Workers/embedders** can run concurrently with heavy models, competing for CPU.
- **Generation monitor** uses `model_server` and can be incompatible with caching backends.
- **3-way mode** does not call `_erase_slots()` after timeouts.
- **/health** only reports circuit states; does not probe backends for liveness.
- **ROLE_TIMEOUTS** exist but are not enforced inside backend calls (global 600s used).

## Plan (Decision Complete)
### Phase 1 — Cross-Process CPU Lock (Core Enforcement)
- Create a global file lock under `/mnt/raid0/llm/claude/tmp/heavy_model.lock`.
- **Exclusive lock** for heavy models; **shared lock** for workers/embedders.
- Heavy roles: `frontdoor`, `coder_escalation`, `architect_general`, `architect_coding`, `ingest_long_context`, `vision_escalation` (and any large-model roles on 8080–8085/8087).
- Light roles: `worker_explore`, `worker_math`, `worker_fast`, `worker_vision`, embedder ports `8090–8095`.
- Workers/embedders may only run when no heavy model lock is held.
- Add lock contention and hold-time logging.

### Phase 2 — Async Safety Everywhere
- Wrap all blocking inference in `asyncio.to_thread()`:
  - `_execute_direct`, `_execute_repl`, `_execute_react`, `_execute_delegated`, `_execute_proactive`
- Delegated REPL execution must run off-loop.

### Phase 3 — Generation Monitor Compatibility
- If `generation_monitor` is enabled but caching backends are used (no `model_server`), bypass monitored path and log once.

### Phase 4 — Seeding Infra Recovery
- Add `_erase_slots()` in **3-way** mode after timeout/errors with 0 tokens.
- Treat **all roles timed out** as infra failure and trigger `_attempt_recovery()`.

### Phase 5 — Health Check Accuracy
- `/health` should probe core ports (8080, 8081, 8083, 8084).
- Mark degraded if any core backend fails liveness check.

### Phase 6 — Timeout Consistency
- Apply `ROLE_TIMEOUTS` inside LLM backend calls (not just routing metadata).
- Frontdoor should not inherit 600s unless explicitly set.

### Phase 7 — Uvicorn Workers (Safe with Lock)
- Use 2–4 uvicorn workers for API responsiveness.
- Cross-process lock ensures only one heavy inference runs across workers.

## Tests / Validation
- Quick `/chat` direct request should respond <60s.
- Two parallel `/chat` requests: second should wait, not time out.
- 3-way dry-run (3 questions): no full infra collapse; slot erasure logs on timeout.
- Add unit test for async concurrency + heavy lock behavior.

## Required Final Step (post-implementation)
Update the following:
- Agent logs (append-only)
- Progress report for the day (`progress/YYYY-MM/YYYY-MM-DD.md`)
- Relevant documentation chapters (e.g., `docs/chapters/17-memory-seeding.md`, `docs/chapters/25-cost-aware-rewards.md`, or a dedicated infra/stability section)

## Notes
- `coder_primary` is an alias of frontdoor; treat as frontdoor in role lists.
- This is a CPU inference project; heavy model concurrency is forbidden by design.
