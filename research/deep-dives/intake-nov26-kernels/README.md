# November 26 research intake

15 submitted sources and nine expansions. Three of four authorized sweeps were used. Click a source to read its verified passages, hardware limits, counterevidence and proposed action. [Proposed filing](stage3-plan.md)

| Intake | Source and dive | Owning program |
|---|---|---|
| intake-2982 | [hip : fix bf16 MFMA operand vector type for CDNA](33086.md) | rocm-kernel-authoring |
| intake-2983 | [CUDA: split gate and up weight reads for small-k MMVQ](33019.md) | autokernel-loop |
| intake-2984 | [llama,ggml,tests: batch invariance support](32081.md) | kv-cache-program |
| intake-2985 | [FlashInfer v0.7.6](flash.md) | speculative-decoding |
| intake-2986 | [ggml : vectorize ggml_vec_exp_f32](33077.md) | cpu-decode-roofline-program |
| intake-2987 | [Any-Rate: Half-Bit Multi-Precision LLM Quantization with Coded Bit-Planes](2611.34402.md) | quantization-and-low-bit |
| intake-2988 | [DFly2: Turbocharging Long-Context Speculative Decoding by Sharing the Target's Sparsity](2611.34776.md) | speculative-decoding |
| intake-2989 | [Improving Tail-Augmented Speculative Drafting with Hidden State Mixing and Gradient Detach](2611.34092.md) | speculative-decoding |
| intake-2990 | [Asymmetric Speculative Decoding: Unlocking In-Context Learning in Draft Models](2611.34010.md) | speculative-decoding |
| intake-2991 | [Ostinato: Low-Latency CPU-GPU MoE Inference for Local Agents](2611.11533.md) | cpu-decode-roofline-program |
| intake-2992 | [llama : share compute buffers with the partner context](33068.md) | speculative-decoding |
| intake-2993 | [llama : fix seq state restore with ON_DEVICE](30318.md) | kv-cache-program |
| intake-2994 | [Partial Routing: Trace-Tuned Delegation for Resource-Efficient Agentic Workflows](2611.33402.md) | routing-program |
| intake-2995 | [What Does Skill Lift Actually Measure? A Source-Code-Level Audit and Noise-Aware Reanalysis of SkillsBench](2611.33943.md) | eval-tower-program |
| intake-2996 | [Collect for Coverage, Replay with Evidence: Adaptive and Efficient On-Policy Distillation for Long-Horizon Agents](2611.34756.md) | harness-program |
| intake-2997 | [hoonki2002/Any-Rate](Any-Rate.md) | quantization-and-low-bit |
| intake-2998 | [rrrrr4788/skillsbench-lift-reanalysis](audit.md) | eval-tower-program |
| intake-2999 | [Tencent/AngelSpec](angel.md) | speculative-decoding |
| intake-3000 | [llama : fix K/V and recurrent state cleanup after failed restores](27530.md) | kv-cache-program |
| intake-3001 | [feat(batch_invariant): `chunk_gated_delta_rule(batch_invariant=True)`, the GDN class `gdn.bf16.c64`](9405.md) | kv-cache-program |
| intake-3002 | [feat(batch_invariant): `sampling_from_probs` / `sampling_from_logits` under `batch_invariant=True`](9365.md) | speculative-decoding |
| intake-3003 | [feat(batch_invariant): batch-invariant top-k / top-p / min-p sampling](9619.md) | speculative-decoding |
| intake-3004 | [feat(cake_ssd_combined): read and write states in a caller state pool by slot](9644.md) | kv-cache-program |
| intake-3005 | [Beyond Gain: Measuring Skill Internalization for Agent Skill Retirement](2610.32322.md) | eval-tower-program |

## Ranking and expansion

Stage 1 ranked the submitted sources in this order, highest first: intake-2993, intake-2984, intake-2995, intake-2983, intake-2991, intake-2988, intake-2985, intake-2992, intake-2982, intake-2987, intake-2994, intake-2990, intake-2986, intake-2989, intake-2996. Checkpoint recovery, deterministic dispatch and the skill-gate controls have identified consumers and discriminating tests. Reachability and fit determine whether to spend hardware time on the other claims. The operator preselected every recommended dive.

Sweep 1 covered all 15 submitted sources. Sweep 2 checked the quantizer, skill reanalysis and AngelSpec repositories, the restore-cleanup prerequisite, and four FlashInfer implementation PRs. Sweep 3 checked Beyond Gain, which distinguishes unaided competence from low marginal uplift. The independent reconstruction recomputes author tables rather than collecting new outcomes. The retirement paper did not establish a live EPYC retirement request requiring a fourth sweep.

The EAGLE-3 baseline, the older context-asymmetric AsymSpec paper, original SkillsBench and SkillReducer already have distinct intake records (070, 1837, 096, 302). The prior AsymSpec record describes different conditioning and exactness. The Any-Precision comparison and other quantizers become useful for an equal-bytes quality test; the present conclusion is representation feasibility. The other sparse-draft and expert-cache baselines are discussed in their parent dives; a new serving reproduction depends on a mapped drafter or a positive route-trace screen. Generic routing and OPD baselines add no local paired trace or training budget. The compiler issue and RDNA precursor do not supply CDNA execution. The scratch allocator precursor becomes relevant on a documented fit failure. The FlashInfer row-reduction prerequisite and tracker add no new EPYC sampler decision; KDA-specific invariant expansion requires a KDA cross-phase consumer. Each remaining lead is identified in its parent dive.

## Evidence boundary

All 24 entries use PARTIAL primary reads. The source authors supply the benchmark numbers. 72 anchors received independent reviews (60 YES, 12 PARTIAL). The index stores the reviewed wording. Machine containment was checked again against retained bytes. The project-owned handoff and implementation references are pinned to EPYC root a660ead17, C21 98ff8a4 and orchestrator faa783c7.

Distinct hardware questions: gfx90a is wave64 with 64 KB LDS and no native FP8; NVIDIA occupancy, RNG streams and ISA are not timing proxies. Zen 5 comparisons require AVX-512 dispatch proof, per-NUMA memory placement and real row shapes. No new runtime measurements were taken.

Artifact audit: clean. External raw snapshots are content-addressed in the Vidya store. This run produced source reviews and no experimental figures.
