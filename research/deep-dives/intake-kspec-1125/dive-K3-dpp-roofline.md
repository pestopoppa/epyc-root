# K3-dpp-roofline: llama.cpp PR #32867 (HIP DPP warp prefix sum) and the LLM roofline-intensity paper

Entries: intake-2962 (llama.cpp PR #32867, head 46f9316db490), intake-2960 (arXiv 2611.32975v1).
Date: 2026-11-25. Stage-2 wave 1. Dive agent: Sonnet 5.5.

Read depth: intake-2962 FULL (s07 PR page text, s07d full diff). intake-2960 FULL (s05, all 100,475 chars, in
chunks, including all appendix tables). Code read: C21 worktree `/mnt/raid0/llm/llama-worktrees/c21-20261124`
at 98ff8a4. In-house lines pinned at lane head f19b902 (line numbers re-checked with `git show f19b902:`).
Adversarial web pass: not run. Both sources are one-author-group items with no replication to find, and the
adversarial work that mattered was internal (reading the PR's own tables and the paper's own appendix).

## Bottom line

1. **intake-2962: the scan the PR speeds up is NOT on any served path of ours.** `GGML_OP_CUMSUM` is emitted
   by exactly one model graph builder: the non-fused chunked GDN path (`build_delta_net_chunking`). The served
   graph takes the fused GDN op instead (both `fused_gdn_ar` and `fused_gdn_ch` default true and are only
   reset by a probe). In the fused path no CUMSUM node exists, and `warp_prefix_inclusive_sum` has exactly one
   caller on CUDA/HIP, `cumsum.cu`. The only other CUMSUM producer is the sampler (vocab-length rows, backend
   sampling only). So the operator steer "value = GDN/cumsum paths" does not hold for the scan half of the PR.
2. **The PR is bigger than its title.** 14 commits; the diff also rewrites `warp_reduce_sum` to DPP on HIP
   (with a `only_lane0_is_used` flag) and touches mmvf, mmvq, norm, quantize, ssm-scan, wkv, and
   `gated_delta_net.cu`. The reduction half is the part that could touch our GDN decode kernel, and we already
   hand-wrote DPP reductions for the two non-default GDN variants.
3. **PR numbers are correct as arithmetic, but measured on GCN gfx906 (MI50) and RDNA4 only, never on CDNA.**
   The index claim "shapes under ~1024 are neutral" is true on RDNA4 only; on MI50 small shapes also gain.
4. **DPP sequence is correct for wave64** (row_shr 1,2,4,8, then row_bcast:15 mask 0xa, then row_bcast:31
   mask 0xc). gfx90a defines `CDNA2`, so it takes the row_bcast branch.
5. **intake-2960: numbers check out against its own tables.** But the paper is NVIDIA-heavy (3 of 4 GPUs),
   uses MI300X only (59 of 179 cases), has no gfx90a, and predicts arithmetic intensity, not achieved GB/s or
   recoverable time, which is what VERIFY-KERNEL-ROOFLINE-CENSUS-1 ranks by. An LLM pre-estimate would not
   have fixed census r1 (its failure was attribution, not estimation). Small, real use: plausibility check on
   counter reads and a ranking prior for kernels not yet booked.

## Per-claim verdicts

### intake-2962 (PR #32867)

| # | Claim (index) | Verdict | Locator / evidence |
|---|---|---|---|
| 0 | HIP DPP float scan; row_bcast branch for GCN+CDNA, permlanex16/readlane for RDNA | CONFIRMED | s07d diff `warp_prefix_inclusive_sum`: `#if defined(GCN) \|\| defined(CDNA1..4)` branch, else permlanex16 + readlane(31) branch. Gate is `std::is_same_v<T, float> && (width == 32 \|\| width == 64)`; half2/float2 overloads untouched |
| 1 | MI50 CUMSUM f32 about 14-19% faster at large sizes | CONFIRMED (narrow) | s07 MI50 table: large 1-row shapes -15.4 to -18.8 %. Spot checks: [2000000,1,1,1] 5260.37 -> 4428.40 = -15.82 %; [128,128,4,4] 11.40 -> 9.18 = -19.47 %. Absolute gain at ne0=200000 is 88 us per call. MI50 = gfx906 (GCN5), not gfx90a |
| 2 | RX 9060 XT up to about 23% faster | PARTIAL | s07 RDNA4 table max is -24.36 % ([131072,16,1,1]); the [2000000,*] rows are -15 to -23 %. "Up to 24 %" is the accurate ceiling |
| 3 | Shapes under about 1024 elements are neutral | PARTIAL / OVERTURNED for MI50 | Neutral (within +/-3 %) on RDNA4 only. On MI50 [128,1,1,1] -6.57 %, [128,4,1,1] -17.36 %, [128,8,1,1] -10.54 %, [128,16,1,1] -9.29 %, [1024,1,1,1] -6.48 % (all labelled gain). The PR also labels -1.13 % "noise" on MI50 but -3.36 % "gain" on RDNA4 for the same shape [2048,16,5,4]: the verdict threshold is not stated |
| 4 | Merge after #32215 | CONFIRMED | s07 body "Merge after #32215". C21 has none of the PR's DPP helpers in `vendors/hip.h`, so the PR is not already in C21 |

Not found in source: the benchmark harness and command (presumably test-backend-ops perf), run count, A/A
noise floor, any correctness or bit-exactness statement, any CDNA2/CDNA3 number. AI usage disclosure says YES.

DPP correctness for wave64 (read from s07d, reasoned, not run): after the four row_shr steps each lane holds an
inclusive prefix inside its 16-lane row (out-of-row reads give 0 via bound_ctrl). `row_bcast:15` with
row_mask 0xa adds lane 15 of rows 0 and 2 into all lanes of rows 1 and 3. `row_bcast:31` with row_mask 0xc adds
lane 31 (which now holds row0+row1) into rows 2 and 3. That is a correct 64-lane scan. For width==32 on a
wave64 device only the first bcast runs, which is correct for two independent 32-lane groups. Floating-point
association differs from the old `__shfl_up` Hillis-Steele loop, so results are not bit-identical to before.
`row_bcast` is marked "GCN/CDNA only" in the PR's own macro comment (`vendors/hip.h`), consistent with gfx90a.

### intake-2960 (arXiv 2611.32975v1)

| # | Claim (index) | Verdict | Locator / evidence |
|---|---|---|---|
| 0 | ISA raises within-1.20x RAI share well above source-only | CONFIRMED | Abstract and §4.1: 8-14 % (ZS-Code) -> 26-32 % (ZS-ISA); gains +20.0/+17.8/+18.7 pp with paired-bootstrap CIs [14.5,25.5]/[12.2,23.6]/[12.0,25.4] (Table A.14). Table A.15: gpt-5.6 8-14 -> 32.4 at 1.20x, but at 4x it is 77.0 % vs 76.5 % (no gain) |
| 1 | FLOPs far better than traffic; traffic the main error | CONFIRMED | §4.1: total-FLOP 59-88 % vs traffic 36-40 % under ZS-ISA |
| 2 | Bound class mostly right, above majority baseline | CONFIRMED with a caveat | 78-92 % ZS-ISA (Table A.7: 83.9 / 78.3 / 91.8). Baseline 73.2 % = 131/179 (recomputed from Table A.8: 24+9+23+8+16+8+30+13 = 131). The baseline is fitted in-sample, so it is a strong baseline. Always-BB = 52 % (93/179). But 109 of 179 cases lie more than 4x from the balance point, so overall accuracy is flattered; the 40 near-balance cases show gpt-5.6 at 79.5 % ZS-ISA (42.5 % ZS-Code) |
| 3 | Agentic helps one model by a few points at several times the cost | CONFIRMED | Table 1: gpt-5.6 32.4 -> 38.9 % (+6.5 pp, CI [3.4,9.6]); cost 0.223 -> 0.800 USD (3.6x); latency 1.3 -> 3.4 min (2.6x from the rounded table values; the text says 2.5x, from unrounded). deepseek +2.5 pp CI [-1.8,6.6], gemini +0.2 pp CI [-3.4,3.7]; their completion falls to 88 % and 64 %, class accuracy to 75 % and 54 % |
| R | 179 cases, 3 models, 8,055 runs | CONFIRMED | 179 x 3 strategies x 3 models x 5 reps = 8,055 (five families x four variants x nine GPU-runtime combos = 180 minus one unavailable) |

MI300X subset (the only AMD data, no MI210): 59 of 179 cases (Table A.6: A10 40, A100 40, H100 40, MI300X 59).
Per-GPU numerical accuracy appears only in figures (Fig. 9) that the text extraction does not carry; the text
gives: lavaMD gpt-5.6 ZS-ISA 90 % on A100, 100 % on H100, 2.5 % on A10, 5 % on MI300X; inversek2j best on
MI300X but FLOP accuracy 68 % and RAI 67 % there, caused by packed-FMA and division-helper counting
conventions (1.26x FLOP overestimate, Table A.5); MI300X traffic ratios predicted/profiled 0.67 (lavaMD), 0.04
(particlefilter), 0.16 (particles) (Table A.13a). MI300X counters measure TCC/L2 toward MALL, including MALL
hits, with a 256 MB Infinity Cache, a boundary that does not exist on MI210. The MI300X majority-class
baseline is 71.4 % (FP32) and 76.5 % (FP64), so classification on MI300X is not clearly above its lookup.

Other limits the paper states: five kernel families, no atomic-heavy kernels, no comparison against dedicated
static FLOP/traffic models, fixed prompts, $2,000 budget, three surviving models of ten considered. No
LLM/ISA test on ML kernels (GEMV, attention, scans); the families are Rodinia/AxBench/CUDA-sample kernels.

## Q1: where the scan lives in C21 (98ff8a4)

- Definition: `ggml/src/ggml-cuda/common.cuh:516-526` (generic `__shfl_up_sync` Hillis-Steele; float2 at 529,
  half2 at 544 @ 98ff8a4). Only caller: `ggml/src/ggml-cuda/cumsum.cu:146` and `:157` (per-warp scan, then scan
  of warp sums in warp 0). Also a SYCL copy in `ggml-sycl/cumsum.cpp`, irrelevant.
- On HIP the CUB path is off: `GGML_CUDA_USE_CUB` is defined only when not HIP and not MUSA
  (`common.cuh:110-112`). So every HIP CUMSUM runs `cumsum_kernel` (`cumsum.cu:86-187`, dispatch `:214-262`), 4
  elements per thread, block up to 256. Op is F32 only (`cumsum.cu:267-300`).
- Graph emission: `ggml_cumsum` appears in `src/models/delta-net-base.cpp:89` (inside
  `build_delta_net_chunking`, gate cumsum over chunk length CS=64, so ne0 = 64, wave64-exact, rows =
  g_ne0 x n_chunks x H_v x n_seqs), and in `src/llama-sampler.cpp:1173,1487` (backend sampling CDF over the
  vocab). Nowhere else in `src/models/*.cpp`.
- Dispatch: `build_delta_net` (`delta-net-base.cpp:425-446`) uses the fused op when `fused_gdn_ar` (n_tokens==1)
  or `fused_gdn_ch` (n_tokens>1); both are set true at `src/llama-context.cpp:315-316` and only reset by the
  fused-op probes at `:650-651`. `build_delta_net_chunking` (with CUMSUM) runs only if the probe fails. No
  scan or CUMSUM call exists inside `gated_delta_net.cu` (grep: `warp_prefix_inclusive_sum` has no hit there).
- Served models: qwen35 / qwen35moe / qwen3next all call `build_delta_net` (`delta-net-base.cpp:777`). So for
  Qwen3.8-27B (GPU, DFlash2) and Qwen3.6-35B-A3B the CUMSUM node is absent on both decode (n_tokens==1) and
  verify/prefill (n_tokens>1) as long as the fused probe passes. In-house evidence it is not showing in any
  trace: a case-insensitive grep for `cumsum` over `handoffs/active/*.md` (first 15 hits read: the two I opened were
  unrelated KV-ring text; I did not read all hits) found no trace row naming a CUMSUM kernel, and the C18 27B
  verify trace attributes the verify to q8 GEMVs and the GDN op (`autokernel-loop.md:5035 @ f19b902`).
- Sizes if it ever ran: chunked path ne0=64 (one wave64), prefill or verify alike; sampler path ne0 = vocab
  (~2e5 order), one row per sampled position.
- Verdict: **not on any served path** except the unproven backend-sampling case. If backend sampling were on,
  the MI50 figure for ne0=200000 is -88 us per call (494.60 -> 406.94, s07); an MI210 figure is unknown and
  would be under 0.1 ms against a 40 ms verify (`autokernel-loop.md:5035 @ f19b902` trace), below any
  futility floor in use.
- CPU analogue: CPU CUMSUM exists (`ggml-cpu.c:2314`) and is likewise unreachable on the served CPU graphs for
  the same reason (CPU has `GATED_DELTA_NET`, profiled as `gdn_recurrence`, `autokernel-loop.md:8749 @ f19b902`).
  An AVX-512 in-register prefix scan (log-step `vpermd`/mask-add, or `vpexpandd` tricks) is technically fine for
  64-element rows but has no consumer. No port.

## Q3: in-house comparison

- **AK-BW-GDN-GATE-FOLD** (`autokernel-loop.md:5042-5046 @ f19b902`) is ticked and closed by pre-registered
  futility: fold made verify slower, saved -0.867 ms (futility floor 0.6), 2182 vs 2614 dispatches. It is about
  gate math, projections and launch count, not scans. The PR does not bear on it.
- **gdn-state-fwd** (`autokernel-loop.md:8752 @ f19b902`, and `:8749` GDN-RECURRENCE) is a CPU state-copy elision
  (252 MB per step on A3B). It is DRAM traffic, not cumsum. Unrelated to the PR.
- **GDN decode kernel reductions**: stock recurrent kernel `warp_reduce_sum<warp_size>` is a shfl_xor loop
  (`gated_delta_net.cu:660,673,735,749,763,778 @ 98ff8a4`). We already authored DPP reductions in two variants,
  both default off: `gdn_rows_sum16` (`:864-872`, knob `GGML_HIP_GDN_ROWS`) and `gdn_fu_sum8x2` (`:1236-1250`,
  `GGML_HIP_GDN_FUSED`, GDN-FUSED-VARIANT KEEP at op level, `autokernel-loop.md:5189-5196 @ f19b902`: 1.40x at
  T1, 2.37x at T8 F32 K1). So the PR's reduction half is ALREADY-PRESENT in spirit; the PR's only new element
  there is the `only_lane0_is_used` return (`wave_ror:1` instead of a broadcast shuffle). Open question: the
  stock kernel's reduction share of its 9.5-30 us per layer is unmeasured.
- **VERIFY-KERNEL-ROOFLINE-CENSUS-1** (`rocm-kernel-authoring.md:1192-1195 @ f19b902`): r1 ended
  FUTILITY_ATTRIBUTION because the forward was not located and no counter rows came back twice at ctx1024 w1;
  r2 is being built with aggregate-by-kernel attribution. The census ranks by recoverable time =
  time x (1 - achieved/peak) from FETCH_SIZE + WRITE_SIZE, which are measured.
- Calibration warning from our own record: VATTN-ROOFLINE-4 predicted ~1,280 GB/s for RF6 attention from an
  in-flight-bytes model and measured 303-392 GB/s, a ~3.3x miss (`rocm-kernel-authoring.md:1191 @ f19b902`).
  Analytic pre-estimates of achieved bandwidth have already failed here; that supports measuring directly, and
  also shows the failure mode is efficiency, which the paper's RAI does not predict at all.

### Would an LLM/ISA arithmetic-intensity pre-estimate help the census?

No for the census itself. Reasons, in order of weight:
1. The census's quantity is achieved GB/s and percent of the 1638 GB/s peak per kernel, ranked by time share.
   RAI is FLOP/byte. Our verify kernels are weight-streaming Q8_0 GEMVs and attention, all firmly bandwidth-bound
   on an MI210 (balance point is in the tens of FLOP/byte; Q8 GEMV intensity is about 2 FLOP/byte per verified token). Class (BB vs CB) is
   already known for every candidate, so the paper's headline (78-92 % class accuracy) adds nothing.
2. Bytes for GEMV rows are exact analytically (tensor size x launches); the paper's weak spot (cache-dependent
   traffic) is absent there. Where traffic is cache-dependent (attention K/V reuse across GQA heads, the GDN
   state), the paper shows the LLM at 36-40 % within 1.2x and up to 26x low on a strided kernel: exactly the
   kernels we most need numbers for.
3. Census r1 failed on attribution (locating the forward in the trace), which no estimator fixes.
4. The paper's reference counters are NVIDIA L2-to-DRAM and MI300X TCC-to-MALL; MI210 has no MALL, so its
   transfer to FETCH_SIZE/WRITE_SIZE semantics is unvalidated.

Where it could help (small, cheap, optional): (a) a plausibility gate on a counter read, flagging a kernel whose
FETCH_SIZE implies GB/s above peak or bytes far from a source-derived footprint (this can be done with a
deterministic analytic footprint, no LLM); (b) a pre-booking ranking prior for kernels outside the first census
shapes (the paper's Figure 1 use case), with five-run agreement as a confidence signal (Table A.10: same-class
agreement 147/179 cases at 98.6 % for gpt-5.6, but only 28 % of cases agree numerically and half of those
agree on a wrong value). Net: knowledge-only; the deterministic footprint check in (a) is the actionable part.

## Principles table

| Principle | Source evidence | MI210 (gfx90a) verdict | EPYC Zen 5 verdict | Why (mechanism) | Port cost |
|---|---|---|---|---|---|
| DPP row_shr + row_bcast:15/31 wave64 inclusive scan (replaces shfl_up log-steps) | s07d diff; MI50 -15 to -19 % at large shapes (s07) | TRANSFERS-WITH-CHANGES: correct and gated to take the CDNA2 branch, but no consumer on any served path | DOES-NOT-TRANSFER (no wave; CPU CUMSUM unreachable on served graphs) | Each shfl_up step is a ds_bpermute (LDS crossbar); DPP rides the VALU operand path, no LDS round trip. Only matters if a scan runs | Low (one helper + one branch), but zero served value now |
| DPP-based `warp_reduce_sum` with lane0-only tail | s07d `warp_reduce_sum_impl`; touches `gated_delta_net.cu` call sites | ALREADY-PRESENT (our `gdn_rows_sum16`, `gdn_fu_sum8x2`, default-off variants); stock GDN kernel still shfl_xor | DOES-NOT-TRANSFER | Same mechanism: quad_perm, row_half_mirror, row ops replace xor shuffles. Our variants already won at op level | Low to port the generic helper; value limited to stock-kernel reduction share (unmeasured) |
| In-register prefix scan on x86 | none in sources | n/a | UNKNOWN-NEEDS-PROBE only if a CPU CUMSUM consumer appears (none now) | AVX-512 log-step scan over 16 lanes is possible; no served CPU graph emits CUMSUM | Low, no consumer |
| ISA + instruction-mix prompting for static AI estimates | s05 8-14 -> 26-32 % within 1.2x; class 78-92 % | DOES-NOT-TRANSFER for the census (class already known, bytes analytic, MI210 has no MALL boundary) | DOES-NOT-TRANSFER (paper is GPU-only; CPU decode is DRAM-bound by byte count) | Estimator predicts FLOP/byte, not achieved fraction of peak; weak where traffic is cache-dependent | Low per query, but no decision it improves |
| Cache-dependent traffic is the dominant estimate error | s05 FLOP 59-88 % vs traffic 36-40 %; particlefilter 4-26x low; lavaMD MI300X 5 % | UNKNOWN-NEEDS-PROBE (attention K/V and GDN state are the cache-dependent kernels; plausible same weakness) | UNKNOWN-NEEDS-PROBE (L3-resident tensors already known to overprice a byte roofline, see memory note on L3-resident tensors) | Counter boundary decides what is counted; footprint != traffic | Needs a rocprofv3 comparison row, which the census already is |
| Agentic sandbox + self-written cache simulators | s05 +6.5 pp at 3.6x cost (one model); others uncertain, completion down to 64 % | DOES-NOT-TRANSFER as a cost/benefit | DOES-NOT-TRANSFER | Gain is model-dependent, cost 3.6-17.7x; budget is better spent on the measured census | n/a |
| Replicate-agreement as a confidence signal | s05 Table A.10: all-five same class -> 98.6 % correct, 82 % of cases | TRANSFERS-WITH-CHANGES if an LLM prior is ever used: gate on agreement, not on one run | same | Cheap uncertainty estimate; numeric agreement is weaker (55 % vs 23 % accurate) | Low |

## Derived actionables ledger

| ID | Action | Owner guess | Disposition |
|---|---|---|---|
| KS-K3-1 | Do not port the scan. Record that `warp_prefix_inclusive_sum` has one caller (cumsum.cu) and CUMSUM is absent from the served fused-GDN graphs; revisit only if the fused probe fails or backend sampling is enabled | `handoffs/active/autokernel-loop.md` (knowledge note under GDN rows) | knowledge-only |
| KS-K3-2 | Cheap op-level screen of the PR's DPP `warp_reduce_sum` (incl. lane0-only tail) in the stock GDN recurrent kernel at the GDN-VERIFY-BASE shapes (S_v128, T1/T8/T16); stop-on-futility if the reduction share of the op is under 3 % or gain under the A/A p95 floor. Step 1 is a code-read of which of stock, ROWS, FU is dispatched by default in C21 (stock, by the knob defaults above) | `handoffs/active/autokernel-loop.md` (new box after GDN-FUSED-VARIANT) | monitor (low expected value: GDN-FUSED already beats the stock reduction path by 1.4-2.4x at op level, and its fold decision is separate) |
| KS-K3-3 | Add a deterministic plausibility check to the census post-processing: flag any kernel row whose FETCH_SIZE+WRITE_SIZE-derived GB/s exceeds the measured 1.498 TB/s peak or whose bytes differ from the analytic footprint (tensor bytes x launches) by more than 2x. No LLM | `handoffs/active/rocm-kernel-authoring.md` (VERIFY-KERNEL-ROOFLINE-CENSUS-1 r2 post-processing) | immediate (zero compute, closes the "counters returned nothing or nonsense" failure class cheaply) |
| KS-K3-4 | Do not build an LLM/ISA roofline pre-ranker for the census; if the AutoKernel planner wants a prior, use analytic bytes and measured time shares, and gate any LLM prior on five-run agreement | `handoffs/active/rocm-kernel-authoring.md` (census) | decline (reason: the quantity ranked is achieved fraction of peak, not RAI; class is known; r1 failure was attribution) |
| KS-K3-5 | Check whether backend sampling (`llama-sampler.cpp:1173,1487`) is enabled on any served GPU role; if so, run one op-level CUMSUM shape [vocab,1] on gfx90a before judging the PR | `handoffs/active/autokernel-loop.md` | monitor (UNKNOWN-NEEDS-PROBE; expected under 0.1 ms per call) |

## Dive-surfaced sources

- arXiv 2512.04355 "Counting without running: Evaluating LLMs' reasoning about code complexity" (FLOP-count
  prediction precursor, printed in s05 reference list). Settles: how FLOP-only prediction fares (the easier half).
  bears_on intake-2960. Recommend: decline (superseded by intake-2960's FLOP table, and no kernel we need).
- arXiv 2605.31464 "GPU forecasters: Language models as selective surrogates for kernel runtime optimization"
  (printed in s05 reference list). Settles: whether LLMs can forecast relative kernel speedup to prioritise GPU
  measurement, which is closer to the census ranking need than RAI. bears_on intake-2960. Recommend:
  ingest-and-dive (it predicts speedup, the quantity we actually rank by).
- arXiv 2603.21331 "AutoKernel: Autonomous GPU kernel optimization via iterative agent-driven search" is
  already in our record as intake-1246 (index cross-reference); no new action.
- PR #32215 (named in s07 as the merge prerequisite; contents not read). bears_on intake-2962. Recommend:
  decline for now; revisit only if KS-K3-2 is opened.
