# Laguna S 2.1 CPU Port — Experimental Branch

**Status**: stub (design / investigation) — created via /research-intake Stage-2 (plan `async-brewing-wirth`, operator-approved 2026-07-22)
**Created**: 2026-07-22
**Priority**: P2
**Effort**: Low-Medium (base arch ~350 LOC; DFlash spec path is a separate larger port)
**Categories**: local_inference, moe_optimization, speculative_decoding, quantization, hardware_optimization
**Source**: intake-879 (poolside launch blog) + intake-880 (GGUF model card) + Stage-2 deep-dive 2026-07-22
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**:
- [`iqk-iquant-enablement.md`](iqk-iquant-enablement.md) — Laguna UD-IQ2_M IQ-quant acceleration (already-coded branch; add Laguna as 5th beneficiary)
- [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) — the DFlash draft-dflash spec path + accept-rate bench
- [`deepseek-v4-flash-cpu-port.md`](deepseek-v4-flash-cpu-port.md) — the reusable experimental-branch new-arch CPU-port precedent (pattern, not coupling)
- [`architect-model-selection-bench.md`](architect-model-selection-bench.md) — Laguna as a candidate once served

---

## Objective

Port the **Laguna** architecture (poolside/Laguna-S-2.1: 118B-total / 8B-active MoE — 256 routed experts top-10 + 1 shared; 48 layers mixed 12 full-attention + 36 sliding-window(512); **sigmoid**-routed MoE with score-correction bias; **softplus attention-output gate**; QK-norm; per-layer-type RoPE — YaRN on full layers, plain RoPE on SWA layers) onto an experimental llama.cpp branch on the EPYC 9655 CPU stack, validate quality + throughput vs the production kernel, and merge into a new production version **only** after both gates pass. **NEVER modify frozen `production-consolidated-v7`** — all work on `llama.cpp-experimental` off a fresh production pull, per the four-step workflow.

## Why now

`/research-intake` ingested Laguna 2026-07-22; the operator is downloading Q4_K_M (poolside, 75GB) + UD-IQ2_M (unsloth, 37GB) + the DFlash-BF16 drafter (2.2GB). Laguna is a weight-class-leading agentic coding model whose 8B-active MoE shape is favorable for bandwidth-bound CPU decode, and it lands directly on the active spec-dec-mtp-refresh line. **Base arch support is already MERGED upstream** (ggml-org/llama.cpp PR #25165, 2026-07-22T01:54Z, approved), so the forward-port can pull from upstream rather than only poolside's fork.

## Key facts (Stage-2 deep-dive, 2026-07-22)

- **PR #25165 is MERGED** (22 files, +1091/−1): base arch only in `src/models/laguna.cpp` (+332) + `conversion/laguna.py` (+207). The `conversion/` package is **already present** in the v7 tree → the converter applies clean. **DFlash spec path is NOT in the PR** — it lives only in poolside's fork branch `laguna` (`--spec-type draft-dflash`).
- **DFlash = z-lab block-diffusion** (arXiv:2602.06036, intake-158), SAME codebase (GGUF `dflash.target_layers` = HF `target_layer_ids` +1, matching z-lab `offset=1`). No timestep/denoise tensors → single-pass conditioned block drafter, not iterative diffusion. Draft cost is cheap; the open question is acceptance.
- **DFlash-on-CPU is still likely NO-GO for quantized targets.** The March NO-GO (`../completed/dflash-block-diffusion-speculation.md`, 27% accept, AR drafter won 36.5 vs 13.0 t/s) roots in TARGET-side quant noise in the conditioning hidden states — which poolside's BF16 drafter does NOT fix. Only a near-lossless target (Q8_0 / F16) plausibly reopens it. See `speculative-decoding-mtp-refresh.md`.
- **UD-IQ2_M iqk coverage**: 92.2% of bytes are IQ-quant (IQ2_XXS 51% + IQ3_XXS 37% + IQ2_S 1.4% + IQ4_XS 2.3%), stubbed on frozen v7; the code-complete `iqk-iquant-enablement` branch already covers 97.6% of the IQ bulk (all but the 2 IQ4_XS tensors). No new kernel needed — see that handoff.

## Tasks

- [ ] Forward-port base Laguna arch (merged PR #25165 commits, ~350 LOC: `src/models/laguna.cpp` +332, `models.h`, 1-3-line touches to `llama-arch`/`llama-model`/`llama-vocab`, `conversion/laguna.py` +207) onto a FRESH-pulled `llama.cpp-experimental` off `production-consolidated-v7`; validate S-2.1 Q4_K_M loads + coherence/garbage smoke
- [ ] Confirm the PR-author-flagged "GQA head-ratio backend dispatch" bug does not hit the CPU build (PR touches no `ggml/` files; per-layer `n_head` handled at graph level → likely CUDA-only)

## Notes

All Laguna quality/speed numbers to date are poolside self-reported OBSERVATIONS per MEASUREMENT.md — none gate a decision. The iqk (Laguna UD-IQ2_M beneficiary), DFlash (accept-rate bench + draft-dflash port), and architect-bench rows live in the linked handoffs and are cross-indexed under the "Laguna S 2.1 experimental-kernel cluster" in [`inference-acceleration-index.md`](inference-acceleration-index.md) so the whole cluster can be tackled in one session.
