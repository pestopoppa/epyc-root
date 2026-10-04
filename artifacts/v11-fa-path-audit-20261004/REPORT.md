# v11 FlashAttention path audit: losing rocWMMA FA on gfx90a (MI210)

2026-10-04. Read-only audit: no builds, no GPU or CPU workloads, and no tree modified. The one piece of binary analysis was reading the gfx90a code-object metadata already shipped in the production `libggml-hip.so`, using `llvm-readelf --notes`. Saved by the coordinating session from the audit subagent's hand-back; the subagent's tool could not write files.

**Sources:**
- v10 tree `/mnt/raid0/llm/llama.cpp` @ `ffc1bac82`, read with `git show`/`git diff` only.
- `origin/master` @ `1537a0a8b` (2026-10-03), already fetched in that clone.
- The KVU-19a fold record, and the KVU-19b `FOLD.md`/`PROVENANCE.md`.
- The live `gpu_slot2.sh` run directory.
- `wiki/hardware-optimization.md` and the DFlash2 handoff.
- `gh` against ggml-org/llama.cpp.

**Model shape throughout:** Qwen3.8-27B attention, D=256, 24 Q heads and 4 KV heads. That is GQA 6, so `gqa_ratio_eff = 2`. KV is q8_0 with `--kv-unified`.

## Summary

**Upstream does not move most of our verify path to MMA; it moves it to TILE.** On upstream master, gfx90a sends D=256 to MMA only above 32 query rows for our GQA-6 model. Decode stays on vec. Everything from 3 to 32 rows goes to TILE, which uses no matrix cores. That covers 1–3-slot DFlash2 verify and batched decode. 4-slot verify (36 rows) and prefill go to MMA `<256,256,32,2>`. Our v10 compile of that kernel spills 314 VGPRs (the rocWMMA kernel spills none).

**Upstream evidence:**
- On RDNA4 the same rocWMMA→TILE swap lost about 2× (#26220).
- No gfx90a FA numbers exist upstream. CDNA tuning was done on gfx908 (MI100).

**Correctness risk.** Our DF2-9 record says the non-rocWMMA path on gfx90a gave all-NaN DFlash target features at about 2k-token prompts. It was never root-caused, and v11 runs exactly that path.

**Ports:**
- KVU-19a: only the WMMA hunk is lost; the rest needs a medium rebase.
- 19b commit 1: ports as-is, and matters more on v11.
- 19b commit 2: WMMA-only; the live slot shows it 13–21% slower on aligned verify and breaking its own exactness rule. Hold it.

**Recommendation:**
1. Fold 19a and 19b commit 1 now.
2. Before rebasing, A/B a ROCWMMA=OFF build of the champion, which reproduces v11 routing. Gate on DF2-9.
3. Carry rocWMMA in v11 as an in-binary A/B arm (about 1–2 days).
4. Port #29510 to CDNA if it merges.

## 0. Findings up front

1. **"CDNA now uses MMA" is only half true for our shapes.**
   - Upstream master sends D=256 to MMA on gfx90a only when `ne[1]·gqa_ratio_eff > 64`, i.e. more than 32 query rows.
   - Decode (1–2 rows) stays on vec.
   - **3–32 rows go to the generic TILE kernel, which uses no matrix cores.** That covers 1-slot DFlash2 verify (9 rows), 2–3-slot verify and 4×1 batched decode. All of these run on rocWMMA, i.e. MFMA, in v10.
   - Only 4-slot verify (36 rows), mixed ubatches and prefill land on MMA.
2. **The closest upstream analog is a 2× loss.**
   - #26220: on RDNA4, D=256 moved from rocWMMA to TILE after #26046, and pp4096 at depth 127k fell from 777 to 395 t/s (−49%).
   - CDNA was declared unaffected only because MMA covers D=256 at large batch. Nobody checked the ≤32-row TILE band on CDNA.
   - No gfx90a FA numbers exist upstream. The CDNA FA tuning (#28576, #28907) was done on gfx908 (MI100).
3. **The MMA config v11 would use for our prefill spills heavily on gfx90a.**
   - The kernel is `flash_attn_ext_f16<256,256,32,2>`, as compiled by ROCm 6.2 into the v10 library.
   - Register use: 256 VGPR, 0 AGPR, **314 VGPRs spilled, 1040 B scratch per lane**.
   - Cause: the 512-thread, 64-column config means 2 waves per SIMD, and gfx90a's unified register file then caps each wave at 256 registers.
   - The rocWMMA kernel v10 actually runs (`<256,16,4,64,float>`) uses 192 VGPRs with 0 spills.
   - #28576 (fp32 VKQ accumulators on MFMA) is inherited by v11 and adds register pressure.
4. **v11 runs a path our records already show producing NaNs.**
   - DF2-9 / CH-8 (2026-08-27): with ROCWMMA OFF, all 12 olympiadbench prompts failed with `3020800/3020800 non-finite target features`. A 25-character prompt passed on the same binary.
   - The root cause was never localized. Prompt length is the discriminator, which fits the >32-row MMA route: a short prompt's prefill goes to TILE, while a ~2k prompt is split into 512-row ubatches that go to MMA.
   - `test-backend-ops` passed on that binary, so it cannot serve as the gate.
   - v10 also carries a local guard (`99f3fffd6`) that routes D=256 MFMA-MMA to TILE when the KV is unpadded, because `test-backend-ops` failed there.
5. **How our patches carry over:**
   - **KVU-19a** ports in principle. Its tile and MMA hunks already exist (MMA skip works on AMD since `nstages≤1`); only its WMMA hunk dies.
   - **19b commit 1** routes one-row-per-sequence batches to vec. It does not depend on any kernel and matters more on v11, where 4×1 decode would otherwise land on TILE.
   - **19b commit 2** (sequence-aligned tiles) works only in WMMA.
   - Live slot2 data for commit 2 so far: aligned 4×8 verify is 13–21% slower in round 1, and 6 of 119 cases break its own "skip on ≡ skip off" exactness claim. Do not port it as it stands.
6. **Recommendation:**
   - Measure the WMMA→TILE/MMA delta before the rebase. A ROCWMMA=OFF build of the champion source reproduces upstream's D=256 routing exactly.
   - Carry rocWMMA FA into the v11 candidate as an in-binary A/B arm.
   - Gate v11 on the DF2-9 reproducer.
   - Fold 19a and 19b commit 1 now and re-port them at the rebase. Hold 19b commit 2.
   - Treat #29510 `kv_rows` as the MMA-side successor.

## 1. What #26046 changed, and who serves which shape

**#26046** (JohannesGaessler, merged 2026-07-24 as `fa72aeccb` after one day of review):
- It is a pure deletion (−798/+5) of:
  - `fattn-wmma-f16.{cu,cuh}`;
  - the `GGML_HIP_ROCWMMA_FATTN` CMake and `hip.h` plumbing;
  - the WMMA dispatch branch;
  - the tile kernel's `GGML_USE_WMMA_FATTN` skip-list.
- The body says only that the kernel "is now obsolete as all relevant AMD hardware can use the better kernel in fattn-mma-f16.cuh". It has no benchmarks.
- After merge there was one regression report (#26220, RDNA4) and one note that the removal fixed a gfx1100 crash.
- `fa72aeccb` is NOT in v10, whose merge base is `a8dc0e326` (2026-07-16).

**Dispatch for D=256, q8_0, gfx90a, GQA 6, KV padded to 256:**
- v10 has `ROCWMMA_FATTN=ON` with rocWMMA 1.5.0; the CDNA gate requires a version other than 2.0.0, which holds.
- v11 is upstream `ggml_cuda_get_best_fattn_kernel`.

| Workload (unified KV) | `ne[1]` | v10 | v11 upstream | v11 + 19b commit 1 |
|---|---|---|---|---|
| decode, 1 slot | 1 | vec (native q8_0) | vec | vec |
| 2-row verify | 2 | vec | vec | vec |
| batched decode, 4 slots | 4 | WMMA (q8_0→f16 convert) | TILE (convert) | vec, one row per block (native q8_0) |
| DFlash2 verify, 1 slot (n_max 8 → 9 rows) | 9 | WMMA | TILE `<8..16, ncols2=2>` | TILE |
| verify, 2–3 slots | 18–27 | WMMA | TILE | TILE |
| verify, 4 slots | 36 | WMMA | MMA `<256,256,32,2>` | MMA |
| prefill / mixed ubatch | 33–512 | WMMA `<256,16,4,64,float>` | MMA `<256,256,32,2>` | MMA |
| non-unified streams, 8 rows | 8 | WMMA | TILE | TILE |

Notes on the table:
- **v10 runs one kernel for everything above 2 rows.** With prec=F32, which llama always sets, rocWMMA uses `cols_per_block=16` with float KQ accumulation.
- **MMA needs at least 16 columns at D=256.** Upstream's MFMA threshold at D≤256 is 64 effective columns. Below 16 columns (MFMA guard in `fattn-mma-f16.cuh`), the `<256,256,8,*>` configs exist but are rejected.
- **No v10 binary can measure TILE.** The v10 binary contains no D=256 GQA tile kernels: every `flash_attn_tile<256,256,*,ncols2>1>` is a `NO_DEVICE_CODE` stub (37 VGPR, 0 LDS) because of the WMMA skip-list. Measuring TILE needs a ROCWMMA=OFF build.
- **The K/V conversion is unchanged.** TILE and MMA set `need_f16_K/V=true`, as WMMA did. Only vec reads q8_0 natively. 19a's dead-block conversion skip therefore stays relevant, and 19b commit 1 is the only conversion-free path.

**Upstream numbers that exist:**
- #19806 (MI300X): pp512 +7.3%, pp4096 +39.4% vs no-FA; tg −9.7%.
- #28576 (gfx908, 190 W): fp32 VKQ gives +12–24% on MMA shapes. The D=256 q8_0 nb=512 case went from 29.2 to 32.7 TFLOPS, and one config had to be retuned for VGPR pressure.
- #28907 (gfx908) contains our exact shape, `hsk=256 nh=4 nr23=[6,1]`: 23.8–26.1 TFLOPS at nb=512 for kv 4k–128k, and 1.6–3.0 TFLOPS at nb=1.
- None of these is gfx90a.
- Searches for MI210, MI250 and gfx90a FA regressions found nothing. That is an absence of reports, not proof of parity.
- Upstream HIP CI is on ROCm 7.x (#25775).

**Other upstream FA changes v11 inherits:**
- b74f590ea #27870: fixes a divergent barrier in the MMA combine when np>1. All AMD D=256 MMA configs have np=2.
- bfdc32183 #28576: fp32 VKQ accumulation on MFMA.
- e4b9af007 #25635: XOR-swizzled shared-memory tiles.
- Sparse-FA #27970/#28770/#29298: NVIDIA-only; aborts on HIP.
- 2ebd9ae62/c2a9e1606: MMA for DKQ>256 on CDNA.
- f11d642a2 #29572: a CDNA dispatch leak at D=576.
- d028c697b #29231: fp8 needs ROCm≥6.3. This absorbs our `0ebf1b4d7`.
- e79e4bf66 #26696 and 91f8c9c5f #25495: these absorb our fast-math commits `b861c32fa` and `78f0f1b10`.
- #21519 (2026-04-07): fixed the CDNA2 compute-capability constant (0x910 → 0x90a).

## 2. Our local investments in the WMMA path

Local FA-touching commits come from `git log a8dc0e326..HEAD -- fattn* hip.h ggml-hip/`, plus the KVU-19 branches.

| Item | In WMMA? | v11 action | Effort | Better host? |
|---|---|---|---|---|
| `db18f3937` eight-wave VKQ: CDNA2, D=128, ≤8 rows, 8 warps (+6.08% dec-b4) | entirely | Dies with WMMA. Affects only D=128 GPU models, never the 27B. Re-search on TILE/MMA via AutoKernel. | S | unknown |
| `5582ebccf`, `5e323013a` vec launch tuning (+2.0%, +1.6% tg128) | no | Port. Upstream `launch_fattn` gained `use_sparse`, the swizzle and a stream-k fixup rewrite, so expect conflicts. | S–M | n/a |
| `99f3fffd6` HIP FA coverage fix | no | The D=320 part is absorbed upstream. **Keep the "D=256 unpadded KV → TILE" guard** until v11 `test-backend-ops` on ROCm0 proves MMA D=256 unpadded is correct. | S | — |
| `0ebf1b4d7` fp8 guard; `b861c32fa`/`78f0f1b10` fast-math | no | Drop; upstream has them. | 0 | — |
| **KVU-19a** `ac97e305a` (+ CPU `a0d0ae238`): liveness scan, skip in vec/MMA/tile/WMMA, dead-block conversion | 17 lines only | Drop the WMMA hunk. Rebase `fattn-common.cuh` (+357) and the tile/MMA/vec hunks onto #25635, #27970 and #27870. Re-run its 52 unified test cases and fa_harness. | **M** (2–4 days) | Neutral to better. MMA skip is a uniform branch and already designed in. TILE uses the loop-index form, chosen because a branch made tile D=512/576 nondeterministic. On v11, TILE becomes the hot verify path. |
| **19b commit 1** `1bceceb05`: `n_seq` hint from `ubatch.n_seqs_unq`, so rows-are-sequences batches go to vec, one row per block | no; it sits before the arch branches | Port as-is. | **S** | Better on v11. Slot2 round 1 for 4×1 kvu: 1080 µs at 16k and 5489 µs at 80k. Streams: 1117 and 5263. k19a: 1865 and 9138. Base: 1735 and 8774. |
| **19b commit 2** `c7f5ac9ad`: planner `flash_attn_plan_seq_tiles`, `tile_rows` argument; only WMMA reads it (tile and MMA mark it unused) | yes | Hold. Re-implement in TILE only if a win survives measurement. For MMA, prefer #29510. | M (TILE) / M–L (MMA) | — |

**19b commit 2 live evidence** (`slot2-20261004T044448Z`, round 1 of 3, still running at 04:56Z on a shared GPU; preliminary):

| Case | commit 2 on | k19a | seqoff | Change |
|---|---|---|---|---|
| aligned 4×8, 16k | 2535 µs | 2100 | 2175 | +17–21% (worse) |
| aligned 4×8, 80k | 11858 | 10484 | 10359 | +13–14% (worse) |
| uneven, 16k | 2540 | 2687 | — | −5% |
| uneven, 80k | 11900 | 13657 | — | −13% |

- The fold's own expectation was "4×8 aligned ≈ seqoff", so it is currently falsified.
- **Exactness.** `exact.txt` requires "on vs skipoff bit-identical", and 6 of 119 differ (cases 110/111/118/119/126/127: hs=128, nb=32/25, 4 sequences, ndiff=384, nmse ≤8.3e-10). Something in the WMMA sequence-tile path depends on `GGML_CUDA_FA_MASK_SKIP`.
- Every other check passes: 19a ≡ alloff 119/119, and every arm is within 5e-4 of CPU (worst 8.97e-5).

**Other FA-adjacent facts:**
- The tile D=512/576 kernel is codegen-sensitive on gfx90a (about 1e-4 nmse run-to-run). This is upstream code, and it affects Gemma-4 D=512 layers.
- DF2-6's 1-row vs multi-row split ("FA vec vs rocWMMA") becomes "vec vs TILE/MMA" on v11.
- The wiki ruling CH-8 makes rocWMMA ON the house standard (`wiki/hardware-optimization.md:4724-4752`).

## 3. Opportunities

1. **MFMA tiles for prefill: probably a win, once the gfx90a config is fixed.**
   - MMA beats rocWMMA's single 16-column, 4-warp tile with 32/64-column tiles, stream-k and fp32 VKQ (+12–24% on gfx908).
   - But the 64-column D=256 config (512 threads) spills on gfx90a. That is structural to 2 waves per SIMD on the unified register file.
   - Inference, not measured: gfx908's separate AGPR file hid this from upstream.
   - The 32-column config `<256,256,16,2>` fits: 499 registers including 243 AGPR, 0 spills.
   - A two-line local change may be the cheapest v11 prefill lever: cap D=256 at `ncols1=16` on CDNA2, or give `(256,256,64)` 256 threads. Leave the choice to AutoKernel.
   - These register numbers come from our v10 compile, which predates #28576, so re-check v11's own code object.
2. **Retune the TILE/MMA crossover for gfx90a.** Upstream's 64-column threshold was tuned on gfx908, without masked-skip or q8_0 conversion. For 9–32 rows the candidates are TILE, MMA `<8|16,2>` (needs at least 8 rows) and carried WMMA. Pick by measurement.
3. **#29510 `kv_rows`** (open, updated 2026-10-03):
   - It is safe by default on HIP. An init probe (`llm_fused_op_flash_attn_kv_rows_probe`) plus a NONE return off NVIDIA means it disables itself instead of falling back to CPU.
   - Its only consumer is MMA, which on gfx90a serves exactly the >32-row shapes 19b commit 2 targeted.
   - The gather lives in `flash_attn_ext_f16_load_tile`, which also has the synchronous load branch AMD uses (no cp.async).
   - CDNA port, effort M once merged:
     - widen the `IS_NVIDIA && turing_mma_available` gate to include `amd_mfma_available`;
     - validate the synchronous gather;
     - check `use_gqa_opt` with `n_kv` taken from `kv_rows`.
   - The survey §2.4 limits still apply: no slicing for `split_simple` verify ubatches, and a fallback when cells are shared (`n_sum > n_kv`).
   - Port it as an A/B arm, not a replacement.
4. **Conversion.** It does not change in kind. The opportunity is to gather only live or `kv_rows`-referenced blocks, a small add-on to the #29510 port.
5. **rocWMMA bugs we carry: none on our pin** (ROCm 6.2, rocWMMA 1.5.0).
   - #16221 (rocWMMA 2.0.0 fakes fp16 accumulation on CDNA) and #19461/#19591 (LLVM 22 + rocWMMA 2.2) only bite on ROCm ≥7.
   - The only WMMA anomaly we carry is 19b commit 2's exactness deviation.

## 4. Risks

**4a. Performance: high probability.**
- The 9–32-row verify band moves from MFMA to vector-ALU TILE. Peak is about 45 TF for packed fp16 versus 181 TF on MFMA.
- A 9-row verify costs about 0.22 MFLOP per KV cell, i.e. 12.6 GFLOP per layer-op at 57k cells.
- v10 rocWMMA at 8 rows and 16k cells reaches only about 6.5 TF effective, conversion included (498 µs). So TILE may not lose by the full peak ratio, but #26220 shows −49% for the same swap on RDNA4.
- Prefill moves to an MMA config that spills under our compiler.
- DFlash2's +28–48% over MTP comes mostly from verify, so a verify regression lands directly on the champion's headline.

**4b. Correctness and determinism.**
- **DF2-9 (main risk).** Champion `5c278648a` (v9 lineage, before #27870 and #28576) produced all-non-finite target features at ~2k-token prompts. It was never root-caused, and v11 by construction runs that path. Ranked candidates:
  1. the D=256 MFMA-MMA route itself, which fits the length discriminator and the `99f3fffd6` guard;
  2. fp16 VKQ accumulation in the MFMA downcast path, now fp32 after #28576. Weak, since WMMA also accumulates VKQ in half;
  3. the #27870 divergent barrier. Weak on AMD, where `s_barrier` is counted rather than PC-matched.
- `test-backend-ops` cannot catch this class: its random [-1,1] inputs never overflow.
- **Never-compiled kernels.** The TILE D=256 `ncols2=2` kernels v11 will use for verify have never been compiled into any of our builds, and the tile family is codegen-sensitive on gfx90a. Prove run-to-run bit-exactness; do not assume it.
- **Numerics change on purpose.** fp32 VKQ and the WMMA→TILE/MMA swap change multi-row numerics. Greedy parity against v10 will not be bit-exact, so classify divergences as near-tie per DF2-6. The vec-vs-multi-row split remains, and DFlash2 acceptance may shift; measure it.
- **Stream-k** in MMA depends only on shape and CU count, so it is deterministic per device.
- **19a's exactness design** (skip on ≡ skip off) carries over to TILE and MMA.

**4c. HIP-graph capture: low risk.**
- Kernel choice is a pure function of ubatch shape, so graph keys behave as today.
- TILE and MMA add no host syncs. The stream-k fixup and 19a's scan are extra launches inside the graph.
- 19b commit 1 deliberately forces a re-capture when `n_seqs_unq` changes.
- The only upstream graph change since our base is `ebb546b7e` (MUL_MAT_ID), which does not touch FA.
- The known spec-dec re-capture thrash (Q4 −5% with graphs) is unchanged.

**4d. DFlash2 verify correctness.** Hard gates: DF2-9 (12/12 prompts finite) and DF2-4/6 (parity classified near-tie, acceptance within noise). The DFlash drafter's own attention shapes belong in the micro-bench.

**Can rocWMMA FA be carried in v11? Yes.**
- **What to restore:**
  - `fattn-wmma-f16.cu` (~705 lines) and `.cuh` (~51);
  - the dispatch branch and the `WMMA_F16` cases;
  - the CMake and `hip.h` flags.
- **Leave the tile skip-list out** so the same binary also carries the TILE GQA kernels for the A/B. That costs compile time and library size.
- **Adapt** the kernel to v11's `fattn_kernel_t` and `launch_fattn` signatures (sparse, `KV_live`, `tile_rows`).
- **Re-apply** `db18f3937` and 19a's WMMA hunk.
- **Cost:** about 1–2 engineer-days, plus a recurring conflict tax on a file upstream no longer tests.
- **Constraint:** it pins us to rocWMMA 1.x; moving to ROCm 7 brings the #16221/#19461 bugs back.
- **Shape:** an in-binary arm (e.g. `GGML_CUDA_FA_PREFER_WMMA` or a per-band mask), so the ONE candidate binary carries its own control, like `GGML_CUDA_FA_MASK_SKIP`. That is consistent with the full-candidate and ONE-champion rules.
- **Drop-when:** TILE/MMA is at least as fast as WMMA on every band, and DF2-9 is clean without WMMA.

## 5. Recommendation

**Order of work:**
1. **Now, on the v10-lineage champion:** once `gpu_slot2.sh` completes, fold 19a (`ac97e305a`, `a0d0ae238`) and 19b commit 1 (`1bceceb05`). Hold 19b commit 2.
2. **Before the rebase (decisive and cheap):**
   - In an experimental worktree, never the frozen tree, build the champion with `ROCWMMA_FATTN=OFF`. This exactly reproduces upstream's D=256 routing.
   - Build a second arm with `b74f590ea` (#27870) and `bfdc32183` (#28576) cherry-picked, to approximate v11's MMA kernel.
   - Run the DF2-9 reproducer and the A/B below on both arms against the ON build.
   - This decides whether v11 needs the WMMA carry, a crossover retune, an ncols cap, or nothing.
3. **Rebase:** start from fresh upstream in `llama.cpp-experimental`. Re-apply:
   - the vec AK patches;
   - the `99f3fffd6` D=256 guard;
   - 19a without its WMMA hunk;
   - 19b commit 1;
   - rocWMMA as an in-binary arm.
4. **#29510:** if it has merged, enable it on CDNA and A/B it against 19a/19b commit 1 on the KVU-18 cells and 4×80k. Drop the loser (survey Rec 4).
5. **Promote** the full candidate. Drop the WMMA arm only on evidence; otherwise carry it with an explicit drop-when.

**A/B shapes** (D=256, 4 KV heads, GQA 6, q8_0, unified KV):
- rows: 1, 2, 4×1 (rows-are-seqs), 9, 18, 27, 36, 512, and mixed 512+3×9;
- own cells {4k, 16k, 57k} × foreign cells {0, 3×~100k};
- layouts: kvu single, kvu 4-seq aligned and uneven, streams;
- D=256 with unpadded KV;
- the drafter's attention shapes.

**Arms:** WMMA, TILE, MMA with `ncols1` 8/16/32, upstream default, ±19a, ±19b commit 1.

**Instruments:**
1. `test-backend-ops -o FLASH_ATTN_EXT` perf mode with `-p` filters, reporting TFLOPS. Comparable to #28576/#28907.
2. The 19b `perf2` micro-bench (unified masks, µs/op, 3 alternating rounds).
3. A register audit of every candidate `libggml-hip.so`:
   - dump the `.hip_fatbin` section with `llvm-objcopy`;
   - split it on `__CLANG_OFFLOAD_BUNDLE__` into per-TU objects and unbundle the gfx90a target with `clang-offload-bundler`;
   - read `llvm-readelf --notes` for `.vgpr_spill_count` and `.private_segment_fixed_size`.
   - Working scripts: `split.py` and `notes.py` in the audit subagent's scratchpad `/tmp/claude-1000/-workspace/654db1ee-133c-43cc-883a-95de28742ec2/scratchpad/`. The v10 table is `fa_dm.tsv` there.
4. End to end:
   - `llama-batched-bench` npl 4, `-kvu` vs `-no-kvu`;
   - the P3 harness, where L0 must hold drafted 36.3 and no-draft 20.4 tok/s from v10;
   - the DF2-4 protocol (12 prompts, np=1, 2048 cap, alternating pairs).

**Correctness gates** (on the full candidate binary):
- `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0` passes everything, including D=256 unpadded KV. Re-run with `MASK_SKIP_MIN_KV=0` and with each FA arm forced.
- **A new FA case with large magnitudes and long KV** (|V|~30, kv≥4k) checked against the CPU reference.
- fa_harness exactness: skip on ≡ skip off, and two runs bit-identical, including TILE D=256 `ncols2=2` and MMA `<256,256,32,2>`.
- **DF2-9 reproducer: 12/12 prompts with zero non-finite values.**
- DF2-4/6 parity against v10: every divergence classified as near-tie, with acceptance and t/s reported per arm.

## Pointers

- **KVU-19a fold:** `/mnt/raid0/llm/views/epyc-root-main/docs/design/fa-masked-block-skip-20261003-fold.md`.
- **KVU-19b:**
  - worktree `/mnt/raid0/llm/llama.cpp-experimental-fa-maskskip-batched-20261004`;
  - build `/mnt/raid0/llm/kernels/builds/gpu-20261004-c7f5ac9ad/{FOLD,PROVENANCE}.md`;
  - live slot `/mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/slot2-20261004T044448Z/`.
- **DF2-9 / CH-8:** `/workspace/handoffs/active/dflash2-block-drafter-experimental-build.md:419-432,520-541` and `/workspace/wiki/hardware-optimization.md:4724-4752`.
- **Register audit source:** `/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/libggml-hip.so.0.16.0`.
- **Upstream:** #26046, #26220, #19806, #21519, #27870, #28576, #28907, #29559, #29572, #29231, #29510.
