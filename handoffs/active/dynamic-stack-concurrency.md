# Dynamic Stack Assembly & Concurrency Management

**Status**: Phases B-D complete. DS-6 (QuarterScheduler) scaffolding implemented 2026-04-11, DS-7 (stack templates) scaffolding 2026-04-11 + Gap 3/4 closure 2026-04-21 (NIB2-19). Phase E awaiting AR-3 results.
**Created**: 2026-03-24
**Updated**: 2026-04-21

## DS-7 Gap 3 + Gap 4 closure (2026-04-21, NIB2-19)

- **Gap 3 (migration path)**: Full-restart protocol implemented in `src/config/stack_migration.py` (~230 LOC). Six phases: save_kv → stop_all → start_target → restore_kv → verify_health. Dry-run mode for CI/pre-flight. CLI: `orchestrator_stack.py start --migrate-to <profile> --dry-run`. Diff-based migration deferred to DS-6 QuarterScheduler (NIB2-18) per `feedback_numa_concurrency_complexity`.
- **Gap 4 (resource budget)**: `ResourceBudget` dataclass (`max_mlock_gb`, `max_total_gb`, `reserve_kv_gb`) added to `StackTemplate`. Optional `resource_budget:` block in template YAML; system defaults when absent. `validate_template()` extended with 3 new checks (HOT mlock ceiling, total loaded ceiling, KV headroom floor). `default.yaml` carries an explicit budget block (800/930/100 GB).
- **Tests**: 10 new tests in `tests/unit/test_stack_templates_v2.py`, all passing. Full unit suite (296 tests) clean.
**Priority**: HIGH (pre-warm + migration enables optimal single-session AND concurrent throughput)
**Blocks**: Multi-session performance
**Blocked by**: Nothing — Phase E (autoresearch exploration) can start
**Domain**: routing-and-optimization (primary — Phases B-E: stack exploration, QuarterScheduler, templates, autoresearch); inference-acceleration (Phase F KVCOMM cross-listed for discoverability — F1 blocks on AM compaction P2)
**Related**: [`routing-intelligence.md`](routing-intelligence.md), [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md), [`routing-and-optimization-index.md`](routing-and-optimization-index.md), [`kv-cache-quantization.md`](kv-cache-quantization.md) (DS-3 slot-save-path interacts with KV quant config), [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) (Phase F KVCOMM compounds with AM compaction), [`inference-acceleration-index.md`](inference-acceleration-index.md) (Phase F landscape row), [`numa-prefill-decode-disaggregation.md`](numa-prefill-decode-disaggregation.md) (feasibility stub — disagg literature spawned 2026-04-26)

## Research Intake Update — 2026-04-26

Disaggregated-serving + scheduler literature ingested (intake batch 458-472). Direct relevance to DS-6/DS-7/Phase-F design:

- **[intake-459] DistServe** (arXiv:2401.09670): foundational prefill/decode disaggregation. 4.48× throughput claim is goodput-under-SLO on multi-tenant GPU traffic — NOT free transfer.
- **[intake-460] Splitwise** (arXiv:2311.18677): heterogeneous machine pools per phase; KV migration over high-bandwidth back-plane.
- **[intake-472] Mooncake** (arXiv:2407.00079): KVCache-centric global pool + Conductor scheduler with cache-aware routing. The pool/tiering pattern is portable to NUMA DRAM even without full disagg.
- **[intake-468] ORCA** (OSDI'22): iteration-level scheduling + selective batching. Foundational for the orchestrator scheduler abstraction; selective batching (per-op batchability classification) is the right framing for MoE expert routing across heterogeneous KV in the QuarterScheduler.
- **[intake-469] Sarathi v1** (arXiv:2308.16369): superseded by Sarathi-Serve (intake-048, already_integrated). Important as the **counter-architecture** to disagg — chunked prefill + piggybacking achieves prefill/decode interference elimination WITHOUT KV migration. Likely the more EPYC-appropriate path.
- **[intake-471] Expert Choice Routing** (arXiv:2202.09368): not_applicable — training-time routing change, not retrofittable to pretrained Qwen3/REAP/GLM checkpoints.

**Tier 2b critique (important)**: Disagg can REGRESS 20-30% on short-prompt / low-concurrency workloads (BentoML, vLLM docs). NVIDIA "Beyond the Buzz" (arXiv:2506.05508) shows disagg only wins on prefill-heavy + larger models and requires dynamic rate-matching. KV-transfer overhead on EPYC xGMI (~64 GB/s) will be proportionally worse than on NVLink. **Single-user CPU regime is the wrong regime for naive disagg adoption** — see [`numa-prefill-decode-disaggregation.md`](numa-prefill-decode-disaggregation.md) for the qualified feasibility study.

**Concrete actions for DS-6/DS-7**:
1. Adopt ORCA's selective-batching abstraction in the QuarterScheduler (which ops are batchable across heterogeneous KV).
2. Lift Mooncake's KVCache-tiering pattern (NUMA-local DRAM + SSD spill) into Phase F KVCOMM scope as a stretch goal.
3. **Consider Sarathi-Serve adoption BEFORE NUMA-disagg** — it's already in intake (intake-048) and avoids the KV-transfer tax.

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

## DS-6 Design Audit (2026-04-09)

Review of the DS-6 design spec identified 6 gaps that must be resolved before implementation:

1. **No dynamic URL list update API.** `RoundRobinBackend` and `ServerURLsConfig` hold static role→URL mappings. Scheduler needs `add_instance(role, url)` / `remove_instance(role, url)` methods on the backend — these don't exist yet.

2. **No liveness check.** Scheduler assumes pre-warmed instances are alive. No heartbeat/health protocol for quarter servers. If a quarter server crashes, scheduler has no way to detect it.

3. **Port allocation ambiguity.** Does Q0A always use port 8080 (port stays, role changes), or do ports float? Design needs to clarify whether ports are quarter-fixed or role-fixed.

4. **Burst mode race condition.** Draining 2 quarters for architect leaves in-flight requests to those quarters unhandled. Need a graceful drain protocol (e.g., stop accepting new requests, wait for in-flight to complete, then reassign).

5. **Missing idle-time tracking.** 60s idle timeout requires `idle_since` timestamp per instance. `ConcurrencyAwareBackend` tracks active/total counts but not idle time.

6. **No degradation strategy.** What happens if a quarter is evicted mid-request? Need defined behavior (reject? queue? redirect?).

**Status**: BLOCKED on Phase E dependencies (Package B data, RI-10 canary, DS-5 autoresearch). No scaffolding work recommended — model roster may change entirely.

## DS-6 Gap Resolutions (2026-04-09)

Concrete design decisions for each gap identified in the DS-6 audit above. These resolve the spec so implementation can proceed cleanly once Phase E unblocks.

### Gap 1 Resolution: Dynamic URL List Update API

Add thread-safe instance management to `RoundRobinBackend` (`src/backends/round_robin.py`):

```python
def add_instance(self, url: str) -> None:
    """Add a backend instance to the rotation. Thread-safe."""
    with self._lock:
        self._backends.append(url)
        self._active_per_instance.append(0)
        self._total_per_instance.append(0)

def remove_instance(self, url: str) -> bool:
    """Remove a backend instance. In-flight requests complete normally. Thread-safe."""
    with self._lock:
        idx = next((i for i, b in enumerate(self._backends) if self._get_base_url(b) == url), None)
        if idx is None:
            return False
        self._backends.pop(idx)
        self._active_per_instance.pop(idx)
        self._total_per_instance.pop(idx)
        # Counter wraps naturally on next _next() call via modulo
        return True
```

Add parallel methods on `ConcurrencyAwareBackend` (`src/backends/concurrency_aware.py`):
- `register_quarter(role: str, url: str)` — adds to the role's quarter backend list
- `unregister_quarter(url: str)` — removes from whichever role's list contains it

**Key invariant**: `ServerURLsConfig` remains the boot-time-only config. The `QuarterScheduler` mutates backends at runtime via these methods. Removal only stops new routing — in-flight requests to a removed backend complete normally (the HTTP connection is already established).

### Gap 2 Resolution: Liveness Check

Each quarter server exposes `GET /health` (standard llama-server endpoint, already available).

**Heartbeat protocol**:
- `QuarterScheduler` runs a background `asyncio.Task` polling each quarter every 10 seconds via `httpx.AsyncClient.get(f"{base_url}/health", timeout=3.0)`
- State machine per quarter: `HEALTHY` (≥2 consecutive successes) → `SUSPECT` (1 failure) → `DEAD` (3 consecutive failures)
- On `DEAD`: call `remove_instance(url)` on the relevant backend, mark quarter as `AVAILABLE` for relaunch
- Leverage existing `BackendCircuit` pattern from `src/api/health_tracker.py` — wrap each quarter in a `BackendCircuit(failure_threshold=3, recovery_timeout=30.0)`

**Relaunch strategy**: On DEAD detection, scheduler invokes `server_lifecycle.restart_server(quarter_id)` (existing module). Quarter state transitions to `LAUNCHING` until next health check succeeds, then back to `HEALTHY`.

### Gap 3 Resolution: Port Allocation — Quarter-Fixed

Ports are **quarter-fixed, not role-fixed**:

| Quarter | Port | Fixed to NUMA Cores |
|---------|------|-------------------|
| Q0A | 8080 | 0-23, 96-119 |
| Q0B | 8180 | 24-47, 120-143 |
| Q1A | 8280 | 48-71, 144-167 |
| Q1B | 8380 | 72-95, 168-191 |

When the scheduler reassigns a quarter from role A to role B, the **port stays the same** — only the model loaded on that port changes. Full-node instances (96t) use a separate port range: 8070-8079.

**Rationale**: Quarter-fixed ports are simpler for monitoring (Grafana dashboards key on port), log correlation (port → quarter → NUMA node is stable), and firewall rules (no port churn). The alternative (role-fixed ports) would require port remapping on every reassignment with no operational benefit.

### Gap 4 Resolution: Burst Mode Drain Protocol

3-phase graceful drain when architect needs a full NUMA node (2+ quarters):

**Phase 1 — DRAINING**: Set quarter state to `DRAINING` in `QuarterScheduler.quarter_assignments`. The `RoundRobinBackend._next()` method skips instances in DRAINING state (add state check to the existing round-robin loop). No new requests are routed to these quarters.

**Phase 2 — WAIT**: Poll `_active_per_instance[idx] == 0` for each draining quarter. Timeout: 30 seconds (matches existing `_SLOT_SAVE_TIMEOUT`). During the wait, the burst caller receives an estimated wait time so it can display progress.

**Phase 3 — REASSIGN**: Once all draining quarters reach zero active requests:
1. KV-save any active conversations via `POST /slots/{id}/save` (slot API from DS-3)
2. Stop the quarter llama-server instances
3. Launch the architect instance with full NUMA node allocation
4. Return the architect instance URL to the caller

**Timeout behavior**: If in-flight requests don't complete within 30s, force-drain — set quarter state to `UNAVAILABLE`, let the in-flight request complete (it will get a connection error on its next LLM call → `_classify_error()` returns `BACKEND_UNAVAILABLE` → normal retry routes to another instance).

### Gap 5 Resolution: Idle-Time Tracking

Add `idle_since: float | None` field to `QuarterState`:

```python
@dataclass
class QuarterState:
    quarter_id: str           # Q0A, Q0B, Q1A, Q1B
    role: str | None          # Currently assigned role, or None if unassigned
    port: int                 # Fixed port (see Gap 3)
    status: QuarterStatus     # HEALTHY, SUSPECT, DEAD, DRAINING, LAUNCHING, AVAILABLE
    last_request: float       # time.monotonic() of last request start
    idle_since: float | None  # time.monotonic() when active count hit 0, None while busy
```

**Tracking mechanism**:
- In `RoundRobinBackend`: extend with `_last_request_per_instance: list[float]`, updated on each `_next()` call
- In `ConcurrencyAwareBackend._release()`: when `_active_per_instance[idx]` transitions from >0 to 0, set `idle_since = time.monotonic()` on the corresponding `QuarterState`
- When a new request arrives: clear `idle_since = None`

**Eviction check**: Scheduler runs a periodic check every 15 seconds. For each quarter where `idle_since is not None and (monotonic() - idle_since) > idle_timeout_s`, the quarter becomes eligible for reassignment. Eviction preference: lowest-priority role first.

**Configurable threshold**: `QuarterScheduler.__init__(idle_timeout_s: float = 60.0)`. Can be tuned based on autoresearch findings about session inter-arrival times.

### Gap 6 Resolution: Degradation Strategy

Mid-eviction safety net (should not occur with the drain protocol in Gap 4, but as defense-in-depth):

1. In-flight request to an evicted quarter gets a connection error from httpx (server stopped)
2. `_classify_error()` in `src/graph/error_classifier.py` returns `ErrorCategory.BACKEND_UNAVAILABLE`
3. Existing retry logic: `_should_retry()` returns `True` for transient backend errors (up to `max_retries` per turn)
4. On retry, `RoundRobinBackend._next()` routes to the next available instance (full-speed 96t, or another quarter for the same role)
5. If ALL instances for a role are unavailable: `_should_retry()` returns `False` after max retries → `_should_escalate()` triggers tier escalation to the next level

**Net effect**: Transparent retry with ~1-2 second latency bump. No request is lost. The degradation follows the existing error taxonomy — no new error handling code is needed, only the scheduler's drain protocol (Gap 4) prevents the scenario from occurring under normal operation.

**Extreme case**: If both full-node and all quarter instances are unavailable (hardware failure), the request escalates to the next tier in the escalation ladder. If the top-tier architect is also unavailable, the task terminates with a clear error message. This matches the existing behavior for total backend failure.

**Updated status**: Design gaps resolved. Implementation remains BLOCKED on Phase E dependencies.

## DS-7 Design Audit (2026-04-09)

Review of the DS-7 concept identified 4 gaps:

1. **No template schema defined.** A template needs: hot_roles, warm_roles, instance counts, NUMA allocation, model selection, acceleration params (draft_max, p_split), mlock settings. Currently scattered across `NUMA_CONFIG`, `HOT_SERVERS`, and `ServerURLsConfig` in 3 different files.

2. **No selection mechanism.** How to choose a template at startup? `--profile` CLI flag? Env var? Auto-detection? Not specified.

3. **No migration path between templates.** Switching profiles without DS-6 scheduler means full stack restart (~2-3 min). DS-6 would enable graceful transitions.

4. **No resource validation.** Templates could over-subscribe memory. Need constraint checking that total mlock'd instances fit in 1130 GB RAM budget.

**Status**: BLOCKED on Phase E. Templates encode autoresearch findings — can't define template contents until autoresearch identifies optimal configurations.

## DS-7 Gap Resolutions (2026-04-09)

Concrete design decisions for each gap identified in the DS-7 audit above.

### Gap 1 Resolution: Template Schema

Formal YAML schema for stack templates. Templates live in `stack_templates/<name>.yaml` relative to the orchestrator root.

```yaml
# stack_templates/coding-heavy.yaml
meta:
  name: coding-heavy
  description: "Optimized for multi-file coding sessions with strong coder escalation"
  version: 1

roles:
  frontdoor:
    model: Qwen3.5-35B-A3B
    quant: Q4_K_M
    tier: HOT                    # HOT | WARM | COLD
    instances:
      full:                      # Full NUMA node instance (96t, single-session optimal)
        threads: 96
        numa_node: 0
        port: 8070
        mlock: true
      quarters:                  # Quarter instances (48t, concurrent mode)
        - quarter: Q0A
          threads: 48
          port: 8080
          mlock: true
        - quarter: Q0B
          threads: 48
          port: 8180
          mlock: true
        - quarter: Q1A
          threads: 48
          port: 8280
          mlock: true
        - quarter: Q1B
          threads: 48
          port: 8380
          mlock: true

  coder_escalation:
    model: Qwen2.5-Coder-32B
    quant: Q4_K_M
    tier: HOT
    instances:
      full: { threads: 96, numa_node: 1, port: 8071, mlock: true }
      quarters:
        - { quarter: Q0A, threads: 48, port: 8081, mlock: true }
        - { quarter: Q0B, threads: 48, port: 8181, mlock: true }
        - { quarter: Q1A, threads: 48, port: 8281, mlock: true }
        - { quarter: Q1B, threads: 48, port: 8381, mlock: true }

  architect_general:
    model: Qwen3.5-122B-A10B
    quant: Q4_K_M
    tier: HOT
    instances:
      full: { threads: 96, numa_node: [0, 1], port: 8072, mlock: true }
      replicas:
        - { threads: 96, numa_node: [0, 1], port: 8172, mlock: true }

  architect_coding:
    model: REAP-246B
    quant: Q4_K_M
    tier: HOT
    instances:
      full: { threads: 96, numa_node: [0, 1], port: 8073, mlock: true }
      replicas:
        - { threads: 96, numa_node: [0, 1], port: 8173, mlock: true }

  worker_explore:
    model: Qwen3-Coder-30B-A3B
    quant: Q4_K_M
    tier: HOT
    instances:
      full: { threads: 96, numa_node: 0, port: 8074, mlock: true }
      quarters:
        - { quarter: Q0A, threads: 48, port: 8084, mlock: true }

acceleration:
  draft_max: 8
  p_split: 0.1
  speculation_enabled: true

resource_budget:
  max_mlock_gb: 800            # Hard cap on mlock'd model memory
  max_total_gb: 1000           # Hard cap on all loaded models (mlock + non-mlock)
  reserve_kv_gb: 130           # Minimum reserved for KV caches + OS overhead
```

**Dataclass**: `StackTemplate` in `src/config/stack_templates.py` — mirrors the YAML structure using `@dataclass` with validation. Each `RoleConfig` contains `model`, `quant`, `tier`, and `InstanceConfig` entries. Model sizes are resolved against `model_registry.yaml` at load time.

**Key design points**:
- `quarters` are optional per role — roles that don't need concurrent mode omit them
- `replicas` vs `quarters`: replicas are full-node instances on different NUMA nodes; quarters are same-node partitions
- `tier` controls pre-warm behavior: HOT = mlock + always loaded, WARM = loaded but not mlock'd, COLD = not loaded until needed
- Port assignments follow the quarter-fixed policy from DS-6 Gap 3

### Gap 2 Resolution: Selection Mechanism

Template selection at startup, resolved once at boot:

| Priority | Mechanism | Example |
|----------|-----------|---------|
| 1 (highest) | CLI flag | `--stack-profile coding-heavy` |
| 2 | Env var | `ORCHESTRATOR_STACK_PROFILE=coding-heavy` |
| 3 (fallback) | Default | `stack_templates/default.yaml` |

**Resolution flow** in `orchestrator_stack.py`:
1. Parse `--stack-profile <name>` from CLI args (new argparse argument)
2. If not provided, check `os.environ.get("ORCHESTRATOR_STACK_PROFILE")`
3. If still not set, use `"default"`
4. Load `stack_templates/{name}.yaml`
5. Validate (see Gap 4)
6. Generate `ServerURLsConfig` and `NUMA_CONFIG` dicts from the template
7. Proceed with normal startup using generated config

**`default.yaml`**: Matches the current hardcoded configuration exactly — no behavioral change unless a different profile is explicitly selected. This ensures backward compatibility.

**Auto-detection** (future, not in initial implementation): Detect available RAM, GPU, and NUMA topology at startup and select the best-fitting profile. Requires autoresearch data to define "best-fitting." Deferred until autoresearch (DS-5) produces enough profiles to make selection meaningful.

### Gap 3 Resolution: Migration Path Between Templates

Two migration strategies depending on DS-6 scheduler availability:

**Without DS-6 scheduler (current state)** — full restart:
1. `POST /admin/save-all-kv` — save KV state for all active conversations via slot API
2. Stop all llama-server instances (graceful shutdown, wait for in-flight)
3. Load new template YAML, validate
4. Start new instances per template config
5. Restore KV states where source and target model match (KV is not transferable across different models)
6. Estimated downtime: **2-3 minutes** (dominated by model load time for large models)

**With DS-6 scheduler (future)** — diff-based migration:
1. Compute diff between current and target template: `changed_roles`, `added_roles`, `removed_roles`, `unchanged_roles`
2. For `unchanged_roles`: no action — instances stay running
3. For roles where only `tier` changed (e.g., HOT→WARM): toggle mlock via `madvise(MADV_DONTNEED)` — no restart, <1s
4. For roles where `model` or `quant` changed: use DS-6 drain protocol (Gap 4) to gracefully drain, then swap
5. For `added_roles`: launch new instances from pre-warm pool if available, else cold start
6. For `removed_roles`: drain and stop
7. Target: **<30s** for a 2-role model change (dominated by KV save/restore)

**Constraint**: Both paths are single-user safe. Concurrent-user migration requires a request queue to hold incoming requests during the transition window.

### Gap 4 Resolution: Resource Validation

Validation runs at template load time, before any instances are launched.

**Validation checks**:

```python
def validate_template(template: StackTemplate, registry: ModelRegistry) -> list[str]:
    """Returns list of validation errors (empty = valid)."""
    errors = []

    # 1. Model existence: every model/quant combo in template exists in registry
    for role in template.roles.values():
        if not registry.has_model(role.model, role.quant):
            errors.append(f"Model {role.model} @ {role.quant} not in registry")

    # 2. Memory budget: mlock'd models fit within budget
    total_mlock_gb = sum(
        registry.model_size_gb(role.model, role.quant) * role.instance_count
        for role in template.roles.values()
        if role.tier == "HOT"
    )
    if total_mlock_gb > template.resource_budget.max_mlock_gb:
        errors.append(f"mlock total {total_mlock_gb:.0f} GB > budget {template.resource_budget.max_mlock_gb} GB")

    # 3. Total memory: all loaded models (HOT + WARM) fit
    total_loaded_gb = sum(
        registry.model_size_gb(role.model, role.quant) * role.instance_count
        for role in template.roles.values()
        if role.tier in ("HOT", "WARM")
    )
    if total_loaded_gb > template.resource_budget.max_total_gb:
        errors.append(f"Total loaded {total_loaded_gb:.0f} GB > budget {template.resource_budget.max_total_gb} GB")

    # 4. KV reserve: enough headroom for KV caches + OS
    remaining_gb = 1130 - total_loaded_gb  # 1130 GB = system RAM
    if remaining_gb < template.resource_budget.reserve_kv_gb:
        errors.append(f"KV reserve {remaining_gb:.0f} GB < minimum {template.resource_budget.reserve_kv_gb} GB")

    # 5. Port conflicts: no two instances share a port
    ports = [inst.port for role in template.roles.values() for inst in role.all_instances]
    if len(ports) != len(set(ports)):
        errors.append(f"Port conflict: {[p for p in ports if ports.count(p) > 1]}")

    # 6. NUMA conflicts: no two full-node instances on same NUMA node (unless replicas)
    # (check numa_node overlap across different roles)

    return errors
```

**Fail-fast behavior**: If `validate_template()` returns any errors, startup aborts immediately with a clear error listing all violated constraints. No partial launch — either the entire template is valid or nothing starts.

**`--validate-only` flag**: New CLI argument that loads and validates the template, prints the resource summary (per-role memory, total mlock, total loaded, KV headroom), and exits without launching any servers. Useful for testing template changes before deployment.

**Updated status**: Design gaps resolved. Implementation remains BLOCKED on Phase E dependencies.

## Key Insight

Routing intelligence determines *which model* for each task (quality decision). Stack assembly determines *how that model is provisioned* (capacity decision). The pre-warm strategy makes these fully orthogonal — routing doesn't need to know about NUMA topology, and the concurrency-aware router handles instance selection transparently.

## Phase F: Cross-Instance KV Cache Sharing (KVCOMM)

**Status**: PLANNED — blocked on AM compaction validation (attention-matching P2 gate)
**Research basis**: intake-352 (KVCOMM, NeurIPS'25, arxiv:2510.12872)
**Created**: 2026-04-13

### Problem

When the orchestrator delegates to 3+ coder-32B instances (same model, same quant, different tasks) against the same codebase, each instance independently prefills the shared context (10K-50K tokens). With 4×48t NUMA quarters, this means 3-4 redundant prefills of identical code context — each taking seconds to minutes depending on length.

### Solution

KVCOMM anchor-based offset estimation. First coder instance prefills shared context normally. Subsequent instances reuse the first instance's KV cache by estimating and applying the offset caused by different system prompts (role-specific instructions).

**Paper results**: 70%+ reuse rate, 7.8x TTFT speedup (5-agent, 1K tokens, H100 GPU).

### Concrete Example

```
frontdoor → architect → plan (text)
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    coder-32B (Q0A)  coder-32B (Q0B)  coder-32B (Q1A)
    "implement auth"  "implement API"   "implement tests"

    ← ALL share 50K-token codebase context →
```

Without KVCOMM: 3 × 50K-token prefills = 150K prefill tokens
With KVCOMM: ~65K effective prefill (1.3x vs 3x)

### Compounds with AM Compaction

AM compresses 50K codebase → 5K compact KV entries (10x). KVCOMM then shares those 5K entries across workers without redundant prefill. AM reduces size, KVCOMM eliminates redundant computation — complementary.

### Integration Point

`ConcurrencyAwareBackend` gains an anchor pool. Routing becomes cache-aware:
- Track which instances have prefilled which contexts (via anchor fingerprints)
- Route to instance with best anchor match, not just round-robin
- Fall back to full prefill + anchor creation when no match exists

### Prerequisites

1. AM compaction validated on coding contexts (attention-matching-kv-compaction.md P2 gate)
2. q4_0 offset estimation feasibility tested (novel — paper assumes f16; our KV is q4_0 after Hadamard. Offsets are small (~50% have |offset| < 0.1), may be lost in quantization noise)
3. Cross-NUMA IPC design for anchor pool (shared memory region vs explicit copy across Infinity Fabric)

### Work Items

| Task | Description | Effort | Blocked By |
|------|-------------|--------|-----------|
| F1 | Prototype offset estimation on q4_0 quantized KV | HIGH | AM compaction P2 |
| F2 | Anchor pool design for cross-NUMA sharing | MEDIUM | F1 |
| F3 | ConcurrencyAwareBackend → cache-aware routing | MEDIUM | F2 |
| F4 | Metrics: prefill_speedup_coder_pool in eval tower | LOW | F3 |

### Decision Gate

IF q4_0 offset estimation preserves >95% quality on shared codebase tasks THEN proceed to F2-F4. ELSE defer until f16 KV becomes practical (e.g., after GPU acquisition).

### Cross-References

- [attention-matching-kv-compaction.md](attention-matching-kv-compaction.md) — AM compaction compounds with KVCOMM
- [kv-cache-quantization.md](kv-cache-quantization.md) — q4_0 interaction is the key open question
- `research/deep-dives/kv-compaction-attention-matching-cluster.md` — full deep-dive analysis
- `research/intake_index.yaml` intake-352 — KVCOMM paper details

## See Also

- [`routing-and-optimization-index.md`](routing-and-optimization-index.md) — umbrella index
- [`routing-intelligence.md`](routing-intelligence.md) — role selection, factual risk
- [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) — autoresearch framework
- [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) — KV compaction (compounds with Phase F)
- `src/backends/round_robin.py` — runtime instance routing (supports dynamic backend list)
