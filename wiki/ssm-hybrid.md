# SSM Hybrid Architectures

**Category**: `ssm_hybrid`
**Confidence**: verified (CPU/arch findings) · observation (2026-07-06 MI210 bf16-GDN-state numbers — single-run, no P-GPU-1 per MEASUREMENT.md)
**Last compiled**: 2026-08-23 (evening wave-2 compile: MiniCPM-SALA — the paper is wrong about its own linear half (Simple GLA, not Lightning Attention) and a correctness-first port needs ZERO new ggml operators; the Gates 4/5 portability addendum (a device-agnostic oracle, a ggml primitive per mixer); GDN-2 at 1.0× state for +375.5M always-active params; #27018 `LLM_ARCH_MINIMAX_01` merged four days post-freeze and absent from our tree; the CoT-SFT amnesia hazard (arXiv 2606.11052) — a recall failure invisible to PPL+NIAH on our exact frontdoor architecture — and the strongest published argument AGAINST replacing our 10 full-attention layers with sparse ones (arXiv 2606.15378, seven of nine authors SALA co-authors); see bottom sections; earlier same-day: **K28 fused chunked GDN kernel closed as a measured no-go on the full-model ceiling — GDN is only ~12–15% of MI210 prefill device time, and the verdict survived the later discovery that a working CDNA2 kernel already existed upstream**; earlier 2026-08-12 note: **the headline reason to want Log-Linear GDN is inverted on the released checkpoint** — its state is ~15× *larger* than standard GDN, not 4–10× smaller; and all three activation gates fired, six months after the checkpoint went public, because three staleness reviews asserted "no checkpoint" without querying HuggingFace — see below; earlier 2026-08-08 note: LFM2.5-2.6B is a runnable worker challenger, not yet a replacement)
**Sources**: 20 documents

## Compiled Update — 2026-08-12: the state-size argument runs backwards, and the monitoring that should have caught it never ran

**Confidence: verified** for the artifact facts (tensor dims, config, license, gate dates, HuggingFace publication date) — these were read off the released checkpoint. **Inferred/undecided** for whether to port: that decision is explicitly the operator's and is gated on an oracle that does not exist yet.

### RETRACTED: "Log-Linear GDN gives a 4–10× state-size reduction"

This page and its index entry have carried the 4–10× state reduction as the reason Log-Linear Gated DeltaNet could unblock hybrid-SSM speculation. **Measured against the actual released checkpoint, the comparison runs the other way.** Log-linear GDN replicates state across a 15-level set, so per layer its state is **≈15× larger** than standard GDN — **≈557 MB vs ≈37 MB** over 21 layers at f32.

The reduction claim is not fabricated, it is *mis-anchored*: it holds against a **softmax-attention KV cache**, which grows linearly in sequence length, and never against standard GDN, which is already O(1). The original bullet did not name its baseline, and that omission is what let the number face the wrong direction for months. Any planning that assumed log-linear GDN reduces *our* residents' state must be re-derived.

### The checkpoint had been public for six months, and three reviews said it wasn't

`hanguo/log-linear-attention` has been public since **2026-02-13**. The handoff recorded "no pretrained checkpoint" from 2026-04-14, and **two later staleness reviews restated it** — under a standing monthly-cadence monitoring commitment. All three activation gates fired on 2026-08-12 when someone finally queried the API. The gate was not late upstream; **the monitoring never executed**, and a review that restates a prior status without re-deriving it is indistinguishable from one that checked.

Artifact facts as released: **795.690 M params, F32, ≈3.2 GB, 21 layers, hidden 1536, 6 heads, head_dim 192**. Licensing has a wrinkle worth recording — MIT ships *inside the model folder*, while the GitHub repository itself carries no LICENSE and reports `license: null`.

### What is genuinely undecided

Neither the numerical oracle (`hattention_recurrent()` wired into the forward pass) nor the GGUF converter tensor map exists, and the operator decision on whether to port is explicitly gated behind the oracle. The sources do **not** settle whether log-linear GDN is worth porting; they settle that the reason previously given for wanting it was wrong.

### Related: the verification wall this was supposed to relieve

Nothing in this pass changes the standing finding that sequential Delta Net verification, not draft availability, is the CPU blocker for hybrid-SSM speculation. What changes is that the state-size lever cannot be the argument for relieving it.

### Source References (2026-08-12)

- [`log-linear-gated-deltanet-readiness.md`](../handoffs/active/log-linear-gated-deltanet-readiness.md) — the three fired gates, checkpoint identity and license, and the inverted state-size derivation.
- [`progress/2026-08/2026-08-12.md`](../progress/2026-08/2026-08-12.md) — the retraction in its session context and the "three gates fired and were never checked" framing.
- [`qwen36-27b-cpu-feasibility.md`](../handoffs/active/qwen36-27b-cpu-feasibility.md) — CPU-side feasibility context for hybrid residents on this host.

## Compiled Update — 2026-08-08: LFM2.5-2.6B is a runnable worker challenger, not yet a replacement

**Confidence: verified for artifact identity, template behavior, and static runtime support; external for vendor benchmark numbers.**

LFM2.5-2.6B is a 2.69B dense hybrid with 22 short-convolution blocks, eight GQA blocks, a 128K
vocabulary, and 131,072-token context. The official repository publishes both Q4_K_M and Q8_0 GGUFs,
and frozen production-consolidated-v8 already contains LFM2 loading plus the specialized LFM2.5 Pythonic
tool parser. The official template always opens a reasoning section; separate LEAP sidecars omit that
reasoning prefill and tool rendering, so they are not interchangeable without a behavioral parity test.

The small footprint makes the model a credible `worker_general` challenger under EPYC's noncommercial
use, but neither vendor tables nor community anecdotes compare it with the actual Gemma4 26B-A4B
incumbent under one harness. The decision gate is therefore a matched three-arm run—official Q4_K_M,
official Q8_0, and unchanged Gemma4—with identical prompts, tool schema, seeds, limits, template, and
scorer era. Promotion depends on strict task success and tool compliance together with reasoning-token
overhead, retries, TTFT, prompt/decode throughput, peak memory, and complete wall time. No role alias,
registry, stack, or production process changes on architectural promise alone.

### Source References

- [Architect Model Comparison Benchmark](../handoffs/active/architect-model-selection-bench.md) — WG-LFM-1 matched Q4/Q8/Gemma decision contract
- Intake 1006 in [the research index](../research/intake_index.yaml) — launch article, mandatory reasoning, and benchmark caveats
- Intake 1014 in [the research index](../research/intake_index.yaml) — base model/config/license and frozen-v8 static support
- Intake 1019 in [the research index](../research/intake_index.yaml) — pinned official GGUF revision and artifact/template inspection

## Summary

Hybrid State Space Model (SSM) architectures -- specifically Qwen3.5's combination of Delta Net recurrent layers with standard attention layers -- present fundamental challenges for the EPYC inference stack. The core problem is that recurrent layers process tokens sequentially regardless of batch size, which destroys the efficiency of multi-token speculation, tree search, and any technique that relies on parallel token verification. This single architectural constraint has blocked every speculative decoding approach tested and forced the abandonment of MTP-1 speculation despite achieving 78.5% draft acceptance rate.

Qwen3.5-35B-A3B uses 75% Delta Net recurrent layers and 25% standard attention layers. The MTP-1 speculation handoff (now closed) documents exhaustive testing: the draft acceptance rate was excellent (78.5% exact match, 97.7% top-5) and the MTP-only eval cost was minimal (~10ms, 5% of full decode). However, 2-token verification batches cost 3-4x a single decode (560-816ms vs ~220ms) because recurrent layers cannot parallelize across batch tokens. Net speculation throughput was 0.56x baseline -- a 44% slowdown. Every other speculation approach was also ruled out: tree speculation (Approaches 0, A, C) failed on recurrent state costs, MoE self-draft failed on low acceptance, and attention-only draft produced incoherent output.

The only remaining theoretical option is Approach B (linearized Delta Net approximation) at ~40% viability, which is approximate and has been deferred. DFlash (intake-158, block diffusion drafting) validates that Qwen3.5-35B-A3B cooperates well with speculative decoding on GPU. The former SGLang/vLLM-only, no-llama.cpp/GGUF framing is obsolete: upstream llama.cpp merged `draft-dflash` in PR #22105 on 2026-06-28 and production carries the 2026-07-18 forward-port. That availability change does not alter the CPU no-go: Delta Net verification remains sequential and uneconomical.

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
- DFlash validates Qwen3.5-35B-A3B as a good spec-decode target on GPU (2.4-2.8x speedup on B200). Upstream llama.cpp now supports `draft-dflash`; the remaining CPU blocker is sequential Delta Net verification, not DFlash or GGUF availability [mtp-speculative-decoding.md]
- **bf16 Delta-Net recurrent state is a GPU aggregate lever — the campaign's one clean GDN kernel win (2026-07-06, MI210, OBSERVATION).** On gfx90a, storing the recurrent state in bf16 instead of fp32 **halves the state gather+scatter** (not just kernel compute), giving **+21.5% aggregate @B=32** on Qwen3.5-27B (162.8→197.8 t/s; drift PPL +0.0035%, byte-identical isolation, `test-backend-ops` 1103/1103) and generalizing across **all three GDN-hybrid sizes** — deployed frontdoor 35B-A3B **+17.7%**, architect 122B IQ2 **+16.4%** — plus the qwen3next-80B GDN family (+13.3%, first confirmation outside qwen3.5). Runtime-gated `GGML_CUDA_GDN_STATE_BF16` (default-off, byte-identical when off), commit `496e2f098`, carried onto the reconciled v7-candidate kernel. High-batch-only (B=1 neutral). This is a *serving* lever orthogonal to the CPU verification wall above — it does not unblock speculation, it makes the recurrent machinery cheaper on GPU. Detail in [Hardware Optimization](hardware-optimization.md). [fable5-window2-findings-05c, kernel-reconciliation-audit]
- Qwen3.5-35B-A3B frontdoor: Q4_K_M baseline 83% quality, 13.8 t/s. Spec decode is a bust. MoE6 lookup best acceleration at 19.6 t/s [qwen35-frontdoor-benchmark.md]
- Multiscreen architecture preserves attention paradigm with sub-quadratic complexity -- theoretically compatible with KV cache and speculation, but no implementations exist [multiscreen-attention-evaluation.md]
- IHA (Interleaved Head Attention) is the highest-priority watch item: FlashAttention-compatible, +112% RULER at 16K multi-key retrieval [multiscreen-attention-evaluation.md]
- **GLM-MoE-DSA wiring is now closed on current source; the remaining question is sparse-compute behavior.** Experimental-v7 `3dee86a5a` routes `LLM_ARCH_GLM_DSA` through `llama_kv_cache_dsa` and the DeepSeek32 DSA graph, and the current-source smoke returned `READY` with `Lightning Indexer enabled`. The open gate is D2 profiling to determine whether final attention is dense-mask or real sparse, plus the long-context quality path. `verified` (current-source smoke + source audit) [llama-cpp-dsa-contribution.md, glm51-reap-cpu-evaluation.md]
- **IndexShare reuses one sparse-attention indexer across every 4 sparse-attn layers**, cutting per-token FLOPs ~2.9x at 1M context (arXiv 2603.12201), introduced with GLM-5.2. It is an indexer-amortization lever stacked on top of DSA — a sparse-attention efficiency mechanism distinct from the linear/recurrent (Delta Net) family the page otherwise tracks. `external` (vendor/preprint) [intake-699]

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

CPU20 bundles: [`2026-04-30-state-sync-cost-probe/`](../repos/epyc-inference-research/data/cpu_optimization/2026-04-30-state-sync-cost-probe/) (canonical 3×2 + state-sync probe), [`2026-04-30-divergent-tree-sweep/`](../repos/epyc-inference-research/data/cpu_optimization/2026-04-30-divergent-tree-sweep/) (4 configs × 5 prompts engagement probe).

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
- [intake-699](https://huggingface.co/unsloth/GLM-5.2-GGUF) GLM-5.2-GGUF (unsloth dynamic quants of zai-org/GLM-5.2) -- 754B GLM-MoE-DSA, MIT, 1M context; DSA forward pass unimplemented in our fork (dense-MLA fallback, gated on PR #21149); new IndexShare (arXiv 2603.12201) reuses the sparse-attn indexer across every 4 layers for ~2.9x FLOP cut at 1M context
- [llama.cpp DSA contribution handoff](../handoffs/active/llama-cpp-dsa-contribution.md) -- PR #21149 tracking; `LLM_ARCH_GLM_DSA` dense-MLA fallback; one forward-pass impl unlocks V3.2 + GLM-5.1 + GLM-5.2
- [GLM-5.1 REAP CPU evaluation handoff](../handoffs/active/glm51-reap-cpu-evaluation.md) -- GLM-5.2 elevated to PRIMARY GLM-MoE-DSA target (supersedes 5.1); storage viable via UD-IQ2; gated on DSA forward pass
- [intake-490](https://pytorch.org/blog/hybrid-models-meet-sglang-more-than-full-attention/) PyTorch SGLang blog (Dec 2025) -- Slot-promotion mechanism for hybrid SSM speculation; per-candidate state slots via `S_new = S_parent + Δ(k,v,β,g)`; the basis for the 2026-04-28 reopener
- [Hybrid SSM slot-promotion reopener handoff](../handoffs/completed/hybrid-ssm-slot-promotion-spec-dec.md) -- CLOSED 2026-04-30: Phase 1.0 GATE MET, Phase 1.1 dispatcher v1 LANDED but mechanism net-negative on Qwen3.6-35B + Qwen3-1.7B (97% primary wins); dispatcher v1 stays in tree disabled-by-default
- [findings-05c lever × model-category matrix (L20 GDN)](../handoffs/active/fable5-window2-findings-05c-mi210-lever-category-matrix.md) -- GPU GDN levers: occupancy path NO-GO (theoretical occupancy already 100%; the ~42% is pure memory-latency), the one win is **bf16 recurrent-state** (+21.5% agg @B32, halves gather+scatter), generalizes across all GDN-hybrid sizes + qwen3next-80B
- [Kernel reconciliation audit](../handoffs/completed/kernel-reconciliation-audit.md) -- bf16-GDN-state kernel (`496e2f098`, `GGML_CUDA_GDN_STATE_BF16`) carried onto the reconciled v7-candidate; GPU (`ggml-cuda/gated_delta_net.cu`) and CPU/iqk subsystems disjoint

## Lightning Attention port — L2 + L3 COMPLETE, compile gate PASSED (2026-04-30 PM)

The port advanced from L1 scoping to a working compile-tested implementation across L2 (converter) and L3 (model variant).

### L2: GGUF converter (convert_hf_to_gguf.py) — +148 lines

- `BailingMoeLinearV2ForCausalLM` arch handler added with 17 tensor paths (verified by Python smoke test — all expected tensor paths resolve correctly)
- Token embeddings, QKV/gate/output per linear-layer (shape-dependent paths for linear vs softmax layers), attn_gate/attn_output_norm, MoE FFN family (`ffn_up_exps`/`ffn_down_exps`/`ffn_up_shexp`/`ffn_down_shexp`/router)
- Files: `convert_hf_to_gguf.py` (+21), `gguf-py/gguf/constants.py` (+26), `gguf-py/gguf/tensor_mapping.py` (+2), `src/llama-arch.cpp` (+3), `src/llama-arch.h` (+1), `src/llama-model.cpp` (+95)

### L3: Model variant (`src/models/ring-linear.cpp`) — ~205 LOC

- Derives directly from `llm_graph_context` (NOT from `llm_build_delta_net_base` — see L1 template strategy correction)
- Forward: `build_qkv → Q/K norm → partial NeoX RoPE → ggml_cont → arange/exp/repeat decay tensor g → ggml_gated_linear_attn(K,V,Q,g,state,scale) → state cpy → ggml_group_norm + per-channel mul → sigmoid gate from g_proj(input) → output proj`
- Softmax-layer branch reuses standard `build_attn()` — no new code
- Wired via: forward decl in `models.h`, `build_graph` dispatch after `KIMI_LINEAR`, RoPE type added to NEOX group, CMakeLists auto-glob via `file(GLOB models/*.cpp)`

### Compile gate PASSED (L3.7)

Build in `build_lightning/` on `llama.cpp-experimental` HEAD `23bcd6aaf`. Used low parallelism (`-j 4`) to leave EPYC headroom for parallel inference benchmarks. One compile error fixed in flight (`hparams.n_embd_head_k` → method-call form). 66 binaries built clean. `nm -D libllama.so` confirms `llm_build_ring_linear` constructor symbol present.

**Branch state on `feature/lightning-attention-port`**: 7 modified + 1 new file, ~366 LOC net. **No commits yet — working tree only.**

### Threading caveat (flag for L4)

GLA kernel partitions heads across threads. Ring-mini has H=16 heads. On EPYC 96-thread bind, only 16 of 96 threads do work per GLA call → severe underutilization on linear-attn layers. Investigate H-replication or chunked per-head dispatch at L4.

### Next gate

L4 inference smoke decode requires user approval per `feedback_no_concurrent_inference.md` AND a quiet inference window on EPYC.

Sources: [lightning-attention-port.md L2/L3 findings](../handoffs/active/lightning-attention-port.md), [progress/2026-04/2026-04-30.md PM section](../progress/2026-04/2026-04-30.md)

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

## Liquid LFM2 / LFM2.5 family — conv+GQA hybrid (2026-05-29)

The Liquid AI LFM2 family (intake-650 blog / 651 model card / 652 catalog / 653 tech report arXiv:2511.23404) is a conv+attention hybrid MoE distinct from the Qwen3.5 Delta Net and Nemotron Mamba2 lines tracked above. Deep dive: [`research/deep-dives/lfm2-lfm25-family-deep-dive.md`](../research/deep-dives/lfm2-lfm25-family-deep-dive.md).

- **Architecture**: LFM2.5-8B-A1B = 8.3B total / 1.5B active, 24 layers = 18 double-gated **LIV (Linear Input-Varying) short-conv** layers + 6 GQA attention layers (32 experts, Top-k=4, 131K context, own 128K `lfm2` BPE vocab). Tech report self-discloses the gated short-conv as "closely related to Mamba/Hyena/Griffin short-range components" — **novelty is LOW**; the real contribution is a hardware-in-the-loop NAS *finding*.
- **Regime-boundary insight (the reusable takeaway)**: the report's "minimal conv+GQA suffices, SSM/linear-attention operators do NOT help" claim is explicitly scoped to the **on-device 350M–2.6B / 32K-context edge regime**. This does NOT contradict intake-503 (Ling-Linear) / Minimax-01, whose linear-attention wins are at 16B–104B / long-context (100K+) — the two cleanly bound each other's regime.
- **llama.cpp**: `lfm2moe` arch support is **present in our HEAD** (`LLM_ARCH_LFM2MOE`, `LLM_TYPE_8B_A1B`, `Lfm2MoeForCausalLM`; upstream PR #16464 + follow-ups). Static source-tree check only — not yet smoke-loaded with a local GGUF. Official GGUF Q4_K_M = 5.16 GB. License `lfm1.0` = source-available (free commercial <$10M rev), non-blocker for self-host.
- **NOT a spec-dec drafter**: its own 128K `lfm2` vocab is incompatible with every production target tokenizer (Qwen3.6, gemma4); spec-dec requires exact tokenizer match; all production spec-dec is self-speculation (gemma4 MTP / REAP+draft). Standalone-only.
- **Deployment verdict**: no current production role has a gap a 1.5B-active edge model fills, so intake-651 was set to worth_investigating (not adopt_component). The 63.47 AA-Omniscience non-hallucination figure is a calibrated-**abstention** RL artifact (Accuracy 8.67, Index −24.70), not a knowledge win — though that calibrated-abstention behavior could suit a future router/triage role. **LFM2-ColBERT-350M** (late-interaction retriever) is a candidate vs GTE-ModernColBERT for `internal-kb-rag.md`, but is **PyLate/PLAID-only — NOT GGUF/llama.cpp/ONNX** (HF-only per Liquid docs).

Sources: [`research/deep-dives/lfm2-lfm25-family-deep-dive.md`](../research/deep-dives/lfm2-lfm25-family-deep-dive.md), [`handoffs/active/multiscreen-attention-evaluation.md`](../handoffs/active/multiscreen-attention-evaluation.md), [`handoffs/active/internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md), intake-650/651/652/653.

## Nemotron-3-Ultra-550B — first in-RAM Mamba2-hybrid MoE with a CPU path (2026-06-12)

From the intake-694 open-weights roundup triage: **NVIDIA Nemotron-3-Ultra-550B-A55B** (hybrid Transformer-**Mamba2** MoE, 55B active, 1M ctx, MMLU 89.1). The deep-dive **corrects the roundup's "GPU/NVFP4-gated" framing**: CPU-runnable GGUFs already exist (unsloth / DevQuasar BF16 + Q4; **Q4_K_M ≈ 300 GB RAM, fits our 1.1 TB host**; build `-DGGML_CUDA=OFF`). This is **not** Log-Linear Gated DeltaNet and **does not fire the GDN readiness gate** — but it is the first production-scale Mamba2-hybrid MoE available as a concrete artifact to smoke-test the **hybrid-SSM CPU decode / state-management path** on our llama.cpp fork. **Pre-req before any load**: verify it doesn't hit the Nemotron-Nano `mamba-base.cpp:173 GGML_ASSERT` regression (ggml-org/llama.cpp#20570) that has bitten sibling Nemotron GGUFs; MTP is unsupported in GGUF. Flagged as a P1 own-entry follow-up.

Sources: [`research/deep-dives/2026-06-12-open-weights-roundup-followups.md`](../research/deep-dives/2026-06-12-open-weights-roundup-followups.md), [`handoffs/active/log-linear-gated-deltanet-readiness.md`](../handoffs/active/log-linear-gated-deltanet-readiness.md), intake-694.

## GLM-5.2 / Dynamic Sparse Attention — the sparse-attention family's CPU blocker is the DSA forward pass (2026-06-21)

The sub-quadratic / sparse-attention family this page tracks (Multiscreen, IHA/MEA/KHA, and the GDN/Delta Net recurrent line) now has a concrete deployment-gated member: **GLM-MoE-DSA**, the architecture behind GLM-5.x and DeepSeek-V3.2. Unlike the linear/recurrent (Delta Net) mechanisms, DSA keeps the attention paradigm but selects a sparse top-k of keys via a learned Lightning Indexer — the same "preserve attention, cut cost" property that makes Multiscreen and IHA tracked here.

- **DSA forward pass is a dense-MLA fallback in our fork (verified).** `LLM_ARCH_GLM_DSA` loads the indexer tensors but does NOT run the Lightning Indexer / sparse fattn — it dispatches to dense MLA. This works for <8K context but means the 1M-context / long-context value collapses to short-context dense behavior. Any GLM-5.x or V3.2 quality result obtained today must be labeled **short-context dense fallback only**, never used to claim 131K/1M viability. Tracked via upstream **PR #21149** (fairydreaming; CPU/CUDA/Vulkan backends, token-gen sparse path only, no prompt-processing speedup yet). One DSA forward-pass implementation unlocks DeepSeek-V3.2 + GLM-5.1 + GLM-5.2 (multi-model-for-1 leverage). [llama-cpp-dsa-contribution.md](../handoffs/active/llama-cpp-dsa-contribution.md), [glm51-reap-cpu-evaluation.md](../handoffs/active/glm51-reap-cpu-evaluation.md)

- **GLM-5.2 is the PRIMARY GLM-MoE-DSA target (intake-699), supersedes GLM-5.1.** 754B GLM-MoE-DSA, MIT, 1M context. Storage is NOT the blocker — the unsloth UD-IQ2 dynamic quant (~238 GB, vs Q4_K_M 466 GB) fits the ~633 GB raid0 free; DSA, not RAM/disk, gates deployment. GLM-5.1-REAP demoted to fallback comparison datapoint.

- **IndexShare (arXiv 2603.12201) is the genuinely-new technique in the 5.2 point release.** It reuses the same sparse-attention indexer across every 4 sparse-attn layers, cutting per-token FLOPs ~2.9x at 1M context — an indexer-amortization lever on top of DSA. External/preprint confidence (vendor-reported, no CPU measurement). Relevant here as a sparse-attention efficiency mechanism distinct from the Delta Net recurrent family, and a future consideration once the base DSA forward pass lands. [intake-699]

Sources: [`handoffs/active/llama-cpp-dsa-contribution.md`](../handoffs/active/llama-cpp-dsa-contribution.md) "Research Intake Update — 2026-06-20", [`handoffs/active/glm51-reap-cpu-evaluation.md`](../handoffs/active/glm51-reap-cpu-evaluation.md), intake-699, [deepseek-v32-dsa deep-dive](../research/deep-dives/deepseek-v32-dsa-llamacpp-pr21149.md).

## Compiled Update — 2026-08-22: a fused chunked GDN kernel is a measured no-go on ceiling, not feasibility — and the ceiling survived the discovery that the kernel already existed upstream

**Confidence: verified** for the attribution numbers, the falsified-lever ledger, the upstream-PR facts and the checkpoint/reference-code readings (all measured on frozen binaries or read from primary source). All MI210 speed numbers remain **observation-grade** per `P-GPU-1` — no production-named rerun exists, and none is proposed; **v9 is FROZEN and no v9 change is proposed by any of this.**

### K28 closed as a measured no-go: GDN is only ~12–15% of MI210 prefill device time, so no op speedup clears the bar

**The K28 fused-chunked-GDN-recurrence project (the `//TODO: Add chunked kernel` at `gated_delta_net.cu:191`) is COMPLETE with a no-go verdict, and no fused recurrence kernel was ever authored.** The accepted Phase-0 gate ran direct profiler attribution (schema `epyc.autokernel.rocprofv1_attribution.v1`) on the clean frozen-v9 HIP binary, Qwen3.6-35B-A3B Q8, physical gfx90a, graphs disabled:

| Prompt | GDN share of summed device-kernel time | Full-model ceiling under a deliberately optimistic 4× GDN op speedup |
|---:|---:|---:|
| p2048 | 15.397% | 11.548% |
| p8192 | 14.649% | 10.987% |
| p32768 | 12.180% | 9.135% |

The ceiling **declines with context** and reproduces the 2026-07-20 default-off HIP-event timing hook (15.45% / 14.64% GDN share at p2048/p8192 → 11.59% / 10.98% ceilings) instead of raising it — two independent instruments, one answer. Receipt: `/mnt/raid0/llm/autokernel/probes/k28-rocprofv1-attribution-20260811-r3/receipt.json`, SHA-256 `981306080a…74e74c5a0`; durable runner in epyc-inference-research commit `48350b24`. The default-off scaffold (branch `k28/prototype-20260720`) and the SGLang four-stage design notes are **reference material only, not latent implementation tasks**.

**The headroom was real — the kernel is serial-dependency-bound, not bandwidth-bound.** The K28.1 op microbench shows effective bandwidth *falling* with length (51.17 GB/s at 64 tokens → 26.87 GB/s at 1024, ~1.7% of MI210's ≈1.6 TB/s HBM peak), the fingerprint of a per-token serial loop that cannot amortize. And the generic-ggml chunked graph — which already dispatches its matmuls to matrix cores — still **loses** to the serial kernel by 6.30–6.69% full-model prompt, proving the bottleneck is op-launch/HBM round-trips (~144 launches per 1024 tokens at C=64), not matmul throughput. Headroom at the op level was never the question; **the model-level share was, and it caps everything.**

**Falsified-lever ledger (do not re-tread):** further GDN occupancy rewrite ✗ (occupancy is not the limit), compact-LDS ✗, graph-vs-fused policy switch ✗ (−6.30…−6.69%), single-stream BF16 state ✗ (neutral: −0.76/−0.79% prompt, +0.74% decode).

**Reconciliation with this page's findings-05c row ("the one win is bf16 recurrent-state, +21.5% agg @B32"):** both numbers are the *same* `GGML_CUDA_GDN_STATE_BF16` mechanism in two regimes. State bandwidth only dominates at **batch**; single-stream is dependency-bound and the mechanism is neutral there. "BF16-for-speed is dead" is true single-stream only — **batched-decode state bandwidth remains the live GDN lever** across the family (35B frontdoor +17.7%, 122B architect +16.4%).

### The SOTA bar is four autotuned Triton stages, not a megakernel — and kernel names drift under you

**SGLang does not run one monolithic fused GDN kernel** (intake-1030#record, dive-verified against `sgl-project/sglang` main): it runs four separately-autotuned Triton stages behind one autograd wrapper — `chunk_local_cumsum` → `recompute_w_u_fwd` (WY/UT transform) → `chunk_gated_delta_rule_fwd_h` (state scan) → `chunk_fwd_o` — keeping chunk-local tensors on-chip between them. All four stage files are pure Triton with no `is_cuda` guard (necessary but not sufficient for gfx90a). A citation-hygiene lesson rode along: two intake sources name a `chunk_gated_delta_rule_fwd_kkt_solve_kernel` that **no longer exists in current source** (the stage is now `recompute_w_u_fwd_kernel`); neither was wrong when written, both are wrong now, and neither recorded the commit it was true at — **cite kernels by role and commit, and verify absence in the kernels tree, not the model tree.**

### Post-closeout correction: the no-go's premise was already false when written — the measurement stands, the cost side collapsed

**K28's claim that "no CDNA2/ROCm-tuned GDN kernel exists … genuinely open territory" was false ten days before it was written.** llama.cpp **PR #24561** — a chunked MFMA prefill kernel for `GATED_DELTA_NET`, scoped explicitly to CDNA/gfx90a — was opened 2026-06-13 and closed *unmerged* 2026-07-10 on **maintenance/authorship grounds, not merit**: the ggml CUDA/HIP maintainer declined it as apparently machine-generated with no volunteer maintainer while confirming *"a 5-10% E2E improvement … on my NVIDIA/AMD hardware."* A third party independently measured **+11.8% / +12.1% prefill on 2× MI210** after four fixes. Applying Amdahl to the *measured* gfx90a op speedups (1.63–2.44×) gives a realistic **~6–9% full-model prefill** for our geometry — *below* the ceiling K28 already judged insufficient, so **the no-go verdict is unchanged; only the cost side changed** (two complete implementations exist versus the "weeks of authoring" the gate was framed against). Decode is unaffected by construction — both kernels gate off below 128/512 tokens per call.

Three non-obvious selection constraints, all read from frozen v9, for anyone who revisits:

1. **PR #26001 would never fire on our frontdoor**: it requires `K == 1`, and `--spec-type draft-mtp` makes `K = cparams.n_rs_seq + 1 > 1` (`src/models/delta-net-base.cpp:570`). **#24561 supports keep_rs/MTP by design** — the *closed* PR is the usable one on our exact configuration.
2. **#26001 has no AMD runtime path at all** — its dispatch gate is literally `GGML_CUDA_CC_IS_NVIDIA(cc_dev)`; the working gfx90a version exists only as an unmerged patch in a GitHub comment.
3. **#24561's `MIN_BLOCKS_PER_SM 3` occupancy floor keeps it dark at `-np 1` on our model**: 312 blocks needed on MI210's 104 CUs vs the 256 our 32 v-heads yield at `n_seqs=1`; it fires unmodified at `-np >= 2` (compile-time macro).

**A numerics caveat now attaches to any chunked adoption:** the chunked formulation is algebraically equivalent but **not floating-point equivalent** — error grows with chunk count and hence prompt length. Upstream widened its op-test NMSE gate from 1e-7 to 2e-7 and it **still fails on MI210 at T=2048** (2.97e-7 / 3.70e-7 at 128 chunks), while our own GDN correctness cases top out at 256 tokens. Today's fp32 sequential kernel is the most conservative option in the tree; adopting a chunked kernel means giving that up, and any adoption is `llama.cpp-experimental` work under the four-step promotion workflow.

### Log-Linear GDN: the reference is not runnable as shipped — port from the pure-PyTorch recurrent form, which needs no lookup table

Extending this page's 2026-08-12 update (gates fired, state-size claim inverted): **gate 2 is satisfied as code but an executor who clones the repo and calls `.generate()` gets nothing.** Two concrete blockers, both read from source: (1) the only wired compute path is Triton/GPU (`mode == 'chunk'`, else `raise NotImplementedError`) — the pure-PyTorch `hattention/recurrent.py` is reachable only by editing the model; (2) `hattention/base.py` hard-codes an author-cluster absolute path for the cached L×L level-lookup matrix, and the in-repo fallback is an O(L²) Python double loop (≈2.7·10⁸ iterations at L=16384).

**The settled port consequence: port from `hattention/recurrent.py`, not the chunkwise kernels.** The recurrent form needs **no L×L LUT at all** — `HState.cascade_weak()` derives the level from per-level counters (`counts[level] == base**level` → carry), a ggml-friendly integer state machine; the LUT exists only to materialize the parallel/chunk-form mask. Two further checkpoint facts bound any deployment reading: the level count is a **fixed 15** (`attn.L [6, 15]`, = ceil(log2 16384)+1) with `max_position_embeddings` 16384 — a 262K-context claim needs 19 levels and therefore a **different checkpoint** — and the level set is constant in L. The port-or-wait decision itself remains the operator's, gated on a numerical oracle that does not yet exist (unchanged from 2026-08-12).

### The GDN forgetting-fix design space now has four structurally distinct branches — easy to conflate, and the distinction is load-bearing

Recorded from the 2026-08-21 Stage-2b intake wave (dive-verified; no action attached):

| Branch | Lever | Entry | Standing |
|---|---|---|---|
| Grow the state | O(L log L) hidden states | intake-356#record | gates fired, port not started |
| Segment checkpoints | O(NL) | intake-354#record | reference only |
| Bounded exact side-cache | fixed state + bolt-on bounded cache | intake-1272#record (LTE), intake-1268#record (HOLA) | LTE opened the branch 8.5 months before HOLA |
| Fix the update rule | diagonal key-Gram preconditioner, state size unchanged | intake-1273#record (PGDN) | no checkpoint anywhere; activation gate closed |

**PGDN is the only branch with near-zero state cost** — one d_k vector per head against the existing d_k×d_v matrix (~0.8%), versus the log-linear branch's measured ~15× state *increase* — and the smallest llama.cpp delta of the four; but it adds weight tensors no pretrained GDN checkpoint contains, so it is inert until someone trains one. **Do not cite LTE as evidence the bounded-cache branch works**: its own Table 2 has plain GDN beating it 88.9 → 83.1 on RULER S-NIAH at 1.4B, the advantage inverts across its single scaling step, nothing is measured beyond its 4096 training length, and it was withdrawn from ICLR 2026.

**A ratio-convention trap for the m-a-p hybrid-band checkpoints:** their "N:1" means *one attention layer every N layers* (attention fraction 1/N), not a literal linear:full count — `hybrid-3-1` is 8 attention layers of 24. Our production 30-GDN + 10-attention (10-of-40) is therefore **"4:1" in their convention**, which is not one of their five trained arms; it sits between 3-1 and 6-1, inside their recommended band under either reading.

(The readiness tracker's 2026-08-21 measurement tasks — the #27442 first-token boundary sweep, the HOLA frozen-backbone retrofit and its hybrid-transfer A/B — are open, compute-gated work, not knowledge, and are deliberately not compiled here. The one settled fact from that cluster: whether the #27442 hybrid-cache defect reaches non-Metal backends is a **live unknown** — nobody anywhere has tested any backend but Metal, and the upstream reporter's own log refutes their cache-corruption diagnosis (intake-1279#record).)

### Source References

- [K28 fused chunked GDN kernel research (COMPLETED)](../handoffs/completed/k28-fused-chunked-gdn-kernel-research.md) — the rocprofv1 attribution no-go, the serial-dependency diagnosis, the falsified-lever ledger, the SGLang four-stage finding, and the 2026-08-22 PR #24561/#26001 correction with the fp-numerics caveat.
- [Log-Linear Gated DeltaNet readiness tracker](../handoffs/active/log-linear-gated-deltanet-readiness.md) — the two runnability blockers, the port-from-`recurrent.py` consequence, the fixed-15-level/16K position bound, and the 2026-08-21 GDN branch map.
- intake-1030#record in [the research index](../research/intake_index.yaml) — the SGLang `fla/` four-stage enumeration and the kernel-name-drift lesson.
- llama.cpp PR #24561 and issue #20354 (cited from the K28 handoff) — the closed-unmerged CDNA chunked MFMA kernel with maintainer-confirmed 5-10% E2E, and the AMD register-pressure landmine that motivated the CDNA2 caution.
- epyc-inference-research commit `48350b24` + receipt `k28-rocprofv1-attribution-20260811-r3/receipt.json` (SHA-256 `9813060…`) — the durable attribution runner and the signed no-go evidence.
- intake-1272#record / intake-1273#record in [the research index](../research/intake_index.yaml) — the LTE caution (withdrawn, Table 2 inversion) and the PGDN fourth branch.

---

## Compiled Update — 2026-08-23 (evening): MiniCPM-SALA, the portability gates 4/5, and the two literature results that bound the hybrid architecture choice

**Confidence: verified** — the SALA reattribution reads the released checkpoint and code (`modeling_minicpm_sala.py`), corroborated by three independent implementers (vllm #44095/#48999, sglang #30360); the zero-new-operators table is a static read of frozen v9; the hazard and counter-argument rows are abstract-verified at the primary source through intake-1287#record.

### MiniCPM-SALA: the paper is wrong about its own linear half, and a correctness-first port needs ZERO new ggml operators

MiniCPM-SALA (9B hybrid, 8 of 32 layers InfLLM-V2 block-sparse exact attention at 2 KV heads, the rest linear; Apache-2.0, rev `9180fe1d`) landed on the GLA path 2026-08-22 (intake-1287). **Read the artifact, not the prose**: the paper says "Lightning Attention" and cites Qin et al. 2024, but the released code calls `fla.ops.simple_gla` with a parameter-free ALiBi power-of-2 slope schedule — **constant-decay Simple GLA without the layer-scaled decay that distinguishes MiniMax's Lightning Attention**. Three independent implementers read it the same way. Reattribute to Simple GLA when citing the *mechanism*; keep "Lightning Attention" only when quoting the paper. **This helps us**: constant-decay GLA is exactly what `GGML_OP_GATED_LINEAR_ATTN` already implements (`ggml/include/ggml.h:569`; SIMD CPU f32 forward at `ops.cpp:10556`; CUDA `gla.cu` hipifies for gfx90a via the glob). The paper is also contradicted by its own checkpoint on QK-Norm (§2.1 claims it on all attention layers; the checkpoint has q_norm/k_norm on the 24 linear layers only).

**The correctness-first port table** (read from frozen `0db32c06e3e5`, 2026-08-23): constant-decay gated linear attention — already shipped; per-layer recurrent/attention hybrid memory — `llama-memory-hybrid.cpp` with `hparams.is_recr_impl` (`llama-hparams.h:153`), precedents `kimi-linear.cpp` and `qwen3next.cpp`; NoPE/QK-norm/attention output gates — all expressible today; InfLLM-V2 block-sparse top-k — **the only missing primitive, and the reference does not need it either** (the vendor instantiates ordinary dense attention for the sparse layers whenever CUDA is unavailable — a dense-fallback GGUF port is numerically correct and gives up only the sparse-prefill speedup, exactly as the vendor's own CPU path does). Closest template for the linear half: upstream PR **#27018** (`LLM_ARCH_MINIMAX_01`, lightning-attention decay slopes on hybrid recurrent memory), **merged 2026-08-14 — four days after our v9 freeze** — therefore absent from our tree, which carries `LLM_ARCH_MINIMAX_M2` but not `_01`; read it before writing any new arch handler. Tasks: **Z9** (write the ~30-line pure-PyTorch constant-decay simple-GLA recurrence so an HF CPU numerical oracle exists at all — today there is none: `fla.ops.simple_gla` is Triton and Triton needs a GPU stack this host does not have for gfx90a); **G18** (SALA port + CPU parity smoke on `llama.cpp-experimental` branched from the current production tip — never v9; 3 prompts × 32 tokens, all under `sparse_config.dense_len` = 8192 so both sides run dense; gate: token-identical output; filed, not run — both compute planes held); **B8** (blocked on G18: throughput, the NoLiMa 40.9-vs-23.86 adjudication, and an InfLLM-V2 block-sparse ggml op justified only if dense fallback makes prefill binding above ~32K — with the standing declines recorded: no port of `infllmv2_cuda_impl` to HIP (sm80-only), and no SALA adoption as a production model (9B dense vs our 35B-A3B, no reproduced number from anyone in six months)).

### The portability gates: Gates 4 and 5, added 2026-08-22 to every GDN-branch candidate

Two further gates apply to every candidate on the GDN branch map because the original three **cannot tell apart three cases the wave put side by side** — they do not retract the 2026-08-12 activation. **Gate 4 — a device-agnostic (non-Triton) numerical oracle exists** (not just "reference code exists"): log-linear GDN has the code (`hattention/recurrent.py`, pure PyTorch) but it is not wired into the model — gate OPEN for log-linear too; Gated DeltaNet-2 (intake-1281) is the inverse (better decode path, no non-Triton path at all). **Gate 5 — a ggml primitive exists for every mixer type, or a numerically-correct fallback is identified**: SALA fires all three original gates yet needs the fallback clause (its block-sparse selection has no ggml op); log-linear GDN fails today (`ggml_log_linear_state_update()` and `ggml_log_linear_attention()` do not exist). **Why this is not bookkeeping:** gates 2 and 4 came apart in *opposite directions* on two candidates in a single wave — a gate list that scores both as "reference implementation available" cannot tell you which port has something to check its output against, and that is the distinction that decides whether a port is startable at all.

### GDN-2 is the other end of the state-size axis: 1.0× state, +375.5M always-active parameters

The branch map had one data point on the state-size axis (log-linear's 15×). GDN-2 (intake-1281) replaces GDN's scalar delta gate with channel-wise erase/write gates; its recurrent state is **byte-identical in size** to GDN's and KDA's (Appendix E.1 matches all three at `H · d_k · d_v` = 262,144 floats per layer per batch element) — it changes *how the state is edited*, not how large it is. The cost moves elsewhere: two full-rank per-layer projections no pretrained GDN checkpoint contains, ≈ **+375.5M always-active dense parameters** ≈ **+12.5%** active parameters for **zero** state saving. **Quote the state-size axis and the active-parameter axis together or the comparison is meaningless**: log-linear buys context scaling with 15× state; GDN-2 buys update expressiveness with +12.5% active weights; PGDN buys it with ~0.8%. Z12 (Z, executable now) asks whether GDN-2's `b_proj`/`w_proj` can be low-rank factorized — the precedent is in our own tree (Kimi Linear already factorizes its decay projection; `LLM_TENSOR_SSM_F_A`/`F_B` at `llama-arch.h:473-474`).

### The CoT-SFT amnesia hazard — a recall failure invisible to every instrument we routinely run

**`arXiv:2606.11052` (intake-1287#record, abstract verified at the primary source):** CoT-SFT *"systematically degrades long-context recall in hybrid linear-attention models… HypeNet-9B on NIAH-S2@256K decreases from 67.2% to 9.4%"*; the proposed fix, **QK-Restore** (restore `W_Q`/`W_K` from the pre-SFT checkpoint), is training-free. **Why it is a hazard for us and not a curiosity:** the damage is invisible to PPL and short-context evals, our standing quality case, and **the production frontdoor is exactly this architecture** — Qwen3.6-35B-A3B, 30 GDN + 10 full attention, a 256K-context serving role. Nothing in the repo has ever measured it. **G1** (highest-value compute row of the wave — no port, no new model, no training): RULER **S-NIAH-2** (essay haystack, numeric magic value) on the production artifact at 4K control / 32K / 64K / 128K, 50 trials per length, exact-match, per-question persisted; harness already on disk (`long_context_adapters.py`: `NeedleAdapter`'s essay haystack + `RULERAdapter`'s numeric needle = S-NIAH-2, a composition not a new harness); three mandatory server deviations (dedicated `-np 1 -c 262144` instance — the :8070 frontdoor is `-np 4` = 65,536 tokens/slot, so the 128K arm cannot run there; `--spec-type none`; `cache_prompt=false` greedy seed 42) and a mandatory **f16-KV control** (production is q8_0/q8_0 and "quantized KV damaged recall" predicts the same sign). **Gate: ≥ 10 pp below the 4K control at any of 32K/64K/128K with the paired 95% bootstrap CI excluding zero, surviving the f16-KV control** (≈ 2.4 SE at 50 trials; the published effect is 5.8× the threshold). **If the gate opens this is a PRODUCTION DEFECT — escalate to the operator, do not file it to a research backlog.** The probe measures the symptom; attribution (and the QK-Restore remedy) needs the Base weights — no Base `Qwen3.6-35B-A3B` GGUF is on disk, deliberately not a prerequisite for the probe. Scope note: the 67.2→9.4 figure is HypeNet-9B, not our model — it is a reason to *measure*, and the measurement is cheap.

### The strongest published argument AGAINST replacing our 10 full-attention layers with sparse ones

**`arXiv:2606.15378`** (abstract-verified): *"long-range retrieval is mainly carried by full attention, whereas efficient attention shapes its optimization trajectory"*; different hybrids converge under sufficient training; and a named **"Large-Window Laziness"** effect (larger SWA windows *delay* retrieval-head formation in full-attention layers). Three things make it unusually strong as a counter-argument to the SALA-direction swap: **(1)** seven of nine authors are SALA co-authors — same-lab, and adversarial to SALA's own premise (SALA has no full attention above 8,192 tokens); **(2)** it directly contradicts the move the SALA branch proposes — our 10 full-attention layers are, on this account, *where the long-range retrieval lives*, and replacing them with sparse ones spends exactly the resource the paper says does the work; **(3)** if hybrids converge under sufficient training, SALA's 1:3 ratio is not what produces the result, and SALA ablates that ratio nowhere. Weakening it: abstract-level reading, same-lab provenance cuts both ways. **Consequence, recorded so it is not re-derived: the "swap the dense minority for a sparse minority" direction is argued against by the closest available literature, including its own proponents' lab — before any throughput question is even reached** (that ordering matters: B8 in the SALA handoff is gated on numerical correctness; even a clean correctness result does not make the architectural swap attractive).

### Source References (2026-08-23 evening)

- [`lightning-attention-port.md`](../handoffs/active/lightning-attention-port.md) — the SALA reattribution (Simple GLA, constant-decay), the zero-new-operators table, Z9/G18/B8, the #27018 pointer and the standing declines
- [`log-linear-gated-deltanet-readiness.md`](../handoffs/active/log-linear-gated-deltanet-readiness.md) — Gates 4/5 addendum, the GDN-2 1.0×-state axis (with log-linear 15× and PGDN ~0.8% beside it), the B9 decline cross-reference
- [`multiscreen-attention-evaluation.md`](../handoffs/active/multiscreen-attention-evaluation.md) — the CoT-SFT amnesia hazard (arXiv 2606.11052), the G1 S-NIAH-2 probe protocol and gate, the efficient-attention counter-argument (arXiv 2606.15378)
- [`mi210-big-model-and-acceleration-roadmap.md`](../handoffs/active/mi210-big-model-and-acceleration-roadmap.md) — the one-assert GDN-2 ggml delta and #26001's K==1 constraint (cross-listed with [Hardware Optimization](hardware-optimization.md))
- [`k28-fused-chunked-gdn-kernel-research.md`](../handoffs/completed/k28-fused-chunked-gdn-kernel-research.md) — the #24561/#26001 correction: the no-go's MEASUREMENT stands, its premise about the state of the art did not
