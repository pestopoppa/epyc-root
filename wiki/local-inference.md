# Local Inference

**Category**: `local_inference`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 14 documents

## Summary

The project runs all inference locally through llama-server (from a custom llama.cpp fork) serving GGUF-quantized models on the EPYC 9655 CPU. There is no GPU, no cloud API dependency for inference, and no network-dependent model serving. The entire multi-model orchestrator -- from a 0.5B draft model to a 480B architect -- runs on a single machine using 1.13 TB of DDR5 RAM and a custom production-consolidated branch of llama.cpp that carries 23 patches beyond upstream.

The custom fork (`production-consolidated-v3`, based on upstream + 517 commits) implements features critical for the orchestrator: MoE expert count override (hard mask / REAP), SWA slot reuse optimization, CPU paged attention for flash attention, server slot dynamic management, prompt n-gram lookup, tree speculation with DySpec, HSD capped branch resampling, and freeze-recurrent speculation for hybrid SSM models. The binary is built with `-DGGML_CPU_ALL_VARIANTS=ON -DGGML_BACKEND_DL=ON -DBUILD_SHARED_LIBS=ON -DLLAMA_CURL=ON` and deployed from `/mnt/raid0/llm/llama.cpp/build/bin/llama-server`. Experimental work always happens in a separate worktree at `/mnt/raid0/llm/llama.cpp-experimental` -- the production repo is never used for debug or experimental builds.

GGUF model management follows a strict regime. Models reside on the RAID array at `/mnt/raid0/llm/models/` (~2.1 TB across 90 models) with HuggingFace source models at `/mnt/raid0/llm/hf/` (~850 GB). Q4_K_M is the standard quantization for most models -- empirically validated as optimal for both hybrid and dense architectures on this hardware. Q4_K_M matches f16 quality on the coder benchmark (74% vs 74%) while being 1.7x faster and using 3.5x less RAM. The only exception is the 7B worker (Qwen2.5-7B-Instruct), which runs at f16 because at 14 GB it fits easily in a NUMA quarter and benefits from near-flat verification curves.

Speculative decoding is the primary acceleration method. The production stack uses external draft models (Qwen2.5-Coder-0.5B at 185 t/s, Qwen3-Coder-0.75B at 181 t/s) with configuration validated by a comprehensive 1,290-measurement sweep. Key parameters are model-specific: coder_escalation uses dm=32/ps=0.05 (tree beneficial), architect uses dm=24/ps=0 (tree harmful), and the 480B coding architect uses dm=24/ps=0 (tree harmful at -19%, overturning prior assumption). No speculation is used on hybrid SSM models (Qwen3.5-*) -- all draft configurations are net-negative due to recurrent state overhead.

## Key Findings

- **llama.cpp custom fork carries 23 production-critical patches**: MoE expert override (#1), SWA slot reuse (#5-6), CPU paged attention (#7-10), server slot management (#14-15), prompt lookup (#19), tree speculation (#22), HSD+freeze-recurrent (#20), and SSM checkpointing (#16). The v2-to-v3 rebuild absorbed 517 upstream commits while preserving all patches. [llama-cpp-v3-upstream-rebuild.md]
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
- Intake entries: 5 results including CPU+GPU hybrid MoE inference guide (intake-310, high relevance), rocWMMA (intake-303), and community model evaluations
