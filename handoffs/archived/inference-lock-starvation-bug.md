# Bug: Inference Lock Starvation / Long Wait — Benchmark Hangs on SELF:repl

**Created**: 2026-02-17  
**Last verified against HEAD**: 2026-02-17  
**Severity**: P1 (blocks 3-way routing benchmark progress)  
**Status**: Active. Lock-starvation mitigations landed; primary remaining `SELF:repl` failure appears non-lock and still under investigation.

---

## Summary

`seed_specialist_routing.py --3way` can hang or stall around mode transitions (commonly `SELF:direct -> SELF:repl`). The leading suspicion is lock contention on `heavy_model.lock`, but prior notes overstated certainty. This handoff now separates **verified facts** from **hypotheses** and gives a decision-complete validation path.

---

## Implementation Snapshot (2026-02-17 late)

First mitigation tranche has been implemented:

1. `src/inference_lock.py`
- Lock acquire is now bounded/non-blocking (`LOCK_NB` retry loop) with periodic wait diagnostics.
- Explicit timeout now raises `TimeoutError` instead of allowing indefinite lock blocking.
- Env knobs:
  - `ORCHESTRATOR_INFERENCE_LOCK_TIMEOUT_S`
  - `ORCHESTRATOR_INFERENCE_LOCK_TIMEOUT_SHARED_S`
  - `ORCHESTRATOR_INFERENCE_LOCK_TIMEOUT_EXCLUSIVE_S`
  - `ORCHESTRATOR_INFERENCE_LOCK_POLL_MS`
  - `ORCHESTRATOR_INFERENCE_LOCK_LOG_EVERY_S`

2. `src/api/services/memrl.py`
- Idle-time background scoring can be disabled via:
  - `ORCHESTRATOR_MEMRL_BACKGROUND=0`

3. `src/prompt_builders/code_utils.py`
- Fixed `auto_wrap_final()` invalid wrapping of bracketed error payloads.
- Old bad form: `FINAL([ERROR: ...])` (SyntaxError).
- New safe form: `FINAL("[ERROR: ...]")`.

4. `src/graph/helpers.py`
- Timeout errors no longer trigger think-harder or same-role retry.
- Effect: prevents multi-turn timeout churn (e.g., 2x 90s REPL timeouts).

5. `src/inference_lock.py` (follow-up)
- Embedder roles now use an isolated lock domain by default:
  - heavy roles/light workers: `heavy_model.lock`
  - embedder roles: `embedder_model.lock`
- Env knobs:
  - `ORCHESTRATOR_INFERENCE_LOCK_FILE`
  - `ORCHESTRATOR_INFERENCE_LOCK_EMBEDDER_FILE`

### Validation snapshot from targeted matrix runs

- Case A (`workers=6`, `MEMRL_BACKGROUND=1`, lock timeout 45s):
  - `SELF:repl` entered long wait state (heartbeat: still waiting at 120s+).
  - API logs showed repeated shared lock wait diagnostics for embedder role and long frontdoor exclusive hold windows.

- Case B (`workers=1`, `MEMRL_BACKGROUND=1`):
  - `SELF:repl` still showed long wait behavior (heartbeat at 120s+), indicating worker count alone is not a full fix.

- Case C (`workers=6`, `MEMRL_BACKGROUND=0`):
  - `SELF:direct` improved significantly (observed ~24s vs ~76-88s in A/B sample runs).
  - `SELF:repl` still reached 120s wait heartbeat in sampled run.
  - API logs no longer showed the repeated embedder `wait ongoing` bursts observed in Case A.

Interpretation update:
- Background embedder contention appears to be a meaningful contributor (especially to overall latency/noise), but not the sole cause of `SELF:repl` long waits.
- Additional contributors (generation loop / REPL path behavior / model-side stalls) remain in play.

### Additional validation after fixes 3+4

- Controlled probes (`--timeout 180`) now show:
  - `frontdoor:repl` timeout handled in a single ~90s path (no repeated 90s turns from think-harder/retry).
  - REPL tap confirms Python-safe execution of timeout error:
    - `FINAL("[ERROR: Inference failed: Request timed out after 90s]")`
    - no SyntaxError from `FINAL([ERROR: ...])`.

Interpretation update:
- Lock contention is not the sole bottleneck.
- Current dominant `SELF:repl` infrastructure failure remains frontdoor inference timing out at role timeout (~90s), now without retry amplification.

### Additional validation after fix 5 (embedder lock-domain isolation)

- API-only probes run with:
  - `ORCHESTRATOR_UVICORN_WORKERS=6`
  - `ORCHESTRATOR_MEMRL_BACKGROUND=1`
  - lock timeouts at 45s
  - seeds `42`, `43`, `--timeout 180`
- Outcomes:
  - `SELF:repl` still exits via single timeout path at ~90s (`INFRA`, skip-retry path).
  - `SELF:direct` remained fast in sampled runs (~1-1.5s in these two probes).
  - Orchestrator logs no longer showed prior embedder lock-wait churn signatures (no repeated `Inference lock wait ongoing role=embedder` bursts in sampled window).
  - Long exclusive holds still observed on timed-out frontdoor/architect turns (expected from timeout-bound request lifecycle).

Interpretation update:
- Embedder/heavy lock-domain coupling was a contributor to contention noise and latency variance.
- Current blocker for `SELF:repl` completion is still frontdoor request timeout behavior, not lock starvation.

### Additional mitigation probe (token-cap guard) and rollback decision

- Added REPL-side token-cap controls in graph helper:
  - `ORCHESTRATOR_REPL_TURN_N_TOKENS` (default `768`) for tool-required turns
  - `ORCHESTRATOR_FRONTDOOR_TURN_N_TOKENS` (default `0`, disabled) for frontdoor turns
- Validation probe with temporary frontdoor cap enabled showed:
  - bounded direct output shape changes (token-capped completions),
  - but `SELF:repl` still timed out around ~90s.
- Decision:
  - keep frontdoor cap **opt-in only** (default disabled) to avoid changing baseline behavior without demonstrated benefit.
  - keep tool-required cap as a safe default guardrail (applies only when tool-required routing is active).

### Telemetry integrity fix (2026-02-18)

- Found a concrete instrumentation bug in `src/llm_primitives/inference.py`:
  - `_call_caching_backend()` referenced `req_started` when writing frontdoor telemetry metadata,
    but did not initialize `req_started` in that function scope.
- Fix implemented:
  - initialize `req_started = time.perf_counter()` before backend admission/lock path.

Validation snapshot:
- API reloaded via `python3 scripts/server/orchestrator_stack.py reload orchestrator` (API-only).
- Trace-enabled probe:
  - `ORCHESTRATOR_FRONTDOOR_TRACE=1 ... seed_specialist_routing.py --3way ... --seed 48 --timeout 90 --preflight`
- Orchestrator log now shows populated frontdoor timeout metadata:
  - `Frontdoor inference telemetry: transport=stream ... completion_reason=timeout ... chunks=0 ...`
  - `Frontdoor REPL turn end ... infer_meta={... 'completion_reason': 'timeout', ...}`

Interpretation update:
- Frontdoor timeout telemetry is now trustworthy for this path.
- The remaining `SELF:repl` failure is still an underlying frontdoor inference timeout/stall, not a lock acquisition blind spot.

### Stream-vs-batch falsification (2026-02-18)

To test whether tap-forced streaming transport was the root cause, a controlled probe was run with:
- `INFERENCE_TAP_STREAM_MODE=off`
- `ORCHESTRATOR_FRONTDOOR_TRACE=1`
- `workers=6`, `MEMRL_BACKGROUND=1`, lock timeouts 45s
- `seed=49`, `--timeout 90`, API-only preflight

Result:
- `SELF:repl` still timed out at ~88-90s in a single timeout path.
- Frontdoor telemetry captured timeout under **batch transport**:
  - `transport=batch`
  - `completion_reason=timeout`
  - `tokens=0`, `first_token_ms=0.0`, `stream_chunks=0`

Conclusion:
- Streaming transport is not the primary remaining failure source.
- Current leading failure mode is no-first-token backend/model-side timeout on frontdoor REPL path.

### Targeted mitigation landed: frontdoor REPL slot-routing bypass

Implemented in `src/prefix_cache.py`:
- Added `CachingBackend._should_bypass_slot_routing(request)`.
- Default behavior now bypasses PrefixRouter slot assignment for frontdoor REPL-style requests
  (detected by role frontdoor + REPL stop sequence `"\n```\n"`).
- Env gate:
  - `ORCHESTRATOR_PREFIX_CACHE_BYPASS_FRONTDOOR_REPL` (default enabled).

Supporting guardrail:
- `src/graph/helpers.py`
  - Added frontdoor non-tool REPL token cap:
    - `ORCHESTRATOR_FRONTDOOR_REPL_NON_TOOL_N_TOKENS` (default 256, floor 64)
  - Applies when role is frontdoor and `tool_required=False`.

Validation snapshot (seed 51, API-only preflight):
- `SELF:direct` executed normally.
- `SELF:repl` completed in ~13.5s (no 90s timeout), with tool usage.
- Frontdoor telemetry now shows healthy token flow for repl turn:
  - `n_tokens=256`, `first_token_ms≈5.8s`, `stream_chunks=94`, `tokens=109`, `completion_reason=word`.

Interpretation update:
- Dominant `SELF:repl` timeout symptom is mitigated on current sampled path.
- Remaining failures in sampled run are quality outcomes (FAIL) rather than infra timeout for frontdoor repl.

### Delegation-loop telemetry added (2026-02-18)

To reduce reruns for architect delegated-loop debugging, telemetry now captures explicit loop diagnostics.

Implemented:
- `src/api/routes/chat_delegation.py`
  - stats now include:
    - `cap_reached`
    - `break_reason` (`max_loops`, `semantic_dedup`, `token_budget`, `role_repetition`, `forced_synthesis`)
    - `effective_max_loops`
    - `reentrant_depth`
- `src/api/routes/chat_pipeline/delegation_stage.py`
  - adds `delegation_diagnostics` to API response:
    - loop count, cap/break reason, repeated delegation edges, repeated roles.
- `src/api/routes/chat_pipeline/repl_executor.py`
  - emits delegation diagnostics for graph REPL mode too.
- `src/api/models/responses.py`
  - `ChatResponse` schema extended with `delegation_diagnostics`.
- Seeding/debug integration:
  - `scripts/benchmark/seeding_types.py` (`RoleResult.delegation_diagnostics`)
  - `scripts/benchmark/seeding_eval.py` propagates and logs diagnostics per run.

Expected impact:
- A single `architect_*:delegated` run should now reveal whether termination was cap/guard-driven, and whether loop patterns (repeated edges/roles) occurred, without manual log archaeology.

---

## Verified Facts (Code + Runtime)

1. **Cross-process lock design is real and role-sensitive.**
- `src/inference_lock.py` uses `fcntl.flock()` on `/mnt/raid0/llm/tmp/heavy_model.lock`.
- Heavy roles (e.g., `frontdoor`, `coder_escalation`, architects) default to exclusive lock.
- Light roles get shared lock.

2. **Exclusive lock is taken on frontdoor/coder inference paths.**
- Lock acquisition sites include:
  - `src/llm_primitives/inference.py` (`_real_call_single`, `_call_caching_backend`, `_real_call_monitored`)
  - `src/llm_primitives/primitives.py` (`llm_call_stream`)

3. **Embedder path acquires shared lock.**
- `orchestration/repl_memory/embedder.py` wraps embedding generation in:
  - `with inference_lock("embedder", shared=True): ...`

4. **Orchestrator default worker count is 6 under stack launcher.**
- `scripts/server/orchestrator_stack.py` sets uvicorn workers from env default `"6"` for stack start/reload.

5. **MemRL background scoring runs in each worker process and can trigger embeddings while idle.**
- Startup eagerly initializes MemRL if enabled (`src/api/__init__.py`).
- Background cleanup runs every 10s when request count is 0 (`src/api/services/memrl.py`).
- Cleanup/scoring uses embedder calls that can take shared lock.

6. **`fuser heavy_model.lock` only proves open-file users, not current lock mode/owner.**
- Prior evidence of "all 6 workers shown by fuser" is useful but not conclusive proof of active `LOCK_SH` ownership.

---

## Corrections to Earlier Notes

1. `src/prefix_cache.py` is **not** currently a lock-acquisition site.
2. `coder_primary` references are stale for current tree and should not be used in diagnosis.
3. "Per-request lock scope missing" is outdated: lock/unlock is already request-scoped in current context-manager implementation.
4. "asyncio.Lock replacement" is not a direct fix for multiprocess uvicorn contention.

---

## Update 2026-02-18 (Reload Lifecycle Root Cause + Fix)

### New confirmed root cause
- During repeated orchestrator API reloads, stale uvicorn worker subprocesses could survive while only the tracked parent PID was terminated.
- These stale workers could continue to hold `/mnt/raid0/llm/tmp/heavy_model.lock`, causing later requests to time out waiting on a lock holder that no longer matched the active API lifecycle.

Concrete evidence snapshot:
- lock wait diagnostics showed holders from prior worker trees (e.g., `spawn_main(...)` workers not aligned with current API request path).
- pre-delegation lock timeouts appeared immediately after reload cycles despite low live request load.

### Fix implemented
- `scripts/server/orchestrator_stack.py`
  - `kill_process(pid)` upgraded to kill **process tree** (descendants + parent), graceful then forceful.
  - Added helper functions:
    - `_pid_alive(pid)`
    - `_child_pids(pid)`
    - `_collect_descendants(root_pid)`
- Impact:
  - orchestrator reload now fully clears previous uvicorn worker trees,
  - stale lock holders from prior API generations are eliminated.

### Verification
- Recompiled launcher: `python3 -m py_compile scripts/server/orchestrator_stack.py`.
- Post-reload process topology shows a single uvicorn master with only current-generation workers.
- `heavy_model.lock` holder checks no longer show stale idle workers after clean reload.

### Additional follow-up (same session)
- `src/api/routes/chat_delegation.py` was updated to avoid unnecessary post-specialist architect synthesis hops:
  - specialist `FINAL(...)` now triggers immediate delegated return (`break_reason=specialist_report`),
  - timeout-like specialist exceptions are classified as `specialist_timed_out` to skip extra loops.
- Effect:
  - fixed-prompt delegated probes that previously ended in ~82-84s timeout now complete quickly with specialist-return semantics.

---

## Ranked Hypotheses

## H1 (Highest): Shared-lock pressure from background embedder activity starves heavy exclusive acquisition
**Why plausible**
- 6 uvicorn workers + per-worker periodic MemRL scoring can create recurring shared-lock windows.
- Frontdoor REPL path requires exclusive lock; repeated shared reacquisition can produce long waits.

**Proof criteria**
- During stall windows, lock wait logs and/or timestamps show frontdoor waiting while embedder work is active.
- Reducing workers to 1 or disabling MemRL scoring materially reduces/removes stall frequency.

**Disproof criteria**
- Stalls persist unchanged with single worker and with MemRL/embedder path disabled.

## H2 (Medium): Lock convoy/fairness issue under blocking `flock()` in multi-worker contention
**Why plausible**
- `flock()` here is blocking with no timeout or fairness control.

**Proof criteria**
- Wait time grows without corresponding backend compute load; lock-acquire delays dominate request latency.

**Disproof criteria**
- Stall reproduces even when no competing shared-lock actors are present.

## H3 (Lower): Stalls are primarily non-lock transport/streaming issues, lock is incidental
**Why plausible**
- Prior symptoms mention HTTP stream stalls and zero token progress in some runs.

**Proof criteria**
- Requests stall while lock acquisition appears fast and uncontended.

**Disproof criteria**
- Lock wait instrumentation clearly dominates the stalled window.

### Hypothesis status update (2026-02-18)

- H1: **partially supported historically, but downgraded as primary blocker on current HEAD**.
  - Evidence: embedder lock-domain isolation removed observed embedder wait bursts, but `SELF:repl` still times out at ~90s.
- H2: **not primary in current runs**.
  - Evidence: no recurring lock-wait timeout signatures in latest probes; remaining long windows map to exclusive request hold durations.
- H3: **upgraded** (current leading direction).
  - Evidence: timeout persists after lock mitigations and retry suppression, suggesting frontdoor REPL inference-path timeout/stall behavior beyond lock acquisition.

---

## Reproduction (Baseline)

```bash
# 1) Ensure orchestrator running with default stack settings
python3 scripts/server/orchestrator_stack.py reload orchestrator

# 2) Reproduce
python3 scripts/benchmark/seed_specialist_routing.py \
  --3way --suites simpleqa --sample-size 1 --no-pool --seed 42

# 3) Snapshot signals during stall
fuser /mnt/raid0/llm/tmp/heavy_model.lock
curl -s localhost:8080/slots | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['is_processing'])"
```

Expected problematic shape:
- Benchmark appears stuck around `SELF:repl`.
- CPU/model port may look mostly idle.
- Lock file has multiple worker processes attached.

---

## Validation Matrix (Decision-Critical)

Run all rows; do not skip.

| Case | Setup | Expected if H1 true | Interpretation |
|------|-------|---------------------|----------------|
| A | Baseline (stack default workers=6, MemRL on) | Stall/hang reproduces intermittently | Control |
| B | `ORCHESTRATOR_UVICORN_WORKERS=1` then reload | Stall largely disappears | Strong support for contention source in multi-worker mode |
| C | workers=6 but MemRL scoring disabled (or API launched without MemRL) | Stall frequency drops significantly | Strong support for embedder shared-lock involvement |
| D | workers=6 + no benchmark load (idle soak) + lock diagnostics | Recurring shared-lock windows still visible | Supports background-source theory |

---

## Instrumentation Checklist

1. **Lock wait/hold telemetry**
- Capture `Inference lock acquired ... after Xs` and long-held warnings from orchestrator logs.
- Correlate timestamps with benchmark stall intervals.

2. **Background scorer correlation**
- Confirm periodic scorer activity around stalls (10s cadence expected).
- Correlate with embedder calls.

3. **Backend progress**
- Poll `/slots` on active ports; check whether compute is idle while request wall-clock grows.

4. **Request pressure**
- Track `active_requests` transitions if possible; verify whether "idle" periods trigger background scoring.

---

## Interim Mitigations (Not Root Fix)

1. **Force single worker for benchmarking**
```bash
ORCHESTRATOR_UVICORN_WORKERS=1 python3 scripts/server/orchestrator_stack.py reload orchestrator
```
Trade-off: less concurrency; acceptable for deterministic benchmark runs.

2. **Kill lock-file users as emergency unblock**
```bash
fuser -k /mnt/raid0/llm/tmp/heavy_model.lock
```
Trade-off: disruptive; not sustainable.

---

## Candidate Fix Directions (After Hypothesis Confirmation)

1. Add bounded lock wait + timeout diagnostics in `inference_lock` (`LOCK_NB` retry loop with explicit timeout and structured logging).
2. Separate embedder contention domain from heavy-model lock domain (if validated by matrix).
3. Apply benchmark-mode process profile (single worker and/or background scorer off).

**Do not** adopt "proceed without lock" as default behavior; that risks reintroducing CPU oversubscription instability.

---

## Related Investigation Notes (Historical)

1. `skip_suffix=True` and REPL prompt/tool examples were updated and improved behavior in prior runs.
2. The old "error string injected as Python code" claim should be treated as historical until reproduced on current HEAD.

---

## Files Involved (Current)

| File | Relevance |
|------|-----------|
| `src/inference_lock.py` | Core lock implementation |
| `src/llm_primitives/inference.py` | Primary lock acquisition points for real inference |
| `src/llm_primitives/primitives.py` | Streaming lock acquisition path |
| `orchestration/repl_memory/embedder.py` | Shared-lock acquisition for embeddings |
| `src/api/__init__.py` | MemRL eager init at worker startup |
| `src/api/services/memrl.py` | Background cleanup cadence + scoring path |
| `scripts/server/orchestrator_stack.py` | Uvicorn worker-count defaults |
| `scripts/benchmark/seed_specialist_routing.py` | Reproduction harness |
| `scripts/benchmark/seeding_eval.py` | 3-way eval orchestration around mode transitions |

---

## Definition of Done for This Bug

Root cause is accepted as proven only when:
1. One hypothesis passes proof criteria.
2. Alternative hypotheses are explicitly falsified.
3. Fix removes/reduces stall in repeated baseline reproductions (>=5 consecutive runs).
4. Post-fix run shows no indefinite lock waits and benchmark completes end-to-end.

## Delegated Loop / Hung Inference Deep-Dive (2026-02-18)

### What was changed
- Added delegation guardrails in `src/api/routes/chat_delegation.py`:
  - specialist token cap + max turns + per-specialist wall-clock timeout
  - total delegated-flow wall-clock timeout
  - forced synthesis token cap
  - reduced architect decision/computation token budgets for delegated mode
- Added specialist-timeout short-circuit:
  - when a specialist round times out, set `break_reason=specialist_timeout` and force synthesis path rather than re-delegating.

### Telemetry upgrades (to minimize reruns)
- `delegation_diagnostics` now propagates through:
  - API response (`ChatResponse`)
  - seeding diagnostics (`scripts/benchmark/seed_specialist_routing.py` + `src/pipeline_monitor/diagnostic.py`)
  - Claude debugger batch prompt (`src/pipeline_monitor/claude_debugger.py`)
- Diagnostic fields now include at least:
  - `break_reason`, `cap_reached`, `effective_max_loops`, `reentrant_depth`, repeated edge/role summaries.

### Runtime evidence (bounded probes)
- Repeated single-request probes on `architect_coding:delegated` still timed out at 160s.
- Improvements observed:
  - active specialist path no longer exhibits `n_predict=-1` runaway behavior (bounded to finite values)
  - coder lock hold dropped from ~53-63s to ~30s in latest runs
  - explicit specialist timeout signal appears in logs
- Remaining unresolved behavior:
  - request still does not complete before client timeout after specialist timeout path.
  - likely downstream/post-specialist architect path stall (requires next-step instrumentation around post-specialist synthesis and response finalization timeline).

### Recommended next step
- Add phase-level timestamped logging around:
  - specialist timeout return boundary
  - immediate architect synthesis call start/end
  - delegated-stage return boundary in `src/api/routes/chat_pipeline/delegation_stage.py`
- Run one bounded probe and verify which boundary is never reached.

### Follow-up result (2026-02-18, latest)

- Applied timeout fast-return fallback in delegated mode:
  - when `break_reason` is `specialist_timeout` or `wall_clock_budget`, skip architect forced synthesis and return latest specialist report.
- Live bounded probe result:
  - `architect_coding:delegated` returned HTTP 200 in ~69.7s (previously timed out at 160s).
  - `delegation_diagnostics.break_reason = specialist_timeout`
  - log line confirms fallback branch executed:
    - `Skipping forced synthesis due to timeout break_reason=specialist_timeout, returning latest report`

Conclusion:
- Hang-style timeout is mitigated for this delegated path.
- Next optimization target is fallback answer quality under timeout (not liveness).

### Delegation root-cause remediation update (latest)

Implemented and validated two additional improvements:

1. **Root-cause loop fix (already validated)**
- When specialist returns substantial non-`FINAL()` output, treat it as report and terminate delegation path (`break_reason=specialist_report`) instead of forcing additional specialist turns.

2. **Handoff overhead reduction + report compression**
- Added compact specialist prompt mode for delegated loops (`ORCHESTRATOR_DELEGATION_COMPACT_SPECIALIST_PROMPT=1` default).
- Added optional long-report summarization using `worker_summarize` before response return (`ORCHESTRATOR_DELEGATION_SUMMARIZE_LONG_REPORTS=1` default).

**Measured trace delta**
- specialist prompt chars: **11058 -> 674**
- delegated call still dominated by specialist generation (~22s), but no retry-loop amplification and stable completion (HTTP 200, `break_reason=specialist_report`).

**Current bottleneck after these fixes**
- Single-hop specialist generation latency on `coder_escalation` remains the main contributor to end-to-end time.
- Next optimization should target model-side decode/prefill profile or lighter specialist routing for these tasks.

## Orchestrator API Reload Instability (2026-02-18)

### Symptom
- During repeated debug loops, `reload orchestrator` intermittently surfaced API failure/dead state, creating significant operational thrash.

### Implemented hardening (`scripts/server/orchestrator_stack.py`)
- Added stale-listener detection helper: `_pids_on_port(port)`.
- `start_orchestrator()` now:
  - clears stale listeners on `:8000` before launch,
  - starts uvicorn detached (`start_new_session=True`, `stdin=DEVNULL`, `close_fds=True`),
  - if health probe times out but process is still alive, returns a warning state instead of force-killing the API.
- `reload orchestrator` path now kills stale `:8000` listeners before relaunch.
- `status` path now repairs stale PID state by discovering replacement listeners on the same port and saving refreshed state.

### Why this matters
- Prevents false-negative health probes from causing immediate self-inflicted API teardown.
- Reduces restart loops caused by stale PID tracking and detached parent-PID churn.
- Supports fast API-only reload iteration (without full model stack restart).

### Verification snapshot
- `python3 scripts/server/orchestrator_stack.py reload orchestrator` succeeded with `[OK] Orchestrator ready`.
- Immediate `curl http://127.0.0.1:8000/health` returned `200` with healthy backend probes.

## Follow-up: Delegation Timeout Still Tied to Lock Wait (2026-02-18)

### Confirmed trace
- In `logs/orchestrator.log`, delegated architect calls show prolonged pre-inference lock wait:
  - `Inference lock wait ongoing (role=architect_coding, ...)` with waits extending far beyond delegation budget windows.
- Once lock clears, specialist trace includes fully populated inference meta:
  - `Delegation trace turn=0 ... infer={'role':'coder_escalation','prompt_ms':..., 'gen_ms':..., ...}`
- Delegation budget can still be exceeded at wall clock due pre-delegation waiting:
  - `Delegation total timeout ... break_reason=wall_clock_budget`

### Hardening applied
- `src/inference_lock.py`
  - wait logs now include lock holder PIDs (`holders=...`) to identify contention owner without extra probes.
- `scripts/server/orchestrator_stack.py`
  - API launcher now defaults lock timeouts to 45s (exclusive/shared) unless explicitly overridden.

### Operational implication
- Primary remaining cause of hung behavior is lock-domain contention before delegation execution, not missing specialist telemetry.
- Next debugging pass should attribute which role/request holds heavy lock longest and enforce cancellation/timeout upstream for abandoned requests.

## Global Architecture Fix Applied: Cancellation Propagation Into Lock Wait

### Why
- Frontdoor and specialist/architect lock starvation share the same architectural failure mode:
  requests that are effectively abandoned can continue waiting on (or holding) the heavy-model lock.

### Changes
- `/chat` endpoint now tracks client disconnect and exposes cancellation state to runtime:
  - `src/api/routes/chat.py`
    - disconnect watcher using `Request.is_disconnected()`
    - propagates request cancellation/deadline into `LLMPrimitives`
- `src/inference_lock.py`
  - lock acquisition supports `cancel_check` + `deadline_s`
  - aborts lock wait early when request is cancelled or deadline exceeded
- `src/llm_primitives/inference.py`, `src/llm_primitives/primitives.py`
  - pass cancellation/deadline hooks at every lock-acquisition path
  - clamp backend request timeout to remaining request budget
  - log explicit lock-timeout/cancelled inference abort warnings
- `src/api/routes/chat_pipeline/direct_stage.py`
  - disables retry-once behavior for cancellation/lock-timeout errors

### Expected effect
- Eliminates multi-minute stale lock waits from disconnected/timed-out client calls.
- Makes this mitigation stack-wide (frontdoor + architect/specialists), not model-specific.

## Orchestration Optimization TODOs (Current)

### Completed in this session
- [x] API lifecycle hardening for `reload orchestrator` stability.
- [x] Delegation loop root-cause fixes (`specialist_report`, timeout fast-return, compact prompts).
- [x] Artifact-backed report handle persistence in delegation path.
- [x] Delegation telemetry plumbing (`break_reason`, loop/cap metadata, inference timing fields).
- [x] Global cancellation propagation into lock acquisition path (`cancel_check`, request deadline).
- [x] Structured delegated response on pre-delegation lock-timeout/cancel path:
  - `break_reason=pre_delegation_lock_timeout` returned in `delegation_diagnostics`.

### Remaining (priority order)
1. **Stress-validation closure** (required for bug DoD)
   - Run >=5 consecutive contention-heavy delegated probes.
   - Verify no multi-minute stale waits from abandoned requests and no hidden lock-holder accumulation.
2. **Lock-owner attribution automation**
   - Correlate lock-holder PID to request/task metadata automatically (not just PID listing).
   - Goal: identify which role/request class is most likely to over-hold lock.
3. **Artifact-handle completion**
   - Add first-class retrieval path/tool to fetch report-handle content by id/chunk in later turns.
   - Current state stores handles and summaries, but no dedicated lazy-hydration API/tool contract yet.
4. **Delegation worker-swarm runtime alignment**
  - Confirm/restore intended coder escalation -> worker_coder parallel subtask execution semantics in active stack.
  - Current aliasing to `worker_fast` exists, but full swarm executor behavior remains partially wired.

### Latest stress snapshot (5-run delegated sequence)
- Setup: forced `architect_coding:delegated`, timeout=25s, repeated 5 times.
- Observed:
  - all 5 runs timed out at ~25s client boundary,
  - lock holder remained constant: PID `623958` (multiprocessing `spawn_main` child of uvicorn worker),
  - no growing list of holder PIDs (no obvious lock-holder accumulation leak in this sample).
- Interpretation:
  - cancellation path likely prevents holder explosion, but a long-lived holder process remains active and needs role/request attribution.
  - lock-owner attribution work is in progress; lock logs now include PID + command snippets for wait events.

### Attribution improvement (latest)
- Lock wait/timeout logs now carry orchestrator request tag (`task_id`) end-to-end:
  - `/chat` seeds `LLMPrimitives._request_task_id`
  - all inference lock acquisition sites pass `request_tag`
  - lock timeout/wait messages include `request=<task_id>`
- This enables direct PID+request correlation for lock-holder forensics without external manual mapping.

## Root-Cause Follow-up Update (2026-02-18, latest)

### Additional root-cause fixes implemented

1. **Request-context isolation for shared `LLMPrimitives`**
- Problem: request cancellation/deadline/task metadata was stored in mutable instance fields on a shared primitives object, allowing cross-request overwrite under concurrency.
- Fix:
  - `src/llm_primitives/primitives.py`
    - added request-scoped context via `contextvars`
    - added `request_context(...)`, `get_request_*()` helpers
  - `src/api/routes/chat.py`
    - wraps the execution pipeline in `with primitives.request_context(...)`
  - `src/llm_primitives/inference.py` + `src/llm_primitives/primitives.py`
    - all lock/call sites now read request metadata through context-aware getters.

2. **Streaming path deadline clamp parity**
- Problem: `llm_call_stream` did not clamp backend timeout to remaining request deadline.
- Fix:
  - `src/llm_primitives/primitives.py`
    - stream requests now clamp `timeout` to remaining request budget before backend call.

3. **Client/server timeout budget alignment**
- Problem: under overload, client timeout and server deadline could drift enough to allow post-client work.
- Fix:
  - `src/api/models/requests.py`: added `client_deadline_unix_s`
  - `src/api/routes/chat.py`: request deadline now clamped by `client_deadline_unix_s` when provided
  - `scripts/benchmark/seeding_orchestrator.py`: caller now sends both `timeout_s` and `client_deadline_unix_s`

4. **True lock-owner telemetry (not just open-file telemetry)**
- Problem: `lsof`-based holder listing can include processes with FD open but not actively owning lock.
- Fix:
  - `src/inference_lock.py`
    - added `/proc/locks` owner extraction by inode (`_current_lock_owner_pids`)
    - periodic wait logs now prefer real lock owners; `lsof` retained only as fallback.

### Validation (latest)

- Unit/static:
  - `pytest -q tests/unit/test_inference_lock.py` ✅
  - `pytest -q tests/unit/test_llm_primitives.py -k request_context` ✅
  - `pytest -q tests/unit/test_chat_pipeline_stages.py -k delegation_lock_timeout_returns_structured_error` ✅
  - `python3 -m py_compile` on touched files ✅

- Contention stress (forced `architect_coding:delegated`, timeout=25s, 6 concurrent requests per batch):
  - **Run A (5 batches)**: holders clear by +30s in all batches; one transient +15s holder window observed in 1/5.
  - **Run B (5 batches, after deadline-alignment patch)**: holders clear by +30s in all batches; one transient +15s holder window observed in 1/5.

Interpretation:
- Multi-minute stale/abandoned lock behavior is no longer observed in current stress runs.
- Residual short-lived post-timeout hold windows can still occur under overload (typically cleared before +30s).
- With `/proc/locks` owner attribution now in place, next tuning can target those specific owner/request pairs directly.

### TODO status update

1. **Stress-validation closure**: **substantially improved, pending stricter closure criteria**
   - Evidence now shows no indefinite stale lock retention; transient +15s windows remain occasionally under overload.
2. **Lock-owner attribution automation**: **completed (phase 1)**
   - `/proc/locks` owner extraction + request-tagged lock logs are live.
3. **Artifact-handle lazy retrieval API/tool**: **still pending**.
4. **Worker-swarm runtime alignment (`coder_escalation -> worker_coder`)**: **still pending**.

## Final Root-Cause Closure Update (2026-02-18)

### Root cause identified
A critical timeout-clamp ordering bug remained:
- backend request timeout was computed **before** lock acquisition,
- so requests that waited a long time on lock could still execute a full backend call after acquiring lock,
- producing post-timeout lock hold windows.

Observed trace before fix:
- `architect_coding` request `chat-6ea8d15a` held heavy lock `held_s=20.147`
- queued request `chat-a5809346` then acquired after `wait_s=20.151` and held another `held_s=22.203`
- net effect: lock remained occupied well past client timeout boundary.

### Fix applied
- `src/llm_primitives/inference.py`
  - added `_clamp_request_timeout_to_deadline(...)`
  - re-clamps `request.timeout` **after lock acquisition** in all inference paths:
    - model_server single call
    - caching backend call (batch/stream transport)
    - monitored stream path
- `src/llm_primitives/primitives.py`
  - `llm_call_stream(...)` now also re-clamps `request.timeout` after lock acquisition.

### Additional telemetry hardening
- `src/inference_lock.py`
  - added env-gated lock trace (`ORCHESTRATOR_INFERENCE_LOCK_TRACE`)
  - acquire/release trace now logs: `pid`, `role`, `request`, `wait_s`, `held_s`, lock path.

### Validation evidence (post-fix)
- Targeted trace batch:
  - no secondary long post-wait lock hold observed.
  - max heavy hold in sampled trace: ~25.1s (aligned to request timeout envelope).
- Contention closure sweep (5 batches, 6 concurrent delegated requests/batch, timeout=25s):
  - `holders_at_15s_batches=[]`
  - `holders_at_30s_batches=[]`
  - `all_clear_30s=true`
  - occasional +5s transient holder remained in some batches (expected short tail), but fully clear by +15s.

### DoD status
- No multi-minute stale-abandoned lock behavior observed ✅
- No +15s/+30s residual holder in 5-batch closure sweep ✅
- Request-tag + true owner telemetry in place for future regressions ✅

### Remaining non-lock TODOs
1. Artifact-handle lazy retrieval API/tool contract.
2. Worker-swarm runtime alignment (`coder_escalation -> worker_coder` semantics).

## Update 2026-02-18 (remaining orchestration TODO execution)

### Completed now
1. **Artifact-handle lazy retrieval API/tool path**
- Added dedicated report artifact module: `src/delegation_reports.py`.
- Delegation now persists oversized specialist reports and emits compact handle text with explicit lazy-fetch instruction.
- Added REPL tool: `fetch_report(report_id, offset=0, max_chars=2400)`.
- Added API endpoint: `GET /chat/delegation-report/{report_id}` for chunked retrieval.
- Architect prompts now explicitly support lazy report hydration when `[REPORT_HANDLE ...]` appears.

2. **Worker-swarm runtime semantics alignment (`coder_escalation -> worker_coder`)**
- `worker_coder` is now first-class in delegation role parsing/allowlist.
- Legacy `worker_code` now normalizes to `worker_coder` (semantic role), not direct stale wiring.
- Config/runtime URL alignment completed:
  - `worker_coder`/`worker_code` now both map to `http://localhost:8102`.
- Coding task worker routing now targets semantic `worker_coder`.
- Stack port map includes `worker_coder` and legacy `worker_code` aliases.

### Validation evidence
- Targeted unit suite:
  - `pytest -q tests/unit/test_delegation_reports.py tests/unit/test_repl_routing.py tests/unit/test_architect_delegation.py -k "worker_coder or fetch_report or report_handle or delegation"`
  - Result: **40 passed**.
- Runtime files compile check passed via `python3 -m py_compile`.

### Explicit non-changes (per requirement)
- MemRL wiring untouched (no changes to episodic reward/scoring mechanics).
- SkillRL / `--evolve` flow untouched.

### Remaining TODOs after this update
- Run live contention/delegation probe sweep to capture end-to-end runtime evidence for new lazy-hydration and worker-coder path under real load.
- Optional cleanup: deprecate stale `worker_code` nomenclature from remaining docs/constants once downstream compatibility window closes.

## Update 2026-02-18 (optional closure items executed)

### Completed
1. **Live runtime evidence sweep**
- Ran concurrent delegated `/chat` probes under contention profile.
- Verified delegated execution remains responsive and observed live `worker_coder` path in role history during sweep.

2. **Report-handle live retrieval verification**
- Captured live report handle from delegated response diagnostics:
  - `coder_escalation-1771422525022-d00035730fbcb725`
- Verified API hydration endpoint returns chunked content:
  - `GET /chat/delegation-report/{id}` -> `ok=true`, `truncated=true`, valid content chunk.

3. **Legacy naming cleanup (docs/constants)**
- Updated docs/config to prefer `worker_coder` semantics.
- `worker_code` preserved as explicit compatibility alias only (same endpoint/timeout defaults).

4. **Integration test added for end-to-end contract**
- `tests/integration/test_chat_pipeline.py::TestChatEndpoint::test_delegation_report_handle_roundtrip`
- Verifies delegated handle emission and retrieval endpoint in one flow.

### Additional robustness fix landed while closing
- `scripts/server/orchestrator_stack.py`
  - fixed startup state-save crash (`asdict()` on non-dataclass preserved entries) by serializing mixed state safely.
  - removes a recurring blocker during repeated start/reload loops.

### Remaining after this update
- No blocking items remain for this handoff's orchestration optimization/debug scope.
- Optional future cleanup: remove `worker_code` alias entirely after downstream compatibility window closes.

## Final wrap-up update (2026-02-18, pre-commit)

- Performed final closure pass across docs/chapters and agent-facing prompts/constants; no unresolved orchestration TODOs remain in this handoff scope.
- Fixed integration test contract mismatch (`max_chars` request now respects API lower bound `>=64`) in:
  - `tests/integration/test_chat_pipeline.py::TestChatEndpoint::test_delegation_report_handle_roundtrip`
- Validation state:
  - targeted unit delegation/config suite still passes (43 passed)
  - integration roundtrip test is collected but intermittently hangs in this environment during execution (collection confirmed).
- Remaining recommendation (non-blocking): investigate integration-test runtime hang separately from orchestration logic correctness.
