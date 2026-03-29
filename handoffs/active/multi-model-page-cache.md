# Handoff: Multi-Model Page Cache Optimization

**Status**: **LARGELY RESOLVED** (2026-03-29). REAP-246B swap reduced model footprint from ~508 GB to ~327 GB (29% of 1.1 TB). With 804 GB free, page cache eviction is no longer a production concern. mlock deployed on all roles as defense-in-depth. Original 480B cold-start problem (185s) eliminated by model removal.
**Created**: 2026-03-19
**Updated**: 2026-03-29
**Priority**: LOW — problem resolved by REAP-246B model swap
**Blocks**: None
**Blocked by**: None — all experiments can run on production stack
**Related**: [`inference-acceleration-index.md`](inference-acceleration-index.md), [`numa-orchestrator-deployment.md`](numa-orchestrator-deployment.md)

## Background

Research intake of flash-moe (intake-166) surfaced a transferable insight: removing application-level model weight caching in favor of OS page cache management gave 38% speedup. Our stack doesn't have app-level caching, but investigation revealed a related opportunity — multi-model page cache contention during concurrent serving of ~650GB of models via mmap.

The EPYC 9655 has ~1.1TB RAM across 2 NUMA nodes. Production serves 5+ models totaling ~650GB (all loaded via mmap). When all models are loaded, they fit in physical memory — but page cache pressure during model loading can evict pages from already-loaded models, causing first-request latency spikes from page faults.

### Production Model Memory Footprint (Updated 2026-03-29)

| Role | Model | Size | NUMA Config | mlock |
|------|-------|------|------------|-------|
| frontdoor | Qwen3.5-35B-A3B Q4KM | 20 GB | 4×48t | YES |
| coder_escalation | Qwen2.5-Coder-32B Q4KM | 18.5 GB | 4×48t | YES |
| architect_general | Qwen3.5-122B-A10B Q4KM | 69 GB | 1×96t node0 | YES |
| architect_coding | **REAP-246B Q4KM** | **139 GB** | 1×96t node0 | YES |
| ingest | Qwen3-Next-80B-A3B Q4KM | 46 GB | 1×96t node0 | YES |
| worker_explore | Qwen3-Coder-30B-A3B Q4KM | 16 GB | 1×48t | YES |
| worker_vision | Qwen3-VL-30B-A3B Q4KM | 18 GB | 1×24t | YES |
| **Total** | | **~327 GB** | | **all mlocked** |

**Previous total (with 480B)**: ~508 GB (45% of 1.1 TB) — page cache eviction was a real problem.
**Current total (with REAP-246B)**: ~327 GB (29% of 1.1 TB) — **804 GB free**, no eviction possible even under full load.

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

### S2 Results: mlock CONFIRMED WORKING

**Container rebuilt with `--ulimit memlock=-1:-1` + privileged mode. mlock now works.**

**Setup**: Frontdoor (30B) loaded FIRST with `--mlock`, then 480B (250 GB) and 235B (130 GB) loaded without mlock. Total: 380 GB of models competing for page cache after frontdoor.

**mlock verification**:
- VmLck = **17.60 GB** (vs 0.00 GB in previous attempt) — pages actually locked
- RSS = 83.16 GB, stable across all 3 phases — never evicted

**Latency comparison (frontdoor)**:

| Phase | Latency | Notes |
|-------|---------|-------|
| warm-baseline (no competition) | 264 ms | Clean system, only frontdoor loaded |
| post-480B (250 GB loaded) | 254-266 ms | **No degradation** |
| post-all (380 GB loaded) | **250-261 ms** | **No degradation** |
| S1 reference (no mlock) | 7,897 ms cold | 30x worse without mlock |

**Unlocked models still show cold-start issues**:
- 480B post-all-1: 9,079 ms (cold), post-all-2: 2,688 ms (warming)
- 235B post-all-1: 8,865 ms (cold), post-all-2: 1,292 ms (warming)

**Conclusion**: `--mlock` completely eliminates page cache eviction for the locked model. The 17.5 GB cost is trivial in a 1.1 TB system. This is the strongest mitigation tested — unlike page-in verification (S3), mlock is not zero-sum.

### S4 Results: NUMA Binding — No Measurable Difference

Tested 3 memory binding strategies with 235B on node1 as cross-NUMA pressure:

| Config | P50 | P95 | P99 | Mean | NUMA placement |
|--------|-----|-----|-----|------|---------------|
| A: taskset only (first-touch) | 922ms | 1091ms | 4415ms | 1009ms | N0=83.11 GB, N1=0.01 GB |
| B: numactl --preferred=0 | 936ms | 1101ms | 4360ms | 1022ms | N0=83.11 GB, N1=0.01 GB |
| C: numactl --membind=0 | 912ms | 1075ms | 4285ms | 996ms | N0=83.11 GB, N1=0.01 GB |

**All configs within noise (~2-3%)**. NUMA page placement is identical — first-touch already puts all pages on the local node when CPUs are pinned via taskset. Hard binding (`--membind`) adds no measurable benefit for models that fit on a single NUMA node.

**Conclusion**: `taskset` alone (current production default) is sufficient. No need to add `numactl --membind` complexity.

### S5: SKIPPED — lower priority than S1-S3. Cooldown tuning unlikely to help when the fundamental issue is total model size (~508 GB) approaching system RAM (~1.1 TB) with competing page cache demands.

### Conclusions

1. **Page cache contention WAS a real production problem** — 480B cold-start of 185 seconds was catastrophic
2. **Root cause was total model footprint (~508 GB) approaching system RAM (~1.1 TB)** — loading one model evicted another's pages
3. **REAP-246B swap (2026-03-29) largely resolves this** — footprint dropped to ~327 GB (29%), leaving 804 GB free. No eviction possible.
4. **mlock deployed on all roles as defense-in-depth** — eliminates eviction even under unexpected memory pressure (30x improvement proven in S2)
5. **Page-in verification (S3) is no longer needed** — was zero-sum at 508 GB, but at 327 GB all models fit comfortably. Could revisit if footprint grows.
6. **NUMA binding (S4) adds nothing** — taskset first-touch already optimal

**Current production mitigations (all deployed):**
- `--mlock` on all server roles (orchestrator_stack.py)
- `ulimit -l unlimited` via container config
- taskset CPU pinning for NUMA locality
- REAP-246B replacing 480B (biggest single improvement: -181 GB)

## Validation Checklist

- [x] S1: Baseline residency measured for 3 production models (480B, 235B, 30B)
- [x] S1: Cold vs warm latency delta quantified — 480B: 185s cold → 8ms warm
- [x] S2: **mlock CONFIRMED** — VmLck=17.6 GB, frontdoor 250ms stable after 380 GB loaded (30x vs no mlock)
- [x] S3: Page-in verification — 14.5x improvement for 480B, but zero-sum with other models
- [x] S4: **No difference** — membind/preferred/first-touch all within 2-3% noise, identical NUMA placement
- [ ] S5: SKIPPED — low priority given root cause analysis
- [x] Results published in progress notes
