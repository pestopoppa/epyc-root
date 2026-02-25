# Orchestration Roadmap (Unified)

**Created**: 2026-02-06 (merged from `orchestrator-quality-roadmap.md` + `rlm-orchestrator-roadmap.md`)
**Status**: Active — Live validation pending, Phases 6-8 ready
**Tests**: 2015 passing, 67.48% coverage

---

## Quick Status

| Phase | Description | Status |
|-------|-------------|--------|
| Quality 1-3 | Bug fixes, debug suite, MemRL integration | ✅ COMPLETE |
| RLM 1-5 | Backend, RLM enhancements, escalation, formalizer, tools | ✅ COMPLETE |
| Architecture A-G | Logging, ProactiveDelegator, persona, gates | ✅ COMPLETE |
| **Live Validation** | Phase 3 validation with orchestrator stack | **PENDING** |
| **Phase 6** | Early failure detection | READY |
| **Phase 7** | Hyperparameter tuning | READY |
| Phase 8 | Trajectory visualization | LOW |

---

## Active Work

### 1. Live Validation (Quality Phase 3)

**Status**: Code complete, needs orchestrator stack running

```bash
# Full validation script
bash scripts/benchmark/run_phase3_validation.sh

# Or step by step:
# 0. Start stack
python3 scripts/server/orchestrator_stack.py start --hot-only

# 1. Baseline (routing OFF)
ORCHESTRATOR_SPECIALIST_ROUTING=0 ORCHESTRATOR_MEMRL=0 \
  python scripts/benchmark/compare_orchestrator_direct.py --debug --suite all --debug-seed 42

# 2. Comparative seeding
ORCHESTRATOR_SPECIALIST_ROUTING=1 ORCHESTRATOR_ARCHITECT_DELEGATION=1 ORCHESTRATOR_MEMRL=1 \
  python scripts/benchmark/seed_specialist_routing.py --suites all --sample-size 10

# 3. Learning loop
ORCHESTRATOR_SPECIALIST_ROUTING=1 ORCHESTRATOR_ARCHITECT_DELEGATION=1 ORCHESTRATOR_MEMRL=1 \
  python scripts/benchmark/memrl_learning_loop.py --iterations 5 --sample-size 10 --regression-check

# 4. Analyze routing
python scripts/benchmark/analyze_routing_policy.py

# 5. Regression gate
ORCHESTRATOR_SPECIALIST_ROUTING=1 ORCHESTRATOR_ARCHITECT_DELEGATION=1 ORCHESTRATOR_MEMRL=1 \
  python scripts/benchmark/compare_orchestrator_direct.py --debug --suite all --regression-gate
```

**Decision criteria**: If specialists show quality gain AND regression gate passes → flip defaults to True.

### 2. Early Failure Detection (RLM Phase 6)

**Goal**: Abort bad generations early to save compute

**Work needed**:
1. Wire `GenerationMonitor` into `llm_call_monitored()` in `src/llm_primitives.py`
2. Per-tier entropy thresholds (frontdoor=4.0, coder=5.0, worker=6.0)
3. Add thresholds to `model_registry.yaml`

```python
# In src/llm_primitives.py
def llm_call_monitored(self, prompt: str, role: str = "worker") -> str:
    monitor = GenerationMonitor(
        entropy_threshold=self._get_entropy_threshold(role),
        spike_threshold=self._get_spike_threshold(role),
    )
    tokens = []
    for token in self._stream_call(prompt, role):
        tokens.append(token)
        monitor.observe(token)
        if monitor.should_abort():
            raise EarlyAbortError(f"Generation aborted: {monitor.abort_reason}")
    return "".join(tokens)
```

### 3. Hyperparameter Tuning (RLM Phase 7)

**Goal**: Systematic optimization of model parameters
**Blocker**: Resolved — 31,820 real benchmark questions available via dataset adapters

**Work needed**: Create `scripts/benchmark/sweep_hyperparams.py`
- Temperature sweep (0.0, 0.1, 0.2, 0.3, 0.5, 0.7)
- top_p sweep (0.9, 0.95, 1.0)
- MoE expert count sweep (2, 3, 4, 6)

### 4. Trajectory Visualization (RLM Phase 8) — LOW PRIORITY

**Goal**: Debug UI for recursive execution
- Enhanced SSE events with trajectory metadata
- TrajectoryLogger for JSONL replay
- Deferred until higher priorities complete

---

## Completed Work (Reference)

### Quality Roadmap (Phases 1-3)

| Phase | What | Files |
|-------|------|-------|
| 1 | Bug fixes: prompt canonicalization, stop sequences, loop truncation | `src/prefix_cache.py`, `src/llm_primitives.py`, `src/api/routes/chat.py` |
| 2 | REPL/MemRL integration: 3-way mode selection, output formalizer | Feature-flagged, 690 tests |
| 3 | Specialist routing, GraphEnhancedRetriever, failure veto, architect delegation | `src/api/routes/chat.py`, `src/features.py` |

**Debug suite**: 325 static questions + on-the-fly sampling from 31,820 real benchmark questions

**VL suite**: Rebuilt from OCRBench (1K) + ChartQA (2.5K) with real images

### RLM Roadmap (Phases 1-5)

| Phase | What | Files |
|-------|------|-------|
| 1 | Backend: LlamaServerBackend HTTP, CachingBackend init, role routing | `src/backends/llama_server.py`, `src/llm_primitives.py` |
| 2 | RLM: forced exploration, async llm_batch, recursion depth, cost tracking | `src/repl_environment.py`, `src/llm_primitives.py` |
| 3 | Escalation: error classification, FailureRouter in Root LM loop | `src/failure_router.py`, `src/api.py` |
| 4 | Formalizer: keyword detection, subprocess invocation, context injection | `src/formalizer.py`, 37 tests |
| 5 | Tools: MCP client, tool registry, script registry | `src/mcp_client.py`, 46 tests |

### Architecture Roadmap (A-G) — ALL COMPLETE

- A: Structured logging with task_extra + JSONFormatter
- B: Integration test import fix
- C: ProactiveDelegator + parallel execution (Stage 6.5)
- D: Critical path metric (already implemented)
- E: Persona registry + MemRL auto-selection
- F: Staged reward shaping (StagedScorer)
- G: Parallel gate execution (asyncio.gather)

---

## Key Files

| File | Purpose |
|------|---------|
| `src/api/routes/chat.py` | Main chat endpoint, all execution modes |
| `src/features.py` | Feature flags (specialist_routing, architect_delegation, etc.) |
| `scripts/benchmark/run_phase3_validation.sh` | Full validation pipeline |
| `scripts/benchmark/dataset_adapters.py` | On-the-fly benchmark sampling |
| `orchestration/model_registry.yaml` | Role configs, system prompts |

---

## Unresolved Questions

1. **Latency budget**: 235B architect at 6.75 t/s = 2.7x slower than frontdoor. Acceptable for hard tasks?
2. **480B warm-up cost**: ~120s load time. Skip in seeding if not already warm?
3. **lm-evaluation-harness**: Use directly (60+ benchmarks free) or extract scoring logic?
4. **Formalizer model**: xLAM-2-1B, Qwen2.5-1.5B, or fine-tuned?
5. **TOON for ReAct**: Evaluate whether TOON encoding helps tool-calling format.

---

## Verification

```bash
# Unit tests
cd /mnt/raid0/llm/claude && python3 -m pytest tests/unit/ -x -q

# Gates
make gates

# Full test suite (caution: slow)
make test-all
```
