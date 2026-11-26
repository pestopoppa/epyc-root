# hoonki2002/Any-Rate

PARTIAL at 9e75eb78b4fae9bba7ab6f2c47dc8322873451cb. Read README, format, GEMV wrapper, v14 CUDA and Appendix H throughput/modeled energy. No rerun or per-question audit. Modes 2–4 read prefixes of one uncoded plus six Hamming-coded planes; 5–8 add residual planes with a second GEMV. Batch-1 Llama-3.1-8B RTX AR versus Any-Precision was 142.35 vs 141.63 tok/s at 2 bits, 121.32 vs 124.07 at 3, 104.91 vs 107.57 at 4. Benchmark selects fastest kernel/config per shape and mode. Appendix H puts this model at 59.65% of FP16 average accuracy at 2 bits; the paper four-model average does not apply to each. Energy is modeled from LPDDR/SoC constants.

[Primary source](https://github.com/hoonki2002/Any-Rate)

## Evidence checked

- Each H-plane byte stores two 4-bit codeword indices, one per block of 8 columns. (any_rate/README.md:L69 @ 9e75eb7).
- The GPU kernel setup rearranges the packed planes while preserving their bits. (kernels/ar_gemv.py:L8 @ 9e75eb7).
- The published end-to-end decode rates use one RTX 5070 Ti at batch one. (results/H.Storage_and_Decoding_Efficiency/throughput/table.md:L1 @ 9e75eb7).

## EPYC applicability

MI210 needs wave64 retile of CUDA warp32 per-output-row tables. Budget LDS for double buffering, bank mapping and occupancy within 64 KiB; cp.async is NVIDIA-specific. Zen 5 can test AVX-512 byte permutes on split tables or indexed lookup on wider tables with NPS4-local rows. No FP8 dependency and no AMD measurement.

any_rate/README.md:L64-L81, kernels/ar_gemv.py:L1-L21,L34-L49,L80-L91 and kernels/csrc/ar_gemv_v14_dense.cu:L124-L161 @ 9e75eb7. EXL3 lane handoffs/active/quantization-and-low-bit.md:L74-L90 @ a660ead. (EPYC root a660ead17).

## Counterevidence and limits

Exact-title/arXiv/EXL3 searches surfaced no matched independent reproduction. Author artifacts themselves narrow 2-bit accuracy and show AR slower than Any-Precision at 3/4 bits. No same-quality EXL3 or MI210/CPU result.

## Derived action for review

Use as companion evidence for the paper. Under INF-80 compare effective bytes and scalar decode on frozen EXL3 fixtures and held-out KLD/model inputs before a single AVX-512 or HIP microbench. Freeze baseline, raw row outputs, invalid denominators, and latency/quality stops.

handoffs/active/quantization-and-low-bit.md

## Sources surfaced

Companion arXiv:2611.34402 is already selected. Any-Precision, AnyBCQ and MatGPTQ merit follow-on only for a specific KLD or runtime comparison untouched by the paper/EXL3 lane.
