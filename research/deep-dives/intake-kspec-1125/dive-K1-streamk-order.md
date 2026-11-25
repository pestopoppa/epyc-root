# K1-streamk-order: MMQ stream-k column-tile order (PR #32921) and the Stream-K paper

**Entries:** intake-2956 (llama.cpp PR #32921, head 5bc67fe5d273), intake-2971 (Stream-K, arXiv 2301.03598v1).
**Read depth:** intake-2956 FULL (PR page `s01`, full diff `s01d`, review thread dump). intake-2971 FULL (whole
`x01` text incl. Appendix A.1; reference list skimmed).
**Dive:** 2026-11-25 Stage-2 wave 1, Opus 5.5. In-house lines pinned to lane `f19b902` (handoffs) and C21
`98ff8a4` (code). The handoff text did not change between f19b902 and lane HEAD 65c5bee.

## Bottom line

The PR's claims check out against its own text and diff. But **on our served MI210 path it is a no-op**:

1. **np4 verify (M=36)** reaches MMQ, but on CDNA it picks J=48, which gives **one column tile** (`ntx=1`).
   With one column tile, the old order (IWZJ) and the new one (JIWZ) are the same map. No two tiles share
   a row band of x, so there is nothing to reuse.
2. **27B Q8_0 prefill at ub 256 and 512 never reaches MMQ on gfx90a.** `ggml_cuda_should_use_mmq` returns
   false for Q8_0 with `ne11 > 128` on CDNA2 (`mmq.cu:346-362 @ 98ff8a4`). Those shapes go to dequant plus
   rocBLAS. The tree's own comment says so (`mmq-q8-mf.cu:1703 @ 98ff8a4`: "prefill on the cuBLAS route
   (this tree's default for Q8_0 at large n on gfx90a)"). Our int8-MMQ replacement attempt for that
   regime was dropped at 0.48x vs rocBLAS (AK-ASM-H4).
3. Even with HIP enabled, the PR's gate `J == 128` can never fire on CDNA. The CDNA Q8_0 table stops at
   J=64 (`mmq-config-cdna.cuh:42-48 @ 98ff8a4`).

The mechanism itself is sound, and gfx90a is a stronger case than GB10 *if* MMQ ever serves wide prefill.
Our launcher always runs 104 stream-k blocks and has no tiled-launch escape on AMD
(`mmq.cuh:1333 @ 98ff8a4`). At ub 256/512 the 104 blocks divide evenly into 4 or 8 column tiles, so the
blocks that share a row band would also be in step along K. Keep it as a monitor item for the day the
Q8_0 prefill routing changes.

## Per-claim verdicts

### intake-2956 (PR #32921)

| # | Claim (Stage 1) | Verdict | Locator / note |
|---|---|---|---|
| 0 | Column tile goes slowest so blocks sharing x rows run together and share L2; NVIDIA dense J==128 only; compiled out on HIP/MUSA | CONFIRMED, narrowed | Body "Overview"; diff launcher hunk `@@ -1569,6 +1574,12 @@`. It also needs `!has_fusion` and the stream-k (not tiled) launch, and the fixup kernel picks the order with a runtime branch (`ntizw.z != 0`). |
| 1 | GB10 27B Q8_0 pp2048: 1.257x at ub512, 1.162x at ub256; ub 1024/2048 flat | CONFIRMED | Table rows 917→1160, 794→923, 1142→1141 (0.991), 1129→1114 (0.997). Caveat: the 27B Q8_0 file was requantized from Q4_K_M with `--pure` (real shapes, degraded values); median of 3 rounds. |
| 2 | q8_0 8192x512 (256 tiles) 1.96x on GB10; 12288x512 (384 tiles) unchanged; RTX PRO 6000 within noise | CONFIRMED | Collapsed MUL_MAT table (k=5120, n=512, median of 6). 384 tiles = 8 full waves on 48 SMs, so they run tiled. 256 = 64 row tiles x 4 column tiles, which implies I=J=128 on GB10. |
| 3 | Runtime branch cost up to 8%; template instead; a kernel per J would be +38% compile time | PARTIAL (narrowed) | "up to 8% slower, also for shapes whose order did not change"; J=128-only variant costs +8% compile on sm_121a, every J +38%. A reviewer (JohannesGaessler) asked whether the runtime check was really slow. The author answered "Yes unfortunately there was a regression in doing that", with no numbers. |
| 4 | Not bit-exact; KLD 0.00070 on Qwen3.5 4B Q8_0, measured on an earlier broader version | CONFIRMED | The reference perturbation (master ub256 vs ub512) is KLD 0.00075, so the reorder moves results about as much as changing ubatch. |
| 5 (new) | Review state at head 5bc67fe | CONFIRMED | OPEN, 4 commits, approved by ggerganov and anujj (2 approvals, the required count), with comments from JohannesGaessler (bool→enum, enum names, runtime-check question). |

Counts for intake-2956: C 4 (claims 1, 2, 4 and new claim 5), P 2 (claim 0 narrowed on scope; claim 3 narrowed because the 8% is "up to" and has no data in the thread), O 0, NF 0.

### intake-2971 (Stream-K paper)

| # | Claim | Verdict | Locator / note |
|---|---|---|---|
| 0 | Even share of MAC-loop iterations rather than whole tiles | CONFIRMED | Abstract; §4 Alg. 5. |
| 1 | Split tiles fixed up; seams bounded by processor count | CONFIRMED | §4 ("overheads ... scaling instead with the number of CTAs g"); §7 "O(p) number of splitting seams". |
| 2 | One tile config per precision replaces ensembles | CONFIRMED, narrowed | §1/§6. The paper concedes that small, bandwidth-bound shapes do not compete with cuBLAS. It proposes a second, smaller-tile kernel as future work (§6, last paragraph). |
| 3 | Large peak speedups over CUTLASS and cuBLAS | CONFIRMED, narrowed | Peaks: 14x vs CUTLASS and 6.7x vs cuBLAS (FP16→32). Averages vs cuBLAS are only 1.13x (FP16) and 1.06x (FP64). The minimum vs cuBLAS is 0.64x (FP16) and 0.68x (FP64). All on A100 locked at 1005 MHz. |
| 4 (new) | Basic Stream-K's per-CTA K-offset skew can prevent cross-CTA cache reuse; the DP+SK hybrids limit it | CONFIRMED | §5.2. |
| 5 (new) | The paper does not study tile-visit order for cache reuse; it maps work m→n→k and leaves "cache-aware tile-access patterns such as Morton Order" to future work | CONFIRMED | §4 and §7. PR #32921 is exactly that unstudied lever. |

Counts for intake-2971: C 4 (claims 0, 1, 4, 5), P 2 (claims 2, 3, narrowed), O 0, NF 0.

## Tile arithmetic on gfx90a (C21 code, served 27B Q8_0 shapes)

Code facts @ 98ff8a4:
- Rows divisible by 128 → `fallback=false` (`mmq.cuh:347-349`). CDNA Q8_0 cells: 512 threads, occupancy 1,
  **I=128**, J ∈ {16, 32, 48, 64} (`mmq-config-cdna.cuh:42-48`).
- J choice: smallest J with the fewest column tiles, J stepped 8..128 (`mmq.cu:154-171`).
  n=36 → J=48, ntx=1. n=256 → J=64, ntx=4. n=512 → J=64, ntx=8. (n=65..128 → J=64, ntx=2.)
- Stream-k grid on AMD is always `nsm` = 104 blocks. The `>= 90%` tiled escape is NVIDIA-only
  (`mmq.cuh:1328-1337`). Each block takes a contiguous range of the (tile, k) space, with jt fastest
  (`mmq.cuh:987-1006`).
- Routing: Q8_0 n ≤ 16 goes to the Q8_MF / WVSK / SKINNY kernels (caps 16: `mmq-q8-wvsk.cu:51`,
  `mmq-q8-skinny.cu:32`). n 17..128 goes to MMQ. n > 128 goes to rocBLAS (`mmq.cu:353-362`;
  `ggml-cuda.cu:2128-2156`).

Shapes stated in handoffs (rows x K): 17408x5120 (ffn up/gate) and 5120x17408 (ffn down)
(`autokernel-loop.md:4574 @ f19b902`); attn_q 12288 rows and attn_k/v 1024x5120
(`autokernel-loop.md:5035-5036 @ f19b902`); 6144x5120 (Q8 in-place test shape,
`rocm-kernel-authoring.md:1161 @ f19b902`).

Tiles = (rows/128) x ntx, compared with 104 blocks:

| Tensor (rows x K) | row tiles | np4 verify M=36 (ntx 1) | ub256 (ntx 4)* | ub512 (ntx 8)* |
|---|---|---|---|---|
| 17408 x 5120 | 136 | **136 > 104**, 1.31 tiles/block | 544 | 1088 |
| 5120 x 17408 | 40 | 40 < 104 (k-split) | 160 | 320 |
| 12288 x 5120 | 96 | 96 < 104 | 384 | 768 |
| 1024 x 5120 | 8 | 8 | 32 | 64 |
| 6144 x 5120 | 48 | 48 | 192 | 384 |

\* Hypothetical. These shapes route to rocBLAS on gfx90a today, not MMQ.

- **M=36:** the "more tiles than blocks" precondition holds only for the 17408-row tensors (136 vs 104).
  But blocks never share x row bands there: each tile *is* one row band (ntx=1). A tile split across
  two blocks splits K, so the two blocks read disjoint bytes. The PR's index map is the identity when
  `ntj=1`, because jt = 0 under both orders and it = t under both.
- **ub256/512 (if MMQ served them):** the precondition holds widely, and 4 or 8 column tiles share each
  row band. Under the current order, each block walks a band's column tiles one after another. In
  between, the other 103 blocks stream their own bands. A Q8_0 band is 128 x 5120 x 34/32 = 696,320 B
  (K=5120) or 2,367,488 B (K=17408). About 104 bands are in flight, which is ~69 MiB for K=5120 and far
  above the 8 MB L2. So the model predicts each weight band is re-read from HBM ntx times. Under JIWZ,
  blocks b, b+104/ntx, ... sit on the same band. 104 is divisible by 4 and 8, so those blocks also start
  at the same K offset. That removes the K-phase skew that Stream-K §5.2 warns about. This is a byte
  model, not a measurement.

## G17 WGM vs the PR's within-block order

- G17 (`autokernel-loop.md:3574-3579`, `:3923-3947 @ f19b902`) remapped *launch/tile order* with the Triton
  `GROUP_SIZE_M` grouping over an (M-tile x N-tile) grid, on batched decode shapes with few N tiles and on
  Q4_K/Q6_K. Every nonzero group size regressed 1.286-4.050%, and WGM8 lowered TCC hit rate from 67.304% to
  59.849%. F3's explanation is that grouping M enlarges the concurrently resident *weight* footprint.
  The G17 patch source is not on disk: branch `experimental-v9-autokernel-wgm-20260811` has no commits past
  `0db32c06e`. So this comparison rests on the handoff text.
- The PR changes the order *inside each stream-k block's contiguous range* so that blocks spaced
  `104/ntx` apart work the same x band at once. That **shrinks** the concurrent weight footprint by about
  ntx, and the activation (y) footprint stays the same. It is the opposite direction to WGM-M grouping.
- **Does G17's negative predict the PR on gfx90a? No.** G17's mechanism (more distinct weight bands in
  flight → lower hit rate) is consistent with the PR's mechanism (fewer bands → higher reuse). Neither
  experiment tests the other. Two in-house rules still bind any future probe:
  `l2-hit-rate-is-not-an-objective-on-gfx90a` (`autokernel-loop.md:3367`: TCC hit rate and device time
  moved in opposite signs) means a wall-clock veto gate is required. The search-surfaced HipKittens paper
  makes the same point for CDNA4 (that is a restatement, not a replication).

## AK-MMQ-SK2 context

AK-MMQ-SK2 CLOSED on 2026-11-24 (`autokernel-loop.md:4574-4579 @ f19b902`):
- force-tiling: every cell within ±0.0033 of default.
- small I=64 table: −0.19 to −0.38 at small n.

The two PRs act on different levers. #32837 changes the tiling rule and tile size; #32921 changes the
order inside stream-k. SK2's box is still open because its step-2 shape census was never filed. The tile
table above covers the dense 27B part of that census.

## EPYC Zen 5: the analogous question in ggml-cpu

- With `GGML_IQK=1` (production), dense Q8_0 prefill goes to `iqk_mul_mat`. Each thread takes one
  contiguous band of weight rows (`iqk_mul_mat.cpp:692-696 @ 98ff8a4`). Inside it, `mul_mat_NxM` steps
  64 rows of x and sweeps **all** Ny columns before moving on (`iqk_mul_mat.cpp:81-110`). Each weight row
  is read from DRAM once, and the activations are re-read from cache. The PR's goal is **already present**.
- Exception: when `npt = Nx/nth ≤ 16` and Ny ≥ 16, threads split Ny into halves, so each x band is read by
  two threads, `ith` and `ith+nth/2` (`iqk_mul_mat.cpp:667-686`). Under NPS4 those two threads can sit on
  different nodes. This only applies to small-row tensors at prefill. It is unmeasured.
- Non-iqk fallback: on NUMA the chunk plan splits by thread along the larger dimension
  (`ggml-cpu.c:1323-1327`). Inside a chunk the loop is iir1 outer, iir0 inner, in 16x16 blocks
  (`ggml-cpu.c:1374-1384`). So a thread re-sweeps its whole x band once per 16 columns. Its band is about
  `rows/nth` x row bytes, roughly 1 MB for 17408/96 rows at K=5120 Q8_0, so the re-reads come from L2/L3
  (32 MB per CCD), not DRAM. Same question as the PR, bounded by cache. Only reached when iqk declines.

## Principles table

| Principle | Source evidence | MI210 (gfx90a) verdict | EPYC Zen 5 verdict | Why (mechanism) | Port cost |
|---|---|---|---|---|---|
| (a) Walk column tiles outermost within a stream-k block, so blocks sharing x row bands run at once | s01 Overview; s01d `mmq_get_tile_indices` | DOES-NOT-TRANSFER on served shapes (M=36: ntx=1, identity map; ub256/512 Q8_0 on rocBLAS). TRANSFERS-WITH-CHANGES if MMQ ever serves n > 64 dense | ALREADY-PRESENT (iqk is x-stationary) | Reuse needs ≥ 2 column tiles per band and more tiles than blocks; the CDNA routing removes the wide-n case | Small: drop the NVIDIA / J==128 gates, instantiate J=64 on CDNA, keep the fixup decode in step |
| (b) Order as a compile-time template, not a runtime branch (reported −8%) | s01 body; reviewer exchange | UNKNOWN-NEEDS-PROBE (moot today). A kernel-arg-uniform branch is a scalar branch on CDNA, but the 512-thread occupancy-1 MMQ cell is register-tight | DOES-NOT-TRANSFER (iqk decides partition once per thread, no per-tile decode) | The cost is in the hot per-tile index decode and register allocation | One extra template instance per (type, J=64) |
| (c) Only matters when tiles > blocks; RTX PRO 6000 (188 SMs) saw nothing | s01 GB10 vs RTX PRO tables | Partly holds: the 104-block grid is fixed and never tiled, so wide shapes always qualify. At M=36 only the 17408-row tensors exceed 104, and ntx=1 there | n/a (thread count ≪ chunks; iqk uses a static band split) | Tile/block ratio and ntx together decide the reuse distance | None (analysis) |
| (d) Stream-K K-phase skew blocks cross-CTA reuse; DP+SK hybrid aligns | x01 §5.2 | ALREADY tested: the SK2 force-tiling arm was CLOSE. Under a JIWZ port, 104 % ntx == 0 for ntx 4/8 gives aligned sharers anyway | n/a | Sharers must touch the same K chunk at about the same time | None |
| (e) A single stream-k config can replace ensembles | x01 §1/§6 | DOES-NOT-TRANSFER for gfx90a prefill: rocBLAS beats int8 MMQ (AK-ASM-H4 0.48x) | n/a | CDNA2 MMQ is far from MFMA peak; vendor GEMM wins at large n | n/a |

## Adversarial pass

- WebSearch (2 queries) found no independent reproduction of PR #32921 and nothing contradicting it.
  The PR was too new to be indexed.
- One search summary *restates* that upstream PR #14624 enabled MMQ MFMA stream-k only on CDNA3 "as it
  fails to outperform blas" on other CDNA devices. That is a restatement, but it matches the CDNA2
  routing in `mmq.cu:346-362`.
- HipKittens (arXiv 2511.08083, a search result) reports that optimizing L2 hit rate alone degraded
  last-level cache and overall bandwidth on CDNA4. This restates our own hard constraint; it is not a
  test of #32921.
- Against the PR itself:
  - its 27B files are synthetic requants;
  - its KLD was measured on a different (broader) version;
  - the 8% runtime-branch figure has no data in the thread;
  - all data is on NVIDIA, 48 or 188 SMs.

## Derived-actionables ledger

| ID | Action | Owner guess | Disposition | Reason |
|---|---|---|---|---|
| KS-K1-streamk-order-1 | File the dense-27B tile census (table above: tiles and ntx at M=36, plus routing) under AK-MMQ-SK2 step 2, which closes that box's remaining gap | handoffs/active/autokernel-loop.md (AK-MMQ-SK2) | immediate | The box is open only for the missing census; this dive computed the dense part from code |
| KS-K1-streamk-order-2 | Knowledge note: PR #32921 is a no-op on served gfx90a MMQ (ntx=1 at M=36; Q8_0 n > 128 on rocBLAS; J==128 never on CDNA) | handoffs/active/autokernel-loop.md (next to the K2 knowledge note) | knowledge-only | Stops a future session from porting it for 27B verify |
| KS-K1-streamk-order-3 | If Q8_0 prefill ever routes to MMQ on gfx90a (FORCE_MMQ, a new int8 MMQ, routing change), port the column-outer order with a J=64 CDNA gate as the first cheap lever, with a wall-clock veto | handoffs/active/rocm-kernel-authoring.md | monitor | The byte model predicts ntx-fold weight re-reads under the current order; no served shape exercises it today |
| KS-K1-streamk-order-4 | CPU: the iqk npt ≤ 16 Ny-split reads each small-tensor x band from two threads that may be on different NUMA nodes | handoffs/active/cpu-decode-roofline-program.md | knowledge-only | Prefill-only, small tensors; no evidence it costs anything |

## Dive-surfaced sources

| Id | Title as printed | Settles | Recommend |
|---|---|---|---|
| tetherto#586 (tetherto/qvac-fabric-llm.cpp#586) | original change by Pratik Narola | The broader-reordering version and its unspecified regression | decline: mechanism null on our served shapes |
| arXiv 2511.08083 | HipKittens: Fast and Furious AMD Kernels | Whether L2-hit-rate tile ordering is a sound objective on CDNA | decline for this dive (CDNA4 chiplet L2; our constraint already holds) |
