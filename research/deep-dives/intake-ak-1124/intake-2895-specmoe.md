# Dive — specmoe — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2604.10152v1", retrieved: "2026-11-24", sha256: "6d5f929404ac"}

Stage 2b wave 1 (light dive), expanded from intake-2876 (ccamoe). Question to settle: how the self-draft works, its cost versus acceptance, and whether it overturns ccamoe decline A5.

## 1. Stage-1 fields
- title: SpecMoE: A Fast and Efficient Mixture-of-Experts Inference via Self-Assisted Speculative Decoding
- authors: Jehyeon Bang, Eunyeong Cho, Ranggi Hwang, Jinha Chung, Minsoo Rhu (KAIST; UNIST). Version v1, 11 Apr 2026, cs.AI. Page states it is an extended version of a paper accepted at DAC 2026.
- categories: speculative_decoding, moe_optimization, hardware_optimization, local_inference
- novelty: medium. The self-draft is built from the target's own parts with no training; the paper calls it the first to use MoE structure for speculative decoding (its own claim).
- relevance: low. Setting is GPU + PCIe expert offload at batch up to 256; ours is CPU-resident A3B decode with verify widths 2-16.
- credibility_score: 4 = peer-reviewed (DAC 2026 accepted, per page) +2, within 12 months (Apr 2026) +1, known group (KAIST, Minsoo Rhu) +1, commercial bias 0, independent corroboration 0 (S2-MoE cites it as related work and does not replicate it).
- verdict: adopt_patterns. Cite for the resident-draft-pool mechanism and the verify-union amortisation argument; it does not change any decision (A5 stands).

## 2. Key claims
0. CONFIRMED. The self-draft is the target's non-expert weights plus N draft experts pinned in GPU memory per MoE block (N >= K, same top-K gate over the N pinned, with an L2-distance affinity table redirecting a pick that is not pinned). No experts move during drafting. After each verify the N temporally hottest experts become the next pool at no extra transfer. It is NOT a reduced-top-k draft; K is unchanged. Anchors 0, 1.
1. CONFIRMED as stated, narrow in scope. Up to 4.30x throughput over MoE-OnDemand (NLLB-MoE, batch up to 256) on H100 + PCIe 5.0 with 1 TB DDR5. Gains come from coalescing expert transfers over a slow link; at batch <= 4 caching wins or ties. Anchors 2, 3.
2. CONFIRMED. Draft pool size trades acceptance against draft cost: N=2/4/8/16 gives 6.929/7.265/7.620/7.819 tokens per step but throughput 116.4/123.0/121.3/117.2 tok/s, peaking at N=4. Anchor 4.
3. CONFIRMED. Choosing the pool matters little for acceptance: Random 6.812, HotGlobal 7.220, HotTemporal 7.265 tokens per step (speedup 1.000/1.084/1.143 normalised to Random). Anchor 5.
4. NOT-FOUND-IN-SOURCE. The measured per-token draft cost ratio c (draft time / target time). Eq 2 (S = tau/(gamma*c + lambda)) is given but c is never reported, so the paper cannot support or refute A5's cost-versus-MTP comparison.
5. CONFIRMED. Skew determines acceptance. Table I reports the fraction of routed tokens covered by the top 25% experts: NLLB-MoE 0.84, Mixtral-8x7B 0.32, Llama-4-Scout 0.59. Low-skew models use gamma=5 and get smaller gains (2.17x Mixtral, 1.42x Scout at T=1). Anchor 6.

## 3. Reported results (as stated)
- Hardware: two Xeon Platinum 8558, 1 TB DDR5, one H100 96 GB, PCIe 5.0 (64 GB/s one way); PyTorch 2.5.0 + HF Transformers with a custom batched implementation.
- NLLB-MoE (128 experts, 6 of 24 layers MoE, top-2), WMT-14 EN-FR, greedy verify, gamma=10, N=4: up to 4.30x throughput over MoE-OnDemand, 123.0 tok/s at batch 256, latency 23% of OnDemand at batch 256, CPU-to-GPU transfer down up to 76.73% vs OnDemand/Overlap and 71.89% vs Caching.
- Mixtral-8x7B up to 2.17x, Llama-4-Scout up to 1.42x over OnDemand, CNN-DailyMail, temperature 1, sampling-based verify, gamma=5. SpecMoE below MoE-Caching at batch <= 4.
- NLLB-MoE with experts on SSD: average 2.25x over OnDemand.
- Baselines: MoE-OnDemand, an oracular MoE-Overlap, MoE-Caching (top 10% experts pinned). No MTP, EAGLE or llama.cpp baseline.

## 4. Performance-principles table
| Principle | MI210 gfx90a | Zen 5 EPYC 9655 |
|---|---|---|
| Resident-pool self-draft (non-expert weights + pinned hot experts, drafting never leaves the fast tier) | PARTIAL. Needs an expert pool in HBM; our A3B is served on CPU, so HBM for the pool would come out of the 27B's budget. Real only for a hybrid placement. | NO as designed. All experts are in DRAM; there is no slower tier to avoid. The only tier boundary is L3 (size uncited). |
| Verify coalesces expert transfers across gamma tokens (union of experts, each read once) | YES (principle). Union growth is the verify cost term on any MoE. | YES. Bandwidth-bound verify reads the union at the measured 112.9 GB/s single-quarter ceiling; this is the cost the draft-length rule must price. |
| Pool refresh from verify-time activations (HotTemporal), no extra transfer | PARTIAL. Free only if the pool is device-resident. | NO. No transfer to save. |
| Affinity-table substitution of a non-resident pick by the nearest resident expert (L2 table, under 200 KB for 128 experts) | PARTIAL. Cheap table lookup in the router kernel. | PARTIAL. Same; but it is a lossy draft-side approximation only, verify stays exact. |
| Draft cost model S = tau/(gamma*c + lambda) | YES (algebra), same family as the DTREE-B gain-per-second controller. | YES. Needs measured c and lambda(K) from existing per-K step timings. |
| Lower gamma for low-skew models | YES (idea). | YES (idea): our p_min already acts as an adaptive gamma. |

## 5. In-house state
- No resident-pool or expert-subset drafter exists in C21 `98ff8a4`. A3B decode uses the MTP head; draft loops stop on top-1 probability below p_min (`common/speculative.cpp:1955-1965 @ 98ff8a4`, from the ccamoe dive); p_min 0.5 was kept for A3B by CAFE-1-SERVED-T (`handoffs/active/speculative-decoding.md:514 @ f74b175`).
- Expert-skew data already exists for the A3B target: RT-9 (Qwen3.6-35B-A3B frontdoor) top-10% selection share 0.503/0.419/0.463 prefill and 0.470/0.410/0.461 decode (code/prose/reasoning), top-25% share 0.73/0.68/0.74 prefill, 0 of 40 layers at >= 0.60 (`handoffs/active/cpu-decode-roofline-program.md:6049 @ f74b175`). Same metric family as SpecMoE Table I (top-25% share).

## 6. Derived-actionables ledger
| # | Draft task | Owner | Compute | Stop / decision rule |
|---|---|---|---|---|
| S1 | Refines ccamoe A3 (not a duplicate): compute the A3B top-12.5% expert coverage and the top-25% share per workload from the EXISTING RT-9 traces with `skew_report.py` and record A3 as CLOSED if same-domain coverage at 12.5% is below 0.6 (ccamoe's gate). Report the top-25% share in SpecMoE Table I's definition so it is comparable. | `cpu-decode-roofline-program.md` (RT-9 block, :6049) | code/doc-only, offline script on saved traces (no inference) | Question: does A3 need a new trace capture? Top-10% share is already 0.41-0.50 and top-25% 0.68-0.74, so the 0.6 gate at 12.5% is expected to fail; CLOSE when the 12.5% point confirms, OPEN only if it is >= 0.6 on >= 2 workloads. |
| S2 | DECLINE (reaffirms ccamoe A5): reduced-top-k or resident-subset self-draft on CPU A3B. Reason specific to this entry: SpecMoE's draft wins by never leaving a fast tier while verify pays the slow link; Table III shows throughput peaks at N=4 pinned experts even as acceptance keeps rising (draft cost grows), and the paper reports no draft-cost ratio c, so nothing here shows a draft cheaper than the one-layer MTP head. On a DRAM-resident A3B there is no tier gap. | n/a | n/a | n/a. Reopen only if a measured c for a top-k-reduced A3B draft is below the MTP head's. |
| S3 | DECLINE: port HotTemporal pool refresh or the affinity table. Reason: both serve a GPU-resident pool that ccamoe A4 already declined; HotTemporal adds 6.6% tokens per step over a random pool (7.265 vs 6.812) in a PCIe-bound regime. | n/a | n/a | n/a |

## 7. Dive-surfaced sources
- Cites MoE-SpAc (Li et al., 2026) and SP-MoE (2510.10302), not re-fetched. SP-MoE is already in the index (3 hits; unbounded grep). No further source would change a ledger row: decline.
- No code link in the source (NOT-FOUND-IN-SOURCE).

## 8. Contradiction / adversarial pass
- Authors state SpecMoE underperforms MoE-Caching at small batch (<= 4) and that it should be disabled there; our verify widths 2-16 are per-sequence, np=1.
- Gains shrink with skew (Mixtral 0.32: 2.17x, Scout 0.59: 1.42x) and rest on a slow link (PCIe/SSD).
- Evaluation is greedy for NLLB-MoE and sampled only for the two low-skew models; NLLB-MoE has MoE in 6 of 24 layers (draft is cheap there; not our A3B).
- Table II and III come from the authors' own runs; no replication, no MTP/EAGLE baseline.

## 9. read_depth
FULL (text, tables I-III, equations 1-2; figures not viewable). lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit
artifact audit: clean
