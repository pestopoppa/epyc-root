# DynaSpec: Context-aware Dynamic Speculative Sampling for Large-Vocabulary Language Models

- **Intake**: intake-2741 (`intake-2741#record`)
- **Source**: https://arxiv.org/html/2510.13847v3
- **Verification**: dive-verified · read depth FULL
- **Disposition**: monitor; handoffs: speculative-decoding.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Do not cite its headline speedups (internally inconsistent, unreplicated). The A3B vocab top-k cost belongs to AK-GAP-1-IDSORT, not to a shortlist head.

## Key claims (anchored)

0. Clusters are formed offline by spherical k-means on LM-head columns, and a trained two-layer MLP router selects clusters, with labels from EAGLE-2 runs.
   - Sec 4.2: "These clusters are formed offline by spherical k k -means on column-normalized LM-head weights"
   - Sec 4.2: "The router is implemented as a two-layer feed-forward neural network with ReLU activation."
   - Sec 4.2: "To construct the training labels, we run the Eagle -2 pipeline on a large set of"
1. The drafter reuses the frozen target head, and the target still verifies over the full vocabulary, preserving exactness.
   - Sec 4.1: "The drafter reuses and freezes the embedding"
   - Abstract: "while the target model still verifies over the full vocabulary, preserving exactness."
2. A gathered head adds matmul overhead and can lose to a pre-trimmed dense head; all experiments ran on one A6000.
   - Sec 1: "However, a dynamic (indexed) head introduces gathered matmul overhead and can be slower than a fixed, pre-trimmed dense head."
   - Sec 6.1: "All experiments were run on a single NVIDIA A6000 GPU."
3. Reported numbers are internally inconsistent between the abstract and Table 2, and an FR-Spec acceptance value differs between Table 1 and Table 4.
   - Abstract: "achieves up to a 2.23× throughput gain compared to 1.91× for static approaches"
   - Table 2: "FR-Spec-32k 87.56 101.85 81.81 107.91 84.61 83.46 81.60 89.83 (2.13"
   - Table 1: "FR-Spec 3.39 3.39 3.88 3.88 3.86 3.86 4.16 4.16 3.33 3.33 3.52 3.52 3.31 3.31 3.64 3.64"
   - App A.3 Table 4: "FR-Spec-F 3.38 3.38 3.87 3.87 3.85 3.85 4.16 4.16 3.32 3.32 3.51 3.51 4.11 4.11 3.74 3.74"

## Dive record

2026-11-20 Stage-2b dive (opus; full read; surfaced by intake-2727). Not training-free: clustering is, the router is a trained MLP. Only 128K/152K vocabularies tested; throughput only on Llama-3-8B (94.98 vs 81.47 tok/s full head, 1.17x; 1.057x over FR-Spec). Internal inconsistencies flagged (artifact defect in the source, not ours). MI210: A3B-mtp vocab-wide k_top_k_radix 1.29 ms per drafted token, ~9.9% of decode (autokernel-loop.md:L4494-4495 @b5c5fe7) is already owned by AK-GAP-1-IDSORT (argmax skip / two-stage top-k, exact). CPU ceiling ~5% of step, same as SlimSpec. Adversarial: no code release or replication; SlimSpec states DynaSpec was not reproduced for lack of an implementation. FR-Spec 2502.14856, Gumiho 2503.10135, thunlp/FR-Spec declined. lane_head b5c5fe7b4e63
