# Dive — qnoise — intake-ak-1124 (Stage 2b wave 1, expanded from intake-2872 exactpaper)

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2611.15671v1", retrieved: "2026-11-24", sha256: "542200f0e4d7"}

## 1. Stage-1 fields
- **Title:** The Noise Floor of a Quantization Comparison: Engine, restart, batch and kernel drift, measured against 8-bit and 4-bit effects in two decision models
- **Authors:** Aleks Blagojevich, Trevor Sunderland (Level5). arXiv 2611.15671 v1, 11 Nov 2026 (cs.LG). Code, recipes, per-record outputs and a pre-registration are released (not fetched).
- **Setup:** one NVIDIA GB10 (DGX Spark), Cloudflare decision models Clef-flash (9B) and Clef (27B), both Qwen3.5-hybrid (Gated DeltaNet) with a joint schema head. These are single-forward classification-style decisions over 2,400 records (first 200 of each of 12 tasks), NOT free generation, no speculative decoding, no KV-quant axis. Engines: transformers 5.16.1, vLLM 0.29.0 (16 requests in flight), llama.cpp decision server b11671 (single sequence).
- **Categories:** quantization, benchmark_methodology, local_inference.
- **Novelty:** medium. The restart-floor-vs-quantization-effect design is the same idea as exactpaper (intake-2872) at weight-quantization level; new here are the per-format restart floors, a silent-kernel-selection source, and the "flips are not additive across sources" observation.
- **Relevance:** high for the method (floor protocol for A1/A3/A5), low for its numbers (different workload, device, engine).
- **credibility_score: 1.** Arithmetic: peer-reviewed 0 (arXiv preprint); <=12 months +1; known/major lab 0; commercial bias 0 (vendor-style authors but no product claim at issue); independent corroboration 0 (exactpaper agrees on the method but is a different setup, and the other related papers are cited by this paper, not read here). Outside the formula: pre-registered, per-record data released, Claude-assisted authoring disclosed, two of five predictions reported as failed.
- **Verdict: adopt_patterns.** Take the replica/ratio protocol (largest-pair floor, named denominator, flips split by direction); do not import any number.

## 2. Key claims
1. **llama.cpp restarts are bit-identical, vLLM restarts are not (floor 0 vs 0-22 flips of 2,400).** CONFIRMED. llama.cpp BF16 restart 0/2,400 on both models; vLLM 0, 5, 20 flips (BF16, FP8, NVFP4) on the 9B and 4, 0, 22 on the 27B. Caveat the authors state: llama.cpp processes one sequence at a time, so batch composition never varies, and they have not verified the kernel-level reason. Anchor A1.
2. **The restart floor is specific to the build and a single repeat can understate it by more than 5x.** CONFIRMED but exploratory and small-n: Clef NVFP4 pairs across three instances were 4, 22 and 22 flips; the quantization effect against the reference stayed within two flips (137/139/137). Authors list "five or more instances per build" as the next measurement. Anchor A2.
3. **8-bit quantization is above the llama.cpp floor but at the edge of the largest vLLM floor.** CONFIRMED with correction to the framing: Q8_0 flips 0.88% (9B) and 1.04% (27B) against a llama.cpp restart floor of exactly 0; against the largest (NVFP4 vLLM) restart, Q8_0 is 1.05x and 1.14x, and 29 of 32 8-bit-vs-source differences exclude zero (the three that do not: Q8_0 vs the NVFP4 restart on both models, and 27B Q8_0 vs its llama.cpp engine change, 25 vs 16 flips). Anchor A3.
4. **On the 27B the non-quantization sources are about twice as large, so part of an "8-bit effect" there is floor.** CONFIRMED (full set: engine changes 155/156 flips, batch-8 rerun 130, against 75/67/66 on the 9B; 8-bit builds are 1.7 to 4.0x that floor). Anchor A4.
5. **Every 4-bit effect exceeds every non-quantization source** (Q4_K_M 5.79% / 3.50%, NVFP4 5.79% / 5.67%; ratios 3.8 to 7x on the 2,400 records). CONFIRMED, pre-registered N2 supported. Anchor A5.
6. **Accuracy hides flips, and flips are not additive across sources.** CONFIRMED: Clef Q4_K_M net -6 questions hid 436 that got worse; FP8 vs ref 47 flips vs 51 vs bf16-srv on the 9B. Anchor A6. Two of five pre-registered predictions FAILED (FP8 is not inside restart noise; engine change moves fewer decisions than 8-bit quantization).

## 3. Reported results (as stated; GB10, 2,400 records, 2,000-resample paired bootstrap, exact Clopper-Pearson for zero-flip pairs)
Flip rates (9B / 27B): restart llama.cpp BF16 0.00 / 0.00%; restart vLLM BF16 0.00 / 0.17%, FP8 0.21 / 0.00%, NVFP4 0.83 / 0.92%; engine change BF16 0.25-0.33 / 0.54-0.67%; batch 1 to 8 0.33 / 0.62%; GDN kernel fallback to fla 0.42 / 0.58%; Q8_0 0.88 / 1.04%; FP8 2.12 / 1.62%; Q4_K_M 5.79 / 3.50%; NVFP4 5.79 / 5.67%. Ratios to largest floor on 2,400 records: Q8_0 1.05 / 1.14, FP8 2.55 / 1.77, 4-bit 3.8 to 7. Zero-flip bound: 0 of 2,400 gives an upper bound of 0.15%.

## 4. Performance-principles table (mechanism / cost model)
| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| Restart floor from >=3 instances, floor = largest pair, replicas on the same fixed items | YES: design only. GPU DFlash2 is not deterministic across launches at np1 (20/64, SPEC-ID-NOISE-1), so a multi-launch floor is mandatory there | YES: CPU conc-1 measured 0/64, floor 0 is the llama.cpp-single-sequence analogue; a replica arm is then a cheap re-confirmation |
| Floor named as a ratio denominator ("how far above floor") | YES: analysis-only | YES: analysis-only |
| Flips split into worse / better / wrong-to-wrong against a gold label | YES where a graded eval exists | YES, same |
| Silent kernel selection must be recorded (their GDN kernel chosen by package import) | PARTIAL: our analogue is env knobs that change kernel choice (`GGML_HIP_Q8IP_MMVQ_MAX`, `GGML_ROWEXACT_N`, `LLAMA_SPEC_EXACT`); gate RESULT.json should record the effective values | PARTIAL: same, plus iqk build flags |
| Compare inside one engine, never across engines | YES: already our rule (same server build) | YES |

## 5. In-house state
- Protocol already requires a same-run A/A arm and a paired d test, and says an exact-identity floor of 0 holds only in regime (docs/guides/agent-workflows/spec-identity-gate-protocol.md §2, §4 @ f74b175). It states no replica count and no "largest pair" rule; exactpaper A1 proposes >=3.
- SPEC-ID-NOISE-1 measured CPU spec-off/MTP conc-1 0/64 divergences and GPU DFlash2 M1 vs M2 20/64 across launches (protocol §2 @ f74b175): the same qualitative split as llama.cpp 0-floor vs vLLM non-zero floor here.
- C21 has no batch-invariant flag; verify-path exactness knobs are `GGML_ROWEXACT_N` and `LLAMA_SPEC_EXACT=serial` (see exactpaper dive §5, ggml-cpu.c:1505 and server-context.cpp:6043 @ 98ff8a4).
- Fold gates (kernel-champion-and-promotion.md C17-FOLD-GATES line 28 @ f74b175) use KLD<=0.003, |dPPL|<=0.5% and top-1: a deterministic-quality gate, not a flip-vs-floor gate.

## 6. Derived-actionables ledger
| # | Task line | Owner (lane file; status) | Compute | Stop / decision rule |
|---|---|---|---|---|
| QN-1 (refines exactpaper A1 and A3) | Amend the replica rule: the A/A floor is the LARGEST pair over >=3 independent launches (>=5 when the floor decides a pass/fail), the in-row band is that max pair, and results report distance as a ratio naming its denominator | speculative-decoding.md, new box under SPEC-ID-GATE-1 (that box is [x]); doc plus `spec_dist_gate.py` change | code/doc-only | Question: does a 2-launch floor ever under-state the 3-launch max pair on our retained DFlash2 data? Offline check on SPEC-ID-NOISE-1 retained outputs if >=3 launches exist; otherwise stated as a rule and verified by the first gate run. Stop-on-answer when the doc states the rule and the checker returns INCONCLUSIVE for <3 launches |
| QN-2 (refines exactpaper A4/A5) | In the graded-flip metric report flips split into worse / better / wrong-to-wrong, plus net accuracy change, and state the effect as a ratio to the in-row scheduling floor | eval-tower-program.md for the grader; kv-cache-program.md for the KV-quant gate | code/doc-only until a graded set runs | Question: does the net accuracy change hide a larger two-sided flip count on our q8_0/q4_0 KV comparisons (paper: 436 worse hidden by net -6)? Done when the metric exists in the gate output |
| QN-3 | Record effective kernel-selection env (`GGML_HIP_Q8IP_MMVQ_MAX`, `GGML_ROWEXACT_N`, `LLAMA_SPEC_EXACT`, binary SHA) in every identity-gate RESULT.json header | speculative-decoding.md (same box as QN-1) | code/doc-only | Done when RESULT.json carries the fields; closes the "unknown kernel ran" failure the paper's GDN case illustrates |

Declines: (a) adopting the paper's decision-head protocol itself (single-forward class decisions): our workload is generation under speculation, the margin-class gate already covers the cause analysis; (b) importing any floor magnitude (0.15% bound, 0-22 flips): different engine, device and model, and the protocol forbids imported floors (spec-identity-gate-protocol.md §2).

**Does it change A1/A3/A5?** A1: strengthens and sharpens (max pair, three instances already gave a 5.5x spread between pairs, authors ask for five). A3: sharpens (band = max pair; floor can equal an 8-bit-class effect, so band precision matters). A5: confirms the need for an in-row floor; it does NOT show floor exceeds 8-bit effect on llama.cpp (floor 0), only at the edge on vLLM. No ledger row is overturned.

## 7. Dive-surfaced sources
Unbounded grep of research/intake_index.yaml at lane head:
- 2611.12634 (Lu and Ni, KL mismatch from int8/fp8/int4 vs a vLLM noise floor of 0.17-0.22 nats per sequence): ABSENT. Would change QN-1's band currency: our fold gates are KLD-based (C17-FOLD-GATES) and a nats-per-sequence floor from deliberate reduction-order changes is the missing floor for KLD thresholds. Recommend ingest-and-dive.
- 2610.09111 (Kasa et al., label changes vs a repeatability floor in 180 classifiers): ABSENT. Same method class as this entry; would not change a row beyond QN-1. Decline (duplicative of this entry for our decisions).
- 2608.04714 (Masoudian et al., backend explains ~39% of benchmark variability): ABSENT. Aggregate-score level, no row it would change. Decline.
- 2610.42148 (Flide, exact state forking for decision inference): ABSENT. Decision-serving engine work, no gate row. Decline.
- 2608.06564, 2609.04748 are this wave's sibling keys; 2605.19537 and 2608.13756 already surfaced by exactpaper.

## 8. Contradiction / adversarial pass
- Two of five pre-registered predictions failed and the authors say so; H2's combination rule was added after seeing the 27B (dated). Restart floors rest on one pair per build (third instance only for Clef FP8/NVFP4); first instance differs from later two by cold graph compile and by full-file vs subset stream, which the authors cannot separate.
- vLLM restart comparisons include 16 requests in flight, so they mix instance drift with batch composition (authors' own limitation).
- Single device (GB10), two models of one family, decision models not generation. The llama.cpp zero floor is a property of a single-sequence server, NOT evidence that llama.cpp spec-decode paths are deterministic (our GPU DFlash2 data say they are not).
- Authors disclose Claude wrote code and drafted text; numbers come from scripts. Restatement vs corroboration: exactpaper reproduces the method, not these numbers.

## 9. read_depth
FULL (page.txt through the references; Appendices A-C table headings only, repo and per-record data not fetched). lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit
artifact audit: clean
