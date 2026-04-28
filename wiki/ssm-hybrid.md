# SSM Hybrid Architectures

**Category**: `ssm_hybrid`
**Confidence**: verified
**Last compiled**: 2026-04-28 (targeted update — slot-promotion reopener)
**Sources**: 10 documents

## Summary

Hybrid State Space Model (SSM) architectures -- specifically Qwen3.5's combination of Delta Net recurrent layers with standard attention layers -- present fundamental challenges for the EPYC inference stack. The core problem is that recurrent layers process tokens sequentially regardless of batch size, which destroys the efficiency of multi-token speculation, tree search, and any technique that relies on parallel token verification. This single architectural constraint has blocked every speculative decoding approach tested and forced the abandonment of MTP-1 speculation despite achieving 78.5% draft acceptance rate.

Qwen3.5-35B-A3B uses 75% Delta Net recurrent layers and 25% standard attention layers. The MTP-1 speculation handoff (now closed) documents exhaustive testing: the draft acceptance rate was excellent (78.5% exact match, 97.7% top-5) and the MTP-only eval cost was minimal (~10ms, 5% of full decode). However, 2-token verification batches cost 3-4x a single decode (560-816ms vs ~220ms) because recurrent layers cannot parallelize across batch tokens. Net speculation throughput was 0.56x baseline -- a 44% slowdown. Every other speculation approach was also ruled out: tree speculation (Approaches 0, A, C) failed on recurrent state costs, MoE self-draft failed on low acceptance, and attention-only draft produced incoherent output.

The only remaining theoretical option is Approach B (linearized Delta Net approximation) at ~40% viability, which is approximate and has been deferred. DFlash (intake-158, block diffusion drafting) validates that Qwen3.5-35B-A3B cooperates well with speculative decoding but requires SGLang/vLLM (GPU-only, no llama.cpp/GGUF).

SEAL control vectors are also incompatible with SSM-hybrid architectures. The SEAL concise reasoning experiment found that applying control vectors to Qwen3.5-35B-A3B (Gated Delta Net) causes catastrophic generation collapse to 1 token, while the same technique works normally on MoE (Qwen3-Coder-30B-A3B) and dense (Qwen2.5-Coder-32B) architectures. This means inference-time activation steering is not viable for SSM-hybrid models.

Nemotron-Cascade 2 (intake-237/238) provides direct benchmarking data: Mamba2 (in Nemotron) vs Delta Net (in Qwen3.5) on RTX 3090, with cascade RL training for small models. This is relevant for understanding the SSM landscape but the GPU-specific benchmarks do not transfer to CPU inference. The Qwen3.5 serving recipe (intake-152) provides configuration tips for hybrid MoE + Delta Net models but the tips are primarily GPU-oriented (vLLM, SGLang).

The Multiscreen architecture (intake-256) represents a potential future alternative -- it replaces softmax attention with absolute query-key screening, achieving sub-quadratic complexity while preserving the attention paradigm. Unlike Delta Net, Multiscreen would theoretically be compatible with existing KV cache and speculation infrastructure. However, no pretrained Multiscreen models exist and no llama.cpp implementation is available. Three additional cross-head attention mechanisms (IHA, MEA, KHA) from the 2026-04-12 research intake also offer alternatives, all requiring pretraining with no retrofit possible.

A deep dive on Memory Caching (intake-354) and Log-Linear Attention (intake-356) reveals a critical correction to the speculation bottleneck analysis: the real killer is sequential verification latency (220ms/token through 30 Delta Net layers, ~90% of round-trip cost), NOT state checkpoint size (50-100ms, ~5%). The recurrence nonlinearity `s_new = exp(g) * s_old + k(x) * beta * (v - s_old^T k)` prevents tree-masked cumulative sum factorization, forcing each token through all 30 layers sequentially. Verifying 6 draft tokens at 220ms each costs 1320ms vs 660ms autoregressive -- fundamentally uneconomical.

**Log-Linear Gated DeltaNet** (ICLR 2026, by Songlin Yang + Tri Dao + Yoon Kim) is the highest strategic priority for the SSM-hybrid stack. It replaces the fixed-size hidden state with a logarithmically growing set of hidden states -- O(L log L) complexity with <0.4% parameter overhead. The state size reduction is dramatic: 4-10x at 262K context (~2GB to ~200-500MB), 20-25x at 1M context (~6-8GB to ~300-400MB). Critically, the smaller replay cost could potentially unblock speculation (currently a firm NO on standard Gated DeltaNet). The matmul-rich parallel form maps to existing ggml infrastructure without GPU-centric sparse kernels. Blocked on pretrained model availability; gate criteria tracked in a dedicated readiness handoff.

Memory Caching (intake-354) maps the growing-memory RNN design space -- O(L) fixed to O(NL) segmented to O(L²) full attention -- with GRM (Gated Residual Memory) and SSC (Sparse Selective Caching) as key variants. However, MC requires pretraining and its caching benefits are marginal against the 220ms/token verification bottleneck (saving ~50ms against ~1320ms total for 6-token verification).

The Qwen3.5 frontdoor benchmark sweep confirmed the frontdoor model's production characteristics: Q4_K_M baseline at 83% quality with 13.8 t/s average, with MoE6 lookup achieving 19.6 t/s. Spec decode was "a bust" for 35B due to SSM checkpoint overhead, and abliteration variants (Q4KS, Q5KS) showed degenerate looping behavior.

## Key Findings

- 75% of Qwen3.5-35B-A3B layers are Delta Net recurrent -- these process tokens SEQUENTIALLY regardless of batch size [mtp-speculative-decoding.md]
- MTP-1 speculation achieved 78.5% acceptance rate but 0.56x net throughput due to 3-4x verification batch cost [mtp-speculative-decoding.md]
- ALL speculation approaches exhausted for hybrid recurrent models: tree (0/A/C), MoE self-draft, attention-only draft, MTP-1 [mtp-speculative-decoding.md]
- SEAL control vectors cause CATASTROPHIC generation collapse (1 token output) on SSM-hybrid architectures [seal-concise-reasoning experiment]
- MTP layer itself uses full attention (gated Q, 16 heads), NOT Delta Net. It is 0.84B params (2.3% of total). Correctly marked non-recurrent in llama.cpp [mtp-speculative-decoding.md]
- Linearized Delta Net approximation (Approach B) is the only unexplored option at ~40% viability -- deferred as approximate [mtp-speculative-decoding.md]
- **CRITICAL bottleneck correction**: Sequential verification latency (220ms/token, ~90% of round-trip) is the real speculation killer, NOT state checkpoint size (50-100ms, ~5%). Recurrence nonlinearity prevents parallel verification [deep-dives/memory-caching-log-linear-attention.md]
- **Log-Linear Gated DeltaNet** (ICLR 2026): O(L log L) hidden state replaces fixed O(L) state. State size 4-10x smaller at 262K, 20-25x at 1M. Could potentially unblock speculation by making sequential replay viable. <0.4% parameter overhead [intake-356, deep-dives/memory-caching-log-linear-attention.md]
- Memory Caching (GRM/SSC) maps the growing-memory design space but requires pretraining and saves only ~50ms against ~1320ms verification -- marginal [intake-354, deep-dives/memory-caching-log-linear-attention.md]
- DFlash validates Qwen3.5-35B-A3B as a good spec-decode target on GPU (2.4-2.8x speedup on B200) but requires SGLang/vLLM [mtp-speculative-decoding.md]
- Qwen3.5-35B-A3B frontdoor: Q4_K_M baseline 83% quality, 13.8 t/s. Spec decode is a bust. MoE6 lookup best acceleration at 19.6 t/s [qwen35-frontdoor-benchmark.md]
- Multiscreen architecture preserves attention paradigm with sub-quadratic complexity -- theoretically compatible with KV cache and speculation, but no implementations exist [multiscreen-attention-evaluation.md]
- IHA (Interleaved Head Attention) is the highest-priority watch item: FlashAttention-compatible, +112% RULER at 16K multi-key retrieval [multiscreen-attention-evaluation.md]

## 2026-04-28 Update — Slot-Promotion Reopener (intake-490)

The "speculation is dead for Qwen3.5 hybrid on CPU" claim is being **reopened** under a NEW mechanism, not retracted. The 6 closed handoffs (mtp-speculative-decoding, ssm-hybrid-acceleration, ssm-checkpoint-speculation, tree-speculation-numa-drafting, dflash-block-diffusion-speculation, v3-hybrid-ssm-regression) all closed under a shared assumption: "verification batch = K × single-token cost because Delta Net layers are sequential". They are accurate under that assumption.

intake-490 (PyTorch SGLang blog, Dec 2025) introduces **slot promotion**: each draft token gets a private state slot computed as `S_new = S_parent + Δ(k,v,β,g)`; rejected slots are discarded, accepted slot is promoted. This is architecturally compatible with Delta Net (the recurrence is deterministic from a parent state plus new inputs). Combined with DFlash-style NUMA-parallel single-token verify (one candidate per NUMA quarter), the per-candidate cost drops from 450 MB clone (our prior `clone_cell` failure) to ~KB staged inputs, AND verification wall-clock for K candidates drops from `K × single-token` to `1 × single-token` per quarter. Closure-inflation policy compliance: gates A,B,C met under prior assumption (preserved); gate D unmet under new per-candidate-slot assumption (test target).

Phase 0 falsification probe is queued for the autonomous CPU-optimization agent's next session. Tracked at [`hybrid-ssm-slot-promotion-spec-dec.md`](../handoffs/active/hybrid-ssm-slot-promotion-spec-dec.md). Cost model projects ~1.4× single-instance per-request latency on Qwen3.5-35B-A3B Q4_K_M if Phase 1 lands (trades aggregate-NUMA-4-way for per-request latency — right tradeoff for interactive workloads, wrong for batch).

## Actionable for EPYC

- **Slot-promotion reopener is the active investigation as of 2026-04-28**: the 6 closed handoffs remain accurate under their prior cost-model assumption, but the per-candidate-slot assumption has never been tested in our fork. Phase 0 is research-only (read intake-490 + trace Delta Net state in `delta-net-base.cpp`/`qwen35moe.cpp`/`llama-context.cpp`/`cparams.h`); no code changes deferred behind Phase 0 gate. NO-GO scopes closure narrowly to "slot-promotion in our fork's ggml graph builder is HIGH risk", does NOT generalize to "hybrid spec-dec dead".
- **Use lookup-based acceleration instead**: MoE6 lookup achieves 19.6 t/s vs 13.8 t/s baseline (+42%). This is the best acceleration available for Qwen3.5 on CPU.
- **Do NOT apply SEAL control vectors to SSM-hybrid models**: Catastrophic failure confirmed. Only apply to MoE (works: -7.5% tokens) and dense (neutral) architectures.
- **MTP-1 IS viable on dense attention-only models**: The 78.5% acceptance rate and ~5% MTP overhead would yield ~1.7x throughput on Llama, Mistral, standard Qwen2.5 architectures. Reuse the implementation for non-hybrid models.
- **Monitor Log-Linear Gated DeltaNet first**: Highest strategic priority -- directly upgrades 75% of production stack, CPU-friendly (matmul-rich). Gate: pretrained checkpoint + reference inference code available. Track via `log-linear-gated-deltanet-readiness.md`.
- **Monitor Multiscreen and IHA**: Both could provide sub-quadratic attention that is compatible with speculation. Watch for pretrained models and llama.cpp implementations.
- **If GPU serving is added**: DFlash becomes viable for Qwen3.5-35B-A3B (2.4-2.8x speedup reported on B200). Keep the MTP GGUF files for potential GPU use.
- **Consider dense model alternatives**: Qwen3.5-27B Q6K (dense, 2.54 avg quality, 9.4 t/s base, 13.1 t/s with spec k4) may offer better total throughput when speculation works.

## Open Questions

- Would a linearized Delta Net approximation (Approach B, ~40% viability) provide any practical speedup, or is the quality degradation from approximation too high?
- Will future Qwen model generations reduce the ratio of recurrent layers to make speculation viable?
- Can the Multiscreen architecture be retrofitted to existing model weights, or does it require pretraining from scratch?
- How does Nemotron-Cascade 2's Mamba2 compare to Qwen3.5's Delta Net on CPU inference specifically?
- Would REAP expert pruning on Qwen3.5 (removing routed experts to reduce model size) interact with Delta Net layer behavior?
- Is O(N x L x log L) sequential replay cost on Log-Linear GDN low enough for net-positive speculation on CPU?
- Does O(log L) state set work with q4_K_M weight quantization and q4/q8 KV cache quantization?
- When will pretrained Log-Linear Gated DeltaNet checkpoints become publicly available?

## Related Categories

- [Speculative Decoding](speculative-decoding.md) -- MTP-1 failure is the primary consequence of SSM-hybrid architecture
- [KV Cache](kv-cache.md) -- Delta Net uses recurrent state instead of KV cache for its layers; Multiscreen would change KV dynamics
- [MoE Optimization](moe-optimization.md) -- Qwen3.5 is simultaneously MoE and SSM-hybrid; MoE acceleration (lookup) is the viable path
- [Training & Distillation](training-distillation.md) -- SEAL control vector incompatibility limits distillation options for hybrid models

## Source References

- [MTP speculative decoding handoff](/workspace/handoffs/completed/mtp-speculative-decoding.md) -- Complete history of all speculation approaches tested, timing results, root cause analysis, bug fixes
- [SEAL concise reasoning experiment](/mnt/raid0/llm/epyc-inference-research/docs/experiments/seal-concise-reasoning.md) -- Control vector catastrophic failure on Gated Delta Net
- [Multiscreen attention evaluation](/workspace/handoffs/active/multiscreen-attention-evaluation.md) -- Sub-quadratic attention alternative, watch item status, expanded mechanism cluster
- [Qwen3.5 frontdoor benchmark](/workspace/handoffs/completed/qwen35-frontdoor-benchmark.md) -- Production benchmark results, spec-decode bust confirmation, MoE lookup acceleration
- [intake-152](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html) Qwen3.5 serving recipe -- Configuration tips for hybrid MoE + Delta Net
- [intake-237/238] Nemotron-Cascade 2 -- Mamba2 vs Delta Net benchmarks, cascade RL
- [Log-Linear Gated DeltaNet readiness tracker](/workspace/handoffs/active/log-linear-gated-deltanet-readiness.md) -- Gate criteria, implementation plan, monitoring targets for Log-Linear GDN adoption
- [Memory Caching + Log-Linear Attention deep dive](/workspace/research/deep-dives/memory-caching-log-linear-attention.md) -- Bottleneck correction (verification not state copy), MC/Log-Linear analysis, llama.cpp implementation path
- [intake-354](https://arxiv.org/abs/2602.24281) Memory Caching: RNNs with Growing Memory -- GRM/SSC design space, O(NL) segmented caching
- [intake-356](https://arxiv.org/abs/2506.04761) Log-Linear Attention -- ICLR 2026, O(L log L) Gated DeltaNet variant by architecture creators
- [intake-256](https://arxiv.org/abs/2604.01178) Screening Is Enough -- Multiscreen architecture replacing softmax attention
- [intake-490](https://pytorch.org/blog/hybrid-models-meet-sglang-more-than-full-attention/) PyTorch SGLang blog (Dec 2025) -- Slot-promotion mechanism for hybrid SSM speculation; per-candidate state slots via `S_new = S_parent + Δ(k,v,β,g)`; the basis for the 2026-04-28 reopener
- [Hybrid SSM slot-promotion reopener handoff](../handoffs/active/hybrid-ssm-slot-promotion-spec-dec.md) -- Phase 0 falsification spec, Phase 1+ implementation sketch (~360-635 LOC), closure-inflation policy gate enumeration
