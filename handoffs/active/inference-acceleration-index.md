# Inference Acceleration — Master Index

**Purpose**: Entry point for autonomous agents navigating inference optimization work across the EPYC stack.
**Created**: 2026-03-17
**Updated**: 2026-03-18

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
| [`dflash-block-diffusion-speculation.md`](dflash-block-diffusion-speculation.md) | **UNBLOCKED** (19 commits, multi-token fix ready) | DFlash block diffusion + tree | Dense/MoE (frontdoor, architects) | ~4.6 expected/block (paper: 6.49) | Rebuild + block-mode server test |
| [`tree-speculation-numa-drafting.md`](tree-speculation-numa-drafting.md) | T1-T4 + draft_max optimized | DySpec tree, draft_max tuning | **+17-21% via draft_max on 3 prod models** | +19.4% frontdoor | Apply registry changes |
| [`ssm-hybrid-acceleration.md`](ssm-hybrid-acceleration.md) | Exhausted, Phase 4 UNBLOCKED | MoE self-draft, attn-only, tree, MTP | Hybrid (Qwen3.5) | +5.4% (ext draft only) | NUMA-parallel reopener |
| [`mtp-speculative-decoding.md`](../completed/mtp-speculative-decoding.md) | CLOSED | MTP-1 native heads | Hybrid — NOT VIABLE (0.56x) | N/A | Moved to completed/ |

## CRITICAL: draft_max Optimization (2026-03-18)

**+15-20% throughput across ALL production models by changing `--draft-max` from 16 to 32-48.**

| Model | Role | Change | Delta |
|-------|------|--------|-------|
| Qwen3-Coder-30B-A3B | frontdoor | dm 16→32 | **+19.4%** |
| Qwen3-235B-A22B | architect_general | dm 16→32 | **+17.1%** |
| Qwen3-Coder-480B-A35B | architect_coding | dm 16→48 | **+20.6%** |

Zero code changes — parameter-only update in model_registry.yaml.

## Immediate Action Items (priority order)

1. **DFlash block-mode server test** (highest priority)
   - Devcontainer is rebuilt with OMP_NUM_THREADS fix + build tools (cmake, build-essential)
   - `cd /mnt/raid0/llm/llama.cpp-dflash && cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build --target llama-server -j$(nproc)`
   - Run server with DFlash drafter, send request, check draft acceptance rate in logs
   - Per-token acceptance is 28.8% — block-mode should give ~4.6 accepted per 16-token block
   - If block acceptance is still low, check the "Known Bugs" section at the bottom of `dflash-block-diffusion-speculation.md`
   - Key bugs to verify: multi-token conditioning (`n_ctx_tokens > 1` in cross data), graph rebuild on cross dimension change

2. **Apply production draft_max changes** (ready to deploy)
   - `frontdoor`: add `draft_max: 32` (+19.4%)
   - `architect_general`: add `draft_max: 32` (+17.1%)
   - `architect_coding`: add `draft_max: 48` (+20.6%)
   - In `epyc-orchestrator/orchestration/model_registry.yaml`

3. **NUMA tests** (if on bare metal)
   - T5/T5b/T6: tree speculation on NUMA dual-node
   - S2: NUMA parallel decode

## Active Work Streams

### Viable & In Progress
- **DFlash block diffusion** — Only confirmed drafter: `z-lab/Qwen3-Coder-30B-A3B-DFlash` (0.5B) for frontdoor model. Requires GGUF conversion + hidden state extraction API in llama.cpp. Projected 2-4x on dense/MoE targets.
- **Tree speculation (dense f16)** — +15.8% validated on Qwen2.5-Coder-32B f16. Tree infrastructure ready for DFlash composition.

### Exhausted (No Further Work)
- **All Qwen3.5 hybrid self-acceleration** — 6 approaches tested (MoE self-draft, attn-only, tree×3, MTP-1), all net negative. Fundamental limit: 75% Delta Net recurrent layers process tokens sequentially regardless of batch size.
- **MoE self-draft** — 2.9% acceptance (1-expert), 55% (2-expert). Net throughput always negative.

### Deferred / Conditional
- **NUMA-parallel verification** — Could reopen hybrid acceleration if aggregate throughput from parallel single-token decodes across NUMA nodes exceeds serial.
- **DFlash tree composition** — DFlash top-k logits → DySpec tree → tree verification. Depends on DFlash Phase 3.

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

- **DFlash worktree**: `/mnt/raid0/llm/llama.cpp-dflash` on `feature/dflash-speculation` (19 commits)
- **DFlash GGUFs**: `/mnt/raid0/llm/cache/dflash/` (dev + production, with shared embed/lm_head)
- **Acceptance tool**: `tools/dflash-acceptance/` in the worktree
- **Benchmark data**: `epyc-inference-research/data/tree_speculation/`
- **Devcontainer status**: Rebuilt 2026-03-18 with `build-essential`, `cmake`, OMP_NUM_THREADS fix, wildcard `safe.directory`

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
| DFlash block diffusion | `dflash-block-diffusion-speculation.md` | `tree-speculation-numa-drafting.md` (tree composition) |
| DySpec tree speculation | `tree-speculation-numa-drafting.md` | `dflash-block-diffusion-speculation.md` (DFlash as tree builder) |
| SSM/hybrid acceleration | `ssm-hybrid-acceleration.md` | `dflash-block-diffusion-speculation.md` (NUMA reopener) |
| MTP-1 speculation | `completed/mtp-speculative-decoding.md` | `ssm-hybrid-acceleration.md` (Phase 5) |

## Production Model Stack

| Role | Model | Architecture | Speculation Status |
|------|-------|-------------|-------------------|
| frontdoor | Qwen3-Coder-30B-A3B | Pure MoE | DFlash drafter available, AR drafter active (0.75B) |
| coder_escalation | Qwen2.5-Coder-32B | Dense | Tree +15.8% (f16), no DFlash drafter yet |
| architect_general | Qwen3-235B-A22B | Pure MoE | No DFlash drafter yet |
| architect_coding | Qwen3-Coder-480B-A35B | Pure MoE | No DFlash drafter yet |
| ingest_long_context | Qwen3-Next-80B-A3B | Hybrid (Delta Net) | HYBRID WALL — all speculation approaches exhausted |

## Global Test Matrix

Every test the agent should run, across all handoffs. Ordered by priority.

| ID | Handoff | Phase | Model | Test | Priority | Status |
|----|---------|-------|-------|------|----------|--------|
| D0 | dflash | 0 | Qwen3-Coder-30B-A3B-DFlash | Inspect config, document tensors | CRITICAL | ✅ DONE |
| D1 | dflash | 1 | Qwen3-8B-DFlash-b16 | GGUF conversion + load test | CRITICAL | ✅ DONE — loads as Qwen3 |
| D2 | dflash | 1 | Qwen3-Coder-30B-A3B-DFlash | GGUF conversion + load test | CRITICAL | ✅ DONE — LLM_ARCH_DFLASH + key_length override |
| D3 | dflash | 2 | Any target | Hidden state extraction API | CRITICAL | ✅ DONE — API validated, unique per-layer values |
| D4 | dflash | 3 | Qwen3-Coder-30B-A3B + DFlash | Forward pass + acceptance rate | CRITICAL | ✅ **27.0% acceptance** (with RoPE, paper: ~40%) |
| D5 | dflash | 4 | Qwen3-Coder-30B-A3B (frontdoor) | Linear DFlash vs 0.75B AR | CRITICAL | ⚠️ Prior results INVALID (OMP=1 bug). AR: 36.5 t/s. DFlash: retest with multi-token conditioning fix |
| T1 | tree | done | Qwen3-Coder-480B-A35B Q4_K_M | Tree spec (pair 9) | HIGH | ✅ DONE — -7.6% (5.10→4.71 t/s) |
| T2 | tree | done | Qwen2.5-Coder-32B f16 | Tree spec (pair 10) | HIGH | ✅ DONE — +10.2% (6.05→6.67 t/s) |
| T3 | tree | done | Qwen3-Coder-30B-A3B Q4_K_M (frontdoor) | Tree spec (pair 15) | MEDIUM | ✅ DONE — -13.0% (40.92→35.62 t/s) |
| T4 | tree | done | Qwen2.5-Coder-32B Q8_0 | Tree spec (pair 11) | MEDIUM | ✅ DONE — +0.1% (8.43→8.44 t/s) |
| S2 | ssm | xref | Qwen3.5-35B-A3B Q4_K_M | NUMA parallel decode (1,2,4 concurrent) | MEDIUM | BLOCKED — needs bare-metal NUMA |
| D6 | dflash | 5 | Qwen3-Coder-30B-A3B (frontdoor) | DFlash tree vs linear | HIGH | BLOCKED — needs block-mode bug fix first |
| T5 | tree | 7 | Qwen2.5-Coder-32B f16 | NUMA dual-node tree | MEDIUM | BLOCKED — needs bare-metal NUMA |
| T6 | tree | 7 | Qwen3-Coder-480B-A35B Q4_K_M | NUMA dual-node tree | LOW | BLOCKED — needs bare-metal NUMA |
| D7 | dflash | 6 | Qwen3.5-35B-A3B (hybrid) | NUMA parallel verify | MEDIUM | BLOCKED — needs block-mode fix + NUMA |
| S1 | ssm | 4 | Qwen3-Next-80B-A3B Q4_K_M | NUMA prefill pipeline | LOW | DEFERRED |

## Agent Task Ordering

Recommended execution sequence for an autonomous agent:

### Batch 1 — Tree tests on existing infra (no code changes, ~1 day)
1. **T1-T4**: Run pending tree speculation pairs 9, 10, 11, 15. Script and infra already exist.
   ```bash
   for pair in 9 10 11; do
     bash /mnt/raid0/llm/epyc-inference-research/scripts/benchmark/bench_tree_speculation_server.sh $pair
   done
   # Pair 15 needs adding to script first (see tree-speculation handoff)
   ```

### Batch 2 — DFlash Phase 1 (GGUF conversion, ~2-3 days)
2. **D1-D2**: Create worktree, implement converter, convert both models, validate loads.
   - Start with dev model (smaller, faster iteration)
   - See `dflash-block-diffusion-speculation.md` Phase 1 for full CLI commands

### Batch 3 — DFlash Phase 2-3 (hidden state API + forward pass, ~3-5 days)
3. **D3**: Implement `llama_get_hidden_state()` API, generalize MTP hidden state caching
4. **D4**: Implement DFlash forward pass, test acceptance on dev model first

### Batch 4 — DFlash Phase 4-5 + NUMA (interleaved, ~1-2 weeks)
5. **D5**: Linear DFlash benchmark vs AR drafter on frontdoor
6. **S2**: NUMA parallel decode experiment (quick, ~1 day, can interleave)
7. **T5-T6**: NUMA tree tests
8. **D6**: DFlash tree mode vs linear mode

### Batch 5 — Advanced / Conditional
9. **D7**: DFlash NUMA-parallel verification on hybrid (only if S2 shows promise)
10. **S1**: NUMA prefill pipeline (only if S2 shows promise)

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
