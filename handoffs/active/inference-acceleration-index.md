# Inference Acceleration — Master Index

**Purpose**: Entry point for autonomous agents navigating inference optimization work across the EPYC stack.
**Created**: 2026-03-17
**Updated**: 2026-04-11

## Agent Operating Instructions

Every agent working on inference acceleration MUST follow these protocols:

1. **Progress tracking**: After every significant step, update `progress/YYYY-MM/YYYY-MM-DD.md`
2. **Audit logging**: Source `scripts/utils/agent_log.sh` and call `agent_task_start`/`agent_task_end` for every task
3. **Handoff persistence**: Before context compaction risk (~60% usage), persist findings to the relevant handoff document
4. **Master index updates**: If a handoff status changes, update the landscape table below
5. **Documentation**: Extract reusable findings into docs (research chapters, architecture notes) before archiving handoffs

## Inference Handoff Landscape

| Handoff | Status | Techniques | Target Models | Best Gain | Next Action |
|---------|--------|-----------|--------------|-----------|-------------|
| [`llama-cpp-v3-upstream-rebuild.md`](../completed/llama-cpp-v3-upstream-rebuild.md) | **PRODUCTION** — v3 binary live (2026-04-10), hybrid SSM fix (2026-04-11) | Upstream rebase (538 commits), 24 patches cherry-picked | All production | Coder +101%, REAP +50% (spec decode gains) | Deferred: PPL regression, paged attention RSS, NUMA throughput tests |
| [`kv-cache-quantization.md`](../completed/kv-cache-quantization.md) | **ACTIVE** — Hadamard deployed | KV quant, Hadamard smoothing | All production | q4_0 K/f16 V, PPL +0.017 | Monitor upstream TurboQuant #20977. **Note:** `--kv-hadamard` superseded by upstream PR #21038 (commit `744c0c731`, 2026-04-01) — auto-enables in v3. |
| [`triattention-kv-selection.md`](triattention-kv-selection.md) | **DEPLOYED** — full pipeline in production | EA scoring + server endpoint + autopilot control surfaces | All 4 production models | PPL 0.86-1.10 at 50%; safe range [0.50, 0.90] | S4-S7 ✅ DONE. **Next: S8 autopilot exploration** (per-role keep_ratio + layer_weights Pareto sweep) **→ S9 orchestrator auto-trigger** (wire learned profiles into session handler) |
| [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) | **ACTIVE** — L1-L4+L4b merged to production | KV compaction (Attention Matching, latent-space) | Qwen2.5-Coder-32B (target) | 5x compression (zero degradation, validated on 3 models) | L1-L4 ✅ native ggml NNLS+OLS on `production-consolidated-v3`. L4b K-norm scoring. P2 Coder-32B coding benchmarks: needs model server |
| [`mathsmith-hc-formalizer-eval.md`](mathsmith-hc-formalizer-eval.md) | **STUB** | HC model eval, A/B formalize→solve | Formalizer (Qwen3-8B) | TBD | Download HC GGUF, remove stale spec decode ban |
| [`multiscreen-attention-evaluation.md`](multiscreen-attention-evaluation.md) | **ACTIVE** — Diff Attn V2 designed (implementation path mapped; awaiting pretrained checkpoints) | Differential attention (2h Q, even/odd split, sigmoid lambda) | Future Diff Transformer models | ~65% param efficiency (Microsoft claim) | Awaiting pretrained models from Microsoft. Synthetic GGUF loads. MoBA #2 priority. |
| [`gpu-acceleration-path.md`](gpu-acceleration-path.md) | **RESEARCHED** — DGX Spark target | DGX Spark (128GB unified), rocWMMA, CPU+GPU hybrid MoE | All MoE production models | DGX Spark: ~70 t/s MoE decode | Acquire DGX Spark; existing AMD research retained as fallback |
| [`log-linear-gated-deltanet-readiness.md`](log-linear-gated-deltanet-readiness.md) | **STUB** — activates on pretrained model availability | Log-linear O(log L) state for Gated DeltaNet | Qwen3.5/Qwen4 hybrids | 4-10x state reduction, 1M+ context | Monitor github.com/HanGuo97/log-linear-attention |
| [`qwen36-production-upgrade.md`](qwen36-production-upgrade.md) | **IN-PROGRESS** — Q4_K_M+Q8_0 downloaded | Qwen3.6-35B-A3B drop-in architect upgrade | Architect quarter | Terminal-Bench claims pending local validation | Benchmark (AA-Omniscience + coding) then swap in model_registry.yaml |
| [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) (Phase F KVCOMM only — primary ownership: routing-and-optimization) | **QUEUED** — F1 blocks on AM compaction P2; F2-F4 designed | q4_0 offset estimation, cross-NUMA anchor pool, ConcurrencyAwareBackend, `prefill_speedup_coder_pool` metric | All production (cross-NUMA cache sharing) | Compounds with L4b AM compaction ratio | See primary handoff for Phases B-E status; only Phase F is inference-acceleration-relevant |

### Archived (completed/)

| Handoff | Final Status | Key Result |
|---------|-------------|------------|
| [`numa-orchestrator-deployment.md`](../completed/numa-orchestrator-deployment.md) | DEPLOYED | NUMA 4-way: 6.7x frontdoor, all roles multi-instance |
| [`dflash-block-diffusion-speculation.md`](../completed/dflash-block-diffusion-speculation.md) | CONCLUDED | NOT VIABLE on Q4_K_M (27% per-token, AR wins) |
| [`tree-speculation-numa-drafting.md`](../completed/tree-speculation-numa-drafting.md) | COMPLETE | Tree ≈ linear at 48t; NUMA 4-way is the real win |
| [`ssm-hybrid-acceleration.md`](../completed/ssm-hybrid-acceleration.md) | COMPREHENSIVE | NUMA 4-way = 6.9x on MoE; all hybrid accel net negative |
| [`mtp-speculative-decoding.md`](../completed/mtp-speculative-decoding.md) | CLOSED | NOT VIABLE on hybrid (0.56x) |
| [`reap-moe-expert-pruning.md`](../completed/reap-moe-expert-pruning.md) | **246B DEPLOYED** | 82% quality, 8.0 t/s, 139 GB — replaces 480B |
| [`nemotron-mamba2-evaluation.md`](../completed/nemotron-mamba2-evaluation.md) | CONCLUDED | 69% quality, no deployment. Mamba2 NUMA insight retained. |
| [`multi-model-page-cache.md`](../completed/multi-model-page-cache.md) | RESOLVED | Footprint 508→361 GB, mlock deployed, no eviction |
| [`qwen35-frontdoor-benchmark.md`](../completed/qwen35-frontdoor-benchmark.md) | COMPLETE | Stack recommendations executed |

## CRITICAL: draft_max Optimization (2026-03-18)

**+15-20% throughput across ALL production models by changing `--draft-max` from 16 to 32-48.**

| Model | Role | Change | Delta |
|-------|------|--------|-------|
| Qwen3-Coder-30B-A3B | frontdoor | dm 16→32 | **+19.4%** |
| Qwen3-235B-A22B | architect_general | dm 16→32 | **+17.1%** |
| Qwen3-Coder-480B-A35B | architect_coding | dm 16→48 | **+20.6%** |

Zero code changes — parameter-only update in model_registry.yaml.

## CRITICAL: NUMA 4-Way Parallel Discovery (2026-03-18)

**6-7x aggregate throughput on models ≤65GB by running 4×48-thread NUMA-pinned instances.**

Using all 192 threads is ANTI-OPTIMAL — cross-NUMA memory access penalty reduces throughput by 46-60%. Models ≤65GB fit on quarter-machine NUMA splits. 48 threads saturate MoE/hybrid compute.

| Model | Role | Size | 1×192t | NUMA-optimized | Speedup |
|-------|------|------|--------|----------------|---------|
| 30B-A3B Q4KM | frontdoor | 16 GB | 14.2 t/s | **95.8 t/s** (4×48t) | **6.7x** |
| 35B-A3B Q4KM | hybrid | 19 GB | 7.25 t/s | **49.7 t/s** (4×48t) | **6.9x** |
| 32B Q4KM | coder_esc | 18.5 GB | 10.8 t/s | **43.3 t/s** (4×48t) | **4.0x** |
| 235B-A22B Q4KM | architect | 130 GB | 5.19 t/s | **7.87 t/s** (1×96t) | **1.5x** |
| 480B-A35B Q4KM | coding | 250 GB | 3.36 t/s | **4.08 t/s** (1×96t) | **1.2x** |

Config-only change: `taskset -c <cpu_list>` + round-robin routing in orchestrator.

## Immediate Action Items (priority order)

1. ✅ **NUMA tests COMPLETE** — S2 (6.9x), T5 (6.4x), T6 (+41%), production sweep + full Qwen3.5 sweep done
2. ✅ **DFlash investigation CONCLUDED** — C++ verified correct. Not viable on Q4_K_M.
3. ✅ **draft_max changes applied** to model_registry.yaml
4. ✅ **NUMA-aware orchestrator DEPLOYED** (2026-03-19) — taskset pinning, model swaps (frontdoor→Qwen3.5-35B, architect→Qwen3.5-122B)
5. ✅ **S3 DONE** — ALL draft configs net negative on NUMA 4-way hybrid
6. ✅ **S5 Phase 1 DONE** — Prefill pipeline ceiling ~8%, not worth C++ cost
7. ✅ **Qwen3.5 full sweep** — All hybrids converge to ~12 t/s decode. Only 35B-A3B MoE benefits from NUMA 4-way.
8. ✅ **Quant scaling** — Q4_K_M preferred: Q8 costs 17-39% speed on hybrids
9. ✅ **Coder quant quality benchmarks** (2026-03-24) — Q4KM = f16 quality (74%), confirmed optimal. Saves 186 GB RAM.
10. ✅ **Round-robin routing** (2026-03-24) — `RoundRobinBackend` in `src/backends/round_robin.py`. Comma-separated URLs in config. frontdoor + coder distribute across 4 NUMA instances.
11. ✅ **Benchmark 35B NUMA 4-way** (2026-03-24) — measured 12.7 t/s/inst, ~50.8 agg (moe6-only). Lookup needs ngram corpus to activate — without it the 19.6 estimate was wrong. Segfault after 2 prompts (stability issue, not perf).
12. ✅ **Worker NUMA configs** — CLOSED (2026-03-25). Reviewed: worker_explore (39.1 t/s at 48t Q0A) and worker_vision (24t Q0B) already optimal. No actionable improvement found.

## Active Work Streams

### Highest Impact — Deployed
- **NUMA 4-way parallel** — DEPLOYED 2026-03-19, round-robin routing added 2026-03-24. taskset CPU pinning + `RoundRobinBackend` for multi-instance roles. 35B benchmark: 12.7 t/s/inst moe6-only (~50.8 agg). v3 binary live 2026-04-10.
- **draft_max optimization** — +17-21% via `--draft-max 32-48`. Already applied to model_registry.yaml.

### KV Compression Stack (2026-04-13)

Four orthogonal layers, each operating on a different dimension of KV memory:

| Layer | Method | Compression | Status | Handoff |
|-------|--------|-------------|--------|---------|
| **Quantization** | Hadamard + q4_0 | 2-4x | **DEPLOYED** (`b51c905`) | `kv-cache-quantization.md` |
| **Compaction** | Attention Matching | 2-5x validated | P1 ✅, P2 on 7B ✅, **L1-L4+L4b MERGED** to `production-consolidated-v3` (`81c9ad1ec`, `7784b3d9c`). Native ggml NNLS+OLS + K-norm scoring. 5x zero-degradation on 3 models. Remaining: P2 Coder-32B coding benchmarks. | `attention-matching-kv-compaction.md` |
| **Selection** | TriAttention / Expected Attention | 2-10x | S1 scaffold ready, proxy eval cosine=1.000 at 50% (2026-04-13) | `triattention-kv-selection.md` |
| **Block masking** | Memento | 2-3x | S1 feasibility CONFIRMED + runtime validated (2026-04-13). OpenMementos downloaded. | `memento-block-reasoning-compression.md` |

Combined realistic ceiling: **24-60x** (quant 4x × compaction 2-5x × masking 3x). Note: AM compaction achieves 2x universally lossless, 5x at 0.91 cosine. 10x only viable on early layers or long contexts. Compaction subsumes selection at 20x+ — no benefit stacking both.

At 256K context, Qwen2.5-Coder-32B KV at f16 = 64 GB. With 2x AM + 4x quant: **~8 GB**. With full 5x AM + quant + masking: **~1.1 GB**. Even conservative 8x (2x AM × 4x quant): enables 8 concurrent slots vs 1 today.

**Cross-instance KV sharing** (KVCOMM, intake-352): Eliminates redundant prefill across homogeneous worker pools (4×48t coder instances sharing codebase context). Planned as Phase F in `dynamic-stack-concurrency.md`. Compounds with AM compaction.

### Validated & Complete
- **Tree speculation (dense f16)** — +12.2% on Qwen2.5-Coder-32B f16 with dm=32 ps=0.05. At 48 threads per NUMA instance, tree ≈ linear (overhead negated).
- **NUMA single-node pinning** — 1.2-2.3x for all models. Larger models (235B: 1.5x, 480B: 1.2x) benefit less.

### Concluded / Exhausted
- **DFlash block diffusion** — C++ forward pass verified correct via HF comparison. NOT viable on Q4_K_M (27% per-token, 1.4% block). AR drafter wins.
- **All Qwen3.5 hybrid self-acceleration** — 6 approaches tested, all net negative. NUMA parallel decode is the answer.
- **MoE self-draft** — Not viable.
- **MTP-1** — Not viable on hybrid (0.56x).

### Memory Management
- **Multi-model page cache optimization** — [`multi-model-page-cache.md`](multi-model-page-cache.md). ~650GB mmap'd models may cause page cache contention. 5 experiments: baseline residency, mlock for hot models, page-in verification, NUMA hard binding, cooldown tuning.

### Architectural Insights — External Validation (2026-04-10, from GPU research intake-303–311)

Cross-platform performance analysis from AMD GPU benchmarking confirms and extends our CPU findings:

**Decode phase budget (measured on GPU, architecture-independent):**
| Component | % of per-token time | Bound by | EPYC implication |
|-----------|-------------------|----------|------------------|
| Weight GEMMs | 85-92% (short ctx) | Memory bandwidth | Confirms NUMA 4-way is correct — decode is BW-limited, not compute-limited |
| Attention | 7-12% (short ctx) | Memory bandwidth | Flash attention gains negligible at short context |
| Attention | 25-35% (long ctx) | Compute | At 16K+ ctx, flash attention optimization matters — relevant to `ingest_long_context` |
| Attention | >50% (very long, S >> d_model) | Compute | At very long sequences, attention dominates — KV cache compression (kv-cache-quantization) has throughput impact, not just memory |

**External validation of EPYC strategies:**
- **Multi-instance parallelism**: AMD's own MI300X benchmarking recommends "8× TP1 instances for small models" — identical principle to our NUMA 4-way (4×48t instances). Independent confirmation from production GPU deployments.
- **NUMA balancing disabled**: AMD MI300X inference guide independently requires `disable-numa-balancing.sh` on host. Our `taskset` pinning + `--numa distribute` is the CPU equivalent.
- **Batch size transition**: <64 tokens = memory-bound, >64 = compute-bound. Our n_batch/n_ubatch tuning operates in this regime. For decode (batch=1), we are firmly memory-bound — no amount of compute optimization helps.

**New avenue — per-shape GEMM optimization (not yet explored on CPU):**
TensileLite (intake-308) shows 1.6-2.6x gains from generating GEMM kernels tuned to specific matrix shapes (M=3 for single-token decode). The CPU analogy: llama.cpp's ggml CPU kernels use generic GEMM implementations. Per-model-shape tuning at the ggml level (via AMX/AVX-512 intrinsics) could yield similar gains. This is unexplored territory for CPU inference. See `gpu-acceleration-path.md` intake-308 notes.

### Deferred
- **DFlash on f16 targets** — Could work with full-precision hidden states, but not practical on CPU.
- **DFlash tree composition** — Blocked by DFlash viability on quantized models.

## llama.cpp Build Safety Protocol

All inference optimization work in llama.cpp MUST follow these rules:

1. **Branch discipline**: Work ONLY on dedicated feature branches off `production-consolidated-v3` (rebuild completed 2026-04-09 — see [`llama-cpp-v3-upstream-rebuild.md`](../completed/llama-cpp-v3-upstream-rebuild.md))
   - DFlash: `feature/dflash-speculation` branch
   - Worktree at `/mnt/raid0/llm/llama.cpp-dflash`
2. **Never modify `production-consolidated-v3` directly** — it is the production baseline
3. **Production binary protection**: `/mnt/raid0/llm/llama.cpp/build/bin/llama-server` must remain untouched
4. **Build validation**: Run `cmake --build build --target llama-server` and verify clean build before any benchmark
5. **Recovery**: If build breaks on feature branch: `git stash` or `git checkout -- .` — never touch production
6. **Worktree cleanup**: `git worktree remove /mnt/raid0/llm/llama.cpp-dflash` cleans up completely if abandoned

## Key Artifacts

- **DFlash worktree**: `/mnt/raid0/llm/llama.cpp-dflash` on `feature/dflash-speculation` (21 commits, lm_head fix applied)
- **DFlash GGUFs**: `/mnt/raid0/llm/cache/dflash/` (dev + production, with shared embed/lm_head)
- **Acceptance tool**: `tools/dflash-acceptance/` in the worktree
- **MTP tools**: `tools/mtp-acceptance/`, `tools/mtp-speculation/` on `production-consolidated-v2` (committed 2026-03-28)
- **KV cache experimental**: `/mnt/raid0/llm/llama.cpp-experimental` on `production-consolidated-v3` branch (v3 rebuild complete 2026-04-09)
- **Benchmark data**: `epyc-inference-research/data/tree_speculation/`

## Code Commit Log (2026-03-28)

All hybrid acceleration research committed to `production-consolidated-v2` and pushed to `fork` remote:

| Commit | Scope | Size |
|--------|-------|------|
| `ffb4ad4` | MTP-1 inference, MoE self-draft, skip-recurrent draft, clone-cell API, batch allocator fix, GitNexus docs | 20 files, +995/-75 |
| `937bd12` | MTP acceptance/speculation benchmark tools, Claude skills | 10 files, +1088 |
| `f55bf68` | Gitignore (math-tools, bench-kv-block, avx512-helpers.h) | 1 file, +7 |

Working tree clean — ready for KV cache compression work.
- **NUMA benchmark data**: `epyc-inference-research/data/numa_parallel/`, `data/numa_tree_spec/`, `data/numa_production/`, `data/numa_t6_480b/`
- **NUMA benchmark scripts**: `scripts/benchmark/bench_numa_*.sh`
- **DFlash diagnostic venv**: `/home/node/dflash-venv/` (PyTorch 2.10.0 CPU)
- **Devcontainer status**: Rebuilt 2026-03-18 with NUMA access (privileged, numactl --membind blocked but taskset works)

## Pre-Downloaded Models

### DFlash Drafters
Location: `/mnt/raid0/llm/cache/dflash/`

| Model | Path | Params | Block Size | Target Model | Format |
|-------|------|--------|-----------|-------------|--------|
| Qwen3-8B-DFlash-b16 | `/mnt/raid0/llm/cache/dflash/Qwen3-8B-DFlash-b16` | ~1B | 16 | Qwen3-8B | safetensors (pre-GGUF) |
| Qwen3-Coder-30B-A3B-DFlash | `/mnt/raid0/llm/cache/dflash/Qwen3-Coder-30B-A3B-DFlash` | ~0.5B | 16 | Qwen3-Coder-30B-A3B | safetensors (pre-GGUF) |

Registry entries: `epyc-inference-research/orchestration/model_registry.yaml` under `dflash_drafters` section.

## Cross-Reference Map

| Technique | Primary Handoff | Status |
|-----------|----------------|--------|
| **NUMA multi-instance** | `completed/numa-orchestrator-deployment.md` | DEPLOYED — all roles multi-instance |
| **REAP expert pruning** | `completed/reap-moe-expert-pruning.md` | DEPLOYED — 246B replaces 480B |
| **KV cache quantization** | `kv-cache-quantization.md` | ACTIVE — Hadamard deployed, monitoring TurboQuant |
| **KV cache compaction** | `attention-matching-kv-compaction.md` | ACTIVE — L1-L4+L4b merged to production, native ggml compaction. P2 coding benchmarks pending |
| **KV cache selection** | `triattention-kv-selection.md` | ACTIVE — Expected Attention (S1) + TriAttention (S2) evaluation |
| **Cross-instance KV sharing** | `dynamic-stack-concurrency.md` Phase F (F1-F4) | PLANNED — q4_0 offset estimation, anchor pool, ConcurrencyAwareBackend, `prefill_speedup_coder_pool` metric. **Ownership**: routing-and-optimization (primary); Phase F status mirrored in landscape table above for discoverability. |
| Tree speculation | `completed/tree-speculation-numa-drafting.md` | COMPLETE — tree ≈ linear at 48t |
| DFlash block diffusion | `completed/dflash-block-diffusion-speculation.md` | CONCLUDED — not viable on Q4_K_M |
| SSM/hybrid acceleration | `completed/ssm-hybrid-acceleration.md` | COMPREHENSIVE — NUMA is the answer |
| MTP-1 speculation | `completed/mtp-speculative-decoding.md` | CLOSED — not viable (0.56x) |
| Nemotron Mamba2 eval | `completed/nemotron-mamba2-evaluation.md` | CONCLUDED — 69% quality, no action |
| Page cache optimization | `completed/multi-model-page-cache.md` | RESOLVED — 361 GB footprint, mlock deployed |
| **GPU acceleration (future)** | `gpu-acceleration-path.md` | RESEARCHED — DGX Spark target, vLLM DDTree+Dflash speculation plan added (community 91 t/s on Qwen3.5-27B AWQ). Activates on hardware acquisition. |

## Production Model Stack — NUMA-Optimized (Updated 2026-03-29, v3 binary live 2026-04-10)

> **Note**: v3 binary swap (2026-04-10) improved coder +101% and REAP +50% via spec decode gains. Per-instance t/s values below are pre-v3 measurements — actual production throughput is higher.

| Role | Model | Size | NUMA Config | Per-inst t/s | Agg t/s | Accel |
|------|-------|------|------------|-------------|---------|-------|
| frontdoor | **Qwen3.5-35B-A3B Q4KM** | 20 GB | **4×48t** | 12.7 | **~50.8** | moe6 |
| coder_escalation | **Qwen2.5-Coder-32B Q4KM** | 18.5 GB | **4×48t** | 10.8 | **~43.3** | dm=32, ps=0.05, tree+lu |
| architect_general | **Qwen3.5-122B-A10B Q4KM** | 69 GB | **2×96t** | 4.3 | **~8.3** | moe8+spec, dm=24, ps=0 |
| architect_coding | **REAP-246B Q4KM** | **139 GB** | **2×96t** | **8.0** | **16.5** | dm=32, ps=0 |
| ingest_long_context | Qwen3-Next-80B-A3B Q4KM | 46 GB | 1×96t | ~12 | ~12 | SSM, moe4 |
| worker_explore | **Qwen3-Coder-30B-A3B Q4KM** | 16 GB | **4×48t** | **39.1** | **~156** | dm=8, spec+lu |
| worker_vision | Qwen2.5-VL-7B Q4KM | 4 GB | 1×24t | ~24 | ~24 | — |
| vision_escalation | Qwen3-VL-30B-A3B Q4KM | 18 GB | 1×96t | TBD | TBD | — |

**Total footprint**: ~361 GB (330 GB shared weights + 31 GB per-instance KV/compute). 32% of 1.1 TB RAM, 769 GB free. All mlocked.

## Global Test Matrix

Every test the agent should run, across all handoffs. Ordered by priority.

| ID | Handoff | Phase | Model | Test | Priority | Status |
|----|---------|-------|-------|------|----------|--------|
| D0 | dflash | 0 | Qwen3-Coder-30B-A3B-DFlash | Inspect config, document tensors | CRITICAL | ✅ DONE |
| D1 | dflash | 1 | Qwen3-8B-DFlash-b16 | GGUF conversion + load test | CRITICAL | ✅ DONE — loads as Qwen3 |
| D2 | dflash | 1 | Qwen3-Coder-30B-A3B-DFlash | GGUF conversion + load test | CRITICAL | ✅ DONE — LLM_ARCH_DFLASH + key_length override |
| D3 | dflash | 2 | Any target | Hidden state extraction API | CRITICAL | ✅ DONE — API validated, unique per-layer values |
| D4 | dflash | 3 | Qwen3-Coder-30B-A3B + DFlash | Forward pass + acceptance rate | CRITICAL | ✅ **27.0% acceptance** (with RoPE, paper: ~40%) |
| D5 | dflash | 4 | Qwen3-Coder-30B-A3B (frontdoor) | Linear DFlash vs 0.75B AR | CRITICAL | ✅ CONCLUDED — C++ verified correct via HF comparison. Block 1.4% is expected (p=0.27 chain). AR wins: 36.5 t/s. NOT VIABLE on Q4_K_M |
| T1 | tree | done | Qwen3-Coder-480B-A35B Q4_K_M | Tree spec (pair 9) | HIGH | ✅ DONE — -7.6% (5.10→4.71 t/s) |
| T2 | tree | done | Qwen2.5-Coder-32B f16 | Tree spec (pair 10) | HIGH | ✅ DONE — +10.2% (6.05→6.67 t/s) |
| T3 | tree | done | Qwen3-Coder-30B-A3B Q4_K_M (frontdoor) | Tree spec (pair 15) | MEDIUM | ✅ DONE — -13.0% (40.92→35.62 t/s) |
| T4 | tree | done | Qwen2.5-Coder-32B Q8_0 | Tree spec (pair 11) | MEDIUM | ✅ DONE — +0.1% (8.43→8.44 t/s) |
| S2 | ssm | xref | Qwen3.5-35B-A3B Q4_K_M | NUMA parallel decode (1,2,4 concurrent) | MEDIUM | ✅ DONE — **6.9x aggregate** (4×48t: 49.7 t/s vs 1×192t: 7.25 t/s) |
| D6 | dflash | 5 | Qwen3-Coder-30B-A3B (frontdoor) | DFlash tree vs linear | HIGH | CANCELLED — DFlash not viable on Q4_K_M |
| T5 | tree | 7 | Qwen2.5-Coder-32B f16 | NUMA 4-way tree | MEDIUM | ✅ DONE — **6.4x aggregate** (4×48t: 26.4 vs 1×192t: 4.1 t/s). Tree ≈ linear at 48t. |
| T6 | tree | 7 | Qwen3-Coder-480B-A35B Q4_K_M | NUMA node0 + tree | LOW | ✅ DONE — **+41%** (96t node0 tree: 3.82 vs 192t linear: 2.71). BUT sweep corrected: tree HARMFUL (-19%), use dm=24 ps=0 linear only → 7.0 t/s |
| D7 | dflash | 6 | Qwen3.5-35B-A3B (hybrid) | NUMA parallel verify | MEDIUM | CANCELLED — DFlash not viable on Q4_K_M |
| S3 | ssm | 6 | Qwen3.5-35B-A3B Q4_K_M | NUMA 4-way + AR draft (freeze-recurrent) | HIGH | ✅ DONE — **ALL NEGATIVE** (best: -12.5%). Drafter competes for NUMA quarter bandwidth. |
| S4 | ssm | 6 | Qwen3.5-35B-A3B Q4_K_M | NUMA-split draft/verify pipeline | MEDIUM | CANCELLED — S3 shows draft hurts on NUMA 4-way |
| S5 | ssm | 6 | Qwen3-Next-80B-A3B Q4_K_M | NUMA prefill pipeline (long-context) | LOW | ✅ Phase 1 DONE — ceiling ~8% (not worth C++ cost). Decode NUMA-insensitive (12 t/s). |
| — | ssm | 6 | All Qwen3.5 (9B-397B) | Full hybrid NUMA + quant sweep | HIGH | ✅ DONE — All converge ~12 t/s. Only 35B-A3B MoE benefits NUMA. Q4 preferred. |

## Agent Task Ordering (Updated 2026-03-18)

### ALL BENCHMARKS COMPLETE — Summary of Results

| ID | Status | Result |
|----|--------|--------|
| T1-T4 | ✅ DONE | Tree: +10.2% f16, -7.6% to -13% on Q4KM/MoE |
| D0-D5 | ✅ DONE | DFlash: 21 commits, C++ verified correct. NOT viable on Q4_K_M |
| S2 | ✅ DONE | **NUMA 4-way: 6.9x** (hybrid 35B-A3B) |
| T5 | ✅ DONE | **NUMA 4-way: 6.4x** (dense 32B f16). Tree ≈ linear at 48t |
| T6 | ✅ DONE | NUMA node0: +41% vs 192t. Sweep corrected: tree harmful, linear dm=24 → 7.0 t/s |
| D6-D7 | CANCELLED | DFlash not viable |
| S1 | DEFERRED | NUMA prefill pipeline (infrastructure-heavy) |

### Next Priority: Complete NUMA Deployment

1. ✅ **NUMA-pinned launching DEPLOYED** in `orchestrator_stack.py` (2026-03-19, updated 2026-03-24)
   - frontdoor (Qwen3.5-35B, 20GB): 4×48t instances, moe6+lookup, ~19.6 t/s/inst, ~78 agg
   - coder_escalation (32B Q4KM, 18.5GB): 4×48t instances, spec+tree+lu dm=32 ps=0.05, ~43.3 agg
   - architect_general (Qwen3.5-122B, 69GB): 1×96t node0, moe8+spec+lu dm=24, 4.3 t/s
   - architect_coding (480B, 250GB): 1×96t node0, spec+lu dm=24 ps=0 (NO tree), 7.0 t/s
   - worker (30B-A3B, 16GB): 1×24t Q0A, spec dm=8, 39.1 t/s
2. **Add round-robin routing** for multi-instance models (frontdoor ports 8080/8180/8280/8380, coder ports 8081/8181/8281/8381) — requires src/ changes
3. **Benchmark 35B NUMA 4-way** with moe6+lookup to validate aggregate throughput

## Agent Autonomy Charter

### MAY do:
- Discover and execute additional tests not listed here, as long as well-documented in handoffs/progress
- Create additional feature branches if needed (e.g., `feature/numa-parallel-verify`)
- Modify benchmark scripts to add new pairs or test configurations
- Install Python packages needed for conversion (`pip install safetensors transformers`)
- Run any number of benchmarks on any models present on the machine

### MUST do:
- Update `progress/YYYY-MM/YYYY-MM-DD.md` after every significant step
- Update relevant handoff documents with results after every benchmark
- Update this master index landscape table if any handoff status changes
- Log all actions via `source scripts/utils/agent_log.sh`
- Build and validate before any benchmark (clean build = prerequisite)

### MUST NOT do:
- Modify `production-consolidated-v3` branch or the production binary at `/mnt/raid0/llm/llama.cpp/build/bin/llama-server`
- Delete or overwrite any existing GGUF models
- Push to remote without explicit authorization
- Run benchmarks on the production orchestrator ports (8080-8085)
- Modify any files in `epyc-orchestrator/src/` or `epyc-orchestrator/orchestration/`

### On unexpected results:
- If a test reveals an unexpected result, investigate before moving on — document the finding
- Build failures on feature branch: `git stash`, investigate, fix — never touch production
- If stuck for > 30 minutes on one task, document the blocker and move to the next batch

## Research Intake Update — 2026-04-01

### New Related Research
- **[intake-246] "llama.cpp-tq3 — TQ3_1S 3.5-bit Walsh-Hadamard Transform Quantization"** (github.com/turbo-tan/llama.cpp-tq3)
  - **REVISED after deep-dive: DO NOT MERGE.** Immature (3 commits, 1 author, no peer review). Only tested on Qwen3.5-27B vs Q4_0 — no Q4_K_M comparison, no Qwen2.5 benchmarks. Our bottleneck is throughput, not VRAM.
  - **Monitor instead**: (1) ggerganov PR #21038 — Hadamard rotation on existing KV quant types, 25-77% PPL improvement for free. (2) PR #21089 — CPU TurboQuant KV cache, 5.2x compression.
  - **Bonus discovery**: ChunkKV (arXiv:2502.00299) — training-free chunk-level KV compression, retains 12% of cache matching full quality. See `tq3-quantization-evaluation.md` for full monitor list.

## Research Intake Update — 2026-04-07

### New Related Research
- **[intake-281] "GLM-5: from Vibe Coding to Agentic Engineering"** (arxiv:2602.15763)
  - **754B/40B-active MoE, 256 experts, DSA + MTP + MLA. MIT license.**
  - **DSA (Dynamic Sparse Attention)**: Top-k=2048 token selection, 1.5-2x attention reduction on long sequences. NOT complementary to our Hadamard KV-cache work — DSA selects which tokens to attend to, not how KV is compressed. Different problem layer. Relevant to context_extension, not kv_cache.
  - **MTP**: 3-layer multi-token prediction, acceptance length > DeepSeek-V3.2. But our completed/mtp-speculative-decoding.md found MTP NOT VIABLE on hybrid (0.56x). GLM-5 is pure MoE — different architecture class, results don't transfer to our hybrid models.
  - **llama.cpp status**: PR#19460 merged 2026-02-13 but DSA indexer NOT implemented. Model runs dense attention = 11-13 tok/s gen at Q4, PPL 8.75. Impractical without indexer.
  - **REAP-50% exists**: 0xSero/GLM-5-REAP-50pct-FP8 (381B, 128 experts). No GGUF, no benchmarks. Q4 est. ~230GB — borderline but blocked by missing DSA.
  - **GGUF sizes** (unsloth): Q4_K_M=456GB, Q3_K_M=360GB, Q2_K=276GB, UD-IQ2_XXS=241GB. All exceed our working memory budget for full model.
  - **Verdict: NOT ACTIONABLE for local deployment.** Three independent blockers: (1) size, (2) missing DSA in llama.cpp, (3) unknown REAP quality. Monitor for llama.cpp DSA indexer PR.

## Research Intake Update — 2026-04-10

### New Related Research
- **[intake-303] "rocWMMA: C++ Header Library for AMD Matrix Multiply-Accumulate Operations"** (github.com/ROCm/rocWMMA)
  - AMD's header-only library for mixed-precision MMA on CDNA/RDNA GPUs. API-compatible with CUDA WMMA. Supports FP16/BF16/INT8/INT4, 16x16x16 tiles.
  - In llama.cpp: enables flash attention acceleration via `-DGGML_HIP_ROCWMMA_FATTN=ON`. Up to 2x prompt processing speedup. MI300X 8x achieves 4011 tok/s on Llama-70B (213% over H100).
  - **Critical: RDNA3 performance cliff** — decode regresses 58% at 65K ctx. Root cause: decode path incorrectly forces WMMA where VEC/TILE ops are faster. Community fix exists (lhl/llama.cpp rocm-wmma-tune branch) with +96% prefill / +136% decode recovery. Fix NOT in mainline.
  - **Key finding aligned with EPYC research**: WMMA should ONLY be used for prefill, NOT decode — mirrors our finding that decode is memory-bandwidth-bound, not compute-bound.
  - **NOT DIRECTLY APPLICABLE**: EPYC stack is CPU-only (192-thread NUMA). v3 rebuild has no HIP build flags. Would only apply if GPU acceleration path is pursued.
  - **If evaluating GPU path**: hipBLASLt grouped GEMM (`USE_HIPBLASLT_GROUPED_GEMM=1/2/3`) is the higher-impact llama.cpp optimization for MoE models. GEMM tuning yields 29% on 8B model.
  - **GPU acceleration deep-dive** (9 entries, intake-303 through intake-311):

### GPU Path Architecture — If/When a GPU is Added

**Build configuration for HIP backend:**
```
cmake -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx942 -DGGML_HIP_ROCWMMA_FATTN=ON
```
Additional flags: `GGML_HIP_NO_MMQ_MFMA` (disable MFMA for mmq), `GGML_HIP_GRAPHS` (HIP graph capture), `GGML_HIP_NO_VMM` (disable virtual memory).

**Three-tier GPU optimization stack (priority order):**
1. **hipBLASLt Grouped GEMM** [intake-305, intake-308] — Highest impact for MoE. Bundles different-sized matmuls into single kernel launch. 29% improvement on 8B, ~10x reduction in hipMemcpyAsync calls. `USE_HIPBLASLT_GROUPED_GEMM=1/2/3`. CDNA3 only. TensileLite tuning generates custom GEMM kernels per model shape: 1.6-2.6x for skinny decode matrices (M=3), 3.2x average for large matrices.
2. **rocWMMA Flash Attention** [intake-303, intake-304, intake-306] — Enables `-DGGML_HIP_ROCWMMA_FATTN=ON`. ONLY use for prefill, not decode. Adaptive KQ stride (D≤128→stride 128), `__launch_bounds__` for occupancy, intelligent kernel selection. WMMA supports 16x16x16 tiles, FP16/BF16/INT8/INT4. wave32 preferred over wave64 (dual-issue). Known issues: gfx1201 + ROCm 6.4 broken, ROCm 7.2 template specialization conflicts.
3. **Stream-K GEMM scheduling** [intake-309] — Balances workload across CUs when tile count uneven. Eliminates need for per-shape GEMM tuning. Integrated in rocWMMA since ROCm 6.4, expanded to MI350 in ROCm 7.0. Stream-K++ adds Bloom filter selection (95.8% configuration elimination, up to 43% speedup).

**CPU+GPU Hybrid MoE strategy** [intake-310] — **HIGHEST RELEVANCE for EPYC:**
- Expert offloading: `-ot "exps=CPU"` keeps attention + dense FFN on GPU, routes MoE experts to CPU
- Our stack has massive CPU headroom (192 threads, 1.1TB RAM, 769GB free) — ideal for expert compute
- GPU handles attention + shared expert (small, compute-bound) while CPU handles routed experts (large, sparsely activated)
- Combines with existing NUMA 4-way: GPU accelerates attention path, NUMA instances handle expert compute
- Batch sizing: `-b 4096 -ub 4096` (matches our existing tuning)
- Flash attention: `-fa on` with rocWMMA for prefill acceleration
- NUMA: `numactl --interleave=all --numa distribute` (we already do this)
- For our Qwen3.5 MoE models: attention layers small relative to expert FFNs = ideal for GPU offload pattern

**AITER kernel library** [intake-307] — AMD's optimized kernel repo. Key numbers on MI300X: MLA decode 17x, MHA prefill 14x, fused MoE 3x, block-scale GEMM 2x. DeepSeek V3: 6485→13704 tok/s. NOT integrated with llama.cpp (vLLM/SGLang only). But informs achievable performance ceiling. The 17x MLA decode boost is notable — suggests decode CAN be compute-accelerated with MLA architecture, contradicting the "decode is always memory-bound" assumption for standard MHA.

**ROCm version roadmap:**
- ROCm 6.4: Stream-K in rocWMMA, interleaved GEMM, TopK 3x, SDPA optimization
- ROCm 7.0: FP4/FP6/FP8 in hipBLASLt, AITER launch, Stream-K expanded to MI350, Fragment Scheduler API in rocWMMA
- ROCm 7.2: Latest release. Known rocWMMA template specialization bug (fixed in llama.cpp).

**Key performance reference points (MI300X 8x):**
| Model | Config | tok/s | vs H100 |
|-------|--------|-------|---------|
| DeepSeek-V3-671B Q4_K_M | pp4096, no FA | 1,650 | +76% |
| Llama-3.1-70B Q4_K_M | pp4096, FA on | 4,011 | +213% |
| Llama-2-7B Q4_0 | pp512, FA+rocWMMA | 11,946 | — |
| DeepSeek V3 (AITER/vLLM) | end-to-end | 13,704 | — |

**GPU hardware considerations for EPYC:**
- CDNA (MI300X/MI325X): 192GB HBM3, MFMA INT8 acceleration, hipBLASLt grouped GEMM. Datacenter grade.
- RDNA3 (RX 7900 XTX): Consumer, 24GB GDDR6, WMMA FP16 only, 512 FLOPS/clock/CU. Performance cliffs at long context.
- RDNA4 (RX 9070 XT): 16GB, improved WMMA. ROCm 6.4 compilation issues (fixed).
- MI350X/MI355X: ROCm 7.0+ native FP4, 256 CUs, 256MB Infinity Cache. Next-gen.

**Critical architectural insight — decode phase breakdown:**
- Weight GEMMs: 85-92% of per-token time (memory-bandwidth-bound)
- Attention: 7-12% short/mid context, 25-35% long context (compute-bound at long seq)
- At very long sequences (S ≫ model dim): attention exceeds 50% of MACs, transitions to compute-bound
- This means: GPU most beneficial for prefill and long-context attention, not short-context decode
- Our NUMA 4-way remains optimal for short-context decode; GPU would complement for prefill/long-context

## Research Intake Update — 2026-04-17

### New Related Research
- **[intake-387] "Qwen3.6-35B-A3B: Agentic Coding Power, Now Open to All"** (Qwen Team, April 2026)
  - Relevance: **Direct successor to production model Qwen3.5-35B-A3B.** Same Gated DeltaNet + MoE architecture (10×(3×GDN→MoE → 1×Attn→MoE)), 256 experts, 8+1 active. Improved benchmarks: SWE-bench Verified 73.4% (up from 70.0), Terminal-Bench 2.0 51.5% (up from 40.5). New features: preserve_thinking, enhanced tool calling.
  - Key technique: Drop-in architecture upgrade. GGUF quantizations available (unsloth/Qwen3.6-35B-A3B-GGUF). Q4_K_M = 22.1 GB.
  - Reported results: +3.4pp SWE-bench, +11pp Terminal-Bench, +5pp SWE-bench Pro over Qwen3.5.
  - Delta from current approach: Our production stack runs Qwen3.5-35B-A3B. This is a parameter-for-parameter upgrade with the same architecture our llama.cpp fork already supports. **Warrants immediate GGUF benchmark on EPYC hardware.**
- **[intake-391] Qwen3.6-35B-A3B GGUF (unsloth)** (huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF)
  - Relevance: GGUF quantizations ready for llama.cpp. Q4_K_M = 22.1 GB, Q8_0 = 36.9 GB. Full range from IQ1_M (10 GB) to BF16 (69.4 GB).
  - Delta: Removes conversion blocking step — download and benchmark directly.
