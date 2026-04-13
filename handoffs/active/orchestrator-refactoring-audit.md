# Orchestrator Codebase Refactoring Audit

**Status**: ACTIVE — Plan complete, execution not started
**Created**: 2026-04-13 (comprehensive audit session)
**Updated**: 2026-04-13
**Priority**: HIGH
**Categories**: code_quality, observability, refactoring, benchmarks, scripts

## Current Work — Resume Here

### What's Done (2026-04-13)
- Comprehensive audit of `src/` (80K LOC, 253 files), `scripts/` (47K LOC, 178 files), `benchmarks/`
- Identified 437 `except Exception` handlers across 133 source files (root cause of "subtle diagnostic bugs")
- Verified 8 recent fixes (DDG→curl, web fetch, tokens_generated, preflight_audit, etc.) — all solid
- Full 15-phase refactoring roadmap designed with risk assessment and verification plan
- Plan persisted to this handoff

### Next Action
**Phase 0**: Create `src/observability.py`, extend `ServerStatus` dataclass, extend structured logging vocabulary. Zero behavioral changes.

### State
The audit is complete. No code has been modified. This handoff contains the full plan and serves as the execution tracker for all future refactoring sessions. Each phase should be executed independently and tracked here.

---

## Objective

Make the epyc-orchestrator codebase clean, modular, and designed so that **any bug is immediately identifiable**. The core problem is systemic "silent degradation" — 437 bare exception handlers catch errors and return defaults, making the system appear healthy while quality degrades invisibly.

## Why This Matters for EPYC

- Autopilot runs produce unexplained quality regressions that take hours to diagnose
- Benchmark reward injection failures go undetected, causing MemRL to train on incorrect data
- KV migration failures silently degrade session performance without any operator visibility
- The 2,413-line `graph/helpers.py` is untestable as a unit — bugs in one domain (e.g., budget) are masked by unrelated exception handlers in another (e.g., workspace)
- Cross-repo file duplication has already led to diverged `dataset_adapters.py` and `debug_scorer.py`

---

## Work Items

| Phase | Task | Priority | Status | Risk | Decision Gate |
|-------|------|----------|--------|------|--------------|
| 0 | Create `src/observability.py` (log_suppressed, log_degradation helpers) | HIGH | TODO | Zero | N/A — additive |
| 0 | Extend `ServerStatus` with failure_reason/detail fields | HIGH | TODO | Zero | N/A — additive |
| 0 | Extend structured logging vocabulary | HIGH | TODO | Zero | N/A — additive |
| 1 | Fix log levels: WARNING→INFO for inference telemetry | HIGH | TODO | Zero | Verify no alerts key on WARNING level |
| 1 | Fix log levels: DEBUG→WARNING for health/KV failures | HIGH | TODO | Zero | N/A |
| 1 | Add missing WARNING log entries for timeouts | HIGH | TODO | Zero | N/A |
| 2 | Silent exception remediation — `src/` (437 handlers, 6 priority groups) | CRITICAL | TODO | Low-Med | Verify no performance regression from added logging |
| 3 | Silent exception remediation — `scripts/` and benchmarks | HIGH | TODO | Low | N/A |
| 4 | Reward injection verification (fire-and-forget → checked futures) | CRITICAL | TODO | Medium | Run seeding eval with embedder down, verify WARNING |
| 4 | Atomic CSV writes in inference-research | CRITICAL | TODO | Low | Kill bench mid-run, verify no corrupt rows |
| 4 | Error classification fix (preserve exception class) | HIGH | TODO | Low | N/A |
| 4 | Slot erasure return value + caller verification | HIGH | TODO | Low | N/A |
| 5 | Health check failure classification (ConnectError/Timeout/HTTPStatus) | HIGH | TODO | Low | Hit /health with backends down |
| 6 | Partial success truthfulness (success=True → False for read_timeout_partial) | HIGH | TODO | Medium | Gate behind feature flag; audit all result.success consumers |
| 7 | KV migration atomicity (rollback session_quarter on restore failure) | MED-HIGH | TODO | Low | Test with simulated restore failure |
| 8 | `graph/helpers.py` decomposition into 8 modules | HIGH | TODO | Medium | Start with answer_extraction.py (pure text, zero deps) |
| 9 | Module reorganization: 6 package groupings for loose files | MEDIUM | TODO | Low-Med | Start with cli/ (zero consumers) |
| 10 | Cross-repo benchmark deduplication | HIGH | TODO | Low | diff after symlink |
| 11 | Scripts logging & configuration consolidation | MEDIUM | TODO | Low | grep -rc "print(" count should decrease |
| 12 | Deferred import cleanup (50+ sites) | MEDIUM | TODO | Low | Fix config import-time I/O first |
| 13 | Cleanup & hygiene (commented code, magic numbers, compat shims) | LOW | TODO | Zero | N/A |
| 14 | Feature flag registry (5-copy → single source) | LOW | TODO | Low | N/A |

---

## Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|-----------|
| R1 | Phase 6 (partial success) breaks callers that check `result.success` | Medium | High | Gate behind feature flag; audit consumers first |
| R2 | Phase 8 (helpers.py decomposition) breaks import paths | Low | Medium | Keep helpers.py as re-export shim during transition |
| R3 | Phase 9 (module reorg) breaks `tool_registry.py` consumers (20+) | Medium | Medium | Needs re-export shim in `tools/__init__.py` |
| R4 | Phase 4 (reward verification) slows seeding eval throughput | Low | Low | Futures checked in batch, not per-submission |
| R5 | Phase 2 (added logging) causes performance regression on hot path | Low | Medium | Profile graph/helpers.py exception handlers under load |

---

## Key Findings Summary

### Critical (3)
1. **437 silent exception handlers** across 133 files — root cause of diagnostic invisibility
2. **Benchmark reward injection fire-and-forget** — MemRL trains on incorrect data when injection fails
3. **Benchmark CSV data loss** — no locking, no atomicity, partial results on crash

### High (6)
1. **God module** `graph/helpers.py`: 2,413 lines, 58 functions, 34 bare exception handlers, 7 domains
2. **Log level inversion**: routine events at WARNING, failures at DEBUG
3. **Partial success lie**: `llama_server.py:608-628` returns `success=True` on read timeout
4. **Benchmark error misclassification**: infra errors treated as task failures, not retried
5. **Cross-repo duplication**: `dataset_adapters.py` diverged between orchestrator and inference-research
6. **KV migration non-atomicity**: session routing updated before migration thread completes

### Medium (6)
1. **47 loose files** at `src/` top level without package grouping
2. **Feature flag sprawl**: 70+ flags with 5 copies of the same list
3. **50+ deferred imports** hiding real dependency graph
4. **Scripts silent fallbacks**: `lib/executor.py` has 4 `except Exception: pass` sites
5. **Inconsistent logging** across 64+ Python scripts (print vs logging module)
6. **Hardcoded paths/ports** in scripts and benchmarks

---

## Key Files

| Path | Purpose | Phase |
|------|---------|-------|
| `src/graph/helpers.py` | God module (2,413 lines, 58 functions) — decompose into 8 | 8 |
| `src/backends/llama_server.py` | Log levels, timeout logging, partial success lie | 1, 6 |
| `src/backends/concurrency_aware.py` | KV migration atomicity, log levels | 1, 7 |
| `src/backends/server_lifecycle.py` | Health check failure classification | 5 |
| `src/services/corpus_retrieval.py` | 7 silent exception handlers | 2 |
| `src/prompt_builders/builder.py` | 5 silent exception handlers | 2 |
| `src/config/validation.py` | Recursive guard returns {} silently | 2 |
| `src/api/routes/health.py` | Backend probe loses all error context | 2, 5 |
| `src/model_server.py` | InferenceResult — add `partial` field | 6 |
| `src/features.py` | 752 lines, 70+ flags, 5 copies of list | 14 |
| `src/exceptions.py` | 11-class hierarchy — defined but unused | 13 |
| `scripts/lib/executor.py` | 4 silent exception handlers, hardcoded paths | 3 |
| `scripts/benchmark/seeding_injection.py` | Fire-and-forget reward injection | 4 |
| `scripts/benchmark/seeding_orchestrator.py` | Error stringification, slot erasure no-return | 3, 4 |
| `scripts/benchmark/seeding_infra.py` | Health check silent, idle timeout silent | 3, 4 |
| Research: `bench_all_spec_sweeps.sh` | Non-atomic CSV writes | 4 |
| Research: `dataset_adapters.py` | Cross-repo divergence | 10 |

---

## Recent Fixes (April 2026, verified)

All 8 recent fixes verified solid, no new bare exception patterns introduced:
- Web search DDG→curl+Brave (`src/tools/web/search.py`) — rc=23 handled but not logged
- Web fetch urllib→curl (`src/tools/web/fetch.py`) — partial requests may cache
- Code extractor stdin detection (`src/dispatcher.py`)
- Blacklist cleared (`scripts/autopilot/failure_blacklist.yaml`)
- tokens_generated hack removed (`scripts/benchmark/seeding_eval.py`)
- preflight_audit.py created (`scripts/autopilot/preflight_audit.py`) — 9 checks, well-designed
- chat.py added to CODE_MUTATION_ALLOWLIST (`scripts/autopilot/species/prompt_forge.py`)
- tokens_generated in cheap-first ChatResponse (`src/api/routes/chat.py:324`)

---

## References

- Full audit report: `.claude/plans/lively-mixing-fern.md` (plan file from audit session)
- Progress entry: `progress/2026-04/2026-04-13.md`
