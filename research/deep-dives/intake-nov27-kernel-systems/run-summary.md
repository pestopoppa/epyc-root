# November 27 research intake

Fourteen submitted primary sources. The X announcement is attached to the CPU repository as provenance. Comparative measurements here are author reports. The operator approved the filing plan. Stage 4 filed 13 tasks and three conditional monitor notes.

[Read the approved filing plan](stage3-plan.md).

## Deep-dive priorities

1. GPU spill and F32 shape dispatch, then the CPU near-tie oracle. Each has a concrete local kernel or verifier to inspect before booking inference.
2. HoMe/ReMe and MGMem memory evaluation, paced routing replay, and physical-bank expert tracing. Each has a local incumbent and a cheap comparison arm.
3. IQ4 decode placement, sampled-PC coverage, multi-column verification and skill compatibility. Each requires separating an existing implementation or a foreign backend from the proposed transfer.
4. SWGDN, SPLICE and FlyingStart. Training or a recurrent-depth checkpoint determines the value of a full reproduction. All fourteen primary sources received a dive.

## Source records

| Entry | Source | Local decision |
|---|---|---|
| [intake-3006](intake-3006.md) | Beyond Counters: Instruction-Level GPU Hotspot Profiling with PC Sampling in ROCprofiler-SDK | Identify sampled HIP instructions in existing binaries |
| [intake-3007](intake-3007.md) | Bringing MXFP4 MoE to AMD Instinct MI300 Series GPUs with FlyDSL | Decide whether decode scheduling limits IQ4 or EXL3 |
| [intake-3008](intake-3008.md) | HIP: add split-K F32 GEMM path for untuned RDNA3 chips | Identify underfilled F32 router GEMMs |
| [intake-3009](intake-3009.md) | cuda : use constant V load length when head dim is unpadded | Decide whether to specialize a HIP V-load bound |
| [intake-3010](intake-3010.md) | opencl: add multi token f32 GEMV for spec verify | Determine eligible F32 verify work |
| [intake-3011](intake-3011.md) | moe-cache : deduplicate physical expert banks across looped MoE layers | Price adaptive expert caching versus a static pool |
| [intake-3012](intake-3012.md) | Qwen3-0.6B in raw x86-64 machine code: Gemini 4 Neon vs Claude Opus 5.5 | Preserve greedy parity near logit ties |
| [intake-3013](intake-3013.md) | One Token, Many Lessons: Sliding-Window Attention within Gated Delta Networks | Recognize a future local-mixer architecture |
| [intake-3014](intake-3014.md) | When Every Rollout Fails: Splicing Learner-Conditioned Options into Long-Horizon Agent RL | Decide whether failed groups can support local repairs |
| [intake-3015](intake-3015.md) | HoMe: Toward Practical Harness Optimization of Memory Systems for AI Assistants | Select a cheaper memory harness without leaking evaluation data |
| [intake-3016](intake-3016.md) | CoordRoute: Coordinated Multi-Model Routing for Maximum Compute-Budget Utility | Test whether routing improves under a fixed local capacity budget |
| [intake-3017](intake-3017.md) | When Skills Fail to Compose: Compatibility and Retention in Language Models | Detect skill interactions hidden by single-skill uplift |
| [intake-3018](intake-3018.md) | MGMem: An Efficient, Deterministic, and Provenance-Preserving Framework for Long-Horizon Agent Memory | Test deterministic retrieval into post-compaction history |
| [intake-3019](intake-3019.md) | FlyingStart: Learned Cross-Token Warm Starts for Fixed-Point Decoding in Recurrent-Depth Language Models | Reduce loops per decoded token on recurrent-depth models |
| [intake-3020](intake-3020.md) | Using PC sampling | Identify sampled HIP instructions in existing binaries |
| [intake-3021](intake-3021.md) | [FlyDSL] [CI] [a16w4] Support MXFP4 weights on gfx942 (CDNA3) | Decide whether decode scheduling limits IQ4 or EXL3 |
| [intake-3022](intake-3022.md) | ReMe — HoMe plugin, evaluation and optimization harness | Select a cheaper memory harness without leaking evaluation data |
| [intake-3023](intake-3023.md) | Adaptive LLM Routing under Budget Constraints | Test whether routing improves under a fixed local capacity budget |
| [intake-3024](intake-3024.md) | MGMem: mention-graph retrieval for long-term dialogue memory question answering | Test deterministic retrieval into post-compaction history |

## Expansion decisions

The five follow-ups supplied a gfx90a capability check, the actual AITER decoder, a harness replay contract, a lighter budget allocator, and the released memory parser. The AITER successor paths that use newer conversion instructions provide lineage for MI300. Their code cannot settle whether existing gfx90a IQ4 decode is a limiter. The parent assembly exporter is relevant to file-format provenance; the contest verifier and format specification already identify the historical comparator and different row layout.

Dynamic convolution and full-trajectory RL guidance remain comparison arms if training is proposed. MemPro and AnchorMem enter baseline selection if a generative index is tested. The skill paper’s neologism comparisons concern learned prefixes; EPYC’s first probe uses held-out executable/text skill pairs. Fixed-point cache and continuous-depth scheduling comparisons depend on admitting a recurrent-depth serving model. These citations remain visible in the individual dives. Neither paper results nor community reception are independent replications of live EPYC performance.
