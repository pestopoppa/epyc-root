# Local Inference

**Category**: `local_inference`
**Confidence**: verified
**Last compiled**: 2026-04-23
**Sources**: 20 documents

## Summary

The project runs all inference locally through llama-server (from a custom llama.cpp fork) serving GGUF-quantized models on the EPYC 9655 CPU. There is no GPU, no cloud API dependency for inference, and no network-dependent model serving. The entire multi-model orchestrator -- from a 0.5B draft model to a 480B architect -- runs on a single machine using 1.13 TB of DDR5 RAM and a custom production-consolidated branch of llama.cpp that carries 23 patches beyond upstream.

The custom fork (`production-consolidated-v3`, based on upstream + 517 commits) implements features critical for the orchestrator: MoE expert count override (hard mask / REAP), SWA slot reuse optimization, CPU paged attention for flash attention, server slot dynamic management, prompt n-gram lookup, tree speculation with DySpec, HSD capped branch resampling, and freeze-recurrent speculation for hybrid SSM models. The binary is built with `-DGGML_CPU_ALL_VARIANTS=ON -DGGML_BACKEND_DL=ON -DBUILD_SHARED_LIBS=ON -DLLAMA_CURL=ON` and deployed from `/mnt/raid0/llm/llama.cpp/build/bin/llama-server`. Experimental work always happens in a separate worktree at `/mnt/raid0/llm/llama.cpp-experimental` -- the production repo is never used for debug or experimental builds.

GGUF model management follows a strict regime. Models reside on the RAID array at `/mnt/raid0/llm/models/` (~2.1 TB across 90 models) with HuggingFace source models at `/mnt/raid0/llm/hf/` (~850 GB). Q4_K_M is the standard quantization for most models -- empirically validated as optimal for both hybrid and dense architectures on this hardware. Q4_K_M matches f16 quality on the coder benchmark (74% vs 74%) while being 1.7x faster and using 3.5x less RAM. The only exception is the 7B worker (Qwen2.5-7B-Instruct), which runs at f16 because at 14 GB it fits easily in a NUMA quarter and benefits from near-flat verification curves.

Speculative decoding is the primary acceleration method. The production stack uses external draft models (Qwen2.5-Coder-0.5B at 185 t/s, Qwen3-Coder-0.75B at 181 t/s) with configuration validated by a comprehensive 1,290-measurement sweep. Key parameters are model-specific: coder_escalation uses dm=32/ps=0.05 (tree beneficial), architect uses dm=24/ps=0 (tree harmful), and the 480B coding architect uses dm=24/ps=0 (tree harmful at -19%, overturning prior assumption). No speculation is used on hybrid SSM models (Qwen3.5-*) -- all draft configurations are net-negative due to recurrent state overhead.

## Key Findings

- **llama.cpp custom fork carries 23+ production-critical patches**: MoE expert override (#1), SWA slot reuse (#5-6), CPU paged attention (#7-10), server slot management (#14-15), prompt lookup (#19), tree speculation (#22), HSD+freeze-recurrent (#20), SSM checkpointing (#16), and Differential Transformer V2 architecture support (2026-04-14). The v2-to-v3 rebuild absorbed 517 upstream commits while preserving all patches. [llama-cpp-v3-upstream-rebuild.md, progress/2026-04-14 session 22]
- **Differential Transformer V2 implemented in llama.cpp** (2026-04-14): Full architecture support added across 9 files (155 LOC core graph builder in `src/models/diff-transformer.cpp`). Algorithm: Q doubled to 2h heads, K/V unchanged, single FlashAttention, split even/odd heads, `output = attn_even - sigmoid(W_lambda @ hidden) * attn_odd`. KV cache unaffected. Uses zero new ggml ops. Regression tests passed on all production models (Qwen3.5-35B hybrid SSM, Qwen3-Coder-30B MoE, Qwen2.5-Coder-32B dense). Synthetic test model loads and runs. Accuracy testing blocked on Microsoft releasing pretrained weights. Commits: `llama.cpp-experimental` `3b5514d46`, `llama.cpp` (production) `8bd57177f`. [progress/2026-04-14 session 22]
- **4 patches were dropped in the v3 rebuild**: MTP-1/MoE self-draft mega-commit (all techniques NOT VIABLE), Hadamard KV smoothing (superseded by upstream auto-enabling), enable_thinking Jinja fix (superseded by upstream refactor), and a merge commit. [llama-cpp-v3-upstream-rebuild.md]
- **Q4_K_M is the standard quantization**: Validated across coder (Q4KM 74% = f16 74%, 1.7x faster, 3.5x less RAM), hybrid models (recurrent state update is constant cost, Q8 costs 17-39% speed for marginal quality), and all production roles. The quality ceiling is the model itself, not the quantization. [numa-orchestrator-deployment.md]
- **Draft model selection is critical**: Qwen2.5-Coder-0.5B at 185 t/s generates 4x faster than Qwen3.5-0.8B at 44 t/s, despite similar parameter counts. The Qwen3.5 architecture (752M actual params) has higher per-token overhead. Best production pair: Qwen2.5-7B-f16 + Qwen2.5-Coder-0.5B (42 t/s, 91% acceptance). [specexec-verification-profile.md]
- **Speculation is architecture-dependent, not universally beneficial**: External draft on dense Qwen3-32B gives +55% (13.07 vs 8.44 t/s baseline). All speculation on hybrid SSM (Qwen3.5-*) is net-negative: external draft -33%, self-spec -44% to -52%, tree -53% to -66%, prompt lookup segfaults. Only MoE expert reduction works on hybrids. [hsd-hierarchical-self-speculation.md, self-speculation-benchmark.md]
- **Tree speculation is viable only for specific configurations**: Q4_K_M coder benefits from tree (ps=0.05, +2.7%), f16 targets benefit significantly (+15.8-17%), 480B MoE is harmed (-19%). Tree vs linear is a wash at 48t per instance. DySpec heap-based dynamic construction replaced simpler per-depth expansion. [tree-speculation-numa-drafting.md]
- **HSD capped branch resampling provides free marginal gain**: +0.8% throughput, +0.98pp acceptance rate. When target disagrees with draft, stochastically accepts based on p_draft if above 0.3 threshold. At most one recovery per sequence. [hsd-hierarchical-self-speculation.md]
- **Prompt lookup (--lookup) works on dense models and via freeze-recurrent on hybrid models**, but segfaults on Qwen3.5 hybrids after 1-3 prompts due to prompt cache + recurrent state corruption. Do not use on Qwen3.5 until fixed. [numa-orchestrator-deployment.md]
- **MoE self-drafting is NOT VIABLE**: Using the same model with reduced experts as draft. Raw speedup is promising (1.79x at 1-expert on 235B), but acceptance collapses: 2.9% at 1-expert (categorically different token distributions), 55% at 2-expert (but speedup too small to overcome draft overhead). No sweet spot exists. [ssm-hybrid-acceleration.md]
- **Self-speculation (layer skip) not viable without early-exit fine-tuning**: Dense models achieve 0.5-1.5% acceptance (intermediate logits untrained). Hybrid models suffer -44% to -52% from SSM checkpoint/restore overhead even with 77% acceptance. [hsd-hierarchical-self-speculation.md]
- **CPU paged attention enabled for models >= 39 GB**: Patches #7-10 in the custom fork. Dynamic block allocation with pool statistics. CLI flags exposed for orchestrator integration. RSS impact under NUMA 4-way not yet validated. [llama-cpp-v3-upstream-rebuild.md]
- **--draft-p-split 0 must be explicit for linear speculation**: The production binary defaults p_split=0.1 (tree ON). Silent tree activation causes kv_unified=true, n_seq_max=9, and draft truncation overhead. [numa-orchestrator-deployment.md]
- **Cherry-picked upstream commits fix Qwen3.6 think-loops and Gemma4 template issues (2026-04-20).** Four upstream commits were cleanly cherry-picked onto `production-consolidated-v3` with zero conflicts: `56666fa60` (skip reasoning budget sampler when no budget requested -- the Qwen3.6 fix), `ddf03c6d9` (fix ambiguous Gemma4 grammar rule), `d7ff074c8` (enable reasoning budget sampler for Gemma4), `3fc65063d` (better align to updated Gemma4 template). Validated: Qwen3.6 CLI test produced coherent thinking + correct answer, no `</think>` loops. The reasoning budget sampler was unconditionally activating and trapping models -- the skip commit was the root cause fix. Current HEAD: `cd5f4fcd0`, 35 custom commits ahead of merge base, 121 behind upstream (was 125). Full rebase deferred but no longer blocking. [llama-cpp-fork-rebase.md](../handoffs/active/llama-cpp-fork-rebase.md)
- **Fork conflict risk is lower than initially assessed.** Actual code analysis found: `src/llama-kv-cache*` has ZERO conflict risk (10 of our patches, 0 upstream changes), `common/chat*` has ZERO risk (0 ours, 10 upstream all cherry-pickable), `tools/server/server.cpp` has ZERO risk (handoff was wrong). Real battleground is `common/common.h` (6 ours vs 4 upstream, including `libcommon->libllama-common` rename). Recommended: drop 7 experimental patches during full rebase to reduce conflict surface from 41 to 24 patches. [llama-cpp-fork-rebase.md](../handoffs/active/llama-cpp-fork-rebase.md)
- **GLM-5.1-555B-A14B-REAP GGUF as potential stack addition.** 325GB Q4_K_M fits in 1052GB available RAM with 14B active parameters for an estimated ~25-40 tok/s on CPU. Stack simplification candidate: could replace architect_general (69GB) + architect_coding (139GB) = 208GB with a single 325GB model. Storage constraint: 417GB free on RAID, 92GB remaining after download. llama.cpp launch flags: `--reasoning on --reasoning-format deepseek --jinja`. DSA indexer tensors loaded but forward pass not implemented — dense MLA fallback. [intake-427, glm51-reap-cpu-evaluation.md]
- **Stock upstream produces 73.8% quality on Qwen3.6 vs 0% on our fork (pre-fix).** The reasoning budget sampler bug caused 100% degenerate `</think>` loops on all thinking-capable models. Post cherry-pick, CLI testing confirms the fix. Quality benchmarks should confirm the 0%->73.8% improvement at scale. M2.7 scored worse on upstream (41.1% vs 55.7%) because 4x token budget gave room for more training data leakage -- the model needs `max_tokens` tuning independently. [llama-cpp-fork-rebase.md](../handoffs/active/llama-cpp-fork-rebase.md)

## Actionable for EPYC

- **Standard launch pattern**: `taskset -c <cpulist> llama-server -m <model>.gguf [-md <draft>.gguf --draft-max N --draft-p-split P] [--kv-unified] [--lookup] [-t <threads>] [-np <slots>] [--mlock] [--override-kv key=type:value]`
- **Never run experimental work on the production repo**: Use `/mnt/raid0/llm/llama.cpp-experimental` for all debug, benchmark, and feature development. The production binary at `/mnt/raid0/llm/llama.cpp/build/bin/llama-server` must remain stable.
- **Model registry drives configuration**: `model_registry.yaml` in both epyc-orchestrator and epyc-inference-research defines acceleration type, draft model, draft_max, p_split, thread count, NUMA config, and mlock for each role. orchestrator_stack.py reads this and applies spec_overrides per role.
- **All acceleration params must be sweep-verified**: bench_all_spec_sweeps.sh produces comprehensive measurements. Prior assumptions have been overturned multiple times (coder tree beneficial, 480B tree harmful, registry values 3.6x inflated).
- **v3 rebuild pending validations**: Paged attention RSS under NUMA 4-way, PPL sweep (done 2026-04-13). No blocking issues but measurement confirmation needed.
- **CPU+GPU hybrid inference** is a potential future direction (intake-310: expert offloading guide for MoE models in llama.cpp). No GPU hardware is currently present.

## Open Questions

- The v3 upstream rebuild absorbed 517 commits. Subtle behavior changes in GGML backend dispatch, KV cache management, or sampler logic may emerge in production. PPL sweep completed 2026-04-13 but production stress testing under full orchestrator load is needed.
- CPU paged attention (patches #7-10) interaction with NUMA 4-way multi-instance is untested. Each instance's paged blocks should be NUMA-local but this is not verified.
- Prompt lookup segfault on Qwen3.5 hybrids (related to llama.cpp PR #13194) may be fixed in a future upstream commit. Monitor for fixes.
- TQ3 / TurboQuant quantization (intake-246) is on the monitor list but not yet merged. 3.5-bit Walsh-Hadamard Transform quantization could change the Q4_K_M optimality conclusion.
- REAP permanent pruning (deployed for architect_coding) creates a genuinely smaller model that may interact differently with speculation than dynamic expert override. Needs acceleration benchmarks on the REAP-246B model.

## Related Categories

- [Hardware Optimization](hardware-optimization.md) -- NUMA topology, memory bandwidth, and thread allocation determine inference performance
- [Inference Serving](inference-serving.md) -- the orchestrator stack built on top of llama-server instances
- [Speculative Decoding](speculative-decoding.md) -- detailed analysis of draft/target pairs and tree speculation
- [MoE Optimization](moe-optimization.md) -- expert reduction and REAP pruning for MoE models
- [Benchmark Methodology](benchmark-methodology.md) -- sweep methodology for validating inference configurations

## Source References

- [llama.cpp v3 Upstream Rebuild](/workspace/handoffs/active/llama-cpp-v3-upstream-rebuild.md) -- Patch inventory (23 carry-forward, 4 dropped), conflict hotspot map, build configuration
- [NUMA Orchestrator Deployment](/workspace/handoffs/completed/numa-orchestrator-deployment.md) -- Per-model launch configuration, coder quant decision matrix, comprehensive sweep
- [Tree Speculation + NUMA Drafting](/workspace/handoffs/completed/tree-speculation-numa-drafting.md) -- Phase 1-8 implementation, DySpec, multi-path verification, NUMA 4-way results
- [HSD + Hierarchical Self-Speculation](/workspace/handoffs/completed/hsd-hierarchical-self-speculation.md) -- HSD capped branch, layer-skip benchmarks, HiSpec, orchestrator integration
- [SSM Hybrid Acceleration](/workspace/handoffs/completed/ssm-hybrid-acceleration.md) -- MoE self-draft failure analysis, architecture properties, Q4_K_M optimality
- [SpecExec Verification Profile](/workspace/handoffs/completed/specexec-verification-profiling.md) -- Draft model cost profiling, critical ratios, large-K linear results
- [SpecExec Experiment](/mnt/raid0/llm/epyc-inference-research/docs/experiments/specexec-verification-profile.md) -- Raw data, NUMA impact, inflection points
- [Self-Speculation Benchmark](/mnt/raid0/llm/epyc-inference-research/docs/experiments/self-speculation-benchmark.md) -- SSM checkpoint overhead measurements
- [HiSpec External Draft Benchmark](/mnt/raid0/llm/epyc-inference-research/docs/experiments/hispec-external-draft-benchmark.md) -- Double-buffer optimization, freeze-recurrent validation
- [Chapter 01: Hardware System](/workspace/docs/infrastructure/01-hardware-system.md) -- Baseline performance, runtime optimizations
- [Progress 2026-03-21](/workspace/progress/2026-03/2026-03-21.md) -- Worker swap, registry corrections, sweep-verified params
- [Progress 2026-04-14 Session 22](/workspace/progress/2026-04/2026-04-14.md) -- Differential Transformer V2 implementation (9 files, 155 LOC core), zero new ggml ops, regression-safe on all production models, blocked on pretrained weights
- [llama-cpp-fork-rebase.md](/workspace/handoffs/active/llama-cpp-fork-rebase.md) -- Cherry-pick results (4 commits, zero conflicts), Qwen3.6 think-loop fix confirmed, conflict risk reassessment (lower than estimated), experimental patch drop strategy, full rebase deferred but unblocked
- Intake entries: 5 results including CPU+GPU hybrid MoE inference guide (intake-310, high relevance), rocWMMA (intake-303), and community model evaluations
- [intake-427] GLM-5.1-555B-A14B-REAP GGUF -- 325GB Q4_K_M, 14B active, ~25-40 tok/s CPU estimate, stack simplification candidate
- [glm51-reap-cpu-evaluation.md] GLM-5.1 REAP CPU Evaluation -- deployment feasibility, storage constraints, llama.cpp flags

## 2026-04-23 Additions — Single-instance peak throughput backlog

Three new handoffs (2026-04-23) open the forward-looking CPU throughput backlog for single-instance decode on EPYC 9655:

- **[Intra-Process Tensor-Parallel Decode](../handoffs/active/intra-process-tensor-parallel-decode.md)** — shard each matmul column-wise across 12 CCDs with shared-L3 reduction (effectively free on CPU, unlike GPU where NVLink reduce dominates) and next-layer weight prefetch overlapping the barrier. Per-CCD hierarchical thread pool replaces GGML's global 192-thread barrier. Projected 2–5× single-instance decode, depending on NPS mode. Closes the gap between 1×instance throughput and the N×instance aggregate that NUMA 4-way deployment currently delivers only to concurrent sessions. No known CPU prior art — the design pattern is GPU-native (Megatron-LM column-sharded attention + row-sharded MLP) ported to CPU, where "communication" = shared memory traffic, not a separate fabric.

- **[Single-Instance System Tuning](../handoffs/active/single-instance-system-tuning.md)** — exhaustive audit of system knobs that affect single-instance decode but have never been systematically measured on our hardware: NPS mode (NPS2 → NPS4 / L3-as-NUMA), THP (`madvise` → `always`), explicit 1 GB hugepages (currently 0 allocated), IRQ affinity, per-CCD sync primitive (replaces GGML global barrier), SMT toggle for AVX-512-heavy workloads, per-NUMA weight replication. Projected 15–40% alone; required for TP-sharding's full gain under NPS4/L3aaN. Phases staged so reboot windows are batched.

- **[CPU Inference Optimization Index](../handoffs/active/cpu-inference-optimization-index.md)** — backlog index aggregating all 14 unimplemented CPU throughput techniques (CPU1–CPU14): TP sharding, GEMV ukernels, system tuning, per-CCD sync, hugepages, ZenDNN 5.2 eval, tinyBLAS integration, weight replication, dense-weight sparsity, sub-Q4 quant eval, compiler/PGO/LTO, BOLT post-link, prefill optimizations, `--parallel` slot decode benchmarks. Includes dependency graph (CPU3 Phase 0 baseline gates everything), composition matrix (TP × ukernel × tuning multiplicative up to 460 GB/s BW ceiling), and explicit list of what's deployed or concluded-not-viable so future agents don't re-open closed work.

Start gate for the entire backlog: **CPU3 Phase 0 baseline measurement** — `perf stat` uncore counters + barrier-time profiling on Qwen3-Coder-30B-A3B Q4_K_M at 192t. Tells us which lever has the most headroom before committing to any code.

## 2026-04-23 late-session — Phase 0 executed, CPU2 falsified

Phase 0 ran end-to-end on 2026-04-23 in `llama.cpp-experimental` on `cpu-optimization/backlog-2026-04-23` (HEAD `9e048fbc1`). Key measurements and decisions:

- **Thread sweep** on Qwen3-Coder-30B-A3B Q4_K_M (`-p 0 -n 64 -r 3`, quiet host): 24t=40.8 t/s, 48t=39.6, **96t node 0 pinned = 49.1 (PEAK)**, 144t cross-NUMA=25.7 bimodal, 192t `--numa distribute`=18.7 bimodal.
- **perf profile Qwen3.6-27B Q8_0 @ 96t (4.41 t/s)**: 63.43% `ggml_vec_dot_q8_0_q8_0`, 32.34% libomp spin/barrier, 0.11% DeltaNet (`gated_delta_net` + `ssm_conv` combined — refutes the feared DeltaNet-dominates gate).
- **CPU2 Phase 1 Target #1 implemented and tested**: ported `ggml_vec_dot_q8_0_q8_0` from AVX2 (256-bit) to AVX-512VNNI (512-bit) using existing `mul_sum_i8_pairs_acc_int32x16` helper. Disassembly confirmed `vpdpbusd %zmm` in new path. Measured +1.7% at 96t / −3.6% at 1t — projection of 1.46× falsified. Cause: perf cycles inside the dot loop are DRAM-wait, not ALU. Change reverted.
- **Promotions based on measurement**:
  - CPU1 (TP-sharding) Phase 0 gate PASSED (192t at 8% of 460 GB/s roofline; barrier >15% required, measured 32–45%). Phase 1 prototype remains ~1 week of work.
  - CPU4 (per-CCD sync primitive) promoted from MED-bundled to HIGH standalone on measured 32–45% barrier cost.
  - CPU2 (GEMV ukernels on quantized decode) deprioritized.
- **CPU3 zero-reboot knobs applied via user sudo**: THP→always, numa_balancing=0, 1GB hugepage on node 1. Net within noise on canonical workload.
- **96t-single-NUMA-node operating point** emerged as actionable: +26% vs production worker_explore (1×24t, 39.1 t/s) with no code change. Worth a production sweep separately from CPU1.

See `research/deep-dives/cpu-optimization-phase0-baseline.md` for full analysis + revised gate decisions. Auto-memory entry `feedback_cpu_decode_bw_bound.md` captures the lesson: when perf shows high overhead inside a quantized-decode inner dot loop on this hardware, those samples are typically DRAM-wait cycles; a cheap wider-SIMD A/B test resolves the question in hours before committing to shape-specialized ukernel work.
