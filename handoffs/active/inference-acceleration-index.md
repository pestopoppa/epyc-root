# Inference Acceleration — Master Index

**Purpose**: Entry point for autonomous agents navigating inference optimization work across the EPYC stack.
**Created**: 2026-03-17
**Updated**: 2026-03-24

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
| [`numa-orchestrator-deployment.md`](numa-orchestrator-deployment.md) | **DEPLOYED + SWEEP VERIFIED** | NUMA 4-way parallel + taskset | All production models | **6.7x frontdoor** | Update registry with verified params, round-robin routing, worker replacement |
| [`dflash-block-diffusion-speculation.md`](dflash-block-diffusion-speculation.md) | **CONCLUDED** — C++ verified correct | DFlash block diffusion | MoE (frontdoor) | 27% per-token, block 1.4% (expected) | NOT VIABLE on Q4_K_M |
| [`tree-speculation-numa-drafting.md`](tree-speculation-numa-drafting.md) | **Phase 7 COMPLETE** — NUMA 4-way validated | DySpec tree, draft_max, NUMA parallel | **6-7x via NUMA 4-way** on ≤65GB models | +19.4% dm, 6.7x NUMA | See deployment handoff |
| [`ssm-hybrid-acceleration.md`](ssm-hybrid-acceleration.md) | **COMPREHENSIVE** — S2-S5 + sweep + quant | NUMA parallel, quant scaling | Hybrid (Qwen3.5) | **6.9x 35B-A3B**, ~12 t/s ceiling all others | See deployment handoff |
| [`mtp-speculative-decoding.md`](../completed/mtp-speculative-decoding.md) | CLOSED | MTP-1 native heads | Hybrid — NOT VIABLE (0.56x) | N/A | Moved to completed/ |
| [`mathsmith-hc-formalizer-eval.md`](mathsmith-hc-formalizer-eval.md) | **STUB** | HC model eval, A/B formalize→solve | Formalizer (Qwen3-8B) | TBD | Download HC GGUF, remove stale spec decode ban |
| [`reap-moe-expert-pruning.md`](reap-moe-expert-pruning.md) | **246B DEPLOYED** | REAP expert pruning (permanent) | MoE (246B replaces 480B) | **8.0 t/s, 82% quality, 139 GB** | Deployed as architect_coding 2026-03-29. 480B deleted. |
| [`nemotron-mamba2-evaluation.md`](nemotron-mamba2-evaluation.md) | **CONCLUDED — NO ACTION** | Mamba2 MoE (Nemotron-Cascade 2) | Evaluated for all roles | 40.9 t/s (1×48t), 69% quality, 42% IP | Worker beats on every axis. Mamba2 NUMA scaling insight retained. |

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
- **NUMA 4-way parallel** — DEPLOYED 2026-03-19, round-robin routing added 2026-03-24. taskset CPU pinning + `RoundRobinBackend` for multi-instance roles. **Remaining: benchmark 35B 4×48t with moe6+lookup.**
- **draft_max optimization** — +17-21% via `--draft-max 32-48`. Already applied to model_registry.yaml.

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

### Deferred
- **DFlash on f16 targets** — Could work with full-precision hidden states, but not practical on CPU.
- **DFlash tree composition** — Blocked by DFlash viability on quantized models.

## llama.cpp Build Safety Protocol

All inference optimization work in llama.cpp MUST follow these rules:

1. **Branch discipline**: Work ONLY on dedicated feature branches off `production-consolidated-v2`
   - DFlash: `feature/dflash-speculation` branch
   - Worktree at `/mnt/raid0/llm/llama.cpp-dflash`
2. **Never modify `production-consolidated-v2` directly** — it is the production baseline
3. **Production binary protection**: `/mnt/raid0/llm/llama.cpp/build/bin/llama-server` must remain untouched
4. **Build validation**: Run `cmake --build build --target llama-server` and verify clean build before any benchmark
5. **Recovery**: If build breaks on feature branch: `git stash` or `git checkout -- .` — never touch production
6. **Worktree cleanup**: `git worktree remove /mnt/raid0/llm/llama.cpp-dflash` cleans up completely if abandoned

## Key Artifacts

- **DFlash worktree**: `/mnt/raid0/llm/llama.cpp-dflash` on `feature/dflash-speculation` (21 commits, lm_head fix applied)
- **DFlash GGUFs**: `/mnt/raid0/llm/cache/dflash/` (dev + production, with shared embed/lm_head)
- **Acceptance tool**: `tools/dflash-acceptance/` in the worktree
- **MTP tools**: `tools/mtp-acceptance/`, `tools/mtp-speculation/` on `production-consolidated-v2` (committed 2026-03-28)
- **KV cache experimental**: `/mnt/raid0/llm/llama.cpp-experimental` on `hadamard-kv-smoothing` branch
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

| Technique | Primary Handoff | Related Handoffs |
|-----------|----------------|-----------------|
| **NUMA 4-way parallel** | `tree-speculation-numa-drafting.md` (Phase 7) | `ssm-hybrid-acceleration.md` (S2), all production models |
| DySpec tree speculation | `tree-speculation-numa-drafting.md` | Phases 1-6, tree ≈ linear at 48t |
| DFlash block diffusion | `dflash-block-diffusion-speculation.md` | CONCLUDED — not viable on Q4_K_M |
| SSM/hybrid acceleration | `ssm-hybrid-acceleration.md` | NUMA parallel is the answer |
| MTP-1 speculation | `completed/mtp-speculative-decoding.md` | Not viable (0.56x) |
| **Nemotron Mamba2 eval** | `nemotron-mamba2-evaluation.md` | CONCLUDED — 69% quality, no deployment action |

## Production Model Stack — NUMA-Optimized (Updated 2026-03-29)

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
- Modify `production-consolidated-v2` branch or the production binary at `/mnt/raid0/llm/llama.cpp/build/bin/llama-server`
- Delete or overwrite any existing GGUF models
- Push to remote without explicit authorization
- Run benchmarks on the production orchestrator ports (8080-8085)
- Modify any files in `epyc-orchestrator/src/` or `epyc-orchestrator/orchestration/`

### On unexpected results:
- If a test reveals an unexpected result, investigate before moving on — document the finding
- Build failures on feature branch: `git stash`, investigate, fix — never touch production
- If stuck for > 30 minutes on one task, document the blocker and move to the next batch
