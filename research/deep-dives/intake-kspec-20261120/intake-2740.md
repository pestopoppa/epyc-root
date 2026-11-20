# SlimSpec: Low-Rank Draft LM-Head for Accelerated Speculative Decoding

- **Intake**: intake-2740 (`intake-2740#record`)
- **Source**: https://arxiv.org/html/2605.10453v1
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: speculative-decoding.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Requires drafter training; the source gives no evidence for post-hoc factorization of a borrowed head. On our CPU the head is ~4-7% of the step, so the ceiling is near the floor.

## Key claims (anchored)

0. SlimSpec replaces the draft LM head with a rank-r factorization; since the vocabulary is far larger than the hidden size, cost falls roughly linearly in r.
   - Sec 4.1: "the cost reduction (in FLOPs) is approximately linear in r r"
1. VocabTrim and SpecVocab cut LM-head latency by only about 60% while SlimSpec achieves an approximately 4-5x reduction.
   - Fig 1 caption: "Both VocabTrim and SpecVocab can reduce LM-head latency by only about 60 % 60\% , while SlimSpec achieves an approximately 4 - 5 × 4\text{-}5\times reduction."
2. The low-rank head is trained with KL loss as part of drafter training (128-320 GPU-hours per drafter); single-model low-rank factorizations are stated not applicable to the drafter-target setup.
   - Sec 5.2: "We employ standard KL-divergence loss as our training objective, unless stated otherwise."
   - App A: "Training a single drafter requires 128 GPU-hours for Llama-3.1-8B-Instruct, 288 GPU-hours for GPT-OSS-20B, and 320 GPU-hours for Qwen3-30B-A3B-Instruct."
   - Sec 2: "These methods are not specific to speculative decoding and operate on a single model, so they are not applicable to the drafter-target setup considered here."
3. The gain shrinks when the head is a smaller fraction of total latency.
   - Sec 6: "accounts for a smaller fraction of the total latency, decreasing"
4. Long-context generation, other hardware and serving frameworks are out of scope.
   - App B: "long-context generation, multilingual or domain-specific workloads, tool-use settings, high sampling temperatures, alternative sampling policies, or other hardware and serving frameworks."

## Dive record

2026-11-20 Stage-2b dive (opus; full read). No SVD or post-hoc factorization of a borrowed head is tested. CPU ceiling: Q38FN draft lm_head 6.9 ms of a 97 ms step at d1k (7.1%), 5.9 of 144 ms at d32k (4.1%) (r2 RESULT.json); with the paper's head-cost ratio ~0.21 the saving is ~5.6% at d1k only if acceptance held, near the 4.15% floor. Prior in-house evidence agrees: a -85% draft-head kernel cut gave +1-3% end to end (speculative-decoding.md:L285 @b5c5fe7); FR-Spec trim declined as low-EV (model-evaluation-queue.md:L1260). Q38FN borrows shared_head_head or model.output (qwen4exp.cpp L582-584 @eee3da8). Zero-training stand-in (derived, not in source): requantize the Q8_0 shared draft head to 4-bit, draft-only. MI210 A3B-mtp hot item is the vocab top-k, not the GEMM. Adversarial: no replication. SpecVocab 2602.13836, VocabTrim 2506.22694, CORAL 2502.16880 declined. lane_head b5c5fe7b4e63
