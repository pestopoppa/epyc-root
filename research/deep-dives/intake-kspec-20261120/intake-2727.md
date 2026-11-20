# Efficient and Robust Drafting with Multi-Token Prediction

- **Intake**: intake-2727 (`intake-2727#record`)
- **Source**: https://arxiv.org/html/2611.25813v1
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: speculative-decoding.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Cite the clustered projection mechanism and its measured net 1.01x. Both headline speedups are H100 batch 1. Do not assume the clustered head transfers to a borrowed-target-head MTP without measurement.

## Key claims (anchored)

0. G-MTP is one shared drafting block fed the target final hidden state plus the next token embedding; it cross-attends to the target KV cache and needs no KV cache of its own.
   - Sec 3.2: "the drafter needs no KV cache of its own"
1. The clustered projection groups the drafter unembedding into 2048 balanced k-means clusters of 128 tokens and computes exact logits only for the top-32 clusters; other tokens get a constant minimum logit.
   - Sec 3.3: "then computes exact token logits only for the top-32 most probable clusters"
   - App A.3.1: "logits are computed only for tokens in the top-32 clusters, and all other tokens receive a constant minimum logit"
2. Only the E2B/E4B drafters use it; on a Pixel 11 Edge TPU it cut drafting time about 20% but lowered acceptance, for a net end-to-end gain of 1.01x.
   - Sec 4: "The E2B and E4B drafters use the efficient clustered vocabulary projection while the larger models"
   - Sec 3.3: "On the Edge TPU of a Google Pixel 11, this reduces the drafting time of E2B and E4B by about 20%"
   - Sec 4 mobile NPU: "but it also lowers the median acceptance rate (from 0.49 to 0.48 for E2B and from 0.52 to 0.50 for E4B), which offsets most of this saving"
   - Sec 4 mobile NPU: "the net end-to-end gain is 1.01"
3. Headline speedups are H100, vLLM, batch 1: 3.14x for Gemma 4 31B on 2x H100 and 2.33x for E4B on one H100.
   - Sec 4: "a single H100 GPU for E2B, E4B and 12B, 2 × \times H100 for 26B and 31B"
   - Table 1: "Gemma 4 31B 1024 500M 8 4.26 73.2 230.1 3.14"
   - Table 1: "Gemma 4 E4B 256 77M 9 3.45 178.0 415.5 2.33"
4. The pre-training recipe of the released drafters is out of scope.
   - Limitations: "the pre-training recipe of the released G-MTP drafters is out of scope"

## Claim corrections

- claim 2: **unaffected** — Smallest drafters only; adds that net gain was 1.01x.
- claim 3: **reattributed** — Steering read 3.1x as server-side vs 2.3x on H100; both are H100 (31B on 2x H100; E4B on 1x H100).

## Dive record

2026-11-20 Stage-2 dive (opus; full read). Clustered projection is lossy for the drafter (~43x fewer head MACs, >97% hit rate per the paper) with exact verification; Gemma clusters the drafter's own 256-dim head whereas Qwen3.8 MTP borrows the target head. In-house: Q38FN CPU draft/MUL_MAT:lm_head 6.906 ms/step (7.42%) at d1k, 5.931 (4.38%) at d32k (q38fn-cpu-perop-profile-20261118-r2 RESULT.json; autokernel-akx-program.md:L1659 @1650e3d); ceiling ~6.7 ms/step at d1k before centroid/gather cost and acceptance loss, marginal against the CPU W5 4.15% floor. MI210: A3B-mtp k_top_k_radix 1.29 ms per drafted token, 9.9% of decode; 27B-dflash2 3.1% (autokernel-loop.md:L5746-5749 @1650e3d); a two-stage projection also shrinks the top-k input; DFlash2 selector needs top-16 plus full-vocab probability rows (dflash.cpp L1312-1330 @eee3da838), so it fits draft-mtp better. Adversarial: Google Gemma docs restate (same org); no independent evaluation. lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d) Stage-2 close-out (2026-11-20): arXiv 2510.13847 (DynaSpec) ingested as intake-2741; arXiv 2605.26444 (NanoSpec) declined (same lever as DynaSpec; reopen only if a clustered-head probe keeps).
