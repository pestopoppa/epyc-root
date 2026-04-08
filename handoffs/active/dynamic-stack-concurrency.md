# Dynamic Stack Assembly & Concurrency Management

**Status**: Phase D (KV migration) implemented 2026-03-29. Phases B-D complete.
**Created**: 2026-03-24
**Updated**: 2026-03-29
**Priority**: HIGH (pre-warm + migration enables optimal single-session AND concurrent throughput)
**Blocks**: Multi-session performance
**Blocked by**: Nothing — Phase E (autoresearch exploration) can start
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

| Role | Model | Size | Instances | Config | Per-inst t/s |
|------|-------|------|-----------|--------|-------------|
| frontdoor | Qwen3.5-35B-A3B Q4KM | 20 GB | **1×96t + 4×48t** | pre-warm, ConcurrencyAware | 12.7 (48t), TBD (96t) |
| coder_escalation | Qwen2.5-Coder-32B Q4KM | 18.5 GB | **1×96t + 4×48t** | pre-warm, ConcurrencyAware | 10.8 (48t) |
| architect_general | Qwen3.5-122B-A10B Q4KM | 69 GB | 2×96t | RoundRobin | 4.3 (~8.3 agg) |
| architect_coding | REAP-246B Q4KM | 139 GB | 2×96t | RoundRobin | 8.0 (16.5 agg) |
| ingest | Qwen3-Next-80B-A3B Q4KM | 46 GB | 1×96t | single | ~12 |
| worker_explore | Qwen3-Coder-30B-A3B Q4KM | 16 GB | **1×96t + 4×48t** | pre-warm, ConcurrencyAware | 39.1 (48t) |
| worker_vision | Qwen2.5-VL-7B Q4KM | 4 GB | 1×24t | single | ~24 |
| vision_escalation | Qwen3-VL-30B-A3B Q4KM | 18 GB | 1×96t | single | TBD |
| **Total loaded** | | | | | **~415 GB (37% of RAM)** |

Pre-warm deployment (2026-03-29): +54 GB over previous config (361 → 415 GB). 3 roles now have 5 instances each (1 full-speed + 4 concurrent). 715 GB free for KV caches + OS. `ConcurrencyAwareBackend` routes single session to 96t, concurrent sessions to 48t instances.

---

## Part 2: Pre-Warm Strategy — All Configs Always Running

### Core Principle: Use Abundant RAM to Eliminate Cold Starts

With 769 GB free (32% utilization), we should pre-launch **both** single-instance (max throughput) and multi-instance (max concurrency) configs for every role. No restarts, no cold starts, no migrations that require teardown.

### Pre-Warm Architecture for Frontdoor (Reference Example)

**5 pre-launched instances** — all holding the same Qwen3.5-35B-A3B Q4KM (19 GB each):

| Instance | Config | Port | NUMA | Use Case |
|----------|--------|------|------|----------|
| FD-full | 1×96t | 8080 | node0 | Max single-session speed (higher per-request t/s) |
| FD-q0a | 1×48t | 8180 | Q0A | Concurrent session slot 1 |
| FD-q0b | 1×48t | 8280 | Q0B | Concurrent session slot 2 |
| FD-q1a | 1×48t | 8380 | Q1A | Concurrent session slot 3 |
| FD-q1b | 1×48t | 8480 | Q1B | Concurrent session slot 4 |

**Additional RAM cost**: +19 GB (1 extra instance) = 380 GB total stack (34% of RAM). Trivial.

### Smart Routing (Concurrency-Aware)

The `RoundRobinBackend` is replaced with a **concurrency-aware router**:

```
Single session active:
  → Route to FD-full (1×96t, best per-request throughput)

Second session arrives:
  1. Save KV state from FD-full: POST /slots/0?action=save (~50ms-5s)
  2. Restore on FD-q0a: POST /slots/0?action=restore
  3. Route new session to FD-q0b
  4. FD-full becomes idle (available for next single-session request)

Third+ sessions:
  → Route to next idle quarter instance (FD-q1a, FD-q1b)

All sessions complete:
  → Next request goes back to FD-full for max speed
```

**Key insight**: FD-full (96t) always stays running. It's the fast path. Quarter instances are always running too. The only dynamic operation is KV state save/restore, which is lightweight (existing llama.cpp API, already enabled via DS-3 `--slot-save-path`).

### Applies to ALL Pure MoE Roles

Any role where 96t single-instance outperforms 48t per-instance benefits:

| Role | Full Instance | Quarter Instances | Extra RAM |
|------|--------------|-------------------|-----------|
| frontdoor (35B-A3B) | 1×96t | 4×48t | +19 GB |
| coder_escalation (32B) | 1×96t | 4×48t | +18.5 GB |
| worker_explore (30B-A3B) | 1×96t | 4×48t | +16 GB |

**Total extra**: ~54 GB for full pre-warm across 3 roles → ~415 GB total stack (37% of RAM). Still leaves 715 GB free.

For large models (architect 122B, REAP 246B), 2×96t is already the right config — they can't fit in a quarter. These keep their current setup.

### KV State Transfer (Verified in llama.cpp)

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
- Server must launch with `--slot-save-path <dir>` flag ✅ (DS-3, implemented 2026-03-29)
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

### What Needs to Be Built

| Feature | Status | Effort | Notes |
|---------|--------|--------|-------|
| State save/restore to files | ✅ Exists | — | `--slot-save-path` wired (DS-3) |
| Binary state buffer API | ✅ Exists | — | llama.cpp stable API |
| `NUMA_CONFIG` with full+quarter | **TODO** | Small | Add 1×96t entry per role |
| Concurrency-aware router | **TODO** | Medium | Replace round-robin selection in `RoundRobinBackend` |
| KV migration orchestrator | **TODO** | Medium | Save from full, restore to quarter, on concurrent arrival |
| Queue depth → routing decision | **TODO** | Small | Use DS-1 `_active_per_instance` data |
| Fallback to full when idle | **TODO** | Small | Route to 96t when all quarters idle |

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

## Strategic Sequence (Revised 2026-03-29)

| Phase | Description | Deliverable | Status |
|-------|-------------|-------------|--------|
| **B** | Observability infrastructure | DS-1 (queue depth), DS-2 (escalation rate), DS-3 (slot-save-path), DS-4 (stack state) | ✅ DONE |
| **C** | Pre-warm deployment | ✅ DONE 2026-03-29. 1×96t + 4×48t for frontdoor/coder/worker. `ConcurrencyAwareBackend`, `NUMA_CONFIG`, `ServerURLsConfig` updated. | ✅ DONE |
| **D** | Concurrency-aware router + KV migration | ✅ DONE 2026-03-29. Session affinity, KV save/restore via slot API, background migration thread. | ✅ DONE |
| **E** | Autoresearch-driven exploration | Model selection, tier assignment, instance count optimization via autoresearch loop. | Parallel with D |
| **F** | Template codification | Stack templates in config, selectable profiles (coding-heavy, research-heavy). | Depends on E |
| **G** | Predictive refinement | Workload modeling from conversation logs, anticipatory deployment. | Long-term |

**Key change from original sequence**: Pre-warm deployment (C) and concurrency-aware routing (D) now come BEFORE autoresearch (E), because:
1. Pre-warm is a pure RAM trade (54 GB extra) with zero downside — improves throughput immediately
2. Concurrent sessions are a real use case — round-robin is insufficient
3. Autoresearch can run in parallel and benefits from the pre-warm infra (stack experiments without restarts)

---

## Design Assumptions

- **Multi-session is normal**: User runs parallel Claude Code sessions, autoresearch generates concurrent eval requests. Round-robin is insufficient — load-aware routing with KV migration is required.
- **RAM is abundant**: 769 GB free at 32% utilization. Pre-warming extra instances costs <60 GB. Always prefer pre-launched instances over cold starts.
- **No restarts for experiments**: StructuralLab stack experiments should toggle which pre-launched instances are in the active rotation, not restart servers. Restart-free experimentation enables faster autoresearch iteration.
- **Per-request latency matters**: Single-session requests should get maximum throughput (96t). Only sacrifice per-request speed when concurrency demands it.

---

## DS-6 Design Summary (2026-04-08)

Extracted from Part 4 above into an actionable specification for the deterministic quarter scheduler.

### Goal

Replace the static quarter assignment in `orchestrator_stack.py` with an event-driven scheduler that dynamically allocates NUMA quarters to model instances based on demand.

### Current State (Static)

```python
# orchestrator_stack.py lines 155-161
NUMA_Q0A = ("0-23,96-119", 48)    # Always frontdoor[0]
NUMA_Q0B = ("24-47,120-143", 48)  # Always frontdoor[1]
NUMA_Q1A = ("48-71,144-167", 48)  # Always frontdoor[2]
NUMA_Q1B = ("72-95,168-191", 48)  # Always frontdoor[3]
```

Each quarter is permanently assigned to a role. If frontdoor is idle but coder is overloaded, the idle quarters can't help.

### Proposed: Event-Driven Quarter Assignment

**Schedulable events** (from Part 4 table):

| Event | Detection Source | Scheduler Response |
|-------|-----------------|-------------------|
| New conversation | HTTP request arrives | Route to available HOT instance; if none, check WARM quarters |
| Queue depth > 1 | `RoundRobinBackend.get_stats()` | Launch quarter instance if spare quarter available |
| Escalation needed | Routing decision in `_route_request()` | Ensure specialist is loaded; accept 1-8s WARM latency if not |
| Architect burst | Large model requested | Drain 2 quarter instances → give architect full NUMA node |
| Session end | Conversation completes | Mark quarter available for reallocation |
| Idle timeout | No requests for 60s | Consider evicting to free quarter for other roles |

**Quarter lifecycle**: HOT (loaded, ready, <10ms) → WARM (model on disk, KV-save available, 1-8s) → COLD (not loaded, need full startup, 15-30s).

### Implementation Components

1. **QuarterScheduler class** (new, in `scripts/server/quarter_scheduler.py`):
   - Maintains `quarter_assignments: dict[str, QuarterState]` — Q0A/Q0B/Q1A/Q1B → {role, port, status, last_request}
   - `assign(role, priority)` → selects best quarter (prefer idle, then lowest-priority occupant)
   - `evict(quarter)` → KV-save current model, mark as available
   - `burst(role, n_quarters)` → drain N quarters for large model (architect)

2. **Integration with ConcurrencyAwareBackend** (existing, `src/backends/round_robin.py`):
   - Backend already tracks per-instance active/total counts (DS-1)
   - Scheduler reads backend stats to detect queue depth events
   - Scheduler calls `orchestrator_stack.py` to start/stop quarter instances

3. **Integration with RoundRobinBackend routing** (existing):
   - When scheduler reassigns a quarter, update backend's URL list for that role
   - KV migration via slot API (DS-3 `--slot-save-path`, DS-4 state logging)

### KV Migration Cost Model

| Conversation Length | KV Size (~170 KB/token) | Migration Time |
|--------------------|-----------------------|---------------|
| 500 tokens | ~85 MB | 40-50ms |
| 2K tokens | ~340 MB | 200-300ms |
| 8K tokens | ~1.4 GB | 1-2s |
| 32K tokens | ~5.4 GB | 4-8s |

**Decision rule**: Migrate if queue depth > 1 AND expected wait > migration time.

### Design Constraints

- **Memory budget**: 415 GB currently used (37% of 1130 GB). Each quarter instance adds ~16-19 GB (30-35B model at Q4_K_M). Maximum: 6-8 simultaneous quarter instances.
- **No restart**: Scheduler should toggle which pre-launched instances are active, not restart servers. Pre-warm (Phase C) provides the instance pool.
- **Burst mode**: Architect models (122B, 246B) need 2-4 quarters (full NUMA node). Burst mode drains quarter instances and gives the node to the architect. Current: 78s teardown/rebuild cycle. Target: <10s via KV migration + pre-warm.
- **Single-user optimization**: Current workload is primarily single-session. Scheduler should optimize for that case first, with graceful degradation to concurrent mode.

### Open Questions (from Part 6 research questions)

1. Does 96t single-instance outperform 4×48t concurrent? (Need Package B data)
2. Real-world escalation frequency? (RI-10 canary data will show this)
3. KV state size validation at production context lengths
4. Mixed-model NUMA quarter contention (same-node cross-model interference)

### Dependencies

- **Package B results**: Establish throughput baselines for single vs concurrent mode
- **RI-10 canary data**: Escalation frequency → architect burst demand
- **DS-5 autoresearch**: Model exploration may change which models need quarters

### Implementation Priority

Phase E (autoresearch-driven stack exploration) comes first — it may change which models are in the stack. DS-6 scheduler is Phase F, building on whatever configuration autoresearch discovers as optimal.

## Key Insight

Routing intelligence determines *which model* for each task (quality decision). Stack assembly determines *how that model is provisioned* (capacity decision). The pre-warm strategy makes these fully orthogonal — routing doesn't need to know about NUMA topology, and the concurrency-aware router handles instance selection transparently.

## See Also

- [`routing-and-optimization-index.md`](routing-and-optimization-index.md) — umbrella index
- [`routing-intelligence.md`](routing-intelligence.md) — role selection, factual risk
- [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) — autoresearch framework
- `src/backends/round_robin.py` — runtime instance routing (supports dynamic backend list)
