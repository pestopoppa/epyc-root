# Dive — ccamoe — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2611.28550v1", retrieved: "2026-11-24", sha256: "a375d42c9299"}

## 1. Stage-1 fields
- Title: CCAMoE: Cache-Conditioned Adaptive Inference for Offloaded MoE
- Authors: Xuan Zhang, Haisheng Tan, Han Tian, Jialiang Huang, Yuteng Wang (USTC, Hefei)
- Version/date: arXiv 2611.28550 v1, cs.DC, 21 Nov 2026
- Categories: speculative_decoding, moe_optimization, hardware_optimization, local_inference, inference_serving
- Novelty: medium. Resident-expert self-drafting is credited to SpecMoE / ELMoE-3D / SS-MoE; new is coupling it to draft-hint-driven concurrent prefetch and a TPOT-ratio draft-length rule conditioned on a substitution signal.
- Relevance: medium. Our A3B serves on CPU with every expert in DRAM and an MTP head; the PCIe offload machinery does not apply, but the stop rule and the residency-vs-acceptance data bear on p_min.
- credibility_score: 1 (peer-reviewed 0; <=12 months +1; major lab 0; commercial bias 0; independent corroboration 0 = 1).
- Verdict: worth_investigating. Rule and residency curve are testable offline against RATIFY-A3B-PMIN05; the system itself does not port.

## 2. Key claims
0. Cache-only drafting without draft weights: CONFIRMED, narrowed. Anchor 0 (Abstract), 1 (verification misses go to KTransformers CPUInfer). Eager cache-only drafting alone raised TPOT (ablation); it paid only after CUDA graphs.
1. Draft-guided cache updates overlapping transfers: CONFIRMED. Anchors 2, 3 (-56.8% Qwen, -30.5% DeepSeek; verify latency 83.4 to 42.9 ms, MAL 2.06 to 3.23 at K=4).
2. Cost-aware draft length: CONFIRMED rule, PARTIAL value. Eq 7 anchor 5, Eq 1 anchor 6; contribution only +1.1% / +0.9% (anchor 7); best fixed K 1 to 3 on Qwen as memory 12 to 24 GB (anchor 8).
3. "Up to 2.33x vs SOTA across models and GPU platforms": PARTIAL. Anchors 9-12. 2.33x is the best Qwen cell on RTX 4090 (24 GB, PCIe 4.0 x16, EPYC 9554, 16 threads), batch 1, versus the strongest of 5 offloading baselines per workload (KTransformers, or MoE-SpAc which is a speculative baseline). It is not versus a no-offload or no-spec stock engine. RTX 3080 (10 GB, PCIe 3.0): 1.34x Qwen, 1.20-1.24x DeepSeek. At a 12 GB 4090 budget: 1.33x and 1.09x. Two models, two consumer GPUs.
4. Acceptance of the cache-only drafter: CONFIRMED with conditions. Anchors 13, 14. Fixed K=8 probe on Qwen3-30B-A3B-Base: MAL 2.28 at 12.5% resident, 4.75 at 31.25%. End-to-end Qwen token acceptance 77.5% to 93.3% and MAL 1.33 to 2.83 for 12 to 24 GB (short adaptive drafts inflate acceptance versus K=8). Sampling temperature for these runs: NOT-FOUND-IN-SOURCE.

## 3. Reported results
- Qwen3-30B-A3B BF16 (58 GB routed experts), RTX 4090: 46 tok/s, 1.78-2.33x; full system 21.605 ms/token MT-Bench; 2.66x over eager offloading.
- DeepSeek-V2-Lite: 71 tok/s, 2.21-2.27x; 14.207 ms/token; 2.91x over eager offloading.
- RTX 3080: 1.34x Qwen, 1.20-1.24x DeepSeek; MoE-SpAc OOM on DeepSeek.
- CPU-thread sweep (4-32 threads): 1.54-3.24x Qwen, 1.63-3.05x DeepSeek vs faster baseline; KTransformers Qwen TPOT 49.7 to 90.4 ms going 16 to 4 threads.
- Ablation (cumulative, Qwen / DeepSeek): fixed cache -3.6 / -8.6%; eager cache-only drafting worse; CUDA graphs -62.4 / -52.2%; residency bias -11.7 / -5.0%; profiled layer capacity -2.2 / -4.5%; cache updates -56.8 / -30.5%; controller -1.1 / -0.9%.
- Output length 1k to 8k: TPOT +3.3% Qwen, +11.8% DeepSeek. Batch size 1 only (stated in Sec 7 as future work).

## 4. Performance-principles table
| Principle (mechanism / cost model) | MI210 gfx90a | Zen 5 EPYC 9655 |
|---|---|---|
| Resident-subset self-draft: run non-expert weights plus only resident experts, drop misses, renormalise (Eq 3 residency bias) | PARTIAL. Needs a GPU-resident expert subset; only meaningful for a hybrid placement. Our MI210 hosts the 27B; A3B is CPU-served by choice, so HBM for an A3B expert cache would have to come out of that budget. | PARTIAL. All experts are in DRAM, so "resident" has no tier except L3 (size uncited). A reduced-top-k self-draft would read fewer expert bytes, but each draft step still crosses all layers' attention and shared weights; the existing MTP head is one layer. Judged below MTP on draft cost per token. |
| Verification reads the union of experts across K+1 tokens; cost C(K) nonmonotonic in K | YES (principle). Union growth matters on any MoE verify; on MI210 verify cost also has GEMM-tile cliffs (lane DTREE-B note, speculative-decoding.md:2483 @ f74b175). | YES. Bandwidth-bound: each extra token adds unique expert bytes at the measured 112.9 GB/s single-quarter ceiling. This is the term the draft-length rule must price. |
| H2D expert prefetch overlapped with compute, budget B = min(Bmax, floor(W/tau)) | PARTIAL. Lane measured PCIe Gen4 H2D 28.89 GB/s (kv-cache-program.md:2098 @ f74b175) vs 1.498 TB/s HBM, about 52x lower. Overlap works only for experts reused across rounds. | NO for us. CPU reads DRAM at 112.9 GB/s per quarter, about 3.9x faster than PCIe Gen4; moving an expert to the GPU costs more than the CPU reading it. The paper's gain exists because its CPU executes BF16 experts compute-bound with 16 threads. (Derived from lane-measured numbers.) |
| Segmented CUDA-graph replay with device-side expert mapping tables | PARTIAL. HIP graphs exist on our stack (memory note, uncited here); would need an expert-slot indirection in the MoE kernel. Large build. | NO. No graph-launch overhead problem on CPU decode. |
| Draft-length rule K* = argmin C-hat(K')/G-hat(K') (Eq 7) with G = 1 + sum of prefix-acceptance products (Eq 1) | YES. Same algebra as the DTREE-B gain-per-second controller (measured costs per bucket); transfers as a stop rule for chain drafts. | YES. Cost model fits the bandwidth-bound verify; C(K) can be measured from existing per-K step timings. |
| Acceptance estimator alpha-hat = max(0, 1 - sqrt(lambda * Delta * H)), Delta = reroute disturbance | PARTIAL. H (draft entropy) is available; Delta exists only for expert substitution. Without Delta it reduces to SVIP (1 - sqrt(c H)) with fixed c; paper shows a fixed c fails across Delta strata (rejection 15.4% to 30.7% at one estimate bin). | PARTIAL, same. Our MTP/DFlash drafters have no Delta; calibrate c on our own captures. |
| Transfer budget and online cost refinement (EWMA-style) | YES (idea). Same shape as DTREE-B timing table. | YES (idea). |

## 5. In-house state
- A3B frontdoor p_min 0.5 applied to config 2026-11-23, not yet confirmed serving (speculative-decoding.md:522 @ f74b175); CAFE-1-SERVED-T kept p-min 0.5 by a distribution gate (speculative-decoding.md:905 @ f74b175, per-token post-sampler probs retained).
- Code: draft loops stop on top-1 probability below p_min (common/speculative.cpp:1955-1965, :2446-2450 @ 98ff8a4); DSpark confidence head truncates (:1907-1915 @ 98ff8a4); the DFlash2 branch never reads p_min (speculative-decoding.md:1527 @ f74b175).
- DTREE-B `auto` controller: gain per second from per-arm emission, measured per-(batch, context, arm) round time, chain above batch 4 (speculative-decoding.md:2483 @ f74b175; PARKED 2026-11-22, P5 auto arm 0.892 of linear on the 27B GPU tree). It covers width, not chain stop.
- Orchestrator registry carries draft_p_min 0.75 / 0.5 (orchestration/model_descriptors.yaml:333, :588; research-plane knobs review_plane_knobs.yaml:374-384).
- Expert locality data exists for Q38FN (512 experts, top-10): top 10% of experts cover 0.46-0.60 of selections; within-window LRU hit k=64: 0.62-0.68; hot set is workload-specific (cross-domain coverage <0.23) (cpu-decode-roofline-program.md:6052, :6086, :6089 @ f74b175). That is a proxy, not A3B.
- No expert-subset drafter, residency cache, or per-expert H2D prefetch in C21; llama.cpp offloads experts per layer, not per expert (uncited general knowledge, not checked here).

## 6. Derived-actionables ledger
| # | Draft task | Owner (exists in lane) | Compute | Stop / decision rule |
|---|---|---|---|---|
| A1 | Replay the CAFE-1-SERVED-T A3B per-token probability captures through the Eq 7 stop rule (marginal draft+verify cost vs current TPOT, prefix-acceptance product, calibrated c) versus fixed p_min {0, 0.5, 0.75}, using measured per-K step times; report modelled tokens/s. | speculative-decoding.md (CAFE-1 / A3B-PMIN05 block) | CPU offline replay, no model inference | Question: does a calibrated marginal-cost stop beat the best fixed p_min? KEEP candidate if modelled gain >= 3% with clustered CI lower > 1.0 at T0.3 and T1.0; CLOSE if < 1% and CI upper < 1.02; stop at CI half-width <= 1%. |
| A2 | Extract C(K) (verify wall time vs K, and expert-union bytes) for A3B MTP on CPU from existing rows before any new run; if absent, add it to the next A3B CPU row as a free covariate. | cpu-decode-roofline-program.md (Q38P-1 is the Q38FN analogue at :320) | code/doc first; reuse rows | Decides whether A1 can use measured C(K) or needs one new row. |
| A3 | Compute the A3B residency-coverage curve (fraction of top-k routing weight covered by N hottest experts per layer, per workload) from a routing trace, to bound any GPU-resident-subset drafter. | cpu-decode-roofline-program.md RT-9 (target-model trace open) | CPU row (trace capture) | Proceed to a hybrid-drafter design only if same-domain coverage at <=12.5% residency >= 0.6 and the operator allots spare HBM; else CLOSE for A3B. |
| A4 | Decline: per-expert H2D cache + CUDA-graph slot pipeline port. Reason specific to entry: on our hosts PCIe Gen4 (28.89 GB/s) is about 3.9x slower than one CPU quarter's DRAM read (112.9 GB/s), so moving an A3B expert to the GPU never beats the CPU reading it in place; revisit only if A3 shows high same-domain coverage AND HBM is allotted. | n/a | n/a | n/a |
| A5 | Decline: reduced-top-k or L3-hot-subset self-draft on CPU A3B. Reason: draft step still traverses all layers' attention and shared weights, so cost per drafted token exceeds the one-layer MTP head; nothing measured here contradicts that (arithmetic uncited, from layer counts in the paper's Table 2 only). Reopen if MTP acceptance on A3B collapses at sampling T. | n/a | n/a | n/a |

## 7. Dive-surfaced sources
- SpecMoE (arXiv 2604.10152), ELMoE-3D (2604.14626), S2-MoE (2608.15018): absent from the intake index (unbounded grep of research/intake_index.yaml). They are the resident/self-drafted-expert predecessors; S2-MoE and SpecMoE settle whether fixed-pool self-drafting on edge devices (CPU-class) beats MTP-style heads. Recommend ingest-and-dive for SpecMoE only (it is the cited fixed-pool baseline); decline ELMoE-3D (hybrid-bonding hardware dependency is a genuine hardware requirement, not a software gap, so mark as monitor) and defer S2-MoE to the same pass as SpecMoE since they answer one question.
- MoE-SpAc (Li et al., 2026): no arXiv id in the reference text read; absent from the index by name. Bears on this entry as the strongest speculative baseline. Recommend a lookup of its id then ingest.
- Already in index: SP-MoE 2510.10302 (3 hits), DraftExpert 2607.24434 (2 hits); MoE-Spec (Expert Budgeting) is also present.
- No public code link for CCAMoE found in the source text (NOT-FOUND-IN-SOURCE).

## 8. Contradiction / adversarial pass
- Authors' own ablation: eager cache-only drafting increases TPOT; benefit rests on CUDA graphs (-62.4% / -52.2%) and prefetch; cache-only drafting is not self-sufficient.
- The paper's central draft-length contribution is about 1%; the 6.8% best case is on a separately collected Qwen run.
- Baselines: KTransformers with Expert Deferral disabled and MoE-SpAc with Qwen3-4B-FP8 drafter; no llama.cpp or MTP-head baseline. Headline "SOTA" is per-workload strongest of offloading systems on a 16-thread EPYC 9554 with BF16 experts. Not a statement about Q4/Q8 bandwidth-bound CPU serving.
- Gains shrink with memory: 1.09x at 12 GB DeepSeek, 1.20x on RTX 3080; the authors state this.
- Batch size 1 only; concurrency left to future work. Our verify batches of 2-16 rows are per-sequence, so union growth applies, but np>1 serving is not covered.
- No independent replication; the only other source is the paper itself (no restatement found).

## 9. read_depth
FULL (text, tables, equations, captions; figures not viewable). lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Rule-vs-p_min judgement (requested)
Eq 7 compares round time per committed token across candidate lengths; p_min is a fixed top-1-probability threshold, a constant-alpha proxy for that comparison. Break-even form: continue while (expected next-token acceptance times prefix probability) >= marginal round cost divided by current TPOT. For a bandwidth-bound A3B verify where each extra token adds unique expert bytes, break-even acceptance is plausibly near the p_min 0.5 the lane kept (inference, not measured). The rule could tune p_min per context or temperature, and could replace it only after A1 shows a calibrated estimator beats the fixed threshold; it cannot replace p_min outright today because the expert-substitution disturbance term does not exist for our drafters and top-1 probability is not calibrated acceptance under sampling (the paper's own Fig 3 shows a fixed c miscalibrates).

artifact audit: clean
