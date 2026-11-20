# llama.cpp PR #32266: ggml-cuda : hip few mmq on non wmma arch

- **Intake**: intake-2720 (`intake-2720#record`)
- **Source**: https://github.com/ggml-org/llama.cpp/pull/32266
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: speculative-decoding.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Do not port this PR for the 27B verify band: its gate is GCN-only and caps weight rows at 1024. Never quote its microbenchmark as a gfx90a or 27B number; the Q6_K and Q3_K rows look duplicated.

## Key claims (anchored)

0. PR #32266 adds a HIP branch to the few-row MMQ kernel built on the MMVQ dp4a decoders with the weight decode hoisted out of the column loop.
1. Its gate is GCN-only (validated on gfx906), N 9..24, K >= 2048, at most 1024 weight rows and plain MUL_MAT, so gfx90a (CDNA2) and the 27B verify GEMMs are excluded.
2. The only evidence is a single-shape microbenchmark (M=127, K=2048, N=9); two table rows look copied (Q6_K equals Q8_0, Q3_K approximately equals IQ3_S).
   - PR body table: "Q4_K 56.44 9.68 -46.8 Q6_K 74.6 11.3 -63.3 Q8_0 74.60 11.31 -63.3 Q3_K ~86.3 ~9.0 -77.3"
   - PR body table: "Q5_K 72.83 9.67 -63.2 IQ4_NL 100.30 9.33 -91.0 IQ4_XS 100.53 8.39 -92.1 IQ3_S 86.32 9.04 -77.3"
3. It is a draft awaiting maintainer review.
   - PR page reviewers sidebar: "ggerganov will be requested when the pull request is marked ready for review"

## Claim corrections

- claim 1: **overturned** — Stage-1/steering said gfx90a coverage was unconfirmed and the shape matched spec verify; the diff gate is GGML_CUDA_CC_IS_GCN (cc < CDNA1, common.cuh L91 @eee3da8), so gfx90a is excluded by construction, and src0->ne[1] <= 1024 excludes the 27B K=5120 GEMMs.
- claim 2: **narrowed** — GPU implied gfx906 by the diff comment; table has suspect duplicated rows.
- claim 3: **unaffected** — Draft, no maintainer review; commits carry an AI-assistance trailer.

## Dive record

2026-11-20 Stage-2 dive (opus). Diff evidence (pr32266.diff @ head 23198be90e, not machine-anchorable): HIP gate in ggml_cuda_should_use_mmq_few reads 'validated on gfx906 (VEGA20) only, the other GCN targets are untested' and requires src1->ne[1] in 9..24, src0->ne[0] >= 2048, src0->ne[1] <= 1024, ggml_is_matrix (MUL_MAT only, no ids); launch grid is (src0->ne[1], ceil(N/4)), so each 4-column tile re-reads the weight row. OVERTURNED for our purpose: it cannot cover the 27B Q8_0 12-16-row verify step (DTREE-0: wvSplitK q8wv up to M=11 at 29.8 ms, mul_mat_q+stream_k_fixup from 12 rows at 46.7 ms; speculative-decoding.md L1799 @1650e3d); dp4a without MFMA re-reading K=5120 rows 3-4x would lose to wvsk, which reads weights once for all M columns. mmq-few does not exist in C14 or v10 (upstream #31533 landed 2026-11-12, after our fork base). Port cost would be small (all symbols present, wave64-clean). No duplicate-ID risk (MUL_MAT only). Adversarial pass: no replication or criticism found. lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d)
