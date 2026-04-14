# Parallel Seeding Eval via NUMA Quarter Isolation

**Status**: READY (design complete, not started)
**Created**: 2026-04-14
**Priority**: MEDIUM (2x throughput for AR-3, not blocking)
**Categories**: infrastructure, benchmarking
**Depends on**: None (existing scripts untouched)

---

## Problem

AR-3 evaluates questions sequentially — one at a time through the 3-way pipeline (SELF:direct → SELF:repl → ARCHITECT). With 192 CPU threads and 30 model servers, utilization during seeding is ~13%. Each trial takes 20-40 minutes. Quarter instances (8180-8381) receive zero traffic from seeding.

## Design

Run **2 concurrent eval streams**, each with dedicated ports. No contention, clean speed measurements.

**Why 2, not 4**: architect_general and architect_coding each have only 2 instances.

### Port Assignment

| Stream | frontdoor | coder | worker | architect_gen | architect_code |
|--------|:---------:|:-----:|:------:|:-------------:|:--------------:|
| A | 8080 | 8081 | 8082 | 8083 | 8084 |
| B | 8180 | 8181 | 8182 | 8183 | 8184 |

### New Files (existing scripts untouched)

| File | Purpose |
|------|---------|
| `scripts/benchmark/parallel_seeding.py` | NEW — parallel orchestrator. Imports from existing seeding_eval/orchestrator. Splits questions across 2 streams. ThreadPoolExecutor(2). Thread-safe checkpoint. |
| `scripts/benchmark/seeding_port_sets.py` | NEW — port set definitions (STREAM_A, STREAM_B). |

### Key Details

- Pass `server_urls` dict in ChatRequest to pin each stream to its port set (field already exists)
- Scope slot erasure to stream's own ports only
- Thread lock around checkpoint JSONL writes
- Ingest (1 instance, 8085) could contend — rare in seeding, acceptable

### Expected Impact

- 2x throughput (10-20 min trials instead of 20-40)
- Same quality/speed measurements (no cross-stream contention)
- Fallback: use original `seed_specialist_routing.py` if anything breaks

### Deferred

4-stream parallelism — requires adding 3rd/4th architect instances on remaining NUMA quarters.
