# Bug: Machine-Wide Memory Contention Causing Cascading Backend Timeouts

**Date**: 2026-01-31
**Status**: Resolved (2026-02-11)
**Severity**: Critical (45% error rate on largest model during concurrent workloads)
**Author**: Claude Opus 4.5 (architectural analysis session)

## Summary

When multiple llama-server backends are loaded concurrently on the HOT tier (~535GB across 9 processes), heavy token generation by any single backend triggers machine-wide memory pressure that causes all other backends to stall. These stalls exceed the 300-second timeout ceiling, producing empty results that are silently returned as HTTP 200 OK. The orchestrator has no backpressure, health probing, or failure signaling to detect or mitigate this condition. Error rates correlate with model size: 45% for the 480B model, 24% for the 235B model, 10% for the 30B frontdoor, and 0% for the 32B coder (which runs in isolation during these events).

## Architecture Overview

```
Client Request
    │
    ▼
┌──────────────────────────┐
│  Orchestrator API (:8000)│  ← Single uvicorn worker, sync dispatch
│  FastAPI + httpx          │
└──────────┬───────────────┘
           │  POST /completion (timeout=300s)
           ▼
┌─────────────────────────────────────────────────────────┐
│              llama-server Backend Pool                    │
│                                                          │
│  :8080 frontdoor (30B-A3B)      ~18 t/s                │
│  :8081 coder_escalation (32B)   ~39 t/s (spec decode)  │
│  :8082 worker_explore (7B)      ~44 t/s (spec decode)  │
│  :8083 architect_general (235B) ~6.75 t/s              │
│  :8084 architect_coding (480B)  ~10.3 t/s              │
│  :8085 ingest (80B-A3B)         ~6.3 t/s               │
│  :8086 worker_vision (7B-VL)    ~15 t/s                │
│  :8087 vision_escalation (30B)  ~10 t/s                │
│  :8090 embedder (0.5B)                                  │
│                                                          │
│  ALL processes share 1.13TB DDR5 across 12 channels     │
│  ALL weights mmap'd, KV caches dynamically allocated    │
└─────────────────────────────────────────────────────────┘
```

Request flow:
1. Client sends `POST /chat` to the orchestrator API on port 8000
2. Orchestrator classifies intent, selects backend(s) per the model registry
3. Orchestrator dispatches `POST /completion` to the selected backend with `timeout=300s`
4. Backend's llama-server processes the request: prompt eval → token generation
5. Response returns to orchestrator, which formats and returns to client

For multi-model workflows (e.g., seeding pipelines), the orchestrator issues sequential requests to multiple backends per question.

## The Timeout Chain

The system has a two-layer timeout design, both set to the same 300-second ceiling:

```
Layer 1: Client → Orchestrator API
  httpx.Client(timeout=300s)

Layer 2: Orchestrator API → Backend llama-server
  httpx.Client(timeout=300s)
```

When Layer 2 times out:
- The `httpx.TimeoutException` is caught
- An empty result (0 tokens) is constructed
- This empty result is returned upstream as **HTTP 200 OK**
- The client receives what looks like a successful response with no content

The caller has no way to distinguish "model chose to say nothing" from "backend was unreachable for 5 minutes."

## Root Cause: Shared Physical Memory Contention

All backend processes share the same 1.13TB physical RAM across 12 DDR5 channels. Model weights are memory-mapped; KV caches are dynamically allocated during inference. The failure sequence:

### 1. Trigger: Heavy Token Generation

Any backend generating a large number of tokens (100+ tokens, especially 500+) causes its KV cache to grow significantly. Observed triggers:
- `coder_escalation` generating 501 tokens over 95.6 seconds
- `frontdoor:react` generating 953 tokens

### 2. Propagation: Kernel Memory Management

KV cache growth during generation forces the kernel to:
- Allocate large contiguous memory regions
- Potentially trigger NUMA migration across sockets
- Cause page table contention on shared memory controllers
- Force mmap page-in/page-out for other processes' weight tensors

This is **not** swap — all weights are fully resident (verified: 287GB RssAnon, 0 VmSwap for the 480B model alone). The contention is at the memory controller and page table level.

### 3. Impact: Machine-Wide Stall

The memory pressure affects ALL backends simultaneously, not just the one generating tokens. Evidence:

| Previous Generation | Subsequent Overhead | Scope |
|---------------------|---------------------|-------|
| 2 tokens | ~6 seconds | Local to backend |
| 72+ tokens | ~68 seconds | **Machine-wide** |
| 501 tokens | 300+ seconds (timeout) | **Machine-wide, cascading** |

The ~68-second overhead is invisible to llama-server's own timing (`prompt_ms`, `predicted_ms`). It occurs in kernel space: page table walks, TLB shootdowns, NUMA rebalancing.

### 4. Cascade: Sequential Dispatch Amplification

Because the orchestrator dispatches to backends sequentially with a single worker, a stalled backend blocks all subsequent dispatches. If backend A stalls, backends B, C, D cannot be reached until A either responds or times out at 300s.

## Evidence

### Error Rates by Model Size (from seeding pipeline runs)

| Role | Port | Model Size | Errors/Total | Error Rate |
|------|------|------------|--------------|------------|
| architect_coding | 8084 | 480B (MoE) | 9/20 | **45%** |
| architect_general | 8083 | 235B (MoE) | 5/21 | **24%** |
| frontdoor | 8080 | 30B (MoE) | 3/31 | **10%** |
| coder_escalation | 8081 | 32B (dense) | 0/30 | **0%** |

Error rate correlates with model memory footprint — larger models have more memory-mapped pages competing for bandwidth.

### All Timeouts Hit the Configured Ceiling

Every failed request shows a response time of **300.0–300.1 seconds** with **0 tokens generated**. No partial results. No graceful degradation. The timeout is always the hard cutoff, never an organic slow response.

### Errors Cluster Across ALL Backends Simultaneously

When one backend times out, subsequent backends in the same request pipeline also time out. This rules out per-backend issues (crash, deadlock) and points to a shared resource bottleneck.

### Preceding Trigger: Heavy Token Generation

Every error cluster is preceded by a large token generation event:
- Before 14:41 cluster: `coder_escalation:direct` → 501 tokens, 95.6s
- Before 15:29 cluster: `coder_escalation:repl` → 99 tokens, 80.2s
- Before health check failure: `frontdoor:react` → 953 tokens

### Backends Work Fine in Isolation

Direct test of the 480B model (port 8084) with no concurrent load:
- **Response time**: 2 seconds
- **Generation speed**: 6.2 t/s
- **Prompt eval**: 898ms

The model itself is healthy. The problem is purely contention under concurrent multi-backend workloads.

### All Weights Fully Resident

For the 480B model process:
- `RssAnon`: 300,671,728 kB (~287GB) — all weights resident
- `VmSwap`: 0 kB — zero swap usage
- `RssFile`: 13,276 kB — negligible file-backed pages

This confirms the stalls are not caused by swap thrashing or cold page faults on model weights.

## Architectural Issues

### 1. Silent Failure Propagation

Timeouts produce empty results returned as HTTP 200 OK. No error code, no retry header, no indication of failure. Downstream consumers (seeding pipeline, REPL, UI) interpret this as "model had nothing to say" rather than "backend was unreachable."

### 2. No Backpressure Mechanism

The API gateway accepts all incoming requests regardless of backend health state. During a memory pressure event, new requests pile up behind stalled backends, compounding the problem. There is no admission control, no queue depth limit, no load shedding.

### 3. No Health-Aware Routing

The orchestrator dispatches based solely on task type → model role mapping. It does not check whether the target backend is currently responsive, under load, or in a degraded state. A simple pre-flight health check would avoid dispatching to stalled backends.

### 4. Single-Threaded Gateway with Head-of-Line Blocking

The orchestrator runs a single uvicorn worker making synchronous `httpx` calls to backends. If backend A stalls for 300s, no other request can be processed during that window — even requests destined for healthy backends B, C, D. This turns a single-backend stall into a system-wide outage.

### 5. Uniform Timeout Across All Roles

All backends share the same 300-second timeout ceiling regardless of expected latency profile:
- The 7B worker (expected: <5s) gets the same timeout as the 480B architect (expected: 30-60s)
- A 300s timeout on a 7B model should never occur in healthy operation — it's a strong signal of infrastructure failure, but the system treats it identically to a slow 480B response

### 6. No KV Cache Memory Budgets

Each llama-server process can grow its KV cache without limit. There is no per-process memory budget, no coordination between processes about total memory usage, and no mechanism to signal "approaching memory pressure" before it becomes critical.

## Proposed Architectural Mitigations

Ranked by expected impact and implementation feasibility:

### 1. Backend Health Probing + Circuit Breaker (High Impact)

Add a lightweight health probe (e.g., `/health` endpoint check every 5s) for each backend. Implement circuit breaker pattern: after N consecutive failures or timeouts, mark the backend as "open" (unavailable) and skip it for a cooldown period. Return an explicit error (503) to the caller instead of silently returning empty results.

### 2. Request Queuing with Admission Control (High Impact)

Add a bounded request queue in front of the gateway. When queue depth exceeds a threshold, reject new requests with 429 (Too Many Requests) or 503. This prevents request pile-up during memory pressure events and gives the system time to recover.

### 3. Differentiated Timeouts per Role (Medium Impact)

Set timeouts proportional to expected response time per model role:
- Workers (7B): 30s timeout
- Frontdoor (30B): 60s timeout
- Coder escalation (32B): 120s timeout
- Architects (235B/480B): 300s timeout

A 7B model timing out at 30s is a clear infrastructure failure signal that can trigger immediate circuit-breaking.

### 4. KV Cache Memory Budgets per Backend (Medium Impact)

Configure `--ctx-size` limits per backend to cap KV cache growth. Coordinate total memory allocation across all backends to stay within ~80% of physical RAM, leaving headroom for kernel page management. This addresses the root cause but requires careful tuning.

### 5. Explicit Failure Signaling (Medium Impact)

Replace silent 200 OK on timeout with appropriate HTTP error codes:
- 504 Gateway Timeout when backend doesn't respond within the timeout
- 503 Service Unavailable when circuit breaker is open
- Include structured error metadata: which backend, how long the wait was, whether retryable

### 6. Async Dispatch with Concurrent Backend Calls (Medium Impact)

Replace synchronous sequential dispatch with async concurrent calls. When a multi-backend workflow needs backends A, B, C — dispatch to all simultaneously instead of sequentially. A stall on backend A no longer blocks the dispatch to backends B and C.

### 7. NUMA-Aware Process Pinning (Low-Medium Impact)

Pin each llama-server process to a specific NUMA node to reduce cross-socket memory access. The EPYC 9655 has multiple NUMA domains; unpinned processes cause TLB shootdowns and remote memory access when the kernel migrates pages across sockets. This reduces (but doesn't eliminate) the memory controller contention.

## Reproduction Steps

1. Start the full HOT tier stack:
   ```bash
   python3 scripts/server/orchestrator_stack.py start --hot-only
   ```
2. Verify all backends are responsive:
   ```bash
   python3 scripts/server/orchestrator_stack.py status
   ```
3. Run the seeding pipeline, which dispatches to multiple backends per question:
   ```bash
   python3 scripts/benchmark/seed_specialist_routing.py
   ```
4. Monitor for 300-second timeouts in the orchestrator logs. They will cluster after any backend generates 100+ tokens.
5. Verify with direct backend test during a stall event:
   ```bash
   # This will respond in ~2s even while the orchestrator shows timeouts
   curl -s http://localhost:8084/completion \
     -d '{"prompt": "Hello", "n_predict": 10}'
   ```
   (Direct test bypasses the gateway's head-of-line blocking and typically hits the backend during a window between memory pressure spikes.)

## Resolution (2026-02-11)

All 7 proposed mitigations implemented:

| # | Mitigation | Status | Files |
|---|-----------|--------|-------|
| 1 | Circuit breaker | Already done (post-handoff) | `health_tracker.py`, `inference.py` |
| 2 | Admission control | **New** — per-backend semaphore limits | `src/api/admission.py` (new), `inference.py`, `state.py` |
| 3 | Differentiated timeouts | **New** — workers 30-60s, architects 600s | `model_registry.yaml`, `config.py` |
| 4 | KV cache budgets | **New** — ctx-size per role + q8_0 KV for architects | `orchestrator_stack.py` |
| 5 | Explicit failure signaling | **New** — HTTP 502/503/504/429 instead of silent 200 | `chat.py`, `stages.py` |
| 6 | Head-of-line blocking | **New** — uvicorn workers 2→6, --limit-concurrency 4 | `orchestrator_stack.py` |
| 7 | NUMA-aware placement | **New** — `--preferred=N` for architects | `orchestrator_stack.py` |

Key behavioral changes:
- Workers time out in 60s (was 600s) → circuit opens 10x faster
- Error responses return proper HTTP status codes (502/503/504) with Retry-After headers
- Architect backends limited to 1 concurrent request (admission control)
- Architect KV cache reduced (16384/8192 ctx-size + q8_0 quantized keys)
- 6 uvicorn workers absorb concurrent stalls (was 2)
- Architects pinned to preferred NUMA nodes to reduce page migration

## Related

- `handoffs/active/orchestration-architecture-roadmap.md` — Broader architecture redesign
- `handoffs/active/orchestrator-architecture-review.md` — Code-level review findings (S8: no circuit breakers)
- `handoffs/active/orchestrator-quality-roadmap.md` — Quality improvements roadmap
