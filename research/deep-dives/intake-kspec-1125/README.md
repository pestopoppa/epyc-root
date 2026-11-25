# Intake run intake-kspec-1125: kernels, speculative decoding, eval rigor (2026-11-25)

Fifteen operator-submitted sources (two llama.cpp PRs and thirteen arXiv papers), seven Stage-1
literature expansions and four Stage-2b sources. Entries intake-2956 to intake-2981.

## Sweeps

- **Stage 1:** intake-2956 to intake-2970 (submitted) and intake-2971 to intake-2977 (expansions:
  Stream-K, Dating the Model, Speculative Decoding Speed-of-Light, UBTree, TreeSpark, ForeSpark, Merged
  Not Measured). Six haiku extractors.
- **Stage 2 wave 1:** all 22 entries, nine dives (K1, K2 and S1 on opus; K3, K4, S2, S3, M1 and M2 on
  sonnet). intake-2961 (MXFP4 PTQ) has no arXiv HTML rendering, so it stays stage1-unverified with a
  PARTIAL hand-checked PDF read.
- **Stage 2b wave 2:** intake-2978 (Overflow-Aware Scaling for MXFP4), intake-2979 (agent performance-PR
  validation study), intake-2980 (certified sparse attention), intake-2981 (top-k attention via total
  variation). Two sonnet dives. Every source the wave-2 dives surfaced was declined, so no further wave
  was run (two of the four permitted sweeps used).
- **Second reader (haiku):** 160 quotes re-checked against their claims: 87 yes, 67 partial, 6 no. The
  six "no" anchors were dropped.

## Dive files

| Dive | Entries | Headline |
|---|---|---|
| [K1 stream-k order](dive-K1-streamk-order.md) | intake-2956, intake-2971 | PR #32921's column-outer tile walk is a no-op on served gfx90a shapes (one column tile at M=36; Q8_0 above 128 columns goes to rocBLAS; J=128 never fires on CDNA) |
| [K2 Shifter Quantization](dive-K2-shifter-quant.md) | intake-2957 | Exact full-K integer dot with no per-group float scale; on gfx90a int8 MFMA has the same K per instruction as f16, so no rate gain; CPU K-quant dots already use SHI-style correction products |
| [K3 DPP scan, roofline AI](dive-K3-dpp-roofline.md) | intake-2962, intake-2960 | The DPP scan has no served consumer (fused GDN ops skip CUMSUM); LLM arithmetic-intensity estimates would not help the verify-kernel census |
| [K4 TACPU, MXFP4](dive-K4-tacpu-mxfp4.md) | intake-2959, intake-2961 | Our CPU flash attention has no L2/L3 blocking and runs chunks cheapest-first; Midmax is a +0.12-point weight rule that our only MXFP4 model (a lossless repack) cannot use |
| [S1 Pando trees](dive-S1-pando-trees.md) | intake-2963, intake-2973, intake-2974 | Noise coupling is lossless only with the target-sample walk, not with our rejection verifier; Pando's speedups are modelled; our DICE V3 already tested the idea (NULL) |
| [S2 draft calibration](dive-S2-draft-calibration.md) | intake-2964, intake-2975, intake-2976 | Draft temperature is lossless and already measured in-house as about zero (SPEC-DRAFT-SHARPEN CLOSE) |
| [S3 LEGOSpec, GramDelta](dive-S3-legospec-gramdelta.md) | intake-2965, intake-2966 | DFlux gains are confounded by training scale and no checkpoint is released; GramDelta helps only mid-request grammar growth, which no served role does |
| [M1 perf claims, date](dive-M1-perfclaims-date.md) | intake-2958, intake-2977, intake-2967, intake-2972 | AutoKernel rows have A/A and knob witnesses but no claimed-mechanism counter; llama-server injects the wall-clock date into templates that read it, and no eval result records it |
| [M2 RECAP, effort, Top-K](dive-M2-recap-effort-topk.md) | intake-2968, intake-2969, intake-2970 | The behavior-distortion score works as an untrained grader; effort-tier results all need training; Top-K limits concern singleton-KL ranking, not our learned indexer |
| [W2A OAS, agent PRs](dive-W2A-mxfp4scale-agentprs.md) | intake-2978, intake-2979 | Overflow-Aware Scaling is the same round-up threshold as Midmax; the PR study is artifact-only |
| [W2B sparse-attention certificates](dive-W2B-sparse-attn-certs.md) | intake-2980, intake-2981 | Discarded softmax mass gives an exact KL identity for a kept set, usable as an offline gate only |

The Stage-3 plan is [stage3-plan.md](stage3-plan.md).
