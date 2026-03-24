# Dynamic Stack Assembly & Concurrency Management

**Status**: STUB — architectural exploration needed
**Created**: 2026-03-24
**Priority**: MEDIUM (routing optimization is higher priority, but this unblocks full NUMA utilization)
**Blocks**: Nothing currently
**Blocked by**: Routing intelligence Phase 3+ (need quality routing before optimizing infrastructure)
**Related**: [`routing-intelligence.md`](routing-intelligence.md), [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md), [`numa-orchestrator-deployment.md`](numa-orchestrator-deployment.md)

## Problem

The orchestrator stack is statically configured but the optimal configuration depends on runtime conditions. Key tension: **per-request latency vs aggregate throughput**.

### Concrete Scenario

1. User sends a code request to the max-throughput frontdoor (1×30B-A3B spec, 39 t/s)
2. Frontdoor escalates to coder_escalation → architect_coding pipeline
3. While that pipeline is running, user sends a second request
4. The single frontdoor instance is **idle** (waiting for pipeline to return) but the coder/architect are busy
5. Second request could be served immediately by the idle frontdoor — but what if the frontdoor is also busy?

With 4×NUMA instances, request 2 goes to instance 2 via round-robin. With 1×max-throughput, it queues. The right answer depends on how often this happens.

### The Combinatorial Problem

Testing every combination of {model × instance_count × NUMA_config × accel_flags} per role is infeasible:
- 5 roles × 3-4 model options × 1-4 instances × 3 accel configs = thousands of combinations
- Each config takes minutes to deploy and benchmark
- Interactions between roles (memory pressure, core contention) make isolated testing insufficient

## Proposed Approach: Autopilot-Driven Exploration

**Do NOT enumerate all combinations.** Instead:

### 1. Profile-Based Stack Templates (manual, small set)
Define 3-5 stack "profiles" based on usage patterns:

| Profile | Frontdoor | Coder | Architect | Use Case |
|---------|-----------|-------|-----------|----------|
| **fast-serial** | 1×30B-A3B spec (39 t/s) | 1×32B Q4KM (10.8 t/s) | 1×122B | Single-user coding, max per-request speed |
| **balanced** | 2×35B moe6 (25.4 agg) | 2×32B Q4KM (21.6 agg) | 1×122B | Mixed tasks, some concurrency |
| **high-concurrency** | 4×35B moe6 (50.8 agg) | 4×32B Q4KM (43.3 agg) | 1×122B | Multi-session or heavy pipeline |
| **architect-heavy** | 1×35B moe6 | 1×32B Q4KM | 2×122B (8.6 agg) | Complex reasoning, frequent escalation |

### 2. Autopilot NumericSwarm Explores Within Templates
Rather than searching the full combinatorial space, NumericSwarm optimizes **which template to use when** and **continuous params within each template** (draft_max, p_split, moe experts, timeout thresholds).

### 3. Telemetry-Driven Template Selection
Collect per-session metrics:
- Queue depth over time (how often do requests overlap?)
- Escalation rate (how often does frontdoor → coder → architect pipeline fire?)
- Pipeline concurrency (how many models are active simultaneously?)
- Idle core ratio (are NUMA quarters sitting unused?)

These metrics determine which template fits best. The autopilot switches templates at session boundaries.

### 4. KV Cache Transfer (future, enables mid-session switching)
llama-server supports `/slots/save` and `/slots/restore` for KV cache persistence. Extending this to cross-instance transfer would enable:
- Start conversation on fast single-instance
- When second request arrives, transfer first conversation's state to a NUMA instance
- Fast instance handles new request immediately
- Transfer latency: ~1-2s for 68 MB state (acceptable for "redistributing" UX)

This requires ~200-300 lines of C++ for cross-process state transfer. Not needed for template switching but enables the "5-server" design (1 fast + 4 NUMA standby).

## What This Is NOT

- NOT a replacement for routing intelligence (which model handles which task type)
- NOT per-request optimization (too slow to reconfigure)
- NOT exhaustive search of all combinations (use templates + Pareto exploration)

## Key Insight

The routing intelligence autopilot's **top priority is quality routing using debug suites** — getting the right model for each task type. Stack assembly is a **separate optimization axis** that multiplies the routing gains. The two compose but should be developed independently:
- Routing: "this code task should go to coder_escalation" (quality decision)
- Stack: "coder_escalation should have 2 instances on NUMA quarters" (capacity decision)

## Next Steps

1. **Instrument telemetry**: Add queue depth, pipeline concurrency, and idle-core metrics to the orchestrator
2. **Define 3-5 stack templates**: Based on current deployment knowledge
3. **Add template switching to autopilot**: Simple A/B at session boundaries
4. **Benchmark templates**: Each template gets a T0 eval (10 questions, 30s) to establish quality/speed baselines
5. **Longer term**: KV cache transfer for mid-session instance migration

## See Also

- `routing-intelligence.md` § "Dynamic Stack Assembly" — design and tradeoff table
- `autopilot-continuous-optimization.md` § "Future: Dynamic Stack Assembly"
- `numa-orchestrator-deployment.md` — current static deployment
- `src/backends/round_robin.py` — runtime instance routing (supports dynamic backend list)
