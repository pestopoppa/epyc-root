# SSM Hybrid Architectures

**Category**: `ssm_hybrid`
**Confidence**: verified
**Last compiled**: 2026-04-30
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

Phase 0 falsification probe is queued for the autonomous CPU-optimization agent's next session. Tracked at [`hybrid-ssm-slot-promotion-spec-dec.md`](../handoffs/completed/hybrid-ssm-slot-promotion-spec-dec.md). Cost model projects ~1.4× single-instance per-request latency on Qwen3.5-35B-A3B Q4_K_M if Phase 1 lands (trades aggregate-NUMA-4-way for per-request latency — right tradeoff for interactive workloads, wrong for batch).

### Slot-promotion outcome (CLOSED 2026-04-30)

Phase 1.0 GATE MET. Phase 1.1 dispatcher v1 LANDED (commit `d45126db5` on `feature/cpu-ep-inter-process` in llama.cpp-experimental, +386 LOC: alt-path selection, sequential pre-decode aux state sync, parallel aux decode threads, per-ctx sample-and-accept reducer, winner-state commit).

**Phase 1.1 ≥1.3× gate NOT MET on Qwen3.6-35B-A3B-Q8_0 + Qwen3-1.7B-Q8_0 drafter**. Canonical 3-prompt × 2-rep result: K=1 = 11.40 t/s mean vs K=4 dispatcher v1 = 7.42 t/s mean (K=4 is 35% slower). Divergent-tree sensitivity sweep across 4 (p_split, temperature) configs × 5 prompts (canonical 3 + creative haiku + open-ended consciousness) confirmed dispatcher engages 62 times — but **primary wins 60/62 (97%)**, with the 2 aux-winning rounds delivering just +1 marginal accepted token each. Per-round economics: ~22 ms K-parallel overhead vs ~2.5 ms expected savings = -20 ms/round net loss.

The cost-model projection (1.4× single-instance per-request latency, "trades aggregate-NUMA-4-way for per-request latency") was based on the assumption that K-parallel verify would deliver gain via aggregate decode parallelism. That assumption fails for this drafter/target pair: aux paths verify the SAME tokens primary already verifies in 97% of rounds, even at p_split=0.001 + temperature=0.7. The deeper issue is win-rate, not threading.

**Closure scope (per closure-inflation policy)**: mechanism is structurally net-negative for THIS drafter/target/workload class. Does NOT generalize to "K-parallel verify is dead" — different drafter models (larger drafter that produces alt branches more aligned with target sampling), different target models, different K values, and very different workload classes (long-form generation with frequent ambiguity) remain unevaluated.

**Disposition**: dispatcher v1 stays in tree as disabled-by-default (`--spec-numa-quarters` defaults to 1; `LLAMA_ARG_SPEC_NUMA_QUARTERS` env equivalent). The implementation is correct, race-free (parallel-aux-sync race condition was discovered + fixed by switching to sequential pre-decode sync), and costs nothing at K=1. Re-evaluate on different drafter/target pairs.

The 6.10× ceiling probe that motivated the reopener measured AGGREGATE THROUGHPUT across independent slots (NUMA-quarter splitting for 4× concurrent inference), not per-request K-parallel verify gain. These are two different mechanisms; the aggregate-throughput one is already deployed in production via the orchestrator's 4×24t splits.

CPU20 bundles: [`2026-04-30-state-sync-cost-probe/`](../../epyc-inference-research/data/cpu_optimization/2026-04-30-state-sync-cost-probe/) (canonical 3×2 + state-sync probe), [`2026-04-30-divergent-tree-sweep/`](../../epyc-inference-research/data/cpu_optimization/2026-04-30-divergent-tree-sweep/) (4 configs × 5 prompts engagement probe).

## Updates — 2026-04-28

### Closure-inflation correction on the 7 prior approaches

The 7 approaches catalogued in [`completed/ssm-hybrid-acceleration.md`](../handoffs/completed/ssm-hybrid-acceleration.md) — clone_cell, K-token-batch, MoE self-draft, attention-only draft, prefix prefetch, per-token speculation, multi-context replay — closed under a single shared assumption: **"verification batch = K × single-token cost because Delta Net layers are sequential, and per-candidate state cost is borne by full-state cloning"**. All 7 closures are preserved as accurate under that cost model. The slot-promotion reopener does NOT retract them; it tests a different cost model. This is a closure-inflation-policy-compliant correction: prior gates A/B/C met under prior assumption, gate D unmet under per-candidate-slot assumption.

### Per-candidate state slot mechanism

The core mechanism is the architectural fact that Delta Net's recurrence is deterministic from parent state plus new inputs:

```
S_new = S_parent + Δ(k, v, β, g)
```

This means a candidate token's state can be staged as ~KB of `(k, v, β, g)` inputs plus a pointer to `S_parent`, rather than as a ~450 MB clone of the full state (the failure mode of our prior `clone_cell` attempt). On rejection, the slot is discarded; on acceptance, the slot is promoted (`S_parent ← S_new` for the accepted branch).

This works because:
- Delta Net stores its state as a fixed-size matrix (not a growing KV cache)
- The `Δ` function is a small matrix-vector update parameterised by `(k, v, β, g)` that we already compute per-token in the standard non-speculative path
- Forking in the parent state is the same operation regardless of how many candidates fork from it

### DFlash-style NUMA-parallel single-token verify

Combined with the slot mechanism: one candidate per NUMA quarter processes its drafted token independently on isolated DRAM + L3 capacity. Each NUMA node holds its own `S_parent` snapshot and processes its candidate's `Δ` to produce the candidate `S_new`, then evaluates the verification logits.

This avoids the 3–4× batch-cost multiplication that plagued sequential recurrent replay on hybrid models in the K-token-batch approach (closed). Wall-clock for K candidates is `1 × single-token` per quarter rather than `K × single-token` sequential.

### Targets and projected operating point

Slot-promotion Phase 1 testing candidates: Qwen3.5-35B-A3B (75% Delta Net + 25% standard attention) and Qwen3-Next-80B-A3B (same hybrid topology, larger). Cost model projects ~1.4× single-instance per-request latency. This is a per-request gain, not aggregate — it trades the 6.7× NUMA-4-way aggregate for interactive-latency. Right tradeoff for interactive coding workloads, wrong for batch eval.

### Log-Linear Gated DeltaNet readiness (monitoring)

Per [`log-linear-gated-deltanet-readiness.md`](../handoffs/active/log-linear-gated-deltanet-readiness.md). Monitoring target (intake-356, ICLR 2026, by Songlin Yang + Tri Dao + Yoon Kim — the architecture creators). Gate criteria: pretrained checkpoint public + reference inference code available.

The strategic appeal of Log-Linear Gated DeltaNet is direct: the O(L log L) hidden state size is 4–10× smaller at 262K context (~2 GB → ~200–500 MB) and 20–25× smaller at 1M context. If state replay cost drops by the same factor, the verification-wall cost model assumption that closed the 7 prior approaches is fundamentally weakened — slot-promotion + Log-Linear could compound, or Log-Linear alone could unblock the K-token-batch approach. Currently blocked on pretrained models. Highest strategic priority for the SSM-hybrid stack independent of slot-promotion outcome.

### Multiscreen attention survey (cluster expansion)

Per [`multiscreen-attention-evaluation.md`](../handoffs/active/multiscreen-attention-evaluation.md). The sub-quadratic attention cluster has expanded beyond the original Multiscreen mechanism (replaces softmax with screening; 40% params; 2.3–3.2× latency at 100K context).

Highest-priority watch item: **IHA (Interleaved Head Attention)** — +112% RULER at 16K multi-key retrieval, FlashAttention-compatible. None of the cluster have GGUF implementations, and all are pretraining-required architectures (no retrofit possible to existing weights). Monitor for community reproductions and pretrained checkpoints.

The reason these are tracked under SSM-hybrid (and not under speculative-decoding or KV-cache) is that they preserve the standard-attention paradigm with sub-quadratic cost, which would theoretically be compatible with KV cache and speculation infrastructure — they are an alternative to Delta Net rather than to attention itself.

## Actionable for EPYC

- **Slot-promotion reopener CLOSED 2026-04-30**: the 6 prior closed handoffs remain accurate under their prior cost-model assumption (preserved). The per-candidate-slot assumption was tested end-to-end through Phase 1.1 dispatcher v1 (commit `d45126db5`, +386 LOC). Result: mechanism is functional and race-free, but **net-negative on Qwen3.6-35B-A3B + Qwen3-1.7B drafter** because primary wins 60/62 (97%) of K-parallel rounds across 4 (p_split, temperature) configs × 5 prompts. K=4 = 7.42 t/s vs K=1 = 11.40 t/s on canonical 3×2. Closure narrowly scopes to THIS drafter/target/workload class; does NOT generalize to "hybrid spec-dec dead" or "K-parallel verify is dead". Different drafters, targets, K values, and workload classes (long-form generation with frequent ambiguity) remain unevaluated.
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
- [Hybrid SSM slot-promotion reopener handoff](../handoffs/completed/hybrid-ssm-slot-promotion-spec-dec.md) -- CLOSED 2026-04-30: Phase 1.0 GATE MET, Phase 1.1 dispatcher v1 LANDED but mechanism net-negative on Qwen3.6-35B + Qwen3-1.7B (97% primary wins); dispatcher v1 stays in tree disabled-by-default

## Updates — 2026-04-29 (PM)

**Lightning Attention port unblocked via existing GLA op (intake-503)** — Audit of `llama.cpp-experimental` reveals `GGML_OP_GATED_LINEAR_ATTN` is already implemented (`ggml/src/ggml-cpu/ops.cpp:10605`), with `llm_build_delta_net_base` (`src/models/models.h:23`) hosting Qwen3.5/3.6/kimi-linear/qwen3next variants. Lightning Attention's only meaningful difference from GLA is fixed power-law decay vs learned per-token gating — feed `g` as a constant tensor, done. v1 port is **3-5 days using existing infrastructure**, not multi-week from scratch as initially framed.

Ant Group Ling-Linear-2.0 family (intake-503, arxiv:2510.19338): Ring-mini-linear-2.0 (16B/957M-active, M=4 hybrid ratio), Ring-flash-linear-2.0 (104B/6.1B-active, M=7). Reports ~1/10 inference cost vs 32B dense, AIME-25 86.51% Ring-flash. Open weights on HuggingFace. **No RULER/NIAH/LongBench published** — long-context claim rests on indirect reasoning benchmarks (yellow flag).

Ring-mini at 957M active is genuinely Q-scorer / drafter territory. A working port unlocks a candidate small drafter for spec-dec experiments — architecture mismatch with Qwen-GDN target (Ring uses Lightning Attention; Qwen uses Gated DeltaNet) is a research question, not a default-yes, but the size + reasoning quality combination is unusual.

Tracked at [`lightning-attention-port.md`](../handoffs/active/lightning-attention-port.md) — phases L1 scoping → L2 GGUF converter (~50 LOC) → L3 model variant (~150 LOC, derive `llm_build_ring_linear` from `llm_build_delta_net_base`, mirror `llm_build_kimi_linear` template) → L4 test (gated on inference approval) → L5 optional dedicated `GGML_OP_LIGHTNING_ATTN` op exploiting constant `g` for prefill speedup.

- [intake-503](https://arxiv.org/abs/2510.19338) Every Attention Matters — Ling-Linear-2.0 hybrid (M=4 / M=7) with Lightning Attention, FP8 LingHe kernels, MTP layers retained from Ling 2.0; open weights for Ring-mini (16B/957M-active) + Ring-flash (104B/6.1B-active)
- [Ling-Linear / Lightning Attention deep-dive](../research/deep-dives/ling-linear-lightning-attention-hybrid.md) — corrected effort estimate after GLA-op audit
- [Lightning Attention port handoff](../handoffs/active/lightning-attention-port.md) — active port via existing GLA op, L1-L5 phases

## Lightning Attention port — L1 scoping COMPLETE, GO verdict (2026-04-30)

The Ling-Linear-2.0 port advanced from "GLA-op finding" to a full L1 scoping pass. Six findings, all gates green:

### Architecture confirmed (intake-503, Ring-mini-linear-2.0)

- `model_type = "bailing_moe_linear"`, `architectures = ["BailingMoeLinearV2ForCausalLM"]` — NOT `"ling_linear"` as the original deep-dive guessed
- Linear-attn class: `BailingMoeV2LinearAttention`, kernel reference: `fla.chunk_simple_gla` + `fla.fused_recurrent_simple_gla` from `flash-linear-attention v0.3.2`. **FLA "simple GLA" = scalar per-head decay GLA = exactly what `ggml_gated_linear_attn` implements.**
- 20 layers, 16 Q heads, 4 KV heads, head_dim 128, `layer_group_size=5` (M=4 pattern: 4 linear : 1 softmax via `(layer_idx + 1) % 5 == 0`), `partial_rotary_factor=0.5` on softmax layers only, `max_position_embeddings=131072`
- 256 experts, 8 active per token, 1 shared, `first_k_dense_replace=1`

### GLA op semantics (mathematical correctness)

The recurrence kernel `ggml_compute_forward_gla_f32` accepts `g[t,h,i]` with full per-token, per-head, per-key-dim resolution. To express Lightning Attention's `S_t = γ_h · S_{t-1} + k_t v_t^T` (single per-head fixed scalar), set `g[t,h,i] = γ_h` for all `t, i`. **No shape mismatch, no kernel modification needed for v1.** Constant fill is a degenerate case the kernel handles correctly.

Decay formula extracted: ALiBi-style `(2^-0.5)^h` per-head, scaled by `1-(l-1)/(L-1)+1e-5` per-linear-layer, sign-flipped, exp'd at convert time.

### Template strategy CORRECTED (was wrong in original handoff)

The original recommendation to derive `llm_build_ring_linear` from `llm_build_delta_net_base` is **wrong**. The base class methods all dispatch to `ggml_gated_delta_net` (GDN), not `ggml_gated_linear_attn` (GLA):

| Op | Recurrence | Used by |
|----|-----------|---------|
| `ggml_gated_delta_net` (GDN) | `S_t = S_{t-1}(g_t I − β_t k_t k_t^T) + β_t k_t v_t^T` | kimi-linear, qwen3.5, qwen3-next, qwen3.5-moe |
| `ggml_gated_linear_attn` (GLA) | `S_t = g_t · S_{t-1} + k_t v_t^T` (element-wise per-(t,h,i)) | RWKV-6 (qrwkv mode only) |

Lightning Attention is mathematically a **degenerate-`g` GLA**, not a GDN special case. L3 template must mirror `llm_build_rwkv6_base::build_rwkv6_time_mix` (the only existing GLA consumer in tree), stripped of RWKV-specific time-shift/lerp/receptance machinery. Recommended L3 inheritance: derive `llm_build_ring_linear` directly from `llm_graph_context`, NOT from `llm_build_delta_net_base` and NOT from `llm_build_rwkv6_base`.

### Backend coverage (CPU-target green; pre-existing gaps elsewhere)

| Backend | Status |
|---------|--------|
| CPU (AVX/AVX-512/SVE/NEON + scalar) | ✅ `ggml/src/ggml-cpu/ops.cpp:10524-10702` |
| CUDA / HIP / MUSA | ✅ `ggml/src/ggml-cuda/gla.cu` (HIP+MUSA inherit via CMake glob) |
| SYCL | ✅ `gla.cpp` (106 LOC) |
| CANN | ✅ `aclnn_ops.cpp` |
| BLAS / zDNN / zenDNN | ✅ falls back to CPU |
| Metal / Vulkan / OpenCL / WebGPU / OpenVINO / Hexagon | ❌ pre-existing gaps from RWKV-6 |

For v1 CPU-only EPYC port: fully covered. For upstream contribution: same backend matrix as RWKV-6 already has — adding Lightning Attention does NOT introduce a new hole.

### Threading caveat

GLA kernel partitions heads across threads. For Ring-mini at H=16, EPYC 96-thread bind would have only 16 of 96 threads doing work per call → underutilization on linear-attn layers. **Flag for L4 throughput analysis.**

### Hybrid handling (M=4)

Periodic softmax layers reuse the standard `build_attn` path — no new code needed. The `if (hparams.is_recurrent(il)) { GLA path } else { build_attn path }` pattern from kimi-linear (line 120, 206) is reusable structurally even though we don't inherit from `delta_net_base`.

### Decision gate

**GO** for L2 (GGUF converter, ~50 LOC) + L3 (model variant, ~150 LOC). Both cleared to start, no inference required. L4 inference test path remains GATED on user approval. **Total port estimate: 3-5 days of focused work** for working `convert_hf_to_gguf.py --arch ling_linear` + `llama-cli` decode on Ring-mini Q4_K_M.

### Why this matters (activation value)

Ring-mini-linear-2.0 (16B/957M-active) opens **drafter territory** — 957M active = Q-scorer-class. Ring-flash-linear-2.0 (104B/6.1B-active) opens architect-tier territory. Both are CPU-friendly intermediate paths between full softmax (Qwen3) and pure SSM (Mamba/Jamba).

### Sources

- [intake-503](https://arxiv.org/abs/2510.19338) Every Attention Matters — Ling-Linear-2.0 (full architecture details)
- [`research/deep-dives/ling-linear-lightning-attention-hybrid.md`](../research/deep-dives/ling-linear-lightning-attention-hybrid.md) — corrected effort estimate after GLA-op audit
- [`handoffs/active/lightning-attention-port.md`](../handoffs/active/lightning-attention-port.md) — L1 scoping COMPLETE block + L2/L3 cleared
- HF source verification: https://huggingface.co/inclusionAI/Ring-mini-linear-2.0/raw/main/{config.json,modeling_bailing_moe_linear_v2.py,configuration_bailing_moe_linear_v2.py}
- GLA reference call site: `src/models/rwkv6-base.cpp:137` (qrwkv branch)
