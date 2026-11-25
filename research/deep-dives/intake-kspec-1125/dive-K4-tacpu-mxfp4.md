# K4-tacpu-mxfp4: TACPU (intake-2959) and MXFP4 PTQ composability (intake-2961)

Stage-2 dive, 2026-11-25, lane head f19b902. Read-only.

## Read depth
- intake-2959 (arXiv 2610.38809v3): FULL source.txt read (s04), including Tables 1-13 and appendix.
- intake-2961 (arXiv 2611.32873v1): PARTIAL. The PDF could not be rendered (pdftoppm missing). Read the Stage-1 text extraction (kerning-garbled, tables partly lost). Section 3 (Midmax formula, Eq. 9), 4.1-4.6, conclusion and Tables 4 and 6 were read. Figures, Table 1, Table 3, Table 5 and the appendix were not read in full. Numbers below come from that extraction, so they are stage1-unverified and cannot be machine-anchored.
- Search note: a web search returned "CACPU" with the same four authors, dated 2026-10-28, as an earlier title for intake-2959. Restatement only. No independent replication found for either paper (3 searches used in total across both entries).

## intake-2959 TACPU: per-claim verdicts

| # | Claim | Verdict | Locator |
|---|---|---|---|
| 0 | Up to 2.01x over SDPA / Flex / SGLang kernels | PARTIAL | Table 1 and Table 7. 2.01x holds only at S=128K on Xeon 6767P (AMX). Ratio is vs best baseline per row (4K 8.26/5.00 = 1.65x). Range is 1.45-2.01x. On the AMX-less 265K it is 1.30-1.58x. D=192: 1.30-1.95x. All bf16, one batch, one socket, 64 threads. llama.cpp was NOT a baseline: App. B.4 says it was "significantly slower", with no numbers. |
| 1 | TTFT up to 1.74x on Llama-3.1-8B in SGLang | PARTIAL | Sec 4.2. Value is read from text only (Fig 4 not in source). 1.74x is at 128K on the AMX Xeon, vs SDPA. Attention share grows with length, so short-context gain is much smaller. Accuracy: MMLU 66.2 vs 66.7 (Sec 4.7). |
| 2 | Cost-prioritized shared queue beats FIFO and static | PARTIAL | Table 2: FIFO to cost-priority is 1.01-1.29x on Xeon (avg 14.33%) and 1.01-1.06x on 265K (avg 4.16%). The big numbers (1.71x Xeon, up to 2.45x 265K) are vs the static schedule (Fig 6, not tabulated). The 2.45x is a hybrid P/E-core effect that does not exist on Zen 5. Index-based ordering is within 1% of exact cost in typical cases (Sec 4.3). |
| 3 | Group sizes from an analytic cache formula | CONFIRMED | Eq 2-4, Table 13. G = (f_L2 L2 - U)/Q_b with f_L2=0.65. Default is 0.58% (265K) and 2.34% (Xeon) slower than the best G (Tables 8-9). Note f_L3=0.8 and f_L2=0.65 are fixed constants, not derived. |
| 4 | Far fewer DRAM bytes at 128K | CONFIRMED | Table 4: Xeon 128K 150.50 GB (SDPA) vs 21.13 GB (ours); 265K 1774 vs 517 GB. Measured with VTune on the Xeon with SNC-2, on a 336 MiB L3. |

Overturn-level observations the entry did not carry:
- Ablation interaction (Table 6, Sec 4.6): on Xeon 128K, cost scheduling alone gives 1.08x, L3 blocking 1.34x, overlap 1.12x, q-grouping 1.66x. On the 265K, L3 blocking alone is 0.99-1.00x. The gain comes from the stack, not from any one piece. Cherry-picking one piece should not be expected to deliver the headline.
- Table 6 "All Off" at 128K (8512 ms) is slower than SDPA (6376 ms) in Table 1, so the ablation baseline is a weak starting point.
- The kernel is a PyTorch codegen C++ template, not released code in the source. NOT-FOUND-IN-SOURCE: any repo link.

## What the dispatcher is
Per L3 chunk, the kernel computes each q-group's cost (exact count of non-masked KV tiles, Eq 5), sorts q-groups in descending cost (LPT), puts them in a lock-free shared queue, and threads fetch the next one with an atomic increment on a shared index. The queue is rebuilt per L3 chunk. It beats a contiguous static split because causal masking makes late q-groups cost far more than early ones, and a barrier waits for the slowest thread. It beats FIFO modestly, because FIFO leaves a long group for the last wave (tail effect).

## In-house comparison (C21 @ 98ff8a4)
Path: `/mnt/raid0/llm/llama-worktrees/c21-20261124/ggml/src/ggml-cpu/`.
- Tiling: `ops.cpp:9916-10232` (`ggml_compute_forward_flash_attn_ext_tiled`), Q tile 64 and KV tile 64 (`common.h:9-10`). It loops over all KV (`ops.cpp:10059`) for each Q tile and re-packs K per Q tile (`ops.cpp:10094-10127`). No K/V block reuse across Q tiles, no L3 chunking, no L2 q-group inversion. So TACPU principle 1 and 2 are ABSENT, not present.
- Causal skip: tile skipped when the mask is all -inf (`ops.cpp:10064-10074`). So tile skipping exists via the mask, but no cost model.
- Row chunking: `ops.cpp:10574-10620`. 4 chunks per thread, dynamic via `ggml_threadpool_chunk_add` (`ggml-cpu.c:754`, atomic fetch-add). Chunks are consumed in ascending row order, which is FIFO, not LPT. Rows are indexed head-major then position, so within a head the cheap early positions come first and expensive late ones last: this is the worst order for the tail effect.
- Static fallback: `use_static_chunks = neq1 <= 4` (decode / verify), and chunking is disabled when `ggml_is_numa()` (`ops.cpp:10577-10589`, `ggml-cpu.c:860-862`). `ggml_is_numa()` is true only if `--numa` initialises ggml (`src/llama.cpp:104-112`, DISABLED is the default). In-house launches use `numactl --interleave` rather than `--numa` (numa-placement-and-contention.md:L1764-L1782 @ f19b902), so dynamic chunking is on. UNVERIFIED: that no served launcher passes `--numa`.
- Share of what we serve: CPU flash-attn tiled is 3.47% of cycles at p8192 on the 122B (cpu-decode-roofline-program.md:L5644 @ f19b902), 5.88% (L5683) and 5.59% (L5730) in the PC-0b/PC-3 profiles. Prefill dominates wall clock in long-context turns (PC-1, L5705-L5709: 46.8-83.1% prompt wall), but attention is only a few percent of cycles; GEMM/MoE dominate. At 32K-128K the attention share rises (DEPTH-ENV-1, L109 and L424: depth costs -60% prefill by 128K), so the bound on gain at depth is unmeasured. XFER-4b (L251-L263) is about iqk IQ4_NL/MXFP4 GEMM at N=256, not attention; TACPU is not an XFER-4b input.
- Upper bound: if attention is ~5% of prefill cycles at 8K, a 1.3-2x attention speedup gives ~1-3% prefill. At 128K attention is a larger share, unmeasured here.

## Principles table (TACPU)

| Principle | Source evidence | MI210 (gfx90a) | EPYC Zen 5 | Why | Port cost |
|---|---|---|---|---|---|
| L3 K/V group blocking | Table 4, Table 6 (1.25-1.34x on Xeon) | DOES-NOT-TRANSFER | TRANSFERS-WITH-CHANGES | Zen 5 L3 is 32 MB per 8-core CCD, not one socket-wide cache: the group must be sized per CCD and threads of a group pinned to one CCD. Paper's model assumes one shared L3 (336 MiB). On MI210 FlashAttention-style LDS/L2 tiling already applies and there is no CPU-style L3. | Medium: new tile loop in ops.cpp tiled path plus CCD-aware thread grouping |
| L2 q-group loop inversion (G q-blocks per KV step) | Eq 2-4, Table 6 (1.66x, the largest single piece) | DOES-NOT-TRANSFER | TRANSFERS-WITH-CHANGES | Zen 5 L2 is 1 MB per core vs 2 MB Xeon; G formula must use 1 MB and fp32 K tile. Our kernel re-packs K per Q tile, so reuse across q-blocks is the clearest missing piece. | Medium: restructure `ops.cpp:9916+` loop nest, keep row-exactness (INF-70 note: FA is already not row-exact above 256 KV, L4290) |
| Cost-sorted shared queue (LPT) | Table 2 (1.03-1.29x vs FIFO), Sec 4.3 | UNKNOWN-NEEDS-PROBE | TRANSFERS-WITH-CHANGES | Our chunking is already dynamic but FIFO and ascending in cost; reverse order per head is trivial. Gains vs FIFO on a homogeneous Xeon were modest. The 2.45x is a hybrid-core effect, not applicable. | Low: reverse chunk order or sort rows by cost |
| Analytic cache-size formula | Eq 2-4, Tables 8-9 | UNKNOWN-NEEDS-PROBE | TRANSFERS | Default within 0.6-2.3% of optimum, so no per-CPU tuning. Fixed f_L2 / f_L3. | Low once the loop exists |
| AMX GEMM + AVX-512 softmax overlap | Table 6 (1.10-1.12x) | DOES-NOT-TRANSFER | DOES-NOT-TRANSFER | Zen 5 has no AMX. Our tiled path uses `simd_gemm` fp32 (`ops.cpp:10131`), all on the same vector units, so there is no separate unit to overlap with. | n/a |
| NPS4 dispatcher vs static split | Not tested; Xeon SNC-2 only (Table 12) | n/a | UNKNOWN-NEEDS-PROBE | A shared queue ignores NUMA locality of K/V pages. Under `numactl --interleave` K/V is spread, so locality is moot. Untested in the source. | Probe only |

## intake-2961 MXFP4: per-claim verdicts (stage1-unverified, PDF only, quote-free)

| # | Claim | Verdict | Locator (extraction) |
|---|---|---|---|
| 0 | Recipe is format dependent: MXFP4 gains from rotation + error-correcting PTQ, NVFP4 less | CONFIRMED | Abstract; Sec 4.2 and Fig 11: rotation hurt NVFP4 in 8 of 9 configs, helps every MXFP4 granularity; Block-16/32 best, full rotation smaller. |
| 1 | Midmax beats floor selection in most configs | PARTIAL | Sec 4.4: better in 67% of model x rotation x PTQ combos, but average gain only +0.12 accuracy points (absolute). +0.25 no rotation, about 0 at Block-16, +0.20 at Block-32, +0.30 with Qronos, +0.06 GPTQ, +0.02 RTN. Not uniformly better than MSE; best MXFP4 configs split evenly between MSE and Midmax (Sec 4.6). |
| 2 | MXFP6 activations + MXFP4 weights recover most of the 4-bit loss | CONFIRMED with scope | Sec 4.6, Table 4: A4W4 to A6W4 +1.74 points; A6W4 to A6W6 +1.26. Matches or exceeds BF16 only on 3 tasks for one model (Llama-3.1-8B-Instruct). The reverse order (A4W6) was NOT evaluated (authors say so). |
| 3 | Per-tensor macroscale does not improve MXFP4 average | CONFIRMED | Sec 4.5: -0.66 to -0.85 points at A4W4; task-level gains (GSM8K 79.6 to 81.9). |

Other facts: six small dense base models (Llama-3.2-1B/3B, Llama-3.1-8B, Qwen3-1.7B/4B/8B); metric is the mean of five zero-shot tasks (ARC-E, ARC-C, HellaSwag, PIQA, WinoGrande), no KLD or perplexity; ROCm 6.4 and PyTorch (emulated, no FP4 hardware path stated for the study beyond CDNA4 mention). Total gain at A4W4 from Midmax + block rotation + PTQ is about 3 points over a baseline of RTN, MSE, no rotation.

### Midmax, exactly
E2M1 max v_max = 6. Floor rule (Eq 4): scale = 2^(floor(log2 max|x|) - e_elem_max), e_elem_max=2, which forces the block max into [4, 8) after scaling, so values in (6, 8) clip to 6. Midmax (Eq 9): v_mid = (v_max + 2^(e_max+1))/2 = 7.0 for E2M1 (7.75 for E2M3). If the block max after floor scaling is below v_mid, keep the tight scale; if it is at or above v_mid, round the scale up one power of two. It applies only to power-of-two scales (E4M3 is exempt). In the study, Midmax is applied to weights only, and activations keep floor ("Stats").

### Our quantizer (C21 @ 98ff8a4)
`ggml/src/ggml-quants.c:350-382` (`quantize_row_mxfp4_ref`): `e = floor(log2f(amax)) - 2 + 127` (line 368). That is exactly the floor rule. No Midmax, no MSE search. `quantize_mxfp4` ignores `quant_weights` (the imatrix) (`ggml-quants.c:2302-2304`). Element rounding is nearest-grid via `best_index_mxfp4` (L336-347), so the grid is nearest but the scale is floor. So our default is the paper's weakest baseline for weight requant.

### Applicability
- Weight-only and offline, applicable to GGUF requant: Midmax scale rule; MSE scale search (calibration based; could reuse imatrix as weights); GPTQ-type error correction (needs calibration and a new tool; llama.cpp has none).
- Needs activation quantization or online rotation, NOT applicable as-is: A6W4/A4W4 results (our activations are f32 or q8_1); Hadamard rotation (weight rotation needs matching activation rotation online or absorbable into neighbours, which requires graph changes); macroscale.
- Caveat: no weight-only (A16W4) arm exists in the paper. The Midmax gain was measured while activations were also MXFP4, so its size under f32 activations is unmeasured. Gains this small (0.12 points) will not be visible in a 5-task accuracy average; our KLD gate is more sensitive.

### Models we serve as MXFP4
Only the DeepSeek-V4.1-Flash 1017 MXFP4-experts build. It is a lossless bit-for-bit repack of the native FP4 experts (deepseek-v41-flash-evaluation.md:L1089-L1093 @ f19b902; KLD 0.0102 native vs 0.0290 for the Q4_K requant in the DS4-Flash public evidence, L1357-L1359). Its scales are already fixed by the producer, so Midmax cannot touch it. The requant MXFP4 to Q4_K path was "not pursued" (L1387). No gpt-oss in any active handoff. The XFER-4b allowlist concerns the kernel, not quantization quality (cpu-decode-roofline-program.md:L251). So Midmax matters only for a NEW requant from BF16/Q8 into MXFP4 (none queued).

## Principles table (MXFP4)

| Principle | Source evidence | MI210 (gfx90a) | EPYC Zen 5 | Why | Port cost |
|---|---|---|---|---|---|
| Midmax scale rule for E8M0 | Sec 4.4, Eq 9 | TRANSFERS (offline, device-independent; decode on gfx90a has no FP4, so dequant to int8/fp16 as today) | TRANSFERS (offline; decode uses existing repack) | It is a pure quantizer change, 8 lines in `quantize_row_mxfp4_ref`. Gain small (+0.12 pts avg), 67% of configs. | Low: one function plus a KLD A/B on any model requantized to MXFP4 |
| Block (16/32) Hadamard rotation | Fig 2, Fig 11, Table 4 (+1.17 with Block-32) | TRANSFERS-WITH-CHANGES | TRANSFERS-WITH-CHANGES | Needs rotated activations at runtime for weight-only inference unless absorbed into prior op. A block-32 rotation matches the MXFP4 block, so a cheap per-block online transform is conceivable. | High (graph change) |
| INT8/FP16 emulation of FP4 | Mentions CDNA4 native; study emulates | ALREADY-PRESENT (dequant path) | ALREADY-PRESENT (`mxfp4_8x8_q8_0` AVX2 repack) | no FP4 on gfx90a or Zen 5. | none |
| GPTQ/Qronos error correction | Table 4 (+1.32 GPTQ over RTN) | UNKNOWN-NEEDS-PROBE | UNKNOWN-NEEDS-PROBE | Offline, weight-only in principle, but needs a tool we lack and calibration data. | High |
| A6W4 mixed precision | Sec 4.6 | DOES-NOT-TRANSFER | DOES-NOT-TRANSFER | Needs activation quantization; ours are f32 / q8_1. | n/a |

## Derived-actionables ledger
- KS-K4-1: Port Midmax into an experimental `quantize_row_mxfp4_ref` variant and A/B by KLD against floor on one BF16 model requantized to MXFP4, only when a requant to MXFP4 is queued. Disposition: monitor.
- KS-K4-2: Add a prefill-attention share measurement at 32K-128K on the C21 binary before any TACPU-style port. Disposition: knowledge-only until measured (no new numbers computed here).
- KS-K4-3: If attention share at depth is material, try (cheap) reversing chunk order so expensive late-position rows are dispatched first, then (medium) q-group loop inversion with L2 sizing for 1 MB. Disposition: monitor, gated by KS-K4-2.

## Dive-surfaced sources
- arXiv 2610.00053 "Format-Aware Fusion for Fast FP4 Pretraining" (search result, captured this session): compares upward vs floor power-of-two scale rounding for MXFP4. Bears on intake-2961. Pretraining, not PTQ; recommend decline-unless-asked. Restatement context only.
- arXiv 2603.08713 "Unveiling the Potential of Quantization with MXFP4" (search result): Overflow-Aware Scaling, a competing power-of-two scale fix. Bears on intake-2961. recommend ingest-and-dive (a weight-quant scale rule, independent of Midmax).
