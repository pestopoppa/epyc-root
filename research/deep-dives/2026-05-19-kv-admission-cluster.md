# KV Cache Admission / Eviction Cluster — 2026-05-19

**Date**: 2026-05-19
**Cluster**: Deep-Dive #4 of 8 — KV Cache Admission / Eviction (5 intakes)
**Entries analyzed**:
- intake-538 — SP-KV / Self-Pruned KV Attention (arxiv:2605.14037, FAIR — Szilvasy/Faysse/Lomeli/Douze/Mazaré/Cabannes/Yih/Jégou)
- intake-551 — KVP / Learning to Evict from KV Cache (arxiv:2602.10238, Moschella/Manduchi/Sener, Apple)
- intake-552 — LU-KV / Predicting Future Utility (arxiv:2602.08585, Tang/Jiao/Chen et al.)
- intake-553 — ForesightKV (arxiv:2602.03203, Dong/Liu/Li et al.)
- intake-554 — PBKV / Prediction-Based KV-Cache (arxiv:2605.06472, Zheng/Fu/Wu/Yuan et al.)
**Cross-references**: handoffs/active/{attention-matching-kv-compaction,triattention-kv-selection,summary-token-attention-readiness,multiscreen-attention-evaluation,llama-cpp-fork-rebase}.md ; handoffs/completed/kv-cache-quantization.md ; deep-dives/{kv-compaction-attention-matching-cluster,triattention-kv-selection-cluster}.md ; intake history: H2O, SnapKV, StreamingLLM, TokenButler, Steele/SIP 2601.14279.

---

## Executive Summary

The cluster spans **four mostly-orthogonal axes**: (1) selection time — **write-time admission** (SP-KV) vs **read-time eviction** (KVP, ForesightKV) vs **budget allocation** (LU-KV) vs **residency / re-prefill avoidance** (PBKV); (2) granularity — per-token (SP-KV, ForesightKV) vs per-head (KVP, LU-KV) vs per-cache-entry/per-agent (PBKV); (3) training cost — joint base-LLM fine-tune (SP-KV), offline RL on traces with frozen base (KVP, ForesightKV), offline profiling only (LU-KV), small auxiliary predictor only (PBKV); (4) workflow-awareness — only **PBKV** crosses the orchestrator boundary, every other method is request-local.

For the EPYC stack — **frozen GGUF quants, 1.1 TB RAM, 460 GB/s aggregate DRAM bandwidth, 30 model servers behind an orchestrator that explicitly hands frontdoor→coder/worker prompts back and forth** — **PBKV is the dominant single match** because it operates at the prefix-cache layer (no kernel changes, no fine-tuning) and directly attacks the BW-bound prefill cost that dominates per-turn latency in our orchestrator. **LU-KV is the strong runner-up** as the only frozen-weights-compatible attention-kernel method in the cluster. SP-KV / ForesightKV / KVP are useful as future references once a fine-tuning workstream exists, but are blocked today.

A consistent gap across all five papers: **none of them runs a clean "sink + sliding-window" baseline (StreamingLLM) at matched cache budget with matched fine-tuning budget**. KVP and ForesightKV mention StreamingLLM/H2O/SnapKV but do not isolate "what does the learned scorer add beyond the recency-window component". This corroborates Steele 2601.14279's broader critique and limits how confidently we can claim these methods beat a 30-LOC StreamingLLM patch.

---

## Design-Space Matrix

| Method | Selection time | Granularity | Base-LLM training? | Auxiliary training | Workflow-aware? | Frozen-quant compatible | EPYC fit |
|--------|----------------|-------------|--------------------|--------------------|-----------------|-------------------------|----------|
| **SP-KV** (intake-538) | write (per-token admission) | per-token | **YES — jointly fine-tuned end-to-end** with next-token-prediction loss | utility predictor, head-shared, gated by threshold | no | **NO** (joint FT required) | **Blocked** until DGX Spark FT capacity exists |
| **KVP** (intake-551) | read (post-prefill eviction) | per-head | no (frozen) | offline RL on pre-computed K/V/position traces; 112 per-head MLPs (~650 K params each) for Qwen2.5-7B; reward = cumulative future attention of evicted tokens | no | yes (no LLM weight change) | Medium — need offline trace generation + FlexAttention-equivalent mask machinery; not free on llama.cpp |
| **LU-KV** (intake-552) | budget allocation (one-shot post-prefill) | per-head static profile | no (frozen) | offline convex-hull / PAVA solver + greedy marginal-utility allocator over ~4 K-token calibration corpus, produces lookup table | no | **yes** (offline only; inference is table lookup + per-head Top-k) | **Highest** of the attention-kernel methods — no FT, no in-loop solver, works with any existing per-head scorer (SnapKV/KeyDiff/Expected-Attention) |
| **ForesightKV** (intake-553) | read (per-token eviction every block) | per-token (Top-K multinomial, 2L candidates → L kept) | base LLM frozen but two-stage **Supervised + GRPO** training of MLP scorer required | 2-layer MLP, hidden=16, inputs = K ⊕ V ⊕ 6 attention windows ⊕ cumulative aggregates; oracle = future-attention partitioned into fixed blocks | no | partial (LLM frozen, but oracle-distillation pipeline non-trivial; GRPO needs LM-loss reward signal) | Low — reasoning-only validation (AIME math/code); training cost real |
| **PBKV** (intake-554) | residency (which cache to keep resident; pre-prefill admission to GPU/RAM tier) | per-cache-entry / per-prefix | **no** (orchestrator-layer) | small history-conditioned next-agent predictor (architecture not disclosed in abstract; fuses historical workflow + target context) | **YES — only entry in cluster** | **yes** (no LLM touch, no kernel touch) | **Highest** — matches frontdoor↔coder↔worker pattern directly |

---

## Per-Paper Findings

### intake-538 — SP-KV (FAIR / Szilvasy, Faysse, Lomeli, Douze, Mazaré, Cabannes, Yih, Jégou)

**Mechanism.** Write-time admission. Two parallel KV stores per layer: a **local recency window** (every token written) and a **global long-term cache** (token admitted only if utility-predictor score > threshold). The predictor consumes the per-token KV pair (paper-confirmed: "scores each key-value pair"); it does **not** consume future queries (it cannot — it is write-time). This is exactly the class of "KV-only, query-agnostic write-time scorer" that Steele 2601.14279's SIP ablation falsifies on multiple axes.

**Training.** Predictor + base LLM **jointly fine-tuned end-to-end with next-token-prediction loss only**, "adapted from pretrained LLM checkpoints" (continued pretraining, not from-scratch). This is the binding constraint for us — we cannot run continued pretraining on a Q4_K_M GGUF.

**Benchmarks.** Abstract cites "broad set of downstream tasks" with "vast improvements in memory usage and decoding speed, with little to no degradation of validation loss." No specific LongBench/RULER/AIME numbers surfaced in fetch; PDF body would need fuller extraction. Claimed **3-10× KV reduction**, "longer sequences often being more compressible."

**Baselines compared.** Not surfaced in the fetched abstract/intro. The PDF saved to local fetch cache could be re-mined if a deeper ablation comparison becomes load-bearing. From the intake notes (cross-checked against the family literature), the natural baselines are StreamingLLM (sink + window), H2O, SnapKV, Expected-Attention. **Critical missing experiment** (per Steele's framing): SP-KV vs sink+window alone at matched cache budget after matched fine-tuning compute. We should assume the recency-window component of SP-KV is doing most of the work until shown otherwise.

**Code / license.** Not surfaced in fetch. FAIR papers typically land on github.com/facebookresearch; not yet verified.

**Frozen-weights compatibility.** **No.** Joint fine-tuning is the mechanism.

**Architecture details.** Not in abstract. PDF body needed for predictor size, threshold mechanism, window size. From the intake claims: "lightweight utility predictor" — likely 1-2-layer MLP per layer or head-shared.

**Verdict.** **Blocked for current frozen-quant stack.** Useful as a reference for the eventual fine-tuning workstream. The Steele 2601.14279 critique and the ForesightKV "low-entropy degradation" observation (below) are independent reasons to expect SP-KV's learned predictor to underperform a careful StreamingLLM + sink baseline once both are FT-budgeted equally.

---

### intake-551 — KVP / Learning to Evict from KV Cache (Apple — Moschella, Manduchi, Sener)

**Mechanism.** Read-time eviction **after prefill**. Per-head RL agent ranks tokens by predicted future utility. Inputs: **K, V, token position only — no attention scores, no query**. Compression applied once post-prefill; **zero overhead during decoding**.

**Training.** Offline RL on pre-computed generation traces. Reward = minimize cumulative future attention of evicted tokens, across **all cache budgets simultaneously** (a single agent generalizes across budget sizes). Traces generated by running the base LLM once on training data and caching Q/K/V tensors. Training cost: ~30 minutes on 8× H100 for Qwen2.5-7B. **112 agents** (28 layers × 4 KV heads), each a ~650 K-parameter 2-layer MLP.

**Benchmarks.** RULER-4K, OASST2-4K (perplexity), zero-shot transfer to BoolQ, ARC-Challenge, GovReport. Outperforms StreamingLLM, H2O, SnapKV, and the attention-free baselines KeyDiff, K-Norm, LagKV. Achieves loss comparable to attention-aware methods **despite not consuming queries**.

**Code / license.** Not specified in paper. Contact: luca_moschella@apple.com. Apple papers rarely ship code.

**Frozen-weights compatibility.** **Yes** — LLM weights untouched. Deployed via custom attention masks in FlexAttention (PyTorch).

**Inference overhead.** ~1 % additional FLOPs during prefill; **~0.71 ms vs 404 ms prefill** in their setup; zero decode-time cost.

**EPYC blockers.** (1) Need an offline trace-generation pipeline (run base LLM on a representative training corpus, dump K/V). (2) FlexAttention has no llama.cpp equivalent — we would have to wire per-head masks into the GGML attention path or post-mask the KV cache in the cache layout. (3) Apple paper code unlikely to ship — implementation effort is real.

**Verdict.** **Promising medium-term path.** Frozen-weights compatible, real reported gains, small auxiliary cost. Dev cost lives entirely in (a) trace pipeline and (b) llama.cpp mask integration. Should be staged behind PBKV and LU-KV.

---

### intake-552 — LU-KV / Predicting Future Utility (Tang, Jiao, Chen et al.)

**Mechanism.** Per-head **static** budget allocation produced **offline**. Convex relaxation (isotonic regression / PAVA) of the discrete budget-allocation loss, then greedy marginal-utility solver maximizes long-horizon utility across heads simultaneously. **Online phase has negligible overhead: lookup pre-computed ratios → integer budgets → apply existing per-head heuristic scorer (SnapKV / KeyDiff / Expected-Attention) at the chosen budget.**

**Training.** **Offline only.** No solver runs in-loop. Calibration: ~4 K-token synthetic context with coherent narrative + a diverse query set 𝒬, solve allocation per query across a compression-ratio grid, aggregate into static profile Φ by averaging optimal per-head local ratios.

**Benchmarks.** LongBench at 80 % compression: Mistral-7B-v0.3 with KeyDiff metric goes 40.54 % (AdaKV) → **46.21 %** average accuracy; recovers **84 % of the gap** between compressed model and full-KV upper bound. RULER-16K with SnapKV metric: **69.98 % vs 37.48 %** (AdaKV); on multikey-3: **67.40 % vs 1.00 %** (Uniform).

**Baselines.** Uniform, PyramidKV, AdaKV. **Not directly compared to StreamingLLM** at matched budget — same critique as the rest of the cluster, but mitigated because LU-KV's gains over AdaKV at 80 % compression are large enough that even a generous StreamingLLM advantage is unlikely to close the multikey-3 gap.

**Code / license.** Not mentioned in paper. No repository identified yet.

**Frozen-weights compatibility.** **Yes — fully.** No LLM weight modification. Works with any proxy metric we already have.

**Per-head budget profile.** Number of calibration queries M not disclosed in main text (paper says "M queries"). Profile is static, task-agnostic claimed.

**Verdict.** **Highest-priority frozen-weights attention-kernel method in the cluster.** The offline-only solver + table-lookup execution makes this a much cleaner llama.cpp landing target than KVP or ForesightKV. The reported 84 % gap recovery at 80 % compression on LongBench is the strongest claim in the cluster after PBKV's orchestrator-layer numbers. **Recommend a spike to reproduce the LU-KV profile on a single model (Qwen3.6-35B or Coder-30B) using SnapKV as the per-head scorer.**

---

### intake-553 — ForesightKV (Dong, Liu, Li et al.)

**Mechanism.** Read-time per-token eviction, applied every block. Two-stage training of a small scorer (LLM frozen throughout):
1. **Supervised** — partition the future-attention matrix into fixed-length blocks along the query dimension, aggregate per-head, label each KV pair with "golden" oracle importance, train scorer with **pairwise ranking loss**.
2. **GRPO RL** — formulate eviction as MDP; reward signal explicitly **targets low-entropy tokens** (token's original entropy in bottom 80 % of sequence AND loss increase > threshold η) to compensate for distribution shift between train (full cache) and inference (already-evicted state).

**Scorer architecture.** 2-layer MLP, hidden dim 16, inputs = K ⊕ V ⊕ 6 attention-window features ⊕ cumulative aggregates. Sampling: top-K multinomial — select 2L candidates, sample L for eviction (stochastic policy for GRPO).

**Benchmarks.** AIME 2024 / AIME 2025 on Qwen3-4B, Qwen3-1.7B, DeepSeek-R1-Distill-Qwen-7B. Headline: **preserves 92 % and 99 % of original performance under 2K and 4K KV budgets** respectively. Qwen3-4B AIME2024: **ForesightKV @ 1K = 54.5 %** vs **R-KV @ 2K = 44.8 %** (half the budget, higher accuracy).

**Efficiency.** 32K context @ 1K budget: **9.79× throughput speedup** on A800. Eviction overhead: 2.7 % of total time (vs 8.1 % for R-KV). Concurrent batches: 96 vs 48 with full cache.

**Baselines.** H2O, SnapKV, R-KV. **No StreamingLLM comparison surfaced.** This is the cluster's clearest pure-eviction win, but only on reasoning workloads.

**Code / license.** Not stated in extracted content.

**Frozen-weights compatibility.** **Partial.** Base LLM frozen, but two-stage Supervised+GRPO pipeline plus oracle attention computation is non-trivial — needs a dataset of full-attention traces and a GRPO infrastructure. Per the intake notes, the GRPO recipe was specifically needed because pure supervised distillation degraded LM loss on low-entropy tokens — independent corroboration of the SP-KV critique.

**Critical observation for our stack.** ForesightKV's validation domain is **math reasoning only** (AIME). The intake mentions generalization to GPQA and LiveCodeBench, but headline numbers are AIME. For our frontdoor / coder workloads — which include long non-reasoning prefixes (tool documentation, code context) — generalization is unproven. **The 92 %-at-2K and 99 %-at-4K numbers should not be extrapolated to LongBench-style long-context understanding without re-running.**

**Verdict.** **Defer.** Strongest reasoning-domain result in the cluster but training pipeline cost is real and frozen-quant inference would still need the scorer wired into llama.cpp. Worth revisiting if (a) we acquire fine-tuning capacity and (b) the reasoning workload becomes a dominant token-cost driver in production.

---

### intake-554 — PBKV / Prediction-Based KV-Cache (Zheng, Fu, Wu, Yuan et al.)

**Mechanism.** Operates at the **workflow / orchestrator layer**, not inside the attention kernel. Existing KV-cache managers are either **per-agent** (miss cross-agent reuse) or **per-workflow** (assume a static agent sequence). PBKV predicts which agents will be invoked next using "guidance from historical workflows and context of the target workflow" (history-conditioned predictor), estimates reuse potential per cache entry, and keeps high-potential entries resident in GPU memory (or, in our case, RAM-resident vs evicted-to-disk).

**Training.** Predictor architecture **not disclosed in the abstract/PDF excerpts available** — paper PDF saved locally if deeper extraction needed later. Inputs: historical workflow traces + target-workflow context. Likely a small classifier / next-token-style model over an agent vocabulary.

**Benchmarks.** Three workflow benchmarks (specific names not extracted from abstract; SWE-Bench appeared in PDF extraction excerpt but full enumeration not confirmed; **AppWorld is mentioned in intake notes but not surfaced in fetch — flag for verification**).

**Headline numbers (confirmed from abstract).** **Up to 1.85× speedup over LRU on dynamic workflows** and **up to 1.26× speedup over the SOTA baseline KVFlow on the static workflow**. KVFlow is the prior workflow-level SOTA.

**Baselines.** LRU, KVFlow, implicit per-agent caches.

**Code / license.** **CC-BY 4.0** confirmed from PDF metadata. Code repository URL not yet identified in the fetched content.

**Frozen-weights compatibility.** **Yes — fully.** Operates entirely above the LLM. No kernel changes, no weight changes, no GGUF surgery.

**Integration touchpoints.** PBKV mentions **vLLM and SGLang** as serving frameworks (from PDF excerpt). Our stack uses **llama.cpp**, which has its own prefix-cache machinery (`llama_state` / KV-cache snapshot APIs, RadixAttention-style prefix tree in the active llama-cpp-fork-rebase work). The orchestrator-side residency manager is the load-bearing piece — the inference engine just needs to expose "is this prefix cached?" and "drop this prefix" APIs, both of which we already have or can add via the prefix-cache hooks tracked in `llama-cpp-fork-rebase.md`.

**Mapping to our stack.** Our orchestrator hands a single long prompt across frontdoor → coder/worker in the standard hand-off pattern. Today each downstream model re-prefills from scratch (or relies on llama.cpp's own per-server prefix cache, which has no cross-server visibility). PBKV's prediction layer would let the orchestrator answer "which of the 30 model servers is most likely to receive the next turn, and should it keep this prefix warm?". Even a **heuristic** version (e.g., "if frontdoor just routed to coder with a 5K-token context, keep the coder prefix warm for N turns") may capture most of the 1.85× LRU gain without any learned predictor.

**Verdict.** **Strongest single match in the cluster for the EPYC orchestrator.** Highest immediate ROI, lowest blast radius, no fine-tuning. **Recommend a SPIKE PROPOSAL** (see EPYC Integration Plan below).

---

## PBKV as Strongest Orchestrator Match — Detailed Analysis

PBKV is the only paper in the cluster that operates **above** the attention kernel. Every other method — SP-KV admission, KVP eviction, LU-KV head budgeting, ForesightKV oracle distillation — touches the GGML attention path and requires either GGUF-level surgery or fine-tuning. PBKV touches only the **orchestrator's residency manager** and the inference engine's existing prefix-cache APIs.

### Why this matches our stack

Our orchestrator runs **30 model servers** and the frontdoor explicitly routes (frontdoor) → (coder | worker | drafter | scorer | …). Long prompts are shared (the system prompt + tool documentation + recent conversation history is identical across hand-offs in a single turn). Per `feedback_cpu_decode_bw_bound`, **prefill on EPYC is DRAM-BW-bound** — re-prefilling a 5-10 K-token shared prefix when handing off frontdoor → coder is the dominant per-turn cost. PBKV's prediction layer directly addresses this by amortizing prefill across agents.

### Integration path (no fine-tuning needed)

1. **Predictor (orchestrator-side).** A tiny next-agent classifier over our agent vocabulary (~30 servers + sentinel). Inputs: last-K hand-off history (server IDs + brief context summary or embedding). Output: per-server invocation probability. Even a hand-coded transition matrix from production traces is a useful v0.
2. **Residency manager (orchestrator-side).** For each (prefix_hash, server_id) pair, maintain a "warmth score" = predicted next-call probability × token-count saved on hit. Evict by lowest warmth.
3. **Inference-engine hooks.** llama.cpp already supports `llama_state_save` / `llama_state_load` for prefix snapshots, and the **`llama-cpp-fork-rebase.md`** active handoff is tracking RadixAttention-style prefix-tree integration. PBKV needs `prefix_cache_pin(prefix_hash, server_id)` and `prefix_cache_drop(prefix_hash, server_id)` — both achievable as thin wrappers over existing APIs.

### Does NOT require base-model fine-tuning

This is the crucial distinction from SP-KV / ForesightKV / KVP. PBKV is purely an orchestration / caching decision. Our frozen GGUF stack is untouched.

### Reported numbers (verified from abstract)

- **1.85× over LRU** on dynamic workflows (the regime that matches our routing pattern)
- **1.26× over KVFlow** on static workflows (KVFlow is the prior SOTA workflow-level system — Sui et al., a known reference)

### EPYC dev cost estimate

- **Predictor**: ~100 LOC Python (hand-coded transition matrix v0) → ~300 LOC for a small MLP classifier (v1)
- **Residency manager**: ~500 LOC in `epyc-orchestrator/src/` — new module
- **llama.cpp hooks**: ~50 LOC C wrappers + bindings (depends on RadixAttention work landing first)
- **Trace collection**: existing agent-log infrastructure already captures hand-off sequences (see `scripts/utils/agent_log.sh`); just need a hand-off-sequence extractor (~50 LOC)

**Total spike size**: ~1 KLOC + integration testing. **Order-of-magnitude smaller than KVP / ForesightKV / SP-KV.**

### Success criteria for spike

- Microbench: representative frontdoor → coder hand-off trace, measure end-to-end turn latency with and without PBKV warmth
- Target: **≥ 1.5× decode-tps amortization** on a single hand-off (re-prefill avoided = full prefill cost saved on the downstream server)
- Stretch: **≥ 1.3× steady-state throughput improvement** measured across a 100-turn dynamic workflow trace
- Quality: zero quality regression (deterministic — we are only caching, not changing token selection)

### Open dependency

The RadixAttention-style prefix tree in `llama-cpp-fork-rebase.md` is a soft prerequisite. Without it, PBKV's residency layer still works but its hit rate is limited to whole-prefix matches; with it, partial-prefix hits compose multiplicatively with PBKV's predictions.

---

## SP-KV — Critical Skepticism

Steele 2601.14279 demonstrates that a 1.7 M-parameter learned KV-only scorer (SIP) **fails to beat trivial position-based heuristics** (keep first 4 + last N) across 5 seeds × 4 retention levels × 3 tasks. Random selection sometimes matches learned scoring. **SP-KV is exactly the class SIP falsifies**: KV-only, query-agnostic, write-time. The only meaningful difference is that SP-KV jointly fine-tunes the base LLM to "co-adapt" with its predictor — but the SIP critique is that the *predictor signal itself* contains no information beyond position.

**The experiment SP-KV does not appear to run** (and which would be the only convincing rebuttal): compare SP-KV at retention rate R against StreamingLLM (sink + sliding window) **at matched retention R, matched fine-tuning compute, and matched local-window size**. If the gap is < 1 pp on a battery of LongBench tasks, the learned predictor adds nothing — SP-KV's gains come from the recency-window component and the joint fine-tune itself (which would help StreamingLLM equally).

The ForesightKV team's observation that pure supervised KV scoring degrades LM loss on low-entropy tokens (requiring GRPO with an explicit low-entropy reward) is **independent corroboration**: learned KV importance is brittle without explicit LM-loss safeguards. SP-KV trains only on next-token-prediction loss — it has no such safeguard.

**TokenButler** (which the intake notes references) succeeds precisely because it conditions on the **current query** — directly implying read-time methods have an information advantage write-time admission cannot recover.

**Verdict for our stack:** even if SP-KV's reported 3-10× compression numbers replicate, we cannot use SP-KV without joint fine-tuning, and once fine-tuning capacity exists we should preferentially burn it on read-time / query-aware methods (ForesightKV, KVP) rather than write-time admission.

---

## ForesightKV — Honest Read-Time Eviction

ForesightKV's 92 % / 99 % retention at 2K / 4K budget on AIME is the cluster's most concrete reasoning-domain result, and the 9.79× throughput speedup at 32K context is meaningful. The two-stage Supervised+GRPO recipe is required **because the team observed** pure learned scoring degraded LM loss on low-entropy (deterministic-reasoning) tokens — this is exactly the failure mode the SP-KV critique above predicts.

The honest read of ForesightKV is: **it is the right way to do a learned eviction predictor**. The pipeline cost (oracle attention traces + GRPO infra) is real, the validation is narrow (math reasoning), but the methodology is methodologically sound and the low-entropy reward signal is a genuine technical contribution.

For our stack: defer. We don't have GRPO infra, our workload is not math-reasoning-dominated, and LU-KV gives most of the budget-allocation benefit without any training.

---

## LU-KV — Frozen-Weights Compatible (and Cluster's Best Engineering Trade-off)

LU-KV is the **only attention-kernel method in the cluster that is fully frozen-weights compatible with zero training**. The convex-hull / PAVA / greedy-marginal-utility machinery runs **once, offline**, on a 4K-token calibration corpus and produces a static per-head budget profile. Inference is a 3-step table lookup + per-head Top-k application using **any existing scorer** (SnapKV, KeyDiff, Expected-Attention — all already understood in our cluster from prior intakes).

Reported numbers are strong:
- **LongBench @ 80 % compression**: 46.21 % vs 40.54 % AdaKV (Mistral-7B-v0.3, KeyDiff). Recovers 84 % of the full-KV gap.
- **RULER-16K @ 80 % compression**: 69.98 % vs 37.48 % AdaKV (SnapKV scorer). Multikey-3: 67.40 % vs 1.00 % Uniform.

The multikey-3 case is the most diagnostic: uniform per-head budgeting is essentially useless (1 %), and LU-KV's per-head profile recovers full performance. This is the strongest evidence in the cluster that **per-head heterogeneity is the right axis** and that frozen-weights methods can exploit it.

**Calibration cost.** Paper says "M queries" without disclosing exact M. A reasonable upper bound is a few hundred to a few thousand calibration runs at 4K context. On EPYC at ~50 t/s prefill, that is hours-not-days of one-time CPU time per model.

**llama.cpp integration cost.** Lower than KVP / ForesightKV because the inference path is just "apply existing per-head scorer at lookup-determined budget" — and llama.cpp already has the per-head attention machinery; the missing piece is the per-head Top-k mask. Estimate: ~500-1000 LOC in the GGML attention path + ~200 LOC Python harness for offline profiling.

**Verdict.** **Second-priority spike after PBKV.** Strongest attention-kernel-level frozen-weights result in the cluster.

---

## KVP — Offline RL on Traces

KVP demonstrates that **per-head RL agents trained offline on K/V/position traces, with zero attention scores and zero queries, can match attention-aware eviction methods**. This is technically impressive but operationally heavier than LU-KV without delivering meaningfully larger gains in the regimes our stack cares about.

**Strengths.** No LLM weight modification. Zero decode-time overhead (compression once post-prefill). Tiny agents (~650 K params × 112 = ~73 M params total for Qwen2.5-7B, trivial). Zero-shot generalization to longer contexts and unseen tasks (BoolQ, ARC, GovReport) without retraining.

**EPYC blockers.**
1. Offline trace-generation pipeline — we'd need to run base LLM forward on a calibration corpus and dump Q/K/V tensors per layer per head. Disk + compute non-trivial but feasible.
2. FlexAttention equivalent on llama.cpp — KVP uses PyTorch FlexAttention for the custom per-token attention masks. GGML has no equivalent; we'd need to either bake the masks into the KV cache layout (drop rows) or add a per-head sparse-attention path.
3. Apple paper code not in evidence — implementation from scratch.

**Verdict.** **Third-priority spike.** Cleaner than ForesightKV (no GRPO, no oracle), heavier than LU-KV (real per-head agents not just lookup tables). Stage behind LU-KV — if LU-KV's static profile saturates the per-head heterogeneity gain, KVP's per-token policy is unlikely to add much more.

---

## Comparison: All 5 vs Heuristic Baselines — The Missing Experiment

A consistent gap across the cluster: **none of the five papers presents a clean "sink + sliding-window" baseline (StreamingLLM) at matched cache budget**.

| Method | StreamingLLM compared? | H2O compared? | SnapKV compared? |
|--------|------------------------|---------------|------------------|
| SP-KV | not surfaced in fetch (PDF body needed) | not surfaced | not surfaced |
| KVP | **yes** (named in baseline list) | **yes** | **yes** |
| LU-KV | no (Uniform / PyramidKV / AdaKV only) | no | **yes** (as scorer choice, not as eviction baseline) |
| ForesightKV | no | **yes** | **yes** |
| PBKV | n/a (orchestrator layer, different comparison set: LRU / KVFlow) | n/a | n/a |

KVP is the only paper that explicitly compares to StreamingLLM. The others use stronger learned/heuristic baselines (H2O, SnapKV, AdaKV) as their comparison floor, which leaves the StreamingLLM "easy floor" question unanswered. Per Steele 2601.14279, this is a real concern: at matched budget after matched fine-tuning, the gap between StreamingLLM and the more elaborate methods may be much smaller than headline numbers suggest.

**Operational implication for our stack:** before investing in **any** of the four attention-kernel methods (SP-KV / KVP / LU-KV / ForesightKV), we should first land a clean StreamingLLM (sink_k=4 + window=W) baseline in llama.cpp on a representative model + workload and **measure the floor**. If StreamingLLM + sink at 80 % compression already gets us within a few pp of full-KV on LongBench, the marginal value of the more elaborate methods drops accordingly.

PBKV is exempt from this critique because it operates on a different axis (residency, not selection) and its baselines (LRU, KVFlow) are the right comparison set for its layer.

---

## EPYC Integration Plan (Prioritized)

### 1. **PBKV — SPIKE PROPOSAL (highest immediate ROI)**

- **Why first**: orchestrator-layer, no fine-tuning, no kernel changes, no GGUF surgery, matches our frontdoor↔coder↔worker pattern exactly.
- **Dev cost**: ~1 KLOC across orchestrator + thin llama.cpp wrappers.
- **Prerequisite**: RadixAttention-style prefix tree from `llama-cpp-fork-rebase.md` is a soft dependency (works without it, scales better with it).
- **Success criteria**: ≥ 1.5× decode-tps amortization on a representative frontdoor→coder hand-off trace; ≥ 1.3× steady-state throughput improvement on a 100-turn dynamic workflow trace; zero quality regression (deterministic caching).
- **Handoff target**: propose a new handoff `handoffs/active/pbkv-orchestrator-residency.md` after user approval (per `feedback_audit_parallel_agent_first`).

### 2. **LU-KV — second priority (highest attention-kernel ROI under frozen-quant constraint)**

- **Why second**: only attention-kernel method in the cluster that is fully frozen-weights compatible with zero training; static per-head profile + table-lookup inference; integrates with existing per-head scorers (SnapKV/KeyDiff/Expected-Attention) already understood from prior intakes.
- **Dev cost**: ~500-1000 LOC GGML attention-path changes + ~200 LOC offline profiling harness.
- **Prerequisite**: StreamingLLM baseline landed first (see "Missing Experiment" above) so we can measure LU-KV's gap vs the easy floor.
- **Success criteria**: ≥ 50 % of full-KV LongBench quality at 80 % compression on Qwen3.6-35B or Coder-30B; measured decode-tps improvement consistent with proportional BW reduction.

### 3. **KVP — third priority (defer until LU-KV measured)**

- **Why third**: if LU-KV's static per-head profile already saturates the per-head heterogeneity gain, KVP's per-token policy is unlikely to add proportional value. Re-evaluate after LU-KV results.

### 4. **ForesightKV / SP-KV — defer indefinitely**

- Both require fine-tuning capacity we don't have. Reconsider only when (a) DGX Spark or equivalent FT host is acquired, AND (b) reasoning workloads dominate per-turn cost on the production stack.

---

## Cross-Cutting Concerns vs Active Handoffs

- `attention-matching-kv-compaction.md` — already updated per intake-538 notes. AttentionMatching is a **complementary** approach: it does post-prefill compaction (closed-form, frozen-weights) of an already-selected KV subset. **AttentionMatching + LU-KV is a natural pairing** — LU-KV chooses per-head budget, AttentionMatching compresses within that budget.
- `triattention-kv-selection.md` — TriAttention is query-aware read-time selection. KVP / ForesightKV are in the same family; LU-KV operates one level up (budget allocation, not token selection). **TriAttention + LU-KV are also pairable.**
- `summary-token-attention-readiness.md` — summary-token methods overlap with SP-KV's "local + global" split structurally but use compressed summary representations rather than admission gating. Not directly displaced by anything in this cluster.
- `multiscreen-attention-evaluation.md` — Multiscreen is an inference-time read-side method; SP-KV is its train-time write-side counterpart. Not a current displacement.
- `llama-cpp-fork-rebase.md` — RadixAttention prefix-tree work is the **load-bearing prerequisite for PBKV**. Status should be checked before opening a PBKV spike.
- `handoffs/completed/kv-cache-quantization.md` — KV quantization is orthogonal to all five methods here (quantize values, vs select which entries to keep). Composable with any of the five.

---

## Open Questions for User

1. **PBKV spike approval.** Do you want a `handoffs/active/pbkv-orchestrator-residency.md` stub drafted (subject to your usual no-sub-agent-driven-index-changes policy)? PBKV is the highest-ROI lever in the cluster and the spike is small.
2. **StreamingLLM floor experiment.** Before investing in LU-KV / KVP / ForesightKV implementations, should we first land a clean StreamingLLM baseline in llama.cpp and measure the easy-floor on our 4-5 representative workloads? This is ~200 LOC and would shift the prioritization of methods 2-4 above.
3. **Frontdoor↔coder hand-off trace.** What's the canonical trace we should benchmark PBKV against? `progress/` agent-log dumps capture hand-offs but the per-prefix-token counts aren't easily extractable; should we add a hand-off-sequence extractor to `scripts/utils/`?
4. **Fine-tuning workstream timing.** If/when DGX Spark arrives, should ForesightKV (best reasoning-domain result) or SP-KV (joint co-adaptation across all workloads) be the first fine-tuning-required KV method evaluated? My read: ForesightKV first, since its methodology (oracle distillation + LM-loss-safeguarded RL) is more defensible than SP-KV's pure next-token-prediction joint FT.
5. **PBKV PDF deep-mine.** The PBKV PDF (1.6 MB) is saved in fetch cache. Worth a second pass to extract exact benchmark names (AppWorld vs SWE-Bench vs others), predictor architecture, and code-repo URL — or is the orchestrator-layer mechanism sketch sufficient for a spike proposal?

---

## References

- **intake-538** SP-KV: arxiv.org/abs/2605.14037 — Szilvasy, Faysse, Lomeli, Douze, Mazaré, Cabannes, Yih, Jégou (FAIR)
- **intake-551** KVP: arxiv.org/abs/2602.10238 — Moschella, Manduchi, Sener (Apple)
- **intake-552** LU-KV: arxiv.org/abs/2602.08585 — Tang, Jiao, Chen, Liu, Li, Chen
- **intake-553** ForesightKV: arxiv.org/abs/2602.03203 — Dong, Liu, Li, Chen, Peng, Wang, Zhao
- **intake-554** PBKV: arxiv.org/abs/2605.06472 — Zheng, Fu, Wu, Yuan, Zhang, Wang, Zhu, Yan, Jiang — CC-BY 4.0
- **Contradicting evidence** Steele 2601.14279 (SIP falsification of KV-only scorers)
- **Cluster cross-refs** kv-compaction-attention-matching-cluster.md (2026-04-13); triattention-kv-selection-cluster.md
- **Active handoffs** attention-matching-kv-compaction.md, triattention-kv-selection.md, summary-token-attention-readiness.md, multiscreen-attention-evaluation.md, llama-cpp-fork-rebase.md
- **Completed handoff** kv-cache-quantization.md
- **Related intakes** H2O, SnapKV, StreamingLLM, TokenButler, KVFlow, AttentionMatching, TriAttention, AdaKV, PyramidKV, R-KV, KeyDiff, Expected-Attention

---

**File**: `/workspace/research/deep-dives/2026-05-19-kv-admission-cluster.md`
