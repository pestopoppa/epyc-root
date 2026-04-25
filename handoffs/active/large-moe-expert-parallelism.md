# CPU15 — Large-MoE as Primary Target + Expert Parallelism

**Status**: Intra-process EP exhausted (1a+1b+2, all D3 fails) → **Phase 3.0 IPC prototype validates inter-process EP is viable** (RTT <1 μs, 0.1% token overhead). Phase 3.1+ implementation queued (~2-3 weeks).
**Created**: 2026-04-24
**Updated**: 2026-04-25 (Phase 3.0 IPC prototype landed at /mnt/raid0/llm/cpu-ep-prototype/; GO decision)
**Priority**: HIGH
**Categories**: hardware_optimization, local_inference, moe_optimization, inference_serving
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md)
**Related**:
- [`intra-process-tensor-parallel-decode.md`](intra-process-tensor-parallel-decode.md) (CPU1 — Phase 1.4 substrate reused in Phase 0; Phase 1.2 per-CCD work distribution is the direct substrate for intra-process EP)
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) (CPU2 — Q8_0 AVX-512BW ukernel + auto-mbind stack with EP for Q8 experts)
- [`single-instance-system-tuning.md`](single-instance-system-tuning.md) (CPU3 — NPS4 BIOS state is prerequisite)
- [`orchestrator-nps4-48x4-notes.md`](orchestrator-nps4-48x4-notes.md) (**contention** — NUMA topology is exclusive; see Decision Point D2)
- [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) (candidate model for Phase 0; master-index row 22)
- [`../completed/ssm-hybrid-acceleration.md`](../completed/ssm-hybrid-acceleration.md) (precedent: large-MoE self-draft falsified — EP is a distinct mechanism)
- [`../completed/reap-moe-expert-pruning.md`](../completed/reap-moe-expert-pruning.md) (precedent: expert-level manipulation is tractable)

---

## Objective

Two linked tracks:

**Track A (strategic).** Reframe the primary single-stream CPU inference target from small dense / small hybrid MoE (30B-A3B class) to **large sparse MoE** (≥100B total, ≥10B activated, ≥64 experts). The hypothesis is that the hardware's RAM:BW ratio (1.1 TB : ~460 GB/s theoretical) and 4-way NUMA topology make large sparse MoE near-optimal: total params live in otherwise unused RAM; activated params determine per-token BW; sparse routing naturally parallelises across NUMA nodes.

**Track B (mechanism).** Implement **expert parallelism (EP)** — sharding experts across CCDs / NUMA nodes / processes so a single generation stream exploits aggregate bandwidth currently only available to concurrent requests. The 48×4t concurrent result (~104 t/s aggregate vs 48.81 t/s single-instance, +113% for Qwen3-Coder-30B-A3B Q4_K_M) is proof-of-concept for the available BW delta; EP is the mechanism to convert it to single-stream throughput.

**Expected gain**: 2–5× single-stream throughput on large MoE vs current 1×48t/1×96t baseline, conditional on Phase 0 measurements.

**Why now**: CPU1 Phase 1.4 has shipped (2026-04-24; 48.81 ± 0.08 t/s at 48t with `-fa 1`); CPU3 software levers partially applied; CPU2 AVX-512BW 8×8 Q8_0 kernel + NUMA auto-mbind landed. The master index explicitly states: *"All CPU-general software levers now exhausted on NPS4; next meaningful gate is the L3-as-NUMA BIOS reboot (item 27b)."* Large-MoE EP is the **next open axis** for throughput gains that does not require a BIOS reboot. Phase 0 is also a cheap falsifier — 4–6 hours of measurement settles whether the strategic reframe alone is the answer.

---

## Research Context

| Source | Verdict | Relevance |
|---|---|---|
| User observation 2026-04-24 | origin | Reframe surfaced in conversation — memory-bound single-instance + concurrent-throughput gap ⇒ large sparse MoE is the hardware-matched target |
| `../completed/ssm-hybrid-acceleration.md` (2026-03-18) | precedent (doesn't foreclose) | Large-MoE **self-draft** on Qwen3-235B and 480B measured net-negative (2.9%/55% acceptance, 0.50–0.72× end-to-end). EP is a distinct mechanism — acceptance does not gate it. Reuse 235B/480B baseline measurements for orientation. |
| `../completed/reap-moe-expert-pruning.md` (2026-03-29) | enabler | Expert-level manipulation is tractable in the llama.cpp fork (REAP removes whole experts by router-weighted saliency). Precedent for static per-CCD shard maps. |
| master-index row 22 — [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) (intake-427 revised) | candidate | GLM-5.1-555B-A14B-REAP: 555B / 192 experts / 14B active / ~325 GB Q4_K_M. Storage-gated (~92 GB free). Primary Phase 0 candidate **if** download unblocks. |
| Qwen3-235B-A22B (registry: architect_general) | candidate | 128 experts / top-8 / ~22B active / ~130 GB Q4_K_M. Currently ~6.1 t/s at 1×96t (pre-NPS4 measurement; stale). Phase 0 re-measurement on NPS4 + `GGML_NUMA_WEIGHTS=1` is the cheapest experiment. |
| Qwen3-Coder-480B-A35B (registry: architect_coding, pre-REAP) | candidate | 256 experts / top-20 / ~35B active / ~250 GB. Pre-NPS4 measurement 4.08 t/s at 1×96t. Replaced in prod by REAP-246B but GGUF still on disk. |
| DeepSeek-V3.1 (671B MoE) | uncatalogued | ~350–400 GB Q4_K_M; 256 experts; top-8. Reference-class sparse MoE. Intake entry deferred (requires direct user request per `/workspace/CLAUDE.md`). |
| Kimi-K2 (~1T MoE) | uncatalogued | ~500–600 GB Q4_K_M; may require Q3_K_M for RAM budget. Intake entry deferred (storage + user-approval gated). |

---

## Architecture / Specs

### Hardware substrate

- EPYC 9655 Turin, 96 physical cores, 192 SMT threads
- 12 CCDs, 4 NUMA nodes under NPS4 (3 CCDs per node)
- 1.1 TB DDR5, 12 channels, ~460 GB/s theoretical aggregate BW
- Current NPS4 full-stack single-instance best: **48.81 t/s at 48t** on Qwen3-Coder-30B-A3B Q4_K_M, `-fa 1`, stack `GGML_CCD_POOLS=1 GGML_NUMA_WEIGHTS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1`
- Concurrent 48×4t peak: ~104 t/s aggregate (2.13× single-instance)

### Expert parallelism mechanics — three variants

**Variant 1 — Intra-process per-CCD sharding (Phase 1).**
- One llama.cpp process holds all expert weights.
- `ggml_compute_forward_mul_mat_id` (ggml-cpu.c:1435–1690) modified: expert `e` computed only by threads on CCD(`e mod n_ccd`).
- Router replicated (trivial cost — routers are tiny).
- Expert weight layout reorganised so each expert's matrix is contiguous in the memory of its owning CCD (contrast with current `MPOL_INTERLEAVE` page-striping from Phase 1.3).
- No cross-process communication; reuses CPU1 Phase 1.2 per-CCD work distribution substrate and CPU4 per-CCD barrier (if landed).
- Qwen3-235B-A22B sizing: 128 experts / 12 CCDs ≈ 10–11 experts per CCD; top-8 activation ⇒ ~5–8 CCDs active per token.

**Variant 2 — Inter-process EP (Phase 2).**
- N llama.cpp instances (N=4, one per NUMA node); each holds 1/N of the experts.
- Attention + dense layers **replicated** on all N (cost: ~3× extra RAM for non-expert weights — manageable since experts dominate large-MoE total params).
- Per-MoE-layer flow: all instances run attention + router redundantly → consensus on top-k → dispatch tokens to instances owning chosen experts → each instance computes its expert contributions → gather + combine.
- Communication: shared-memory ring buffers (localhost; no network interconnect).
- Complexity: ~2 synchronisations per MoE layer per token; for a 48-layer MoE ≈ 96 sync points per token.

**Variant 3 — Prefill-only EP (Phase 2 cheap fallback).**
- Full Variant 2 during prefill (many tokens amortise dispatch cost).
- Fall back to single-instance for decode if sync overhead dominates.
- Delivers most of the prefill-latency win without a decode-path scheduler.

### Candidate model sizing

| Model | Total | Active | Experts | top-k | Q4_K_M GB | RAM budget | Phase 0 priority |
|---|---|---|---|---|---|---|---|
| Qwen3-235B-A22B | 235B | ~22B | 128 | 8 | ~130 | fits | **primary** — already in registry, GGUF on disk |
| Qwen3-Coder-480B-A35B | 480B | ~35B | 256 | 20 | ~250 | fits | secondary — GGUF on disk, not in production |
| GLM-5.1-555B-A14B-REAP | 555B | 14B | 192 | 8 | ~325 | fits; storage-gated | tertiary — contingent on `glm51-reap-cpu-evaluation.md` download |
| DeepSeek-V3.1 | 671B | ~37B | 256 | 8 | ~380 | fits | deferred (needs intake + download; user-approval gated) |
| Kimi-K2 | ~1T | ~32B | 384 | 8 | ~550–600 | tight | deferred (storage + quant + user-approval gated) |

---

## Findings / Status Narrative

### 2026-04-24 — Handoff created

Created in response to user observation that memory-bound single-instance decode plus the 2.13× concurrent-aggregate gap imply large sparse MoE is the natural target for this hardware's RAM:BW ratio. No measurements yet for this track — Phase 0 opens the measurement record.

Baselines carried forward from prior work for orientation (not yet re-measured under CPU15 methodology):

| Config | Model | Throughput | Source |
|---|---|---|---|
| 1×48t NPS4 full stack + `-fa 1` | Qwen3-Coder-30B-A3B Q4_K_M | **48.81 ± 0.08 t/s** | CPU1 Phase 1.4 (master-index row 27) |
| 48×4t NPS4 concurrent | Qwen3-Coder-30B-A3B Q4_K_M | ~104 t/s aggregate | `orchestrator-nps4-48x4-notes.md` |
| 1×96t (pre-NPS4) | Qwen3-235B-A22B | ~6.1 t/s | `model_registry.yaml` (stale) |
| 1×96t (pre-NPS4) | Qwen3-Coder-480B-A35B | ~4.08 t/s | `ssm-hybrid-acceleration.md` (stale) |

The pre-NPS4 large-MoE numbers are **stale** — the current NPS4 + `GGML_NUMA_WEIGHTS=1` + AVX-512BW 8×8 Q8_0 kernel stack has never been measured on 235B or 480B. Phase 0 opens with clean re-measurement.

### 2026-04-24 — Phase 0 measurements landed

Two large-MoE candidates available on disk: **Qwen3-Coder-REAP-246B-A35B Q4_K_M** (138 GiB, ~35B active, REAP-pruned 480B) and **MiniMax-M2.7 Q8_0** (226 GiB sharded, 230B total / 10B active). Qwen3-235B-A22B (handoff's primary candidate) is NOT on disk — deferred. Branch `cpu-optimization/q8-8x8-avx512bw` HEAD `ba1c23900` (Session 15) on `build-noomp` with full CPU1 stack + `GGML_NUMA_WEIGHTS=1`.

**Qwen3-Coder-REAP-246B-A35B Q4_K_M thread sweep** (warm cache, `-fa 1 --numa distribute -n 64 -r 3`):

| Threads | t/s | σ |
|---------|-----|---|
| 48 | 6.12 | 0.08 |
| 96 | **6.14** | 0.01 |
| 144 | 5.92 | 0.12 |
| 192 (HT) | 4.37 | 0.17 |

Peak: **6.14 t/s at 96t** — up from pre-NPS4 4.08 on the original 480B (+50% on the new stack). Plateau from 48-144t identical to the 27B Q8_0 pattern → barrier-bound regime is the same.

**MiniMax-M2.7 Q8_0** (warm cache, `-fa 1 --numa distribute -n 64 -r 3`):

| Threads | t/s | σ |
|---------|-----|---|
| 48 | **10.23** | 0.57 |
| 96 | 8.21 | 0.14 |

Peak: **10.23 t/s at 48t** — 96t REGRESSES (unlike REAP-246B). Pre-NPS4 baseline was 11.1 t/s (master-index row 15); current is roughly comparable, slightly under but within noise band.

**Effective BW utilization**:

| Model | Quant | Active GB/tok | t/s @ best | BW achieved | % of 460 ceiling |
|-------|-------|----------------|-----------|-------------|-------------------|
| Qwen3-Coder-REAP-246B (MoE) | Q4_K_M | ~25 | 6.14 (96t) | ~154 GB/s | **33%** |
| MiniMax-M2.7 (MoE) | Q8_0 | ~15 | 10.23 (48t) | ~154 GB/s | **33%** |
| Qwen3.6-27B (hybrid) | Q8_0 | 26.6 | 4.42 (96t) | 117 | 25% |
| Qwen3.6-27B (hybrid) | Q4_K_M | 15.65 | 6.75 (96t) | 106 | 23% |
| Qwen2.5-Coder-32B (pure dense, registry) | Q4_K_M | 18.5 | 10.8 | 200 | 44% |

**Both large-MoE candidates achieve ~33% BW utilization** — meaningfully better than 75% DeltaNet hybrid (25%) but still short of pure dense (44%). The 11-percentage-point gap from MoE to dense is likely architecture overhead (router + gate + expert dispatch ops added to the per-token op count).

### D1 gate decision

Threshold: ≥20 t/s single-stream on the current stack for "strategic reframe alone suffices".

- REAP-246B: 6.14 t/s — **fails** (3.3× short)
- M2.7: 10.23 t/s — **fails** (2× short)

**D1 GATE FAILS** for both available candidates. Phase 1 (intra-process per-CCD EP) is warranted to push beyond the current ~6-10 t/s single-stream ceiling on large MoE.

The reframe direction is **partially validated**: large MoE does extract more BW utilization than hybrid (33% vs 25%), so the hardware IS better-matched to MoE. But to convert the 2.13× concurrent-aggregate gap into single-stream throughput, the EP mechanism needs to be implemented.

Raw data: `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-24-large-moe-baseline/SUMMARY.md` + thread-sweep logs.

---

## Decision Points

- **D1 — Phase 0 go/no-go on the strategic reframe.** Gate: after Phase 0 baseline, if Qwen3-235B-A22B delivers ≥20 t/s single-instance on the current stack, Track A (strategic reframe) is the answer and Track B is deferred. If <20 t/s, proceed to Phase 1. 20 t/s was chosen as the threshold where a 22B-active MoE is competitive per-token with the current 30B-A3B frontdoor (48.81 t/s × 3B / 22B ≈ 6.7 t/s BW-equivalent; 20 t/s represents a ~3× headroom that would make large-MoE production-deployable without EP).

- **D2 — NUMA topology contention with `orchestrator-nps4-48x4-notes.md`.** Concurrent 48×4t and per-NUMA EP are **mutually exclusive occupancy patterns** — only one can own the NUMA topology at a time. Document the decision criterion before Phase 2:
  - Primary workload = multi-user / concurrent request throughput → 48×4t.
  - Primary workload = single-stream agent loops / batch generation → EP.
  - Hybrid (time-sliced) option deferred to Phase 3 orchestrator layer.

- **D3 — Phase 1 → Phase 2 gate.** Phase 1 intra-process per-CCD EP must deliver ≥20% over Phase 0 baseline to justify Phase 2 effort (2–3 weeks). If <20%, Phase 2 is shelved and the strategic reframe stands on Phase 1 alone.

- **D4 — Upstream contribution strategy.** EP kernel changes in the llama.cpp fork must be env-gated (e.g. `GGML_EXPERT_CCD_SHARDING=1`, `GGML_EP_INSTANCE_ROLE=server|client`) so the default build path is unchanged. Matches the CPU1/CPU2 pattern (all novel levers default OFF in our fork; opt-in for rollout caution).

- **D5 — Expert weight layout change.** Intra-process per-CCD sharding requires expert matrix layout reorganisation (each expert contiguous on its owning CCD instead of `MPOL_INTERLEAVE` page-striped). This is invasive — must be env-gated AND bit-exact-validated against baseline PPL (Wikitext-2) before landing. Matches CPU2 Session 15 PPL-preserve gate.

---

## Known Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Phase 0 shows large-MoE throughput is already BW-saturated (experts too large per activation) → EP delivers little | HIGH | Phase 0 is 4–6 h; cheap falsification. D1 gate explicit. |
| Expert layout change breaks llama.cpp fork compatibility with upstream | MEDIUM | Env-gate the layout; keep baseline path intact. Matches CPU1/CPU2 default-OFF pattern. |
| 235B/480B KV cache dominates BW at long context, masking EP gains | MEDIUM | Measure at 2K, 8K, 32K context in Phase 0; EP expectations adjusted per context. |
| GLM-4.7 repetition precedent (43% quality, severe repetition loops) applies to GLM-5.1-REAP | MEDIUM | Quality verification gate already in `glm51-reap-cpu-evaluation.md` — do not commit to GLM-5.1 without passing it. |
| Inter-process EP dispatch cost (~96 sync points / token) exceeds BW gain | MEDIUM | Variant 3 (prefill-only EP) as fallback. D3 gate catches this. |
| Model size > 1.1 TB RAM at Q4 (Kimi-K2 full) | LOW | Drop to Q3_K_M or skip; flag at intake time. |
| Orchestrator 48×4t and EP contend for NUMA topology (D2) | MEDIUM | Decision criterion documented; no simultaneous deployment without Phase 3 time-slicing. |
| Quality regression from expert sharding due to floating-point accumulation ordering | LOW | PPL-preserve gate (Wikitext-2 bit-exact or <0.5% regression) — same as CPU2 Session 15. |

---

## Work Items / Phases

### Phase 0 — Large-MoE baseline on current stack (4–6 h, no code)

- [ ] ~~Re-measure Qwen3-235B-A22B~~ — NOT ON DISK; deferred.
- [x] Re-measure Qwen3-Coder-REAP-246B-A35B Q4_K_M on 48/96/144/192t (REAP-pruned variant of 480B; ~35B active). Peak 6.14 t/s at 96t. ✅ 2026-04-24.
- [x] Re-measure MiniMax-M2.7 Q8_0 on 48/96t (230B total / 10B active, sharded GGUF). Peak 10.23 t/s at 48t. ✅ 2026-04-24.
- [ ] ~~Re-measure Qwen3-Coder-480B-A35B~~ — replaced by REAP-246B in production; raw GGUF not on disk.
- [ ] GLM-5.1-555B-A14B-REAP — not yet downloaded (master-index row 22 storage-gated).
- [x] Compute effective BW utilisation. Both MoE candidates land at **~33% of 460 GB/s** (vs 25% hybrid 27B, 44% pure dense). ✅ 2026-04-24.
- [x] Record under `data/cpu_optimization/2026-04-24-large-moe-baseline/SUMMARY.md`. ✅ 2026-04-24.
- [x] **Gate D1 — FAILS.** Both candidates well below 20 t/s threshold (REAP-246B 6.14, M2.7 10.23). Track B (Phase 1 EP) is warranted. ✅ 2026-04-24.

**Effort**: ~3 h wall-clock (faster than 4-6 h estimate). **No code changes**; reused existing CPU1 Phase 1.4 + CPU2 stack.

### Phase 1 — Intra-process per-CCD EP prototype (3–5 d)

- [x] Branch: `feature/cpu-ep-intra-process` off `cpu-optimization/q8-8x8-avx512bw` (rebased from the originally-planned backlog branch since Session 15 work landed on the q8-8x8 branch). ✅ 2026-04-25.
- [x] Modify `ggml_compute_forward_mul_mat_id` (ggml-cpu.c:1735-1908): assign expert `e` to CCD(`e mod n_ccd`); within-CCD chunking uses ccd_threads instead of nth. ✅ 2026-04-25 (`8d0428a97`).
- [x] Add `GGML_EXPERT_CCD_SHARDING=1` env gate; preserve existing flat work-stealing code path when unset. ✅ 2026-04-25.
- [x] Add expert weight re-layout pass at model load — env-gated `GGML_EXPERT_CCD_LAYOUT=1` in `init_mappings`. Identifies `*ffn_*_exps*` tensors, mbinds each expert's ne[2] slice to NUMA node (e % n_ccd) / n_ccd_per_node with MPOL_MF_MOVE. ✅ 2026-04-25 (`c98c0123c`).
- [x] PPL validation (Wikitext-2): bit-exact (9.3042 ± 0.991 same with/without on REAP-246B Q4_K_M). ✅ 2026-04-25.
- [x] ~~Benchmark Qwen3-235B-A22B~~ — NOT ON DISK. Substituted REAP-246B Q4_K_M (deployed `architect_coding`).
- [x] **Gate D3 — FAILS.** All EP modes (sharding alone, sharding+layout, sharding+replicate+redirect) within ±2% of baseline 6.24 t/s; target was +20%. Root cause: `mbind` on MAP_SHARED file mmap can't reliably move cached pages without CAP_SYS_NICE; per-expert pinning reports success (131.7 GiB pinned in log) but doesn't translate to throughput gain. ✅ 2026-04-25.
- [ ] ~~Findings to research/deep-dives~~ — captured in this handoff's narrative + commit messages instead. Sufficient for the negative result.

**Effort**: ~6 h wall-clock for both Phase 1a + Phase 1b. **Result**: correct + env-gated infrastructure, no measurable throughput gain. The mechanism (per-expert NUMA pinning via mbind) is fundamentally weaker than expected on file-backed mmap. Phase 2 (inter-process or anonymous-mmap expert copies) needed to actually deliver locality.

### Phase 3 — Inter-process EP, full implementation (~2-3 weeks across 3 sub-phases)

The IPC viability question is settled (Phase 3.0, 2026-04-25). Remaining work is engineering, broken into three sub-phases that can land independently.

#### Phase 3.0 — IPC prototype ✅ 2026-04-25

- [x] Standalone master + 4-worker process pool with NUMA-pinned busy-spin sync at `/mnt/raid0/llm/cpu-ep-prototype/` (commit `4901cc7`).
- [x] Pure IPC RTT measured at 0.86 μs (4 workers); fake-compute RTT 3.42 μs; 0.4% projected token overhead.
- [x] GO decision recorded.

#### Phase 3.1 — Extract `ep_dispatcher` library (~1-2 days)

**Goal**: convert the prototype's monolithic `ipc_bench.cpp` into a reusable C-callable library that llama.cpp can link against. Header + impl + unit tests + standalone latency benchmark using the library (validates the API is right).

- [ ] Create `/mnt/raid0/llm/cpu-ep-prototype/ep_dispatcher.h` with C-compatible API:
    - `struct ep_session;` (opaque)
    - `struct ep_config { int n_workers; size_t broadcast_bytes; size_t gather_bytes_per_worker; const int * worker_cpus; const int * worker_numa_nodes; };`
    - `enum ep_role { EP_ROLE_MASTER, EP_ROLE_WORKER };`
    - `int ep_session_create_master(const ep_config *, struct ep_session ** out);` — returns 0 + populates session; forks N worker children that re-enter as `ep_session_attach_worker()`
    - `int ep_session_attach_worker(int instance_id, struct ep_session ** out);` — child returns from fork, attaches to existing shm
    - `void ep_session_destroy(struct ep_session *);` — sends EXIT, joins workers
    - `int ep_broadcast(struct ep_session *, const void * src, size_t bytes);` — master copies src into broadcast region, signals all workers GO
    - `int ep_wait_workers(struct ep_session *);` — master spin-waits for all workers DONE; resets state to IDLE
    - `int ep_gather(struct ep_session *, const void * out_ptrs[]);` — populates `out_ptrs[w]` with read-only pointer to worker w's gather region
    - `int ep_worker_recv(struct ep_session *, void * dst, size_t bytes);` — worker spin-waits for GO, copies broadcast into dst
    - `int ep_worker_send_done(struct ep_session *, const void * src, size_t bytes);` — worker copies src into gather region, signals DONE
- [ ] Create `ep_dispatcher.cpp` with the implementation (refactored from `ipc_bench.cpp`). Build as static library via simple Makefile (no CMake to keep dependencies minimal at this stage).
- [ ] Create `test_ep_dispatcher.cpp`:
    - **Unit test 1** — round-trip latency at n_workers ∈ {1, 2, 4, 8}, broadcast_bytes ∈ {64, 1024, 5120, 32768}. Print stats.
    - **Unit test 2** — bit-exact: master broadcasts deterministic data, workers transform with known function, gather + verify.
    - **Stress test** — 1M iterations to surface any state-machine race.
    - **Failure injection** — kill one worker mid-decode (`SIGKILL`); master should detect within 1 ms and return an error.
    - **Parent-death test** — fork master, master forks workers, kill master; workers should detect (`getppid() == 1` after PR_SET_PDEATHSIG) and exit cleanly.
- [ ] Migrate `ipc_bench.cpp` to use the library (sanity check that the API surface is right; ipc_bench should produce the same RTT numbers as the monolithic prototype).
- [ ] **Gate**: all unit tests pass, parent-death test passes, RTT numbers within 10% of the monolithic prototype.

**Deliverables**: `ep_dispatcher.h`, `ep_dispatcher.cpp`, `test_ep_dispatcher.cpp`, `Makefile`, `libep_dispatcher.a`. Effort: 1-2 days.

#### Phase 3.2 — llama.cpp integration (~1 week)

**Goal**: wire `ep_dispatcher` into llama.cpp so that running with `--ep-role=master --ep-n-instances=4` spawns 4 worker llama.cpp processes that hold 1/4 of the experts each, and the MoE op (`ggml_compute_forward_mul_mat_id`) calls into the dispatcher at expert boundaries.

- [ ] Branch: `llama.cpp-experimental / feature/cpu-ep-inter-process` off `cpu-optimization/q8-8x8-avx512bw`.
- [ ] **CLI args**: extend `common/arg.cpp` with:
    - `--ep-role={none,master,worker}` (default `none`, baseline behavior)
    - `--ep-instance-id N` (worker only; master is implicitly 0)
    - `--ep-n-instances N` (master sets; worker reads from env passed by master)
    - `--ep-master-shm-fd N` (worker only; master passes the shm fd through env or fork inheritance)
- [ ] **Process orchestration** in `llama.cpp` `main`:
    - When master: parse args, init `ep_session_create_master`, fork N-1 workers (master is also instance 0), proceed with model load
    - When worker (post-fork): call `ep_session_attach_worker`, then proceed with model load — but only loading ITS expert shard
    - `prctl(PR_SET_PDEATHSIG, SIGTERM)` in worker so it dies if master crashes
- [ ] **GGUF shard loading** in `llama-model-loader.cpp`:
    - When `cparams.ep_n_instances > 0`: in `init_mappings`, identify expert tensors `*ffn_*_exps*`, and for each tensor, MEMCPY only the experts assigned to this instance into a smaller anonymous buffer (size = per_expert_bytes × experts_for_this_instance). Reassign the tensor's `data` pointer to the shrunk buffer.
    - Non-expert tensors: loaded normally on all instances (~3× extra RAM for non-expert weights, manageable for large MoE where experts dominate).
    - PPL gate after this change with N=1 instance: must be bit-exact to baseline.
    - PPL gate with N=4 instances: must be bit-exact (since each instance only computes its experts; sum-reduce should equal full computation).
- [ ] **Graph executor hook** in `ggml_compute_forward_mul_mat_id`:
    - When `params->threadpool->ep_session != NULL` and op is MoE expert matmul:
      - Master: serialize hidden state into broadcast region via `ep_broadcast`, kick off own assigned experts in parallel, `ep_wait_workers`, `ep_gather`, sum-reduce all instances' partial outputs into final `dst`
      - Worker: when its compute thread enters this op, `ep_worker_recv` to get hidden state, compute its assigned experts, `ep_worker_send_done` with partial result
    - Router op (`*ffn_gate_inp.weight` matmul): same pattern — each instance computes scores for ITS experts, master gathers all scores via dispatcher, computes global top-K, broadcasts top-K assignment to all workers via a second `ep_broadcast` round.
- [ ] **Threadpool integration**:
    - Add `ep_session * ep_session;` field to `struct ggml_threadpool`
    - When set, the `ggml_compute_forward_mul_mat_id` (and router matmul) takes the dispatcher path; otherwise normal path
- [ ] **Output combine**:
    - Each instance produces a partial output for ITS top-K-assigned experts
    - Master sum-reduces N partials into one (the final MoE op output)
    - This requires the worker→master bandwidth in gather region; for hidden_dim=5120 × n_tokens=1 × n_seqs=1 = 20 KB per instance × 4 = 80 KB → trivial
- [ ] **Test plan**:
    - PPL with `--ep-role=master --ep-n-instances=1` (degenerate single-instance) bit-exact to baseline
    - PPL with `--ep-role=master --ep-n-instances=2` bit-exact (or within rounding noise on FP32 sum-reduce)
    - PPL with `--ep-role=master --ep-n-instances=4` bit-exact
    - Throughput: REAP-246B Q4_K_M `--ep-n-instances=4 -t 24` (24 per instance × 4 = 96 total threads). Gate D3': ≥+20% over the 6.16 t/s Phase 0 baseline (target 7.4 t/s minimum; aspirational 12-25 t/s).
    - Robustness: 5-minute sustained decode with no crashes; SIGTERM master and all workers exit cleanly; SIGKILL one worker and master detects + exits within 1 sec.
- [ ] **Gate D3'**: throughput ≥+20% over Phase 0 baseline. Below that → debug or shelve.

**Risks**:
- *GGUF shard load complexity*: existing model loader is heavily mmap-oriented. Cleanest implementation may be a post-load pass that copies kept experts into anon buffers + redirects tensor->data, rather than modifying mmap handling. ~half a day of careful work.
- *Graph executor reentrancy*: the dispatcher path calls `ep_wait_workers` which blocks; meanwhile the compute thread is supposed to be doing work. Solution: master's "own experts" computation runs in parallel with `ep_wait_workers` by structuring the per-thread inner loop to do master-experts first, then wait.
- *Sum-reduce numeric drift*: bit-exact only guaranteed if N=1; with N=4 the partial sum order changes vs single-instance, so FP32 results may differ by ulps. PPL gate accepts <0.5% drift.
- *Worker model load time*: 4 instances each loading 1/4 of expert weights + full non-expert weights. With sequential mlock waits per `feedback_sequential_model_loading.md`, total load is 4× one instance's load. Acceptable for production but slow for dev iteration.

**Deliverables**: feature branch with all changes; throughput + PPL data committed under `data/cpu_optimization/2026-04-XX-cpu-ep-phase3-2/`. Effort: 1 week.

#### Phase 3.3 — Production wiring (~2-3 days)

**Goal**: deploy inter-process EP via `orchestrator_stack.py` so `model_registry.yaml` can declare a `large_moe_ep_pool` backend and the orchestrator launches the master + workers automatically.

- [ ] Extend `model_registry.yaml` schema:
    ```yaml
    models:
      reap_246b_ep4:
        path: /mnt/raid0/llm/models/Qwen3-Coder-REAP-246B-A35B-Q4_K_M.gguf
        backend: large_moe_ep_pool
        ep_config:
          n_instances: 4
          expert_shard_strategy: round_robin  # e mod n_instances
          per_instance:
            - cpuset: "0-23"
              numa_node: 0
            - cpuset: "24-47"
              numa_node: 1
            - cpuset: "48-71"
              numa_node: 2
            - cpuset: "72-95"
              numa_node: 3
          broadcast_buffer_size: 32768
          gather_buffer_size_per_worker: 65536
    ```
- [ ] Extend `orchestrator_stack.py`:
    - New backend type `large_moe_ep_pool` that launches master with `--ep-role=master --ep-n-instances=N`
    - Master spawns workers internally (not orchestrator-managed); orchestrator only tracks the master process
    - Health check: HTTP GET `/health` on master endpoint; master's handler verifies all worker child PIDs are alive (`waitpid(WNOHANG)`)
    - Sequential launch with mlock wait per `feedback_sequential_model_loading`
    - Graceful shutdown: SIGTERM master → master sends EXIT to workers via dispatcher → all exit cleanly
    - Restart policy: any worker death → orchestrator kills master → restart whole group
- [ ] Document in `orchestration/examples/large-moe-ep4.yaml` with an annotated REAP-246B example
- [ ] **D2 resolution**: document the operational decision criterion for choosing between
    - 4×48t concurrent (multi-user throughput) — keep current
    - 4-instance EP (single-stream throughput) — new
    - Hybrid: time-slicing between modes via a workload classifier (deferred — complex; not in this phase)
- [ ] Memory verification: confirm production deployment uses ~138 GiB (file mmap) + ~33 GiB × 4 (per-instance non-expert weights replicated) ≈ 270 GiB total; fits within the 1.1 TiB host RAM with comfortable headroom.

**Deliverables**: orchestrator config schema + backend wired; one annotated example; D2 decision documented. Effort: 2-3 days.

#### Phase 3 totals

- **Phase 3.0**: ✅ done (1 day)
- **Phase 3.1**: ~1-2 days (dispatcher library + tests)
- **Phase 3.2**: ~1 week (llama.cpp integration + measurement)
- **Phase 3.3**: ~2-3 days (production wiring)

**Grand total**: 2-3 weeks of focused work across multiple sessions. Same as the original handoff scope; the IPC-validation step (3.0) eliminates the largest risk (sync overhead).

### Phase 4 — Upstream contribution (opportunistic, post-Phase 3)

- [ ] Upstream PR to ggml-org/llama.cpp for per-CCD intra-process sharding (Phase 1a) — env-gated, default OFF. Even though net-neutral on hybrid MoE, the work-distribution piece is useful infrastructure for other workloads + composes with future fixes.
- [ ] Separate upstream PR for `ep_dispatcher` + inter-process EP if Phase 3 lands and Phase 3.2 PPL/throughput gates pass.
- [ ] Upstream the auto-mbind CPU_REPACK fix (Session 15 part 2 commit `e84a5c82f`) — independent general bug-fix affecting every multi-NUMA repacked quant.

---

## Measurements

Populate as phases execute.

| Date | Phase | Model | Quant | Config | Threads | Context | t/s | BW util | Raw data |
|---|---|---|---|---|---|---|---|---|---|
| 2026-04-24 | P0 | Qwen3-Coder-REAP-246B-A35B | Q4_K_M | NPS4 full stack `-fa 1` | 48 | 2K | 6.12±0.08 | 33% | `data/cpu_optimization/2026-04-24-large-moe-baseline/` |
| 2026-04-24 | P0 | Qwen3-Coder-REAP-246B-A35B | Q4_K_M | NPS4 full stack `-fa 1` | 96 | 2K | **6.14±0.01** | 33% | same |
| 2026-04-24 | P0 | Qwen3-Coder-REAP-246B-A35B | Q4_K_M | NPS4 full stack `-fa 1` | 144 | 2K | 5.92±0.12 | 32% | same |
| 2026-04-24 | P0 | Qwen3-Coder-REAP-246B-A35B | Q4_K_M | NPS4 full stack `-fa 1` | 192 (HT) | 2K | 4.37±0.17 | 24% | same |
| 2026-04-24 | P0 | MiniMax-M2.7 230B-A10B | Q8_0 | NPS4 full stack `-fa 1` | 48 | 2K | **10.23±0.57** | 33% | same |
| 2026-04-24 | P0 | MiniMax-M2.7 230B-A10B | Q8_0 | NPS4 full stack `-fa 1` | 96 | 2K | 8.21±0.14 | 27% | same |
| 2026-04-25 | P1a | Qwen3-Coder-REAP-246B-A35B | Q4_K_M | NPS4 + `GGML_EXPERT_CCD_SHARDING=1` | 96 | 2K | 6.17±0.02 | 33% | `data/cpu_optimization/2026-04-25-large-moe-ep-phase1/` |
| 2026-04-25 | P1a | Qwen3-Coder-REAP-246B-A35B | Q4_K_M | NPS4 + `GGML_EXPERT_CCD_SHARDING=1` | 48 | 2K | 6.25±0.02 | 33% | same |
| 2026-04-25 | P1a+1b | Qwen3-Coder-REAP-246B-A35B | Q4_K_M | NPS4 + EP_SHARDING=1 + EP_CCD_LAYOUT=1 | 96 | 2K | 6.15±0.02 | 33% | same |
| 2026-04-25 | P1+REPL | Qwen3-Coder-REAP-246B-A35B | Q4_K_M | NPS4 + EP_SHARDING + NUMA_REPLICATE + redirect | 96 | 2K | 3.90±0.01 | 21% (replica overhead) | same |
| 2026-04-25 | P2 | Qwen3-Coder-REAP-246B-A35B | Q4_K_M | NPS4 + ANON_COPIES (no SHARDING) | 96 | 2K | 6.13±0.00 | 33% | `data/cpu_optimization/2026-04-25-large-moe-ep-phase2/` |
| 2026-04-25 | P2 | Qwen3-Coder-REAP-246B-A35B | Q4_K_M | NPS4 + EP_SHARDING + EP_ANON_COPIES | 96 | 2K | **5.88±0.01** | 31% (regression) | same |
| 2026-04-25 | P2 | Qwen3-Coder-REAP-246B-A35B | Q4_K_M | NPS4 + EP_SHARDING + EP_ANON_COPIES | 48 | 2K | 5.93±0.02 | 32% (regression) | same |
| | P2 (inter-proc) | Qwen3-Coder-REAP-246B-A35B | Q4_K_M | 4-instance inter-process EP, 4×24t | 24×4 | 2K | TBD | TBD | TBD |

---

## Composition with Other CPU Tracks

| Track | Composition | Expected interaction |
|---|---|---|
| CPU1 (TP) | stacks | TP for dense+attention layers; EP for expert layers — orthogonal |
| CPU2 (AVX-512BW 8×8 Q8_0) | stacks | Q8_0 experts benefit from both EP and shape-specialised GEMV |
| CPU3 (NPS4 / L3aaN) | prerequisite | EP requires NPS4 topology; future L3aaN would expose 12 effective EP nodes instead of 4 |
| CPU4 (per-CCD barrier) | synergy | Phase 1 intra-process EP wants per-CCD barriers; CPU4 infrastructure directly applies |
| CPU8 (per-NUMA weight replication) | convergent | CPU8 and Variant 2 EP both imply per-NUMA weight placement; share implementation substrate |
| [`orchestrator-nps4-48x4-notes.md`](orchestrator-nps4-48x4-notes.md) | **contention** | NUMA topology exclusive — see D2 |
| [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) | feeds candidate | GLM-5.1-REAP is a Phase 0 tertiary candidate if downloaded |

---

## Reporting Instructions

After each phase:

1. Update the `Measurements` table above with date, config, results, raw data path.
2. Append a dated entry to `Findings / Status Narrative`.
3. Update the `Status` field in frontmatter.
4. Update the CPU15 row in `cpu-inference-optimization-index.md` (status, priority, gain-target).
5. Update `progress/2026-04/2026-04-XX.md` with a summary.
6. If a phase gate is hit (D1, D3), add an explicit go/no-go note to the narrative.

---

## Key File Locations

| Purpose | Location |
|---|---|
| Parent index | [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) |
| llama.cpp MoE kernel (CPU) | `/mnt/raid0/llm/llama.cpp/ggml/src/ggml-cpu/ggml-cpu.c:1435–1690` |
| llama.cpp MoE op signature | `/mnt/raid0/llm/llama.cpp/ggml/src/ggml.c:3264–3302` |
| llama.cpp experimental worktree | `/mnt/raid0/llm/llama.cpp-experimental` |
| Orchestrator launcher | `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py` |
| Model registry (full) | `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml` |
| Benchmark data root | `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/` |

---

## Changelog

- **2026-04-24**: Handoff created. Origin: user observation on memory-bound single-instance decode + the 2.13× concurrent-aggregate gap (48.81 → ~104 t/s on 30B-A3B Q4_K_M) ⇒ large sparse MoE is the hardware-matched target. Phase 0 scoped; no measurements yet. Registered as CPU15 in `cpu-inference-optimization-index.md` and master-index row 27c.
- **2026-04-24 (later)**: Phase 0 measurements landed. REAP-246B Q4_K_M peak 6.14 t/s at 96t (+50% over pre-NPS4 480B); M2.7 Q8_0 peak 10.23 t/s at 48t (~comparable to pre-NPS4 11.1). Both at ~33% BW utilization. **D1 gate FAILS** — Phase 1 (intra-process per-CCD EP) work is warranted. Reframe direction partially validated: large MoE extracts more BW than hybrid (33% vs 25%) but doesn't auto-solve to dense's 44%.

- **2026-04-25**: Phase 1a + 1b implementation landed on `feature/cpu-ep-intra-process` branch.
    - Phase 1a (`8d0428a97`): per-CCD expert work distribution in `ggml_compute_forward_mul_mat_id`. Expert e → CCD(e mod n_ccd); within-CCD chunking uses ccd_threads. Default OFF behind `GGML_EXPERT_CCD_SHARDING=1`. Bit-exact correctness verified (Qwen3.6-35B-A3B Q8 PPL 5.5010 ± 0.525 in both modes).
    - Phase 1b (`c98c0123c`): per-expert NUMA pinning via `mbind(MPOL_BIND, MPOL_MF_MOVE)` in `init_mappings`. Identifies expert tensors by name pattern `*ffn_*_exps*`, partitions ne[2] axis, pins each expert's byte range to NUMA node `(e % n_ccd) / n_ccd_per_node`. Default OFF behind `GGML_EXPERT_CCD_LAYOUT=1`. Log line at load time confirms pinning: "expert-ccd-layout: pinned 14880 experts across 186 tensors = 131.7 GiB to 4 NUMA nodes". Bit-exact PPL = 9.3042 ± 0.991 with and without on REAP-246B Q4_K_M.

    **D3 gate FAILS**. Throughput on REAP-246B Q4_K_M 96t with full noomp + CPU1 stack:

    | Config | t/s @ 96t | Δ vs baseline |
    |---|---|---|
    | Baseline (no EP) | 6.24 ± 0.02 | — |
    | `EP_SHARDING=1` | 6.17 ± 0.02 | −1.1% |
    | `EP_SHARDING=1 + EP_CCD_LAYOUT=1` | 6.15 ± 0.02 | −1.4% |
    | `EP_SHARDING=1 + NUMA_REPLICATE=1` + replica redirect | 3.90 ± 0.01 | −37% (replica overhead dominates) |

    Target was +20% over Phase 0 baseline 6.14. Achieved 0% (within noise).

    **Root cause of the negative result**: `mbind(MPOL_MF_MOVE)` on MAP_SHARED file mmap appears NOT to actually relocate cached pages on this kernel/workload. The 14,880 mbind syscalls return success and report 131.7 GiB pinned, but throughput stays unchanged. Linux treats file-backed page-cache pages specially — user-space `MPOL_MF_MOVE` may decline to move pages that the kernel considers "shared" (with the page cache or other potential mappers) without `CAP_SYS_NICE` and `MPOL_MF_MOVE_ALL`.

    The cleaner alternative is **NUMA_REPLICATE-style anonymous-mmap'd expert copies** with redirect, but the existing `GGML_NUMA_REPLICATE=1` infrastructure copies the ENTIRE model 4× (138 GiB → 552 GiB), and even with my mul_mat_id replica redirect added, the overhead of building+holding 4 full replicas regressed throughput to 3.90 t/s.

    **Conclusion**: Phase 1 as implemented (per-expert mbind on file mmap) is correct but the underlying mechanism (file-backed mbind) is too weak to deliver the projected 20%+ gain. The right Phase 2 path is anonymous-mmap'd EXPERT-ONLY copies (not full model) that are first-touched from threads on the target node — then accessed via redirect from `mul_mat_id`. Substantially more code than Phase 1.

    Branch state on `feature/cpu-ep-intra-process` (3 commits ahead of `cpu-optimization/q8-8x8-avx512bw`):
    - `8d0428a97` Phase 1a — per-CCD work distribution (default off)
    - `c98c0123c` Phase 1b — per-expert mbind layout (default off)
    - (revert of REPLICATE redirect that regressed; not committed)

    Code is correct, env-gated, PPL-preserved. It composes cleanly with future Phase 2 work but doesn't move the throughput needle alone.

- **2026-04-25 (later)**: Phase 2 anonymous-mmap-experts approach implemented + measured. Side-steps Phase 1b's file-mmap-mbind limitation by allocating anonymous mmaps per NUMA node sized to hold each node's expert share, mbind'ing each region BEFORE memcpy (so first-touch reliably places pages). Compute-time `mul_mat_id` redirect via `ggml_ep_anon_lookup_()` registry.
    - Commit `9ccb00245` on `feature/cpu-ep-intra-process`. Default OFF behind `GGML_EXPERT_ANON_COPIES=1`. Memory: 131.7 GiB anon (~33 GiB/node avg) for REAP-246B vs 138 GiB file mmap — 95% extra rather than 4× as in `NUMA_REPLICATE`.
    - **Correctness verified**: PPL = 9.3042 ± 0.991 with `EP_SHARDING=1 EP_ANON_COPIES=1`, BIT-EXACT identical to baseline. Load-time log line confirms the 186 expert tensors / 131.7 GiB are split across the 4 nodes correctly.
    - **Throughput on REAP-246B Q4_K_M @ 96t**:

      | Config | t/s | Δ vs baseline |
      |---|---|---|
      | Baseline | 6.16 ± 0.01 | — |
      | `EP_ANON_COPIES=1` (no SHARDING; redirect path inactive) | 6.13 ± 0.00 | −0.5% |
      | `EP_SHARDING=1 + EP_ANON_COPIES=1` (full Phase 2) | 5.88 ± 0.01 | **−4.5%** |

      D3 gate FAILS again. The anon copies are correctly placed (load-time log confirms 33 GiB/node), the redirect fires (PPL bit-exact), but throughput regresses.

    **Why Phase 2 regresses despite correct locality**: post-mortem analysis suggests **load imbalance** is the actual binding constraint for static-modulo expert sharding on this model:

    1. REAP-246B has 80 experts × top-8 active ≈ 10% activation rate per token.
    2. With `e mod n_ccd` assignment: 80 / 12 CCDs ≈ 6.67 experts per CCD.
    3. Top-8 active under random selection: ~8/12 = 0.67 active experts per CCD per token in expectation. Variance is non-trivial — some CCDs get 0 active experts (idle), others get 2 (bottleneck).
    4. Wall time per layer = max-CCD-time. The slowest CCD (with the most active experts) gates the entire layer.
    5. Theoretical BW math: 132 ns avg latency under interleave vs 80 ns local pinned → ~65% speedup possible. Realized: load imbalance + redirect overhead + hardware prefetcher working better on the file mmap's contiguous expert layout than on the strided per-node anon layout → net −4.5%.

    **Phase 2's anon-copies infrastructure is valid; static-modulo expert sharding is the wrong dispatch policy** for top-K sparse activation. The architectural fix is dynamic expert dispatch (observe which experts are active per token, route them to free CCDs), but that's a substantially deeper change.

    **All three intra-process EP variants ship as env-gated, PPL-preserved scaffolding** for the next push (inter-process EP per Phase 2 of the original handoff scope, 2-3 weeks). Not flipped on by default; baseline behavior unchanged.

    Branch state on `feature/cpu-ep-intra-process` (3 commits ahead of `cpu-optimization/q8-8x8-avx512bw`):
    - `8d0428a97` Phase 1a — per-CCD work distribution
    - `c98c0123c` Phase 1b — per-expert mbind layout (no measurable effect; file-mmap limitation)
    - `9ccb00245` Phase 2 — anonymous-mmap'd expert-only NUMA copies + redirect

    PPL bit-exact on all configurations. The intra-process EP track is **exhausted** as a CPU2-style "drop-in kernel improvement" — the remaining theoretical gain (~65% from full local pinning) is gated by the load-imbalance problem, which requires a dispatch-policy redesign rather than a memory-placement fix.

- **2026-04-25 (later)**: **Phase 3.0 IPC prototype landed and validated.** Per user's clarified ask (split BOTH the prerouting pass AND the active expert pass across 4 NUMA-pinned llama.cpp instances cooperating on a SINGLE generation stream — i.e. the original handoff Phase 2 scope, slightly stronger because the router shards too), the next architectural move is full inter-process EP. Standalone prototype at `/mnt/raid0/llm/cpu-ep-prototype/` (commit `4901cc7` in that repo) measures the binding constraint: **can 4 NUMA-pinned processes synchronize fast enough between MoE layers?**

    Setup: master process + 4 worker processes, each pinned to a distinct NUMA node, busy-spinning on cacheline-separated atomic state. Each iteration: master broadcasts hidden state via shared mmap → workers wake, do simulated compute, signal done → master gathers.

    Round-trip latency on EPYC 9655 NPS4:

    | Configuration | Per-iter RTT | Projected token IPC (62 layers × 3 sync rounds) | % of baseline 162 ms/token |
    |---|---|---|---|
    | **Pure IPC (no fake compute)** | **0.86 μs** | **0.16 ms** | **0.1%** |
    | With 5120-float fake compute | 3.42 μs | 0.64 ms | 0.4% |
    | Hidden=32K (huge state) | 16.22 μs | 3.02 ms | 1.9% |
    | Hidden=1024 (small) | 1.60 μs | 0.30 ms | 0.2% |
    | 8 workers (oversubscribed) | 3.89 μs | 0.72 ms | 0.4% |
    | NUMA-unpinned (control) | 3.41 μs | 0.64 ms | 0.4% |

    **Decision: GO for full Phase 3.** Pure IPC RTT is ~200× under the viability threshold (was ≤200 μs; achieved <1 μs). The synchronization primitive is essentially free; the remaining engineering is model-state sharding across processes, not sync optimization.

    **What this validates**:
    - The user's vision (4 NUMA-pinned llama.cpp instances cooperating on one stream, both router and experts split) is architecturally sound.
    - Sync points (broadcast input, exchange router scores, gather expert outputs — ~3 per MoE layer) cost <1 μs each.
    - Pure busy-spin atomic state on cacheline-separated locations beats futex/eventfd at this granularity. Workers burn a CPU but that's exactly the production deployment pattern.

    **What it doesn't yet validate** (deferred to Phase 3.1+):
    - Per-instance memory placement under real load (prototype uses 20 KB broadcast region; real KV+attention spans MB)
    - GGUF shard loading: each instance must load only ITS 1/4 of expert weights (model-loader change)
    - ggml graph executor calling into the IPC primitive at MoE boundaries (custom op or graph-compute callback)
    - Process orchestration: spawn, health-check, graceful shutdown

    Full RESULTS.md + PLAN.md at `/mnt/raid0/llm/cpu-ep-prototype/`. Detailed Phase 3.1+ scope follows in the next section.
