# NariQ: Sub-3-Bit Quantization for Long-Horizon Agentic Tasks

- **Intake**: intake-2721 (`intake-2721#record`)
- **Source**: https://arxiv.org/html/2611.26157v1
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: quantization-and-low-bit.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Cite the calibration recipe (model-written-token KL, per-module allocation) and the paper's own counts. Do not say 3.0/2.5 bpw match BF16; say not distinguishable at n=113. No CPU or AMD speed exists.

## Key claims (anchored)

0. NariQ keeps the QTIP bitshift trellis with an EXL3-style computed codebook and changes the calibration: the end-to-end KL loss counts only model-written (BF16-generated) tokens from agent sessions, with per-module bit allocation and a banded output layer.
   - Sec 2 Method: "First, the end-to-end loss counts only model-written tokens."
   - Sec 5 Related Works: "bitshift trellis with a computed codebook"
   - Sec 2 Format: "The codebook is computed from the trellis state, as in EXL3"
1. On Qwen3.8-27B in the authors harness (113 DeepSWE tasks, one attempt each) 3.0 and 2.5 bpw solved 47 and 46 tasks against 44 for BF16; the paper calls this level with BF16 within noise, and 2.0 bpw trails.
   - Sec 4.1: "At 3.0 and 2.5 bpw, our files are level with BF16 on DeepSWE (Table 1 )."
   - Sec 4.1: "within noise of it (paired by task"
   - Sec 3.1 DeepSWE protocol: "Each task gets one attempt; agent failures count as zero, and no task is rerun."
2. The runtime is the authors llama.cpp fork tuned for SM120; other GPUs run slower and GPUs older than Ampere fall back to the CPU; no x86 CPU speed is reported.
   - Sec 6 Limitations: "our llama.cpp fork is tuned for one GPU generation (SM120); other GPUs run it slower, and GPUs older than Ampere fall back to the CPU"
   - Abstract / Conclusion: "inference available through our llama.cpp fork at https://github.com/nari-labs/nari-llama.cpp"

## Claim corrections

- claim 0: **unaffected** — Trellis lineage and agent-trace KL objective confirmed.
- claim 1: **narrowed** — Indistinguishable from BF16 at n=113 single attempt (paired s.e. ~3.2-3.6 points per the paper), not shown equivalent; harness differs from the Unsloth harness.
- claim 2: **narrowed** — The CPU fallback refers to pre-Ampere NVIDIA GPUs in the fork; no EPYC-relevant CPU path or figure.

## Dive record

2026-11-20 Stage-2 dive (sonnet; full HTML read). The 'paper 44/47/46 vs card 38.9/41.6/40.7' is one dataset in two units (count of 113 vs percent). Offline agent KL (Appendix A, Table 3): NariQ 3.0 bpw 0.0063 vs GSQ-RCO IQ3_XXS 0.0276 at 3.00 bpw (authors metric). Novel part is the calibration/allocation recipe, not the format. EPYC grounding: our EXL3 track has CPU types EXL3_1..8 / EXL3M_1..8 and an AVX-512 int8 GEMV executor (quantization-and-low-bit.md:L135-L137 @e9ee76c); gfx90a EXL3-3/EXL3-4 unchecked (L65, L80); whether NariQ files decode with our EXL3 kernels is NOT-FOUND-IN-SOURCE (new GGML tensor types in the fork; seeded permutation, 16-band output layer). llama-quantize already supports per-tensor type maps (tools/quantize/quantize.cpp L410-L462 @ffc1bac82); llama-imatrix and --kl-divergence have no token-position mask, so agent-trace masked KLD needs a small patch. Decode upper bound from bytes: 3.0 bpw is 0.72x of UD-IQ4_XS bytes (arithmetic, unverified, before trellis decode cost). Adversarial pass not run; all numbers single-author own-harness. lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d) Stage-2 close-out (2026-11-20): dive-surfaced github.com/nari-labs/nari-llama.cpp ingested and dived as intake-2733; huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF declined (covered by NEW-10, closed FAIL for serving).
