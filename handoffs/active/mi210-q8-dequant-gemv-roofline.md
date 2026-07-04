# Handoff: MI210 single-stream roofline — Q8 dequant-GEMV kernel + batch-1 latency levers

**Status**: OPEN — kernel-authoring task (llama.cpp-experimental). **Created**: 2026-07-04 (Fable5 window-2 MI210 campaign follow-on).
**Owner tree**: `/mnt/raid0/llm/llama.cpp-experimental` (branch `upstream-mtp-verify`; kernel work goes here, NEVER production-consolidated-v6). HIP build `build-hip/`, `export LD_LIBRARY_PATH=<bin>:/opt/rocm/lib; export HIP_VISIBLE_DEVICES=0`.
**Substrate**: MI210 gfx90a/CDNA2, 64 GB HBM2e, ~1.64 TB/s peak, ROCm 6.2. All numbers OBSERVATION (no P-GPU-1).
**Context doc**: `handoffs/active/fable5-window2-findings-05b-mi210-inference-architecture.md` §1/§9.

## Objective

Raise **single-stream** GPU decode throughput for the qwen35/Q8 family toward the bandwidth roofline. Measured today: Q8 decode ~47% roofline (766 GB/s), fp16 ~62%, and rocprof attributes single-stream decode ~78% to `mul_mat_vec_q` (the Q8 weight GEMV) + 5.68% to `quantize_q8_1` (activation requant). Two gaps: **47→62% = Q8 dequant cost** (kernel-addressable); **62→100% = batch-1 latency wall** (memory-level-parallelism, harder). This handoff attacks both.

## Why this matters / transfer

- The already-landed MMVQ→MMQ dispatch fix (`de447119f`, `mmvq.cu:323` CDNA2 `case GGML_TYPE_Q8_0: return ne11<=1;`) gave +17% (27B) / +31.7% (gemma-31B) on the **MTP-verify** batch. This handoff is the **plain single-token** decode, the dominant path.
- Transfers to every GPU-resident Q8 role (the deferred residency bet): frontdoor, and any dense-Q8 model.
- The dequant kernel also unlocks **sub-4-bit** viability (bytes/token axis, below).

## Levers, ranked (each ships with its decisive experiment)

### Tier 1 — the dequant gap (47→62%, kernel-addressable, highest confidence)
1. **Kill the `quantize_q8_1` activation-requant overhead** (measured 5.68% of decode). The GEMV requants activations to Q8_1 every step; investigate fusing it into the GEMV prologue or caching. *Experiment*: rocprof before/after; acceptance = quantize_q8_1 share → ~0, decode +5%.
2. **Fused dequant-in-GEMV / int8-native MMQ path for batch-1.** Current `mul_mat_vec_q` dequantizes Q8 blocks then does fp accumulate. Port the CPU **iqk** approach (weight-block-outer, dequant-under-load; ref `ggml/src/ggml-cpu/iqk/iqk_gemm_legacy_quants.cpp:302-330`) to HIP, or hide dequant under the HBM weight load. *Experiment*: single-stream `llama-bench -n 128` Q8 vs the fp16 62% ceiling; acceptance = Q8 decode → ~55-62% roofline (~34-38 t/s on 27B, +15-30%), PPL/output unchanged.

### Tier 2 — the batch-1 latency wall (62→~80%, harder, MLP-bound)
3. **Async weight prefetch / double-buffering** in the GEMV — software-pipeline the next weight tile's `buffer_load` under current compute (Little's law: more requests in flight → higher achieved BW). *Experiment*: rocprof MemUnitStalled + achieved-BW before/after; acceptance = achieved BW 62%→~70%.
4. **Persistent/megakernel decode** (CUDA-proven, NO ROCm version — greenfield, high-effort). Fuse decode into one launch, weights streamed with pipelining; the Hazy/Mirage ~78% single-dispatch result. *Scope first, don't build blind* — estimate launch-overhead fraction via rocprof gap-analysis before committing.
5. **Weight swizzle/layout for gfx90a** — verify MMVQ HBM access is coalesced to the 64-wide wavefront + 128B cache line. *Experiment*: rocprof L2/MemUnit efficiency; a layout change is only worth it if coalescing is measurably poor.

### Tier 3 — sidestep / bytes-per-token (orthogonal, can exceed BW-% gains)
6. **n-gram / prompt-lookup speculation on GPU** (`--spec-type ngram-simple|ngram-cache|ngram-map-k`, already in v6, UNTESTED on GPU). Zero-cost draft → converts batch-1 into batch-N verify → more MLP + amortized weight read, at high acceptance for code/JSON/repetitive output. *Experiment (cheap, no kernel)*: run `--spec-type ngram-*` on the 27B over a code/structured prompt set, measure decode t/s + acceptance vs plain. **Do this FIRST — it's the cheapest single-stream win and needs no kernel.**
7. **Sub-4-bit weights (IQ2/TQ1/TQ2) + efficient CDNA2 dequant** — fewer bytes/token → higher absolute t/s even at same roofline-%. Gated on Tier-1 dequant kernel + an eval-parity/PPL quality check. *Experiment*: IQ2/TQ quant of the 27B, decode t/s + PPL vs Q8.
8. **KV-quant for single-stream LONG context** (q8-KV, `-fa 1`) — distinct from the aggregate case (where it was dead): at batch-1 long context the KV read adds to bytes/token. *Experiment*: 27B decode at 64k ctx, q8-KV vs f16-KV.

## Start-here sequence for the executor
1. **Lever 6 (ngram-spec) FIRST** — cheapest, no kernel, may bank a single-stream win in an hour.
2. **Lever 1 (quantize_q8_1)** — small, high-confidence kernel win.
3. **Lever 2 (fused dequant-GEMV)** — the main event; port the iqk pattern to HIP.
4. Then Tier-2 (prefetch/megakernel) only if Tier-1 leaves the 62% gap and it's worth the effort.

## Correctness / measurement discipline
- Every kernel change: `test-backend-ops` parity + PPL/greedy-output unchanged (the MMVQ fix was numerically-valid-not-bit-exact; document the same for any new kernel).
- Pair every speed number with a correctness check. Label OBSERVATION until a P-GPU-1 protocol exists.
- Do NOT commit to production-consolidated-v6; experimental only, operator-gated for promotion.

## Key files
`ggml/src/ggml-cuda/mmvq.cu` (dispatch + `mul_mat_vec_q`), `ggml/src/ggml-cuda/quantize.cu` (`quantize_q8_1`), `ggml/src/ggml-cuda/ggml-cuda.cu:2554-2617` (mul_mat dispatch), CPU reference for fused approach: `ggml/src/ggml-cpu/iqk/iqk_gemm_legacy_quants.cpp:302-330`. Profiling artifacts: `/mnt/raid0/llm/tmp/mi210-build/campaign/{prof,finish}/`.
