# Orchestrator Refactoring Audit

**Status**: ACTIVE — execution in progress
**Created**: 2026-04-13
**Updated**: 2026-04-13
**Priority**: CRITICAL
**Primary repo audited**: `/mnt/raid0/llm/epyc-orchestrator`
**Deliverable type**: executable refactoring handoff

## Scope And Method

This document replaces the earlier lightweight audit with a code-grounded refactoring dossier. The findings below were validated against the live orchestrator repo at `/mnt/raid0/llm/epyc-orchestrator`, not just prior handoffs.

Validated scope:
- `src/`: `80,033` Python LOC
- `scripts/`: `46,532` Python LOC
- `benchmarks/`: no Python source files
- Python files across `src/` + `scripts/` + `benchmarks/`: `350`

Validated structural counts:
- Broad catches in `src/`: `436` across `132` files
- Broad catches in `src/` + `scripts/` + `benchmarks/`: `692` across `194` files
- Top-level loose files in `src/`: `49`
- Feature flags in `src/features.py`: `72`

Important correction versus the prior draft:
- The earlier handoff claimed `437` broad catches in `133` source files. The live tree currently contains `436` across `132` files in `src/`.

## Executive Summary

The orchestrator does not primarily suffer from one broken subsystem. It suffers from an architectural pattern: **best-effort execution with weak truthfulness about failure**.

That pattern shows up in four places:
- exception handling that converts defects into silent fallback behavior
- telemetry and status surfaces that omit failure cause and degradation state
- benchmark and reward pipelines that optimize for forward progress over data integrity
- high-churn orchestration modules that aggregate too many responsibilities into one file

The result is predictable:
- bugs are expensive to localize
- degraded behavior looks like healthy behavior
- benchmark data is less trustworthy than it appears
- refactors carry high regression risk because core modules are oversized and cross-cutting

If this codebase is to support reliable future development, the first design principle must be:

**No meaningful failure may disappear without leaving a typed trace, an operator-visible signal, and a verification path.**

## Execution Status

Implemented tranches as of 2026-04-13:
- Phase 0 started: `src/observability.py` added; `ServerStatus` extended with failure/degradation fields; backend health probes now classify failure cause.
- Phase 0 continued: `src/config/validation.py` now records explicit registry bootstrap diagnostics for missing or malformed registry loads instead of silently collapsing all failures to an untraceable empty cache.
- Phase 1 started: `InferenceResult` gained `partial`, `degraded`, `failure_stage`, and `failure_reason`; timeout/degraded results now populate them. The global `success` semantic flip is intentionally deferred pending full consumer audit.
- Phase 2 started: reward injection now tracks `submitted`, `acknowledged`, `failed`, and per-action failure reasons; benchmark callers preserve compatibility by deriving legacy `rewards_injected` from acknowledged deliveries.
- Phase 3 started: health routes and benchmark preflight now record richer diagnostics. Benchmark boolean contracts remain intact on the critical fan-out paths.
- Phase 3 continued: `scripts/benchmark/seeding_infra.py` preflight now records explicit `stage`, `failure_reason`, and `failure_detail` in `last_preflight`, preserving the existing boolean contracts while making API recovery and smoke-test failures diagnosable.
- Phase 4 started: `ConcurrencyAwareBackend` now uses explicit session migration states and no longer records quarter affinity before restore success.
- Phase 5 started: `graph/helpers.py` has already been reduced by extracting `src/graph/answer_resolution.py` and `src/graph/observability.py`.
- Phase 5 continued: `src/graph/workspace.py` now owns workspace prompt/update/broadcast helpers, further reducing `graph/helpers.py` without changing callers.
- Phase 5 continued: `src/graph/file_artifacts.py` now owns solution-file persistence and output spill helpers, leaving the compaction path as the next major extraction boundary.
- Phase 5 continued: `src/graph/session_summary.py` now owns session-log initialization, turn recording, summary refresh, two-level summary construction, and prompt-block assembly.
- Phase 5 continued: `src/graph/compaction.py` now owns compaction prompt resolution, token-estimation helpers, context externalization path selection, and the main context-compaction routine.
- Phase 5 continued: `src/graph/budgets.py` now owns budget thresholds, token-cap helpers, reasoning-length alarm checks, and budget-pressure/exhaustion helpers, with `graph/helpers.py` retaining compatibility re-exports for the critical graph call paths.
- Graph execution cleanup: REPL token-cap defaults were reconciled to the documented/tested `768` baseline, and stale classifier tests expecting the old `5000` default were updated.
- Benchmark executor truthfulness continued: `scripts/lib/executor.py` now carries additive `partial`, `degraded`, `failure_stage`, and `failure_reason` fields on its local `InferenceResult`, and timeout/request-error paths populate them without changing the existing `success` contract.
- Corpus retrieval diagnostic hardening: `src/services/corpus_retrieval.py` now carries a `RetrievalDiagnostics` dataclass populated on every `retrieve()` call, tracking loaded state, format, query ngrams, shard counts (queried/failed/unavailable), candidates, results, elapsed time, and classified failure reasons. Per-shard query failures are now logged at debug level instead of being completely silent. Load errors now use classified `(reason, detail)` pairs.
- Corpus retrieval logging elevated: `src/prompt_builders/builder.py` `build_corpus_context()` failure logging elevated from DEBUG to WARNING for operator visibility.
- Phase 5 continued: `src/graph/think_harder.py` now owns the adaptive think-harder cluster (config access, ROI computation, stats tracking, gating decision, config builder).
- Phase 5 continued: `src/graph/task_ir_helpers.py` now owns task IR processing helpers (file extraction, task seeding, context gathering, anti-pattern detection).
- Phase 5 continued: `src/graph/decision_gates.py` now owns state-transition decision gates (escalation, retry, approval, timeout skip, end-result construction).
- `graph/helpers.py` is now at `966` lines (down from `2413` original — 60% reduction) with 10 extracted modules total.

Verification status:
- Focused suites for the implemented tranches are green.
- Most recent combined targeted verification run: `88 passed` (reasoning alarm + classifier + corpus + seeding infra + config validation + benchmark executor suites).
- Most recent graph-focused verification run after all 10 helper extractions: `46 passed` (reasoning-length alarm + difficulty signal classifiers).
- Most recent corpus retrieval verification run after diagnostic hardening: `33 passed` (28 existing + 5 new diagnostic tests).
- Most recent benchmark-executor verification run after the additive result-contract hardening: `3 passed` direct executor tests and `430 passed` on the touched regression suite.
- Most recent benchmark preflight verification run after stage/failure metadata hardening: `4 passed` direct infra tests and `435 passed` on the touched regression suite.
- Most recent config bootstrap diagnostics verification run after registry-fallback hardening: `2 passed` direct config tests and `437 passed` on the touched regression suite.

## What Is Actually Wrong

### 1. Diagnostics are not first-class

The codebase often catches exceptions, returns a default, logs at `debug`, or does nothing. That makes the system resilient in the narrow sense of “keeps running,” but opaque in the operational sense of “cannot explain why quality degraded.”

Verified examples:
- [src/graph/helpers.py](/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py) contains `34` broad catches and spans token budgeting, workspace state, escalation logging, session compaction, scratchpad management, answer extraction, and execution guards.
- [src/services/corpus_retrieval.py](/mnt/raid0/llm/epyc-orchestrator/src/services/corpus_retrieval.py) returns empty results for many load/query failures, which is safe for uptime but weak for operator diagnosis.
- [src/config/validation.py](/mnt/raid0/llm/epyc-orchestrator/src/config/validation.py) silently collapses registry-load failures into `{}` caches, which hides configuration drift and bootstrap problems.
- [src/api/routes/health.py](/mnt/raid0/llm/epyc-orchestrator/src/api/routes/health.py) probes backends as simple `ok: bool` with no classification of timeout vs connection failure vs non-200 status.

### 2. Truthfulness about partial failure is inconsistent

The system sometimes knows it only partially succeeded but still reports success.

Verified example:
- [src/backends/llama_server.py](/mnt/raid0/llm/epyc-orchestrator/src/backends/llama_server.py) returns `InferenceResult(success=True, completion_reason="read_timeout_partial")` on streaming read timeout with partial output.

That may be acceptable for response salvage, but not as an unqualified success bit. A caller reading only `success` cannot distinguish:
- complete success
- salvageable partial completion
- degraded inference due to transport stall

That is a core diagnostics bug, not just a naming issue.

### 3. Benchmark reward injection is operationally unsafe

The reward path intentionally uses fire-and-forget execution:
- [scripts/benchmark/seeding_injection.py](/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_injection.py) creates a background `ThreadPoolExecutor`
- `_inject_3way_rewards_http()` submits futures and returns submission count only
- failures are logged at `debug`
- the seeding loop records the question as seen after checkpointing, regardless of actual reward delivery

Consequences:
- the harness can report “injected N rewards” when only `N` submissions were queued
- failed reward injection can be operationally invisible
- learning data can silently diverge from evaluation outcomes

This is one of the highest-value refactor targets in the repo.

### 4. KV migration is functionally clever but not operationally honest

[src/backends/concurrency_aware.py](/mnt/raid0/llm/epyc-orchestrator/src/backends/concurrency_aware.py) is a good proof that the routing idea works, but it is still structured as optimistic best-effort control flow:
- migration assignment is recorded before migration completes
- save/restore failures increment counters and log warnings, but do not propagate a typed degraded-routing state
- `session_id -> quarter` affinity is updated prior to restore success
- there is no explicit “migration pending / migration failed / affinity stale” model

The implementation is workable, but it is not yet safe enough as a foundational orchestrator abstraction.

### 5. Core orchestration surfaces are still too wide

The repo has already decomposed some earlier god modules, but the main orchestrator control plane still has oversized hotspots:

Largest verified source files:
- `2413` lines: [src/graph/helpers.py](/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py)
- `1681` lines: [src/api/routes/chat_delegation.py](/mnt/raid0/llm/epyc-orchestrator/src/api/routes/chat_delegation.py)
- `1481` lines: [src/repl_environment/environment.py](/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/environment.py)
- `1116` lines: `src/pipeline_monitor/claude_debugger.py`
- `1105` lines: `src/graph/session_log.py`
- `1064` lines: `src/config/models.py`
- `995` lines: [src/prompt_builders/builder.py](/mnt/raid0/llm/epyc-orchestrator/src/prompt_builders/builder.py)
- `849` lines: [src/model_server.py](/mnt/raid0/llm/epyc-orchestrator/src/model_server.py)
- `834` lines: `src/tool_registry.py`
- `810` lines: [src/backends/llama_server.py](/mnt/raid0/llm/epyc-orchestrator/src/backends/llama_server.py)

The issue is not only line count. It is that these files mix:
- policy and mechanism
- transport and domain logic
- data shaping and recovery behavior
- user-facing behavior and instrumentation concerns

## Top Findings

### Critical

1. **Silent degradation is systemic, not incidental.**
   Evidence: `436` broad catches in `src/`, with the densest concentration in orchestration, inference, and route handling.

2. **Benchmark reward injection is not verified end-to-end.**
   Evidence: [scripts/benchmark/seeding_injection.py](/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_injection.py) submits futures and never checks completion before the seeding workflow proceeds.

3. **`graph/helpers.py` is still the main orchestration god module.**
   Evidence: `2413` lines, `34` broad catches, and at least eight distinct concerns packed into one file.

4. **Partial inference success is reported as full success.**
   Evidence: `read_timeout_partial` in [src/backends/llama_server.py](/mnt/raid0/llm/epyc-orchestrator/src/backends/llama_server.py).

### High

1. **Backend health and server lifecycle status surfaces are under-modeled.**
   Evidence: [src/api/routes/health.py](/mnt/raid0/llm/epyc-orchestrator/src/api/routes/health.py) and [src/backends/server_lifecycle.py](/mnt/raid0/llm/epyc-orchestrator/src/backends/server_lifecycle.py) report limited health truth and lose failure cause.

2. **KV migration state is optimistic and weakly transactional.**
   Evidence: [src/backends/concurrency_aware.py](/mnt/raid0/llm/epyc-orchestrator/src/backends/concurrency_aware.py).

3. **Feature-flag governance is too manual.**
   Evidence: [src/features.py](/mnt/raid0/llm/epyc-orchestrator/src/features.py) duplicates the feature inventory across dataclass fields, `summary()`, production defaults, test defaults, and env parsing.

4. **Top-level `src/` sprawl weakens module boundaries.**
   Evidence: `49` loose files at `src/` root.

5. **Script-side infrastructure checks choose convenience over diagnostic fidelity.**
   Evidence: [scripts/benchmark/seeding_infra.py](/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_infra.py) treats several probe failures as idle/unhealthy without preserving cause.

6. **The shared benchmark executor still encodes ambiguous timeout semantics.**
   Evidence: [scripts/lib/executor.py](/mnt/raid0/llm/epyc-orchestrator/scripts/lib/executor.py) returns partial output with `timed_out=True`, which is better than silent failure but still lacks typed degraded-state modeling.

### Medium

1. **Prompt-builder fallback behavior is too permissive for a central prompt surface.**
   Evidence: [src/prompt_builders/builder.py](/mnt/raid0/llm/epyc-orchestrator/src/prompt_builders/builder.py) falls back on prompt file read failures and some optional behaviors with minimal operator signal.

2. **Corpus retrieval is operationally tolerant but weakly observable.**
   Evidence: [src/services/corpus_retrieval.py](/mnt/raid0/llm/epyc-orchestrator/src/services/corpus_retrieval.py) disables itself or returns empty retrievals on many load/query failures.

3. **Configuration bootstrap hides registry issues.**
   Evidence: [src/config/validation.py](/mnt/raid0/llm/epyc-orchestrator/src/config/validation.py) converts registry-load failures into empty caches.

4. **Older and newer refactors coexist without a single modularity standard.**
   Evidence: some subsystems are now packages, while other similarly sized surfaces remain monolithic.

## Refactor Strategy

The refactor should not start with “split big files.” It should start with **diagnostic truthfulness**, then move to modularity.

Recommended order:
1. observability foundations
2. inference/result truthfulness
3. benchmark data integrity
4. health and lifecycle status modeling
5. `graph/helpers.py` decomposition
6. `src/` package reorganization
7. feature-flag governance cleanup
8. broader exception-policy remediation

## Phase Plan

### Phase 0: Observability Foundation

Goal:
- make suppressed failures visible without changing core behavior yet

Create:
- `src/observability.py`

Add:
- `log_suppressed()`
- `log_degradation()`
- `log_partial_success()`
- `classify_exception()` helpers for transport, dependency, config, filesystem, parsing, and unexpected failures

Extend:
- [src/backends/server_lifecycle.py](/mnt/raid0/llm/epyc-orchestrator/src/backends/server_lifecycle.py) `ServerStatus`

Add fields:
- `failure_reason: str = ""`
- `failure_detail: str = ""`
- `degraded: bool = False`
- `degradation_source: str = ""`
- `checked_at: float = 0.0`

Success criteria:
- no behavior change
- all best-effort paths can emit structured, searchable diagnostics

### Phase 1: Make Inference Result Semantics Honest

Target files:
- [src/model_server.py](/mnt/raid0/llm/epyc-orchestrator/src/model_server.py)
- [src/backends/llama_server.py](/mnt/raid0/llm/epyc-orchestrator/src/backends/llama_server.py)
- [scripts/lib/executor.py](/mnt/raid0/llm/epyc-orchestrator/scripts/lib/executor.py)

Required model changes:
- add `partial: bool = False` to `InferenceResult`
- add `degraded: bool = False`
- add `failure_stage: str = ""`
- add `failure_reason: str = ""`

Rules:
- complete success: `success=True`, `partial=False`, `degraded=False`
- partial salvage: `success=False`, `partial=True`, `degraded=True`
- pure failure: `success=False`, `partial=False`, `degraded=False`

Do not keep `success=True` for `read_timeout_partial`.

Why this matters:
- current callers can mistake transport degradation for valid model behavior
- this blocks reliable routing, eval, and diagnosis

Decision gate:
- audit all `result.success` consumers before changing semantics
- if too risky, add the new fields first and only flip `success` after a consumer audit

### Phase 2: Benchmark Data Integrity

Target files:
- [scripts/benchmark/seeding_injection.py](/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_injection.py)
- [scripts/benchmark/seed_specialist_routing.py](/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seed_specialist_routing.py)
- [scripts/benchmark/seeding_rewards.py](/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_rewards.py)

Replace:
- fire-and-forget submission count

With:
- tracked reward submission objects
- batch completion wait with bounded timeout
- per-reward result accounting
- retry classification for infrastructure failures

Minimum data model:
- `submitted`
- `acknowledged`
- `failed`
- `skipped`

Required behavior:
- checkpoint reward delivery status, not just eval result
- do not report “injected” when only submitted
- make replay idempotent and first-class

This is the highest-value change outside core orchestrator execution.

### Phase 3: Health Truthfulness

Target files:
- [src/api/routes/health.py](/mnt/raid0/llm/epyc-orchestrator/src/api/routes/health.py)
- [src/backends/server_lifecycle.py](/mnt/raid0/llm/epyc-orchestrator/src/backends/server_lifecycle.py)
- [scripts/benchmark/seeding_infra.py](/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_infra.py)

Refactor goals:
- distinguish timeout, refused, non-200, invalid JSON, and dependency-missing cases
- stop flattening backend probe failures into `ok: false` alone
- stop assuming unreachable means idle in harness code

Design rule:
- health APIs should answer:
  - is it healthy?
  - if not, why not?
  - is it degraded or down?
  - what was the last successful check?

### Phase 4: KV Migration Hardening

Target file:
- [src/backends/concurrency_aware.py](/mnt/raid0/llm/epyc-orchestrator/src/backends/concurrency_aware.py)

Refactor goals:
- isolate routing policy from migration mechanism
- treat migration as an explicit state machine
- make affinity changes transactional

Recommended split:
- `routing_policy.py`
- `kv_migration.py`
- `affinity_store.py`
- `concurrency_aware.py` as thin composition layer

Required state model:
- `unassigned`
- `assigned_full`
- `migration_pending`
- `assigned_quarter`
- `migration_failed_cold`

Current risk:
- session affinity is recorded before restore success
- caller-visible semantics do not expose degraded migration outcomes

### Phase 5: Decompose `graph/helpers.py`

Target file:
- [src/graph/helpers.py](/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py)

This is the most important structural refactor.

Current concern clusters inside one file:
- token and budget policy
- workspace tracking
- solution-file persistence
- failure recording and escalation logging
- compaction and externalization
- session-log plumbing
- answer extraction and rescue
- approval and retry helpers

Recommended package split:
- `src/graph/budgets.py`
- `src/graph/workspace.py`
- `src/graph/observability.py`
- `src/graph/compaction.py`
- `src/graph/session_journal.py`
- `src/graph/answer_resolution.py`
- `src/graph/retry_policy.py`
- `src/graph/task_seeding.py`

Recommended first extraction:
- `answer_resolution.py`

Reason:
- relatively pure
- low dependency surface
- easiest to unit test independently

Recommended second extraction:
- `compaction.py`

Reason:
- already conceptually cohesive
- currently mixes file I/O, model calls, token estimation, and feature gating

Execution note:
- `answer_resolution.py` is complete.
- `observability.py` extraction is also complete as a compatibility shim.
- `workspace.py` extraction is complete as a compatibility shim.
- `file_artifacts.py` extraction is complete as a compatibility shim.
- `session_summary.py` extraction is complete as a compatibility shim.
- `compaction.py` extraction is complete as a compatibility shim.
- `budgets.py` extraction is complete (token-cap helpers, band budgets, reasoning alarms).
- `think_harder.py` extraction is complete (adaptive ROI tracking, gating, config builder).
- `task_ir_helpers.py` extraction is complete (file extraction, task seeding, context gathering, anti-pattern detection).
- `decision_gates.py` extraction is complete (escalation, retry, approval, timeout skip, end-result).
- `graph/helpers.py` is now `966` lines — primarily `_execute_turn()` plus thin wrappers. 10 extracted modules total.

Do not start by splitting tiny helpers mechanically. Split by stable responsibility boundary.

### Phase 6: Top-Level Package Reorganization

Problem:
- `49` loose files at `src/` root

Recommended package groupings:
- `src/runtime/`: executor, inference_lock, inference_tap, concurrency
- `src/orchestration/`: dispatcher, escalation, roles, task_ir, delegation cache/reporting
- `src/registry/`: registry_loader, tool_loader, tool_registry, script_registry
- `src/session/`: keep existing package, move analytics-related loose files under it where coherent
- `src/inference/`: model_server, prefix_cache, radix_cache, llm_cache
- `src/interfaces/`: cli and transport-adjacent surfaces if they remain thin

Do this only after Phases 0-5. Right now too many imports still cross unstable boundaries.

### Phase 7: Feature Flag Governance

Target file:
- [src/features.py](/mnt/raid0/llm/epyc-orchestrator/src/features.py)

Problem:
- one logical feature inventory is copied across five places:
  - dataclass fields
  - `summary()`
  - production defaults
  - test defaults
  - env-parse mapping

Refactor goal:
- one declarative registry drives all of the above

Recommended design:
- `FeatureSpec` registry with:
  - `name`
  - `default_test`
  - `default_prod`
  - `env_var`
  - `description`
  - `dependencies`

Generate:
- dataclass or runtime object
- summaries
- validation
- env parsing

This will remove high-friction maintenance work and reduce flag drift.

### Phase 8: Exception Policy Remediation

Do not attempt to remove all broad catches blindly.

Instead classify each one:
- instrumentation guard
- optional dependency fallback
- external I/O degradation
- recoverable user-path failure
- bug-masking catch that should be narrowed or re-raised

Priority modules:
- [src/graph/helpers.py](/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py)
- `src/inference_lock.py`
- `src/llm_primitives/primitives.py`
- [src/api/routes/chat_vision.py](/mnt/raid0/llm/epyc-orchestrator/src/api/routes/chat_vision.py)
- `src/api/routes/chat_pipeline/routing.py`
- `src/api/routes/chat_pipeline/repl_executor.py`
- `src/api/services/memrl.py`

Rule:
- broad catches are allowed only when they emit structured degradation diagnostics and return an explicitly degraded result

## Module-by-Module Recommendations

### `src/graph/helpers.py`

Refactor: required

Why:
- biggest module
- highest catch density
- central execution-path coupling

Primary risks:
- cross-cutting imports
- hard-to-characterize regressions
- silent non-fatal fallbacks hiding real defects

### `src/backends/llama_server.py`

Refactor: required

Why:
- transport concerns, metrics extraction, payload construction, slot operations, and degraded-success handling are mixed

Refactor shape:
- `payloads.py`
- `transport.py`
- `metrics.py`
- `streaming.py`
- `slots.py`

### `src/backends/concurrency_aware.py`

Refactor: required

Why:
- policy and migration state are intertwined
- current affinity semantics are not transactional enough

### `src/backends/server_lifecycle.py`

Refactor: moderate, but important

Why:
- good abstraction start
- weak status model
- stub backends will become liabilities if status semantics stay vague

### `src/model_server.py`

Refactor: moderate

Why:
- `InferenceResult` and request semantics are central contracts
- this file should become the canonical truth for inference status vocabulary

### `src/features.py`

Refactor: required

Why:
- governance cost is high
- every new flag multiplies change surface

### `src/services/corpus_retrieval.py`

Refactor: moderate

Why:
- behavior is useful
- error handling is too fallback-heavy
- loading/query/result formatting should be separated

### `src/prompt_builders/builder.py`

Refactor: moderate

Why:
- not as urgent as execution-path modules
- but still too large for a prompt composition surface
- file fallback behavior should be better instrumented

### `src/api/routes/health.py`

Refactor: required

Why:
- current health output is insufficient for diagnosing subtle infrastructure failures

### `src/config/validation.py`

Refactor: moderate

Why:
- bootstrap safety is good
- silent empty-cache fallback is too permissive for a central config path

### `scripts/benchmark/seeding_injection.py`

Refactor: critical

Why:
- silent reward loss corrupts downstream learning

### `scripts/benchmark/seeding_orchestrator.py`

Refactor: high

Why:
- slot erasure and poll logic are operationally valuable but have too many catch-and-continue paths

### `scripts/benchmark/seeding_infra.py`

Refactor: high

Why:
- health/idle logic currently discards cause and sometimes assumes best-case state

### `scripts/lib/executor.py`

Refactor: high

Why:
- shared benchmark infra contract
- timeout/partial-result semantics need to align with production inference semantics

## Architectural Standards To Adopt

All future orchestration code should follow these rules:

1. Every degraded path must return a typed degraded state.
2. Every broad catch must log structured context and category.
3. Health surfaces must expose cause, not only status.
4. Background work that affects learning or evaluation must be observable and accountable.
5. Core contracts must distinguish:
   - success
   - partial success
   - degraded success
   - failure
6. Large orchestration modules must have one responsibility boundary, not one workflow boundary.
7. Feature flags must have one source of truth.

## Verification Plan

Before each phase lands:
- add characterization tests around current behavior
- add explicit degraded-state tests
- add operator-surface assertions for logs/status payloads

Must-have verification by phase:

- Phase 0:
  - structured diagnostics emitted for representative suppressed failures

- Phase 1:
  - callers tested against complete success, partial salvage, and hard failure

- Phase 2:
  - simulate reward endpoint failure and verify failed delivery is recorded, not merely submitted

- Phase 3:
  - probe timeout, refused connection, non-200, and invalid payload paths separately

- Phase 4:
  - simulate save failure and restore failure independently
  - verify affinity map remains truthful

- Phase 5:
  - characterization tests around answer extraction, compaction, escalation logging, and retry policy before moving code

- Phase 7:
  - test parity between feature registry, summary output, defaults, and env parsing

## Do Not Do

- Do not start with a repo-wide “replace `except Exception`” sweep.
- Do not split `graph/helpers.py` by arbitrary line ranges.
- Do not flip partial-success semantics without auditing consumers.
- Do not keep fire-and-forget reward injection in any benchmark path that feeds learning.
- Do not reorganize `src/` packages before stabilizing core contracts.

## Immediate Next Actions

1. Implement Phase 0 observability primitives and extend `ServerStatus`.
2. Audit all `InferenceResult.success` consumers.
3. Replace reward submission counting with reward delivery accounting.
4. Extract `graph/answer_resolution.py` from `graph/helpers.py`.

## Final Assessment

The orchestrator is not failing because it is too ambitious. It is failing because it still treats diagnosability as optional and because some of its most important control-plane modules are oversized, optimistic, and too tolerant of silent fallback.

The right refactor is therefore:
- first, make failure states truthful
- second, make core contracts explicit
- third, decompose the modules that currently hide those truths

That sequencing will improve reliability faster than a purely cosmetic modularity pass, and it will make every later refactor materially safer.
