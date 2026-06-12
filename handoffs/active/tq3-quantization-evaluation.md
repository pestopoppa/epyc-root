# TQ3 / TurboQuant Quantization — Monitor List

**Status**: monitoring (do NOT merge TQ3_1S — see rationale below)
**Created**: 2026-04-01 (via research intake)
**Updated**: 2026-04-21 (monitoring confirmed — PR #21089 still open, ChunkKV unchanged)
**Categories**: quantization, hardware_optimization

## Status as of 2026-04-21

Backburner monitoring. PR #21038 remains merged and auto-enabled in production v3 (confirmed 2026-04-17). PR #21089 (TBQ3_0/TBQ4_0 CPU KV cache kernels) still open — no movement since last review. ChunkKV proposal unchanged. TQ3_1S rejection stands (immaturity + wrong target; see rationale below). Next revisit: when PR #21089 receives maintainer review or lands.

## Why NOT to Merge TQ3_1S

1. **Immature**: 3 commits, 1 contributor, no peer review, no CPU kernels, undocumented conversion tool
2. **Wrong target**: Only benchmarked on Qwen3.5-27B vs Q4_0. No Q4_K_M comparison. No Qwen2.5 tests. Author warns smaller models are "much less forgiving"
3. **We don't need VRAM savings**: Our EPYC 9655 setup has ample RAM/VRAM. Q4_K_M fits comfortably. Bottleneck is throughput, not capacity
4. **Upstream going different direction**: ggerganov himself is working on Hadamard rotation for existing quant types (PR #21038) — no new types needed
5. **MoE risk**: WHT rotation creates ~367K ghost activations per forward pass, shattering sparse routing. Not applicable to dense Qwen2.5-Coder-32B but relevant for Qwen3.5 hybrid

## What to Monitor Instead (High Priority)

### PR #21038 — ggerganov's Hadamard Rotation ✅ LANDED
- **What**: Applies WHT rotation to ALL existing KV cache quant types (Q4_0, Q5_0, Q8_0 etc.)
- **Impact**: Q4_0 KV cache PPL improves 25-77% on small models. Q8_0 with rotation matches FP16 on reasoning benchmarks
- **Why it matters**: Free quality improvement — no model re-quantization needed, just rebuild llama.cpp
- **Status**: ✅ MERGED upstream as commit `744c0c731` (2026-04-01). Auto-enables in `production-consolidated-v3` when KV types are quantized. `--kv-hadamard` flag removed from orchestrator config (was our prior custom WHT impl, now redundant).
- **URL**: https://github.com/ggml-org/llama.cpp/pull/21038

### PR #21089 — CPU TurboQuant KV Cache (TBQ3_0/TBQ4_0)
- **What**: 3-bit and 4-bit KV cache quantization with CPU kernels
- **Impact**: 5.2x KV cache compression with minimal PPL loss. Extends effective context length
- **Status**: Open PR, under review
- **URL**: https://github.com/ggml-org/llama.cpp/pull/21089

### ChunkKV (arXiv:2502.00299) — Training-Free KV Compression
- **What**: Chunk-level KV cache compression preserving semantic structure. No retraining required
- **Impact**: Retains 12% of KV cache matching full cache quality. 26.5% throughput improvement via layer-wise index reuse
- **Why it matters**: Works on existing pretrained models — directly applicable to our stack
- **URL**: https://arxiv.org/abs/2502.00299

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-246 | llama.cpp-tq3 — TQ3_1S Weight Quantization | medium | worth_investigating (monitor) |
| intake-245 | MSA: Memory Sparse Attention | low | not_applicable (training-only) |
| intake-186 | bitnet.cpp — Ternary Quantization (TQ1_0/TQ2_0) | medium | already_integrated |

## Action Items

- [x] Watch PR #21038 for merge — ✅ LANDED 2026-04-01 as commit `744c0c731`, auto-enables in v3
- [ ] Evaluate PR #21089 when merged — test TBQ3_0 KV cache on Qwen2.5-Coder-32B context extension
- [ ] Read ChunkKV paper — assess if implementable in llama.cpp
- [ ] Revisit TQ3_1S weight quant only if: upstream adopts + multi-model benchmarks + Q4_K_M comparison + CPU kernels

---

## Research Intake Update — 2026-05-21

### AngelSlim toolkit + sub-2-bit weight quantization track

- **[intake-590] AngelSlim toolkit (arxiv:2602.21233)** — Tencent Hunyuan model-compression toolkit. CC-BY-4.0 (per paper) / custom proprietary (per GitHub README) — license inconsistency to resolve before code adoption. Bundles four un-indexed Tencent techniques: Sherry (1.25-bit, intake-591), Tequila (ternary QAT, intake-593), DAQ (delta-aware PTQ, intake-594), SpecExit (intake-592). Verdict: cherry-pick the algorithms + the upstream llama.cpp PR; do NOT adopt the toolkit wholesale (vLLM/SGLang/transformers-first runtime focus).
- **[intake-591] Sherry — 1.25-bit hardware-efficient ternary quantization (arxiv:2601.07892, ACL 2026)** — 3:4 fine-grained sparsity packs 4 weights into 5 bits (power-of-two-aligned 1.25 bpw, SIMD-compatible). Introduces "Arenas" annealing residual synapse to prevent weight-trapping / representational collapse during QAT. LLaMA-3.2-1B: zero accuracy loss vs SOTA ternary baselines, 25% bit savings, 10% speedup on Intel i7-14700HX. AngelSlim/Hy-MT1.5-1.8B-1.25bit-GGUF release is the public reference artefact (440 MB, claimed 1.5x decode speedup).
- **Concrete upstream path**: llama.cpp PR #22836 (STQ1_0 kernel) — sub-2-bit weight quant kernel from Tencent. This is the directly mergeable artefact into our `epyc-llama` fork. Watch consolidated HERE as of 2026-06-12 (formerly on [`llama-cpp-kernel-push-rebase`](../completed/llama-cpp-kernel-push-rebase.md), now archived).
- **[intake-593] Tequila — Trapping-free Ternary Quantization (arxiv:2509.23809)** — QAT method that identifies "deadzone trapping" failure mode and repurposes deadzone-trapped weights as dynamic biases. Claims >4% ARC gain over SOTA ternary, within <1% of FP, 3.0x speedup. Limitation: training-time only — adoption requires Tencent-released Tequila-trained checkpoints (none verified today) or in-house QAT cycle. Deferred.
- **[intake-594] DAQ — Delta-Aware Quantization (arxiv:2603.22324)** — Data-free PTQ preserving post-training deltas (RL / DPO / instruction-tune) via Sign-Preservation-Rate and Cosine-Similarity-of-ΔW metrics instead of reconstruction-error minimization. Claims to recover style-specific capabilities lost under standard PTQ. Limitation: tested in FP8 only at abstract time, where standard PTQ already near-lossless. The load-bearing question (does DAQ help at INT4 / INT2?) is unanswered. Becomes relevant only if/when we move below Q4_K_M. Deferred.

### Delta from this handoff's KV-cache scope

This handoff (`tq3-quantization-evaluation`) tracks **KV-cache** quantization (TurboQuant, TQ3_1S, ChunkKV). The AngelSlim track is **weight** quantization. The portable artefact for both is the same `epyc-llama` rebuild infrastructure but the kernels and PRs are independent. Sub-2-bit weight quant gets its own coordination point: [[angelslim-techniques-evaluation]].

### Caveats (Tier 2b)

- **Sherry is QAT, not PTQ** (correction logged 2026-05-21). Sherry trains on ~10B tokens of UltraFineWeb-style data and cannot be applied to an arbitrary pretrained worker the way GPTQ/AWQ/Q4_K_M can. The STQ1_0 llama.cpp kernel (PR #22836) is generic inference, but real adoption is gated on Tencent (or another party) releasing Sherry-QAT'd checkpoints of a stack-relevant base model. Today only Hy-MT1.5-1.8B and HY-1.8B-2bit are public Sherry-QAT'd weights.
- Sherry evaluated only to 3B params on Intel i7-14700HX (laptop class). Generalization to 7B-122B class on EPYC 9655 (12-channel DDR5, BW-bound regime per `feedback_cpu_decode_bw_bound`) is unverified — the 10% speedup pattern may not transfer.
- All Tequila / DAQ accuracy claims are Tencent self-reported with no third-party reproduction at intake time. ACL 2026 acceptance lifts Sherry credibility specifically (intake-591 credibility=4); intake-593/594 remain credibility=1.

### Action Items (added 2026-05-21; STQ1_0 watch consolidated here 2026-06-12)

- [ ] **Monitor llama.cpp PR #22836 (STQ1_0 kernel) for merge — SINGLE OWNER: this handoff** (consolidated from `llama-cpp-kernel-push-rebase`, archived to [`../completed/llama-cpp-kernel-push-rebase.md`](../completed/llama-cpp-kernel-push-rebase.md) 2026-06-12). On merge: cherry-pick into the next `production-consolidated-v5` (or successor) branch alongside any other pending kernel work.
- [ ] When STQ1_0 lands: llama-bench AngelSlim/Hy-MT1.5-1.8B-1.25bit-GGUF on EPYC 9655 canonical baseline (taskset -c 0-95 -t 96 -fa 1; per `feedback_canonical_baseline_protocol`); compare decode t/s vs Q4_K_M equivalent. If positive at kernel level, note scaling Sherry to worker-class models is gated on a QAT pipeline we do not have (only Hy-MT1.5-1.8B / HY-1.8B-2bit are public Sherry-QAT'd weights).
- [ ] Defer Tequila + DAQ until QAT or sub-4-bit deployment is in scope; not actionable today
