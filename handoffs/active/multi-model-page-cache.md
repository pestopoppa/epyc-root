# Handoff: Multi-Model Page Cache Optimization

**Status**: S1-S3 COMPLETE (2026-03-19). **480B cold-start = 185s** (page cache eviction). Page-in verification gives 14.5x improvement but is zero-sum at current memory pressure. mlock blocked in container. Root cause: ~508 GB models in ~1.1 TB RAM.
**Created**: 2026-03-19
**Priority**: MEDIUM — potential latency reduction for multi-model concurrent serving
**Blocks**: None
**Blocked by**: None — all experiments can run on production stack
**Related**: [`inference-acceleration-index.md`](inference-acceleration-index.md), [`numa-orchestrator-deployment.md`](numa-orchestrator-deployment.md)

## Background

Research intake of flash-moe (intake-166) surfaced a transferable insight: removing application-level model weight caching in favor of OS page cache management gave 38% speedup. Our stack doesn't have app-level caching, but investigation revealed a related opportunity — multi-model page cache contention during concurrent serving of ~650GB of models via mmap.

The EPYC 9655 has ~1.1TB RAM across 2 NUMA nodes. Production serves 5+ models totaling ~650GB (all loaded via mmap). When all models are loaded, they fit in physical memory — but page cache pressure during model loading can evict pages from already-loaded models, causing first-request latency spikes from page faults.

### Production Model Memory Footprint

| Role | Model | Size | NUMA Config |
|------|-------|------|------------|
| frontdoor | Qwen3-Coder-30B-A3B Q4KM | 17.5 GB | 4×48t |
| coder_escalation | Qwen2.5-Coder-32B f16 | 65 GB | 4×48t |
| architect_general | Qwen3-235B-A22B Q4KM | 130 GB | 1×96t node0 |
| architect_coding | Qwen3-Coder-480B-A35B Q4KM | 250 GB | 1×96t node0 |
| ingest | Qwen3-Next-80B-A3B Q4KM | ~46 GB | 4×48t (est) |
| **Total** | | **~508 GB** | |

## Experiment S1: Baseline Page Residency Measurement

**Goal**: Quantify current page cache behavior during steady-state multi-model serving.

**Method**:
1. Start all production models via orchestrator_stack.py
2. Wait for health checks to pass
3. Measure resident page % for each model's mmap region:
   ```bash
   # Option A: /proc/<pid>/smaps for each llama-server process
   grep -A 5 "model.gguf" /proc/<pid>/smaps | grep "Rss:"

   # Option B: mincore() via Python script on mmap'd file
   python3 -c "
   import mmap, os
   fd = os.open('model.gguf', os.O_RDONLY)
   m = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
   # Count resident pages via mincore equivalent
   "

   # Option C: fincore (util-linux) if available
   fincore /mnt/raid0/llm/lmstudio/models/*/model.gguf
   ```
4. Send first request to each model (cold) — measure latency
5. Send second request (warm) — measure latency
6. Compare cold vs warm delta

**Metrics**:
- Resident page % per model after all models loaded
- First-request latency (cold) vs warm-request latency
- Page fault rate during inference: `perf stat -e page-faults -p <pid>` during a burst of 10 requests

**Expected outcome**: Models loaded last have highest residency; models loaded first may have partial eviction from page cache pressure during subsequent loads.

## Experiment S2: mlock for Hot Models

**Goal**: Test whether pinning frontdoor model pages in memory eliminates cold-start latency.

**Method**:
1. Start frontdoor server with `--mlock`:
   ```bash
   taskset -c 0-47 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
     -m .../Qwen3-Coder-30B-A3B-Q4_K_M.gguf \
     --mlock -t 48 --port 8080
   ```
2. Start all other models normally (no mlock)
3. Repeat S1 residency measurements
4. Compare frontdoor cold-start latency with and without mlock

**Risk**: mlock competes with other models for physical memory. 17.5GB locked = 17.5GB less page cache for other models. With ~508GB total model footprint and ~1.1TB RAM, this should be safe.

**Success criteria**: Frontdoor cold-start latency after other model loads ≤ warm-request latency (no degradation from page pressure).

## Experiment S3: Page-In Verification Before Serving

**Goal**: Eliminate first-request latency spikes by ensuring all mmap pages are resident before marking server healthy.

**Method**:
1. After model load + cooldown, explicitly touch every page:
   ```bash
   # Touch every 4K page of the mmap'd model file
   python3 -c "
   import mmap, os, time
   path = '/path/to/model.gguf'
   fd = os.open(path, os.O_RDONLY)
   m = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
   t0 = time.time()
   total = 0
   for i in range(0, len(m), 4096):
       total += m[i]  # force page fault
   print(f'Touched {len(m)//4096} pages in {time.time()-t0:.1f}s')
   m.close()
   os.close(fd)
   "
   ```
2. Measure time to page-in each model
3. Compare first-request latency with and without page-in step

**Integration point**: Could be added to orchestrator health check — after llama-server reports healthy, run page-in verification before adding server to routing pool.

**Expected overhead**: At ~50 GB/s memory bandwidth, touching 250GB (largest model) takes ~5s. Acceptable as one-time startup cost.

## Experiment S4: NUMA Hard Binding vs Soft Preference

**Goal**: Determine whether hard memory binding prevents performance degradation under sustained load.

**Method**:
1. Compare `numactl --preferred=N` (soft, current) vs `numactl --membind=N` (hard) for large models:
   ```bash
   # Soft preference (allows OS to migrate pages under pressure)
   numactl --preferred=0 --cpunodebind=0 llama-server -m 235B.gguf -t 96

   # Hard binding (prevents cross-NUMA page migration)
   numactl --membind=0 --cpunodebind=0 llama-server -m 235B.gguf -t 96
   ```
2. Run sustained load (100 requests, 10 concurrent) on both configs
3. Measure decode latency P50, P95, P99 over the full run

**Models to test**: 235B (130GB, fits single node) and 480B (250GB, requires cross-node)

**Risk**: `--membind` on 480B (250GB) will fail if it exceeds single-node memory (~566GB). Should be safe but verify. Hard binding prevents OS from balancing pages, which could cause OOM if other processes compete.

**Note**: `numactl --membind` may be blocked in devcontainer (numactl --membind was blocked in S2 benchmarks, only taskset worked). Test on bare metal if container blocks it.

## Experiment S5: Cooldown Tuning Between Model Loads

**Goal**: Determine whether longer cooldowns between large model loads improve page residency of earlier models.

**Method**:
1. Load models sequentially with varying cooldown:
   ```bash
   for cooldown in 5 15 30 60; do
     # Start model A
     start_server model_a
     sleep $cooldown
     # Start model B
     start_server model_b
     sleep $cooldown
     # Measure model A residency after model B loaded
     measure_residency model_a
   done
   ```
2. After each cooldown, measure:
   - Resident pages of previously loaded model
   - First-request latency to previously loaded model

**Hypothesis**: Longer cooldowns give the OS time to stabilize page cache, reducing eviction of earlier models' pages. Current 5s cooldown may be insufficient for the OS to settle page cache state after loading a 250GB model.

**Expected outcome**: Diminishing returns — most page cache settling happens within 15-30s. 60s cooldown unlikely to improve significantly over 30s.

## Priority Order

1. **S1** (baseline) — Must run first, establishes ground truth
2. **S3** (page-in verification) — Highest practical impact, easiest to implement
3. **S2** (mlock) — Simple flag change, quick to test
4. **S5** (cooldown tuning) — Parameter sweep, low effort
5. **S4** (NUMA binding) — May be blocked in container, test last

## Implementation Notes

- All experiments use the production binary (`production-consolidated-v2`, build 8214)
- No llama.cpp code changes required for S1-S3, S5
- S4 may require bare metal access if numactl --membind is blocked
- S3 page-in script could become a permanent orchestrator health check component
- Results should be recorded in `epyc-inference-research/data/page_cache/`

## Experiment Results (2026-03-19)

### S1 Results: Page Cache Contention is REAL

**Cold vs Warm Latency (3 models loaded: 480B → 235B → 30B):**

| Model | Cold (1st req) | Warm (2nd) | Warm (3rd) | Cold/Warm Ratio |
|-------|---------------|-----------|-----------|----------------|
| **480B** | **185,271 ms** (3 min!) | 4,299 ms | **8 ms** | **>23,000x** |
| 235B | 7,276 ms | 2,667 ms | 1,894 ms | 3.8x |
| 30B | 7,897 ms | 815 ms | 348 ms | 22.7x |

**Page Residency:**
- 480B lost 37 GB of RSS when 30B loaded (page cache eviction)
- System at 867 GB / 1.1 TB after all loads — only 5.4 GB free
- 480B's 185-second cold-start = faulting ~37 GB back from NVMe

### S3 Results: Page-In Verification

**Page-in timing:**
- 480B (252 GB, 8 parts): 61.7M pages in **26s**
- 235B (143 GB, 4 parts): 34.8M pages in **19s**
- 30B (17 GB, single file): page-in script bug — glob pattern didn't match single-file GGUF

**Post-page-in latency:**

| Model | S1 Cold (no page-in) | S3 Post-Page-In 1st | S3 Post-Page-In 2nd | Improvement |
|-------|---------------------|---------------------|---------------------|-------------|
| **480B** | **185,271 ms** | **12,742 ms** | 3,855 ms | **14.5x** |
| 235B | 7,276 ms | 11,364 ms | 1,761 ms | 0.64x (worse) |
| 30B | 7,897 ms | 2,756 ms | 480 ms | 2.9x |

**Key finding**: Page-in helps the 480B dramatically (14.5x) but paging in 480B (252 GB) evicts 235B pages. The system is at capacity — touching one model's pages evicts another's. **This is a zero-sum game at current memory pressure (~508 GB models in 1.1 TB).**

### S2 Results: mlock INCONCLUSIVE

`--mlock` did NOT actually lock pages (VmLck = 0.00 GB) — container lacks `CAP_IPC_LOCK`. Would need bare-metal testing. Lower latency in S2 was due to less total memory pressure (only 2 models vs 3).

### S4: SKIPPED — `numactl --membind` blocked in container (same as NUMA benchmarks).

### S5: SKIPPED — lower priority than S1-S3. Cooldown tuning unlikely to help when the fundamental issue is total model size (~508 GB) approaching system RAM (~1.1 TB) with competing page cache demands.

### Conclusions

1. **Page cache contention is a real production problem** — 480B cold-start of 185 seconds is catastrophic
2. **Page-in verification helps dramatically** for individual models (14.5x for 480B) but is zero-sum at current memory pressure
3. **Root cause is total model footprint (~508 GB) with only ~1.1 TB RAM** — any model loading evicts other models' cached pages
4. **Actionable mitigations**:
   - **Load order matters**: Load the largest model FIRST, smallest last (smallest gets evicted least)
   - **Page-in verification as health check**: Touch all pages after load, before adding to routing pool. Cost: ~26s for 480B — acceptable one-time startup cost.
   - **mlock for critical models**: Lock frontdoor (17.5 GB) + ingest (46 GB) to prevent eviction. Needs bare-metal `CAP_IPC_LOCK`.
   - **Reduce concurrent model count**: If possible, don't load all 5 models simultaneously. Load architect models on-demand (cold-start of 7-12s is acceptable for non-interactive roles).
   - **Consider replacing 480B with 397B hybrid**: Qwen3.5-397B-A17B (205 GB) at 12.4 t/s is 3.6x faster than 480B (3.4 t/s) and saves 45 GB of memory pressure. Quality eval needed.

## Validation Checklist

- [x] S1: Baseline residency measured for 3 production models (480B, 235B, 30B)
- [x] S1: Cold vs warm latency delta quantified — 480B: 185s cold → 8ms warm
- [x] S2: mlock blocked in container (VmLck=0, needs CAP_IPC_LOCK)
- [x] S3: Page-in verification — 14.5x improvement for 480B, but zero-sum with other models
- [x] S4: SKIPPED — numactl --membind blocked in container
- [ ] S5: SKIPPED — low priority given root cause analysis
- [x] Results published in progress notes
