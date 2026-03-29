# Dynamic Stack Assembly & Concurrency Management

**Status**: Strategic analysis complete — implementation deferred to Phase D
**Created**: 2026-03-24
**Updated**: 2026-03-25
**Priority**: MEDIUM (routing optimization is higher priority, but this unblocks full NUMA utilization)
**Blocks**: Nothing currently
**Blocked by**: Autoresearch bootstrap (Phase A), observability infrastructure (Phase B)
**Related**: [`routing-intelligence.md`](routing-intelligence.md), [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md), [`routing-and-optimization-index.md`](routing-and-optimization-index.md), [`kv-cache-quantization.md`](kv-cache-quantization.md) (DS-3 slot-save-path interacts with KV quant config)

---

## Problem

The orchestrator stack is statically configured but optimal configuration depends on runtime conditions. Key tension: **per-request latency vs aggregate throughput**.

### The Combinatorial Problem

Testing every combination of {model x instance_count x NUMA_config x accel_flags} per role is infeasible:
- 5+ roles x 3-4 model options x 1-4 instances x 3 accel configs = thousands of combinations
- Each config takes minutes to deploy and benchmark
- Interactions between roles (memory pressure, core contention) make isolated testing insufficient

**Solution**: Autoresearch explores this space autonomously via `program.md`-guided experimentation.

---

## Part 1: Physical Constraints

### Hardware (EPYC 9655)
- 2 NUMA nodes x 48 cores (192 logical CPUs with HT)
- ~1,130 GB total RAM (~566 GB per node)
- NUMA quarters: Q0A, Q0B (node 0), Q1A, Q1B (node 1) — each 48 threads

### Cross-NUMA Penalty
Running models with `numactl --interleave=all` (192t) distributes pages round-robin across nodes — every memory access has ~50% chance of hitting remote memory. NUMA-pinned quarters eliminate this entirely.

Result: 4x48t NUMA-pinned gives **6-7x aggregate throughput** vs 1x192t interleaved for models <=65 GB.

### Current Stack (updated 2026-03-29 — REAP-246B swap + NUMA multi-instance)

| Role | Model | Size | Instances | Weights (shared) | Private | Per-inst t/s |
|------|-------|------|-----------|-----------------|---------|-------------|
| frontdoor | Qwen3.5-35B-A3B Q4KM | 20 GB | 4×48t | 20 GB | 4 GB | 12.7 (moe6) |
| coder_escalation | Qwen2.5-Coder-32B Q4KM | 18.5 GB | 4×48t | 18.5 GB | 10 GB | 10.8 (spec dm=32) |
| architect_general | Qwen3.5-122B-A10B Q4KM | 69 GB | 2×96t | 69 GB | 4 GB | 4.3 (~8.3 agg) |
| architect_coding | **REAP-246B Q4KM** | **139 GB** | **2×96t** | **139 GB** | **4 GB** | **8.0 (16.5 agg)** |
| ingest | Qwen3-Next-80B-A3B Q4KM | 46 GB | 1×96t | 46 GB | 0.5 GB | ~12 |
| worker_explore | Qwen3-Coder-30B-A3B Q4KM | 16 GB | **4×48t** | 16 GB | 6 GB | **39.1 (~156 agg)** |
| worker_vision | Qwen2.5-VL-7B Q4KM | 4 GB | 1×24t | 4 GB | 0.5 GB | ~24 |
| vision_escalation | Qwen3-VL-30B-A3B Q4KM | 18 GB | 1×96t | 18 GB | 1.5 GB | TBD |
| **Total loaded** | | | | **330 GB** | **31 GB** | **361 GB (32% of RAM)** |

REAP-246B swap (2026-03-29) reduced footprint from ~540 GB to ~361 GB — from 48% to 32% of RAM. All models can be loaded simultaneously with 769 GB free. Dynamic stack assembly is now a throughput optimization, not a memory management necessity.

---

## Part 2: Single-to-Multi Instance Transition

### The KV Migration Scenario (Validated for Pure MoE)

For pure MoE models (30B-A3B), NUMA scaling differs from hybrid:
- **1x96t (half-machine, node-pinned)**: 29.5-36 t/s raw; with spec+lookup potentially 45-55 t/s (untested)
- **1x48t (quarter)**: 39.1 t/s (with spec+lookup, measured)
- **4x48t (all quarters)**: ~156 t/s aggregate (estimated), 39.1 per request

If 96t single-instance is faster than 48t (plausible for pure MoE), the transition is:
1. Start conversation on 1x96t (max per-request speed)
2. Second conversation arrives -> save KV state (~1-5s)
3. Migrate to 4x48t config (39 t/s per request, 156 t/s aggregate)
4. Restore state to one instance, new conversation starts on another

**This works because it's the same model** — KV state transfer is valid within identical model+quant.

### KV State Transfer Capabilities (Verified in llama.cpp)

**API endpoints (stable, production-ready):**
```
POST /slots/{id}?action=save   -> {"n_saved": 84, "n_written": 14309796, "timings": {"save_ms": 49.865}}
POST /slots/{id}?action=restore -> {"n_restored": 84, "n_read": 14309796, "timings": {"restore_ms": 42.937}}
POST /slots/{id}?action=erase
```

**What gets saved:**
- KV cache (attention K+V tensors for all layers)
- Recurrent state (Delta Net R+S tensors for hybrid models like Qwen3.5)
- Sequence metadata (token sequences, cell allocation)
- Architecture validation (prevents cross-model loading)

**Size estimates:**
- ~170 KB/token (TinyLLaMA reference); 35B estimate: 2-16 GB per conversation (2K-8K tokens)
- Save/restore latency: 40-50ms (small), 1-5s (production conversations)

**Requirements:**
- Server must launch with `--slot-save-path <dir>` flag
- File-based only — no built-in cross-process transfer
- Same model + same quantization required for restore

**Hybrid model support (critical for Qwen3.5):**
```cpp
// llama-memory-hybrid.cpp — saves both KV and recurrent state
void llama_memory_hybrid::state_write(io, seq_id, flags) {
    mem_attn->state_write(io, seq_id, flags);  // KV cache
    mem_recr->state_write(io, seq_id, flags);  // Delta Net state
}
```
Extended flags: `LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY=1` saves recurrent state only (lightweight).

**What would need to be built for dynamic migration:**

| Feature | Status | Effort |
|---------|--------|--------|
| State save/restore to files | Exists | — |
| Binary state buffer API | Exists | — |
| HTTP state export endpoint | Missing | ~200 LOC |
| Cross-instance state relay | Missing | Medium |
| Model compat checking (beyond arch) | Partial | Small |
| Incremental state sync | Missing | High |

### Applies to ALL Pure MoE Roles

The single-to-multi transition isn't just for frontdoor. Any pure MoE model where single-instance speed exceeds per-quarter speed benefits: coder candidates, workers, ingest models. The scheduler must track which models support this pattern.

---

## Part 3: Tiered Deployment Architecture

### HOT / WARM / COLD Model Tiers

| Tier | State | Latency | Memory | Use Case |
|------|-------|---------|--------|----------|
| **HOT** | mlock'd, always running | <300ms | Pinned in RAM | Latency-sensitive roles |
| **WARM** | Loaded, no mlock | 1-8s (page cache) | In page cache, evictable | On-demand roles |
| **COLD** | On disk | 30s-3min | None until loaded | Rarely-used, fallback |

### Tier Assignment is an Autoresearch Optimization Target

Which models belong in which tier is empirical — not hardcoded.

**Arguments for HOT generals:**
- Eliminates burst-mode interruption (~78s teardown/rebuild cycle)
- Escalation latency: milliseconds vs seconds
- With ~540 GB headroom, everything CAN fit HOT

**Arguments for WARM generals:**
- Frees hundreds of GB for more fast-model instances
- Enables larger KV cache budgets for long conversations
- Architect requests may be rare enough that 1-8s latency is acceptable

**Only usage data can settle this.** Autoresearch should test both configurations.

### Burst Mode Analysis

When the orchestrator needs full compute for a large model:

| Config | Escalation Latency | Service Interruption | Memory Cost |
|--------|-------------------|---------------------|-------------|
| HOT generals | <300ms | None | 250-320 GB locked |
| WARM generals | 1-8s first request | None | Freed for fast models |
| Burst mode (take over quarters) | ~78s total | Full interruption | None until needed |

Current deployment keeps all models loaded (~540 GB, 48% RAM). Given headroom, HOT generals are likely optimal — but autoresearch validates.

### Illustrative Memory Budget (not prescriptive)

```
HOT-heavy config (~600 GB, 53% of RAM):
  4x frontdoor                              =  74-80 GB
  4x coder_escalation                       =  74 GB
  2x workers                                =  37 GB
  1x architect_general (122B)               =  69 GB
  1x architect_coding (480B)                = 250 GB
  1x ingest + vision                        =  74 GB
  6x embedders                              =  24 GB
  ─────────────────────────────────────────────────────
  Total                                      ~  608 GB
  Remaining for KV + dynamic                 ~  522 GB
```

---

## Part 4: NUMA Quarter Scheduling

### Quarter as Schedulable Unit

Each NUMA quarter (48 threads, ~280 GB addressable) hosts one model instance. The scheduler assigns models to quarters based on demand.

```
Static (current):
  Q0A: frontdoor[0]    Q0B: frontdoor[1]
  Q1A: frontdoor[2]    Q1B: frontdoor[3]
  (architects on full-node overlay)

Dynamic (escalation-heavy):
  Q0A: frontdoor[0]    Q0B: coder[0]
  Q1A: coder[1]        Q1B: worker_explore[0]
  (architect on full-node overlay when requested)

Dynamic (concurrent sessions):
  Q0A: frontdoor[0]    Q0B: frontdoor[1]
  Q1A: frontdoor[2]    Q1B: coder[0]
```

### Scheduling Events

| Event | Detection | Response |
|-------|-----------|----------|
| New conversation | Request arrives | Route to available HOT instance |
| Queue depth increase | All instances busy | Launch new instance if spare quarter exists |
| Escalation | Routing decision | Ensure specialist loaded; accept 1-8s if WARM |
| Large model request | Architect needed | Burst mode: drain quarter(s), give architect full node |
| Session end | Conversation complete | Mark quarter available for reallocation |
| Idle timeout | No requests for N seconds | Consider evicting to free quarter |

### Context Transfer Mechanisms

Currently, escalation works without KV migration — models are pre-loaded, context transferred via:

1. **REPL solution files** (`/mnt/raid0/llm/tmp/{task_id}_solution.py`) — lightweight, cross-model
2. **Scratchpad/escalation context** — structured `EscalationContext` dataclass
3. **TOON-encoded context** — 52.5% token reduction on structured data

KV state migration is a **new capability** for:
- Same model moving between NUMA configs (single-to-multi instance)
- Instance eviction to free a quarter
- Instance failure recovery

For cross-model escalation (FD -> architect), REPL files + structured context remain primary.

---

## Part 5: System-Level Design Principles

### System Quality > Per-Model Quality

What matters is **end-to-end system quality** — not individual model capability. The orchestrator maximizes system intelligence through:
- Routing + escalation — cheap fast models handle easy queries, generals handle hard ones
- Tools — web research, code execution, file processing, OCR
- Episodic memory — Q-value-guided routing improves over time
- Skillbank — distilled experience for cross-suite generalization
- Deterministic pipelines — OCR, TTS, formalization, extraction
- Specialized small models — vision, embedding, classification at extreme throughput

A 79% model + smart orchestration + tools + episodic memory can outperform an 83% model alone.

### RAM as Competitive Advantage

Unlike GPU inference, 1.1 TB RAM lets us host an army of hyperspecialized models alongside reasoning tiers. Autoresearch should optimize the ENTIRE stack — reasoning tiers AND specialist pipelines.

### Model Selection is an Autoresearch Problem

The frontdoor model, tier assignments, instance counts — none of these should be hardcoded. The registry has many benchmarked models; new ones appear regularly (REAP variants, Nanbeige, MiroThinker). The framework must be model-agnostic.

### Stack Simplification Hypothesis

Claude Code runs on 3 models (Opus, Sonnet, Haiku). Maybe our stack has too many different models and reasoning simplicity is key. Maybe not — our RAM enables specialization cloud can't match. Only empirical testing via autoresearch can determine the optimal simplicity-specialization tradeoff.

---

## Part 6: Connection to Autoresearch

### Stack-Config as Experiment Variable

Autoresearch (see `autopilot-continuous-optimization.md`) should explore ALL of these:

| Axis | Example Questions |
|------|-------------------|
| Model selection per role | Best frontdoor? Best coder? |
| Instance counts | How many workers? Dynamic scaling? |
| NUMA topology | Quarter vs half-node vs full-node per model? |
| Tier assignment | Which models HOT vs WARM vs COLD? |
| Cascade depth | 2-tier vs 3-tier? Does fast-filter tier pay off? |
| General utilization | Are generals prompted efficiently? TOON optimizations? |
| Concurrency patterns | Multi-instance routing quality impact? |
| Specialist pipelines | Vision, OCR, extraction optimization? |

### Findings Flow

```
AutoResearch discovers:
  "Model X + config Y achieves Z quality at W throughput"

Human reviews -> approves integration:
  -> Update model_registry.yaml, orchestrator_stack.py, q_scorer.py

Orchestrator runs deterministically with new config.
AutoResearch proposes next experiment.
```

---

## Open Research Questions

1. **30B-A3B at 96t with speculation**: Potentially 45-55 t/s — key data point for single-to-multi migration
2. **Mixed-model NUMA quarter deployments**: Cross-model memory contention on shared nodes is unknown
3. **General model economics**: How often do architect requests occur? Prompted efficiently?
4. **KV state size for production models**: ~170 KB/token estimate needs validation at 2K-8K tokens
5. **Real workload patterns**: Claude Code usage history could inform workload modeling
6. **Cascade depth diminishing returns**: 3-tier vs 2-tier tradeoff

---

## Strategic Sequence

| Phase | Description | Deliverable |
|-------|-------------|-------------|
| **A** | Autoresearch bootstrap | `program.md`, debug suite scoring, autonomous experimentation |
| **B** | Observability infrastructure | Telemetry (queue depth, NUMA util, escalation rate), `--slot-save-path` |
| **C** | Autoresearch-driven model & stack exploration | Empirically-grounded stack configuration |
| **D** | Deterministic quarter scheduler | Event-driven NUMA allocation, KV save/restore, overflow queuing |
| **E** | Template codification | Stack templates in config, dynamic backend add/remove |
| **F** | Conversation-log-driven refinement | Predictive workload model, anticipatory deployment |

---

## What This Is NOT

- NOT a replacement for routing intelligence (which model handles which task type)
- NOT per-request optimization (too slow to reconfigure)
- NOT exhaustive search of all combinations (autoresearch explores intelligently)

## Key Insight

Routing intelligence determines *which model* for each task (quality decision). Stack assembly determines *how that model is provisioned* (capacity decision). The two compose but develop independently.

## See Also

- [`routing-and-optimization-index.md`](routing-and-optimization-index.md) — umbrella index
- [`routing-intelligence.md`](routing-intelligence.md) — role selection, factual risk
- [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) — autoresearch framework
- `src/backends/round_robin.py` — runtime instance routing (supports dynamic backend list)
