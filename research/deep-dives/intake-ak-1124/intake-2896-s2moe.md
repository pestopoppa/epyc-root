# Dive — s2moe — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2608.15018v2", retrieved: "2026-11-24", sha256: "87593850d24a"}

Stage 2b wave 1 (light dive), expanded from intake-2876 (ccamoe). Question to settle: same as specmoe (how the self-draft works, cost versus acceptance, does it overturn decline A5), plus whether an edge/CPU setting gives evidence for A3 or A5.

## 1. Stage-1 fields
- title: S2-MoE: Enabling Efficient Self-Speculative Decoding for Mixture-of-Experts on Edge Devices
- authors: Haochen Huang, Shengxuan Qiu, Meng Li (Peking University). Version v2, 19 Aug 2026, cs.AI. Code link given: github.com/angerybob/S2-MoE (not fetched).
- categories: speculative_decoding, moe_optimization, local_inference, inference_serving, hardware_optimization
- novelty: medium. Three additions on top of a fewer-experts self-draft: utility-guided tree expansion priced with expert-union cost, reuse-aware gating, shared draft/target KV cache.
- relevance: medium. Implemented in llama.cpp and evaluated on Qwen3-30B-A3B among others; but every configuration is expert-offloaded (SSD or PCIe), never CPU-DRAM-resident.
- credibility_score: 2 = not peer-reviewed 0, within 12 months (Aug 2026) +1, known group (PKU, Meng Li) +1, commercial bias 0, independent corroboration 0 (all numbers are the authors' own).
- verdict: adopt_patterns. Cite for (a) the expert-union marginal-cost utility rule as an A1 cost model and (b) negative evidence on the fewer-experts self-draft baseline. Do not cite for CPU-resident speedups: none are measured.

## 2. Key claims
0. CONFIRMED. The draft is the target model with fewer experts per token (expert sparsity), chosen over quantised and layer-skip drafts. For Qwen3-30B-A3B it activates 3 of the target's 8 experts per token, with a gating cap of 14. Draft length is fixed at 8 for the baselines, width 2; S2-MoE uses adaptive expansion. Anchors 0, 1, 2.
1. CONFIRMED. The fewer-experts self-draft ("ES", the primitive behind ccamoe A5) usually loses to plain autoregressive decoding in this paper's own tables. Raw appendix tables 5-8: ES speedup below 1.0 in 96 of 112 model-task-platform cells (counted from tables 5-8, all four models). For Qwen3-30B-A3B it is 0.52-0.74 on Jetson AGX Orin 64 GB, 0.60-0.80 on 32 GB, 0.94-1.06 on Orin NX 16 GB, 0.63-2.01 on RTX 4090. Anchors 3, 4.
2. CONFIRMED. The winning additions are not the draft itself. S2-MoE reaches 1.48-2.14x on Qwen3-30B-A3B Jetson 64 GB and 1.20-2.87x on RTX 4090 (Qwen3 column, tables 7-8) via: shared KV cache (acceptance +24% to +79% on DeepSeek/OLMoE, table 3), a utility rule U_i = p_i*T_AR / (marginal verification cost + draft cost) >= 1 with marginal cost = number of newly activated experts x T_exp, and reuse-aware gating. Anchors 5, 6, 7.
3. CONFIRMED, with a caveat for us. Reuse-aware gating biases the TARGET's routing during verification, so it is a controlled approximation, not lossless: PPL ratio 1.012-1.013 and top-1 agreement above 89% (Qwen3 93.04%) against the unmodified target. Anchor 8.
4. CONFIRMED. Setting is memory-constrained offload on edge GPUs: Jetson Orin 16/32/64 GB with experts spilling to SSD, and RTX 4090 with cold experts in CPU memory; baseline AR for Qwen3 is 0.41-0.91 tok/s on the Jetson boards. No CPU-only or DRAM-resident configuration. Anchors 9, 10.
5. NOT-FOUND-IN-SOURCE. Per-token draft cost, a residency-coverage curve, or any hot-expert coverage number for A3. The paper keeps "frequently activated experts" resident from offline profiling but reports no coverage fraction. It states acceptance rises with draft top-k while overhead rises too (no numbers in text; figure 10 not viewable).

## 3. Reported results (as stated)
- Headline: 1.3-5.3x speedup on Jetson Orin and 1.2-2.9x on RTX 4090 over autoregressive decoding, about 2.0x on average (abstract). Against EAGLE-3 (llama.cpp PR #18039 branch) and Cascade.
- Models: DeepSeek-V2-Lite (15.3B), OLMoE (6.7B), Qwen3-30B-A3B, GPT-OSS-120B. Seven task types (Spec-Bench style). Temperature not stated (NOT-FOUND-IN-SOURCE).
- Quality (table 2): PPL ratio 1.012-1.013, top-1 agreement 89.13-93.04%, mean KL 0.026-0.065; task accuracy differences small and non-systematic.
- Cost model: predicted vs measured verification latency R^2 0.943-0.999, MAPE 0.8-4.5% across models and memory budgets (offload regimes).
- Raw tables 5-8 give tok/s, acceptance length and speedup per method; Qwen3 HumanEval Jetson 64 GB: AR 0.85 tok/s, ES 0.56 tok/s (0.66x), S2-MoE 1.82 tok/s (2.14x).

## 4. Performance-principles table
| Principle | MI210 gfx90a | Zen 5 EPYC 9655 |
|---|---|---|
| Fewer-experts draft (top-k 3 of 8 on Qwen3) | PARTIAL. Only worth it where expert bytes dominate the draft step; on the MI210 A3B is not served. | NO evidence for. Draft still reads attention, shared experts, router, norms of every layer; the paper's ES baseline loses to AR in most cells. DRAM-resident cost unmeasured. |
| Utility rule U >= 1 with cost = new experts x T_exp (marginal expert-union cost) | YES (principle). Union growth on gfx90a verify plus tile cliffs; same family as DTREE-B gain per second. | YES. Fits bandwidth-bound verify directly; T_exp is a measured bytes/bandwidth constant per expert, fit from our per-K timings. Refit, do not import R^2. |
| Reuse-aware gating (bias router logits toward experts shared across draft tokens) | PARTIAL. A tiny fused router kernel; but changes target routing. | PARTIAL. Same; changes the output distribution (KL 0.026 on Qwen3), so it fails our target-distribution gates by construction. |
| Shared draft/target KV cache with draft KV rolled back before verify | PARTIAL. Our DFlash2/MTP drafters already read the target's context; no separate draft history exists to drift. | PARTIAL. Same: the MTP head conditions on target hidden states, so the paper's drift problem does not arise. |
| Expert-level offload with offline-profiled resident set | PARTIAL. Needs HBM allotment. | NO. No slower tier for A3B. |

## 5. In-house state
- No fewer-experts drafter, reuse-aware gating or union-priced expansion in C21 `98ff8a4`. Chain stop is top-1 p_min (`common/speculative.cpp:1955-1965 @ 98ff8a4`); DTREE-B auto controller prices width by measured round time and runs a chain above batch 4 (`handoffs/active/speculative-decoding.md:2483 @ f74b175`, per ccamoe dive).
- A3B skew already measured: RT-9 top-10% share 0.41-0.50, top-25% 0.68-0.74 (prefill), 0 of 40 layers at >= 0.60 (`handoffs/active/cpu-decode-roofline-program.md:6049 @ f74b175`). So no new trace capture is needed to settle A3's gate.
- A3B p_min 0.5 kept by CAFE-1-SERVED-T (`handoffs/active/speculative-decoding.md:514 @ f74b175`).

## 6. Derived-actionables ledger
| # | Draft task | Owner | Compute | Stop / decision rule |
|---|---|---|---|---|
| T1 | Refines ccamoe A1/A2 (not a duplicate): in the A1 replay, add S2-MoE's marginal-cost term as a candidate stop rule: continue while p_prefix x TPOT_AR >= (new experts in the union x T_exp) + draft cost, with the new-expert count taken from A3B routing traces and T_exp fit from measured per-K verify times. | `speculative-decoding.md` (CAFE-1 / A3B-PMIN05 block, :509-514) | code/doc-only offline replay on saved captures and RT-9 routing traces | Question: does union-priced stopping beat the kept p_min 0.5? Same keep/close thresholds as A1. Futility: if fitted T_exp has R^2 below 0.9 on measured K, close this variant (the paper's 0.943+ is an offload regime). |
| T2 | DECLINE (reaffirms ccamoe A5): fewer-experts self-draft on CPU A3B. Reason specific to this entry: the paper's own ES baseline is below 1.0x in 96 of 112 cells including Qwen3-30B-A3B on every Jetson board, and the paper reports no draft cost, so the evidence points the same way as A5's cost argument; all measurements are offload-bound so they do not prove a DRAM-resident result either. Reopen only on a measured per-token draft cost below the MTP head's. | n/a | n/a | n/a |
| T3 | DECLINE: reuse-aware gating. Reason: it alters target routing during verification (Qwen3 mean KL 0.026, top-1 agreement 93.04%), which our spec gates (distribution KS in CAFE-1-SERVED-T, in-row identity bands) treat as a failed output law. | n/a | n/a | n/a |
| T4 | DECLINE: shared draft/target KV. Reason: our MTP/DFlash2 drafters already condition on the target's state; there is no independent draft context to drift. | n/a | n/a | n/a |

## 7. Dive-surfaced sources
- MoE-SpAc: arXiv id resolved from this paper's reference list as 2603.09983 (Li et al., 2026); unbounded grep of `research/intake_index.yaml`: 0 hits. It would not change a ledger row (A5 and A1 already settled above): decline.
- Cascade / Utility-driven speculative decoding (2506.20675) is already in the index (7 hits); MoESD 2505.19645 already in (4 hits).
- github.com/angerybob/S2-MoE (llama.cpp implementation): not fetched. Would only matter if T1 turned into a code port; decline for now, reopen if T1 passes.
- Zheng et al., "Self-speculative decoding for on-device MoE acceleration" (WWW 2026), no arXiv id in the reference list: decline (no ledger row it would change).

## 8. Contradiction / adversarial pass
- All speedups are against AR in offload-bound regimes (AR 0.41-0.91 tok/s on Jetson Qwen3, about 1 tok/s GPT-OSS); verification reads from SSD, so reducing wasted expert reads is worth far more than on our DRAM-bandwidth-bound CPU.
- Baselines: EAGLE-3 with third-party checkpoints, Cascade re-implemented by the authors; ES and LS are the authors' own configurations (LS evaluated only on two models).
- Reuse-aware gating is lossy by the authors' own statement; speedup attribution (figure 8) is by progressive ablation, figure not viewable.
- No independent replication; Qwen3 on the 4090 shows ES at 0.63-2.01x, i.e. fewer-experts drafting is sometimes a win in the least memory-starved platform, which is the closest hint of a favourable regime but still PCIe-offloaded.

## 9. read_depth
FULL (text, tables 1-8, equations 1-4; figures 1-10 not viewable, so draft-top-k and gating-cap sensitivity curves unread). lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit
artifact audit: clean
