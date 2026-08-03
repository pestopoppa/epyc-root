# Handoff: MI210 single-stream roofline — Q8 dequant-GEMV kernel + batch-1 latency levers

**Status**: OPEN — kernel-authoring task (llama.cpp-experimental). **Created**: 2026-07-04 (Fable5 window-2 MI210 campaign follow-on).
**Owner tree**: `/mnt/raid0/llm/llama.cpp-experimental` (branch `upstream-mtp-verify`; kernel work goes here, NEVER production-consolidated-v6). HIP build `build-hip/`, `export LD_LIBRARY_PATH=<bin>:/opt/rocm/lib; export HIP_VISIBLE_DEVICES=0`.
**Substrate**: MI210 gfx90a/CDNA2, 64 GB HBM2e, ~1.64 TB/s peak, ROCm 6.2. All numbers OBSERVATION (no P-GPU-1).
**Context doc**: `handoffs/active/fable5-window2-findings-05b-mi210-inference-architecture.md` §1/§9.

## UPDATE 2026-07-04 — measured results REFRAME this handoff (Tier-1 premise is WRONG; async-prefetch is the lever)

Kernel-thread `a8afd338` executed the levers below. Corrections, most important first:

1. **Tier-1 lever 2 (fused dequant-in-GEMV) is a NON-TASK.** The Q8_0 GEMV is ALREADY int8-native — `vec_dot_q8_0_q8_1` (`vecdotq.cuh:797`) uses `ggml_cuda_dp4a` integer MAC + one fp scale per 32-block, i.e. the CPU iqk "dequant-under-load" pattern is already implemented on GPU. There is **no per-element fp dequant to hide.** The **47→62% gap is achieved-bandwidth / occupancy, NOT dequant-compute.** Do not port iqk to "hide dequant" — there is nothing to hide.
2. **The real lever is Tier-2 lever 3 (async weight-prefetch / memory-level-parallelism).** Down-payment already LANDED: **nwarps 2→4 for batch-1 Q8_0 on CDNA2 = +4.6% (28.99→30.32 t/s)**, `test-backend-ops MUL_MAT` 1103/1103, committed **`5dc116130`** (fork `upstream-mtp-verify`). Async prefetch (`raw.buffer.load.lds` LDS double-buffer) is now in build+measure — exact gfx90a intrinsic design in [mi210-batch1-latency-wall-greenfield.md](../completed/mi210-batch1-latency-wall-greenfield.md).
3. **Tier-1 lever 1 (`quantize_q8_1` requant) = DEFER.** Measured **3.37%** of decode (this build; 5.68% on the older mi210-hip build). Every GEMV re-quantizes its own activation (call-count == `mul_mat_vec_q` count); localized prologue-fusion is *counterproductive* (would requant the activation `gridDim.x`≈thousands of times). Only fix is graph-level (q/k/v activation caching, or fuse into the preceding RMSNorm), ceiling ~1.5–3% with correctness risk on the 82%-of-decode hot path → not worth it now.
4. **Tier-3 lever 6 (n-gram / prompt-lookup GPU spec) = MEASURED NEGATIVE.** All variants regress on the 27B: plain 28.4 → ngram-simple 27.7 (best) → ngram-cache 26.1 (worst); context-only acceptance **~15%**, below break-even. A zero-cost n-gram does NOT beat plain single-stream here — a real trained drafter (draft-mtp/eagle3) remains the path. (Corpus-static ngram, CPL-4b, is separate but must clear a HIGH acceptance bar to beat this negative.)
5. **rocprof note**: v1 aborts at init on this build (PDL/graph kernels) — use **rocprofv2** with the `pmc:` prefix, and add `/usr/lib/x86_64-linux-gnu` to `LD_LIBRARY_PATH` (`libpciaccess.so.0`).

Net: the Tier-1 dequant framing is superseded. The live single-stream track is **nwarps (done +4.6%) → async-prefetch → SoA-repack**, toward the fp16 62% ceiling. Levers below are kept for the record; read them through this update.

## L3-MoE / L15 quantized-MMQ bet — scope said GO, **BUILD FALSIFIED IT: L3-MoE occupancy rewrite = NO-GO** (2026-07-04)

**Phase-1 result (measure/build-first worked as intended):** the compact-LDS rewrite was BUILT + gated + correct — LDS halved 49→25 KB, LDS-limited residency 1→2 WG/CU, accumulator untouched; `MUL_MAT 1103/1103`, `MUL_MAT_ID 789/789`, PPL indistinguishable — but occupancy stayed **FLAT (3.07→3.07)** and aggregate moved **+1.6% B=32 / −12% B=64**. **The Phase-0 LDS-limit premise is FALSIFIED with data:** at B=32 Q8-MMQ is **grid-limited** (grid = 53248/512 = exactly 104 WGs = 1 WG/CU → no second workgroup to place in the freed LDS), NOT LDS-limited. bf16's aggregate win is its **native-MFMA / zero-dequant compute**, not an occupancy edge Q8 could match by freeing LDS. Raising Q8-MMQ aggregate needs MORE workgroups → **stream-K K-splitting** (a bigger separate bet w/ fixup-kernel overhead; the gated compact-LDS kernel is the ready substrate, saved `campaign/mmq-compact-lds-NEGATIVE.patch`) — or smaller `mmq_y` (forbidden: halves the accumulator; campaign already measured mmid-forcing negative). **Settled: bf16-for-aggregate (B≥16–24), Q8 only for HBM-capacity.** **L15 (sub-4-bit capacity unlock) is INDEPENDENT of this occupancy result and still viable.** The optimistic scope below is kept for the record — read it through this result.

The aggregate-MoE #1 kernel lever, scoped + de-risked into a fundable GO with a concrete mechanism + a measured target.
- **Mechanism (de-risked):** Q8 `mul_mat_q`'s occupancy limiter is the **dequant-staging LDS (45–49 KB > half of 64 KB) + Arch-VGPR (128)**, which caps residency at exactly **1 WG/CU** (grid = 104 WGs) → ~2.5 waves resident → memory unit under-driven at **32%** vs bf16's 48% (the 1.5× maps onto the measured +32% gap). **NOT the MFMA accumulator tile** — bf16 wins with the SAME ~128 Acc-VGPR, just smaller LDS (12.8–25.6 KB) + tiny Arch-VGPR (16). So the "shrink the MFMA tile / lose efficiency" risk is OFF the table; the lever is halving the **staging** footprint only.
- **Target** = bf16's own measured profile: LDS 49→~24 KB, Arch-VGPR 128→~64 → **2 WG/CU** → MemUnitBusy 32→~48% → occ 2.55→~3.2. **Payoff: Q8 aggregate B=32 from 563 t/s toward bf16's 744 — Q8 aggregate-competitive at HALF the HBM.** Residual: at B=128 bf16 also wins on native-MFMA FLOPs, so occupancy alone won't fully erase the top-end; "competitive at half HBM" is the residency-bet goal + achievable. Risk = more dequant recompute / less N-reuse if staging cut too far.
- **L15 sub-4-bit — path ALREADY EXISTS + numerically correct on CDNA2** (not MMVQ-only): IQ2_XXS/XS/S, IQ3, IQ1, Q2_K, Q3_K all MMQ-supported (`mmq.cu:267`) with MFMA tile mappings; CDNA2 gate routes them to MMQ when `n_experts>64 OR ne11≤128`. Live-confirmed (HEAD 7c28056b7): `MUL_MAT 1103/1103` + **`MUL_MAT_ID 789/789, 0 FAIL`** across q8_0/q2_K/iq2/iq3/iq1/iq4. **Missing = a quantized GGUF + the SAME occupancy rewrite** (IQ codebook dequant is MORE LDS-hungry → needs it more than Q8). **Capacity: Qwen3.5-122B-A10B @ IQ2 ≈ 38 GB FITS → fully GPU-resident (the big residency-bet unlock); GLM-5.2 ~238 GB does NOT fit** even at IQ2. **STATUS 2026-07-04: Qwen3.5-122B-A10B UD-IQ2_M (40.4 GB, unsloth) is DOWNLOADING** (in flight ~11%+; obviates the "quantize an IQ2 proxy" step in the build sequence) → on completion, measure PPL + aggregate vs the existing UD-Q4_K_M benchmarks. L15 measurement PENDING.
- **Shared kernel family (one investment, two payoffs):** `mul_mat_q_case<TYPE>` → single `mul_mat_q` device kernel; the LDS-staging/accumulator/occupancy body is SHARED, only `load_tiles` (per-type dequant) differs. **L3-MoE (the shared-body rewrite) is the prerequisite for L15 being fast.**
- **Build sequence:** Phase 0 (sub-4-bit MMQ correctness ✅; remaining = quantize an IQ2 proxy + operator-gated IQ2-vs-Q8 bench) → **Phase 1 (shared LDS-staging/occupancy rewrite, IN PROGRESS)** → Phase 2 (apply to IQ2/IQ3 + retune codebook dequant + quantize 122B→IQ2).
- **Key files:** `ggml/src/ggml-cuda/mmq.cu` (267–340), `mmq.cuh` (MMA tile map 239–264, LDS `MMQ_MMA_TILE_X_K_*` 219–225). Prior CSVs: `campaign/moe-agg/prof/pmc_{q8,bf16}/`.

## UPDATE 2026-08-03 — the gap is ONE handoff but TWO mechanisms; splitting them (research-intake Stage-2b)

_Via `/research-intake` Stage-2b dive 2b-C. This **refines** the 2026-07-04 update above, it does not
contradict it — the recomputed ladder reproduces the existing fable5 series to within 1 pp._

**The full quant ladder, recomputed on one consistent GiB basis** (spec-BW denominator; see the calibration
caveat below), with `mul_mat_vec_q` measured at **77.8% of decode time**:

| Rung | Bandwidth attainment |
|---|---|
| fp16 (llama.cpp) | **62.6%** |
| fp16 (vLLM-ROCm, same device) | **69.2%** |
| Q8_0 | 50.2% |
| Q4_K | 35.1% |
| MoE-bf16 | 34.4% |
| MoE-Q8 (frontdoor) | 21.3% |
| **MoE-IQ2 (architect, `Qwen3.5-122B-A10B UD-IQ2_M`)** | **10.3%** |
| Qwen3-Next-80B i1-IQ2 | 3.3% |

**The reading that matters: 62–69% is already reached on this device, so the memory system is not the
limiter.** The collapse is entirely down the quant ladder. For reference, DGX Spark GB10 reaches **77–80%
at Q4_K_M dense across five models** on the same engine — NVIDIA's quant sag is 5–10 pp; ours is 27 pp.

**Why this handoff now carries two items instead of one.** The 2026-07-04 update's finding —
*"the 47→62% gap is achieved-bandwidth / occupancy, NOT dequant-compute. Do not port iqk to hide dequant"* —
is **correct, and it is correct for Q8_0**, whose GEMV is already int8-native. But **Q4_K 35→50 is a
different mechanism** (k-quant superblock unpack, not occupancy), and treating the two as one gap has
already produced one wrong verdict. They are filed separately in the checklist below.

**Corrected IQ2_XXS characterization** (verified read-only against our tree, supersedes the
"four *dependent* random reads plus *a* sign-table read" framing): per 32 quantized weights there are
**four INDEPENDENT data-dependent gathers** into a 256-entry / 2 KiB grid — all four indices arrive in a
**single 8-byte `memcpy`** (`ggml-quants.c:2500`), so no address depends on another lookup's result, ILP ≈ 4,
**not a pointer chase** — plus **FOUR** sign-table gathers (`ksigns_iq2xs[…]` is inside the `l` loop), each
grid entry expanding to 8 values. The 4+4 ratio holds across every SIMD path including our production iqk
(`iqk_gemm_iquants.cpp:176-181`, signs `:86-90`), AVX2, and CUDA.

**Calibration — MEASURED 2026-08-03, and the correction is smaller than estimated.**
`epyc-inference-research` `328b768d`, receipt
`data/mi210-achievable-bandwidth/20260803T124401Z/receipt.json`
(SHA-256 `0aab9c7e135929e72fd3a5c2498eb807dc16d0f80b773f063e1df3524df7b4d3`).

**Achievable = 1433.3 GB/s, i.e. 87.5% of the 1638 GB/s datasheet peak** — high for HBM2e. Triad 1371.1;
per-kernel medians copy 1412.5 / mul 1413.9 / add 1362.3 / triad 1362.1, p20–p80 within ~1.2%; 10 warmup,
50 timed, correctness PASS (max abs err 0.0). **Correction factor 1.143×, not the 1.17–1.26× estimated
here before the run — the prior ~1.3–1.4 TB/s guess was low.**

| Rung | % of spec (1638) | % of **achievable** (1433.3) |
|---|---|---|
| fp16 | 62.6 | **71.5** |
| fp16, vLLM-ROCm | 69.2 | **79.1** |
| Q8_0 | 50.2 | 57.4 |
| Q4_K | 35.1 | 40.1 |
| MoE-bf16 | 34.4 | 39.3 |
| MoE-Q8 (frontdoor) | 21.3 | 24.3 |
| **MoE-IQ2 (architect)** | **10.3** | **11.8** |
| Qwen3-Next-80B i1-IQ2 | 3.3 | 3.8 |

**⚠ THE BASIS WARNING, and it is the most important line on this page.** Converting *our* numbers to an
achievable basis while leaving *someone else's* on a spec basis makes the gap look smaller without it
being smaller. **The AMD-vs-NVIDIA comparison must stay spec-to-spec** — our fp16 62.6 against DGX Spark
GB10's 77–80, both against datasheet — **until somebody measures GB10's achievable bandwidth.** Our
71.5%-of-achievable set beside their 77–80%-of-spec is a mixed-basis comparison and is not a reading.
This measurement makes our own numbers physically meaningful; **it does not narrow the NVIDIA gap at all.**
That is precisely the error found this session in AMD's own KB, where a per-OAM TFLOPS figure was divided
by a per-GCD bandwidth to give a ridge point off by 2×.

Use the **achievable** column for headroom and campaign sizing (it is the real roof); use the **spec**
column for any cross-vendor comparison, and say which one you used — a utilisation quoted without its
denominator is not a number.

**Free incidental finding in our own CPU tree, filed here because it is the same IQ2 sign path:**
`iqk_gemm_iquants.cpp` contains an AVX512-VPOPCNTDQ routine deriving IQ2 signs arithmetically with **zero
table reads**, but its dispatch at `:184` is guarded by `#if defined z_HAVE_FANCY_SIMD && …`. **The `z_`
prefix makes the macro undefinable, so the branch is permanently dead** (same at `:109`, `:571`) and the
table lookup always runs — **including on our Zen 5 host, which has VPOPCNTDQ.** Inherited verbatim from
ik_llama.cpp via `fec061dea`; not introduced by us. Experimental branch only — production is frozen.

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

## Progress checklist

- [x] nwarps 2->4 (+4.6%, committed 5dc116130) ✅
- [x] async weight-prefetch raw.buffer.load.lds (+3.3%, committed 7c28056b7) ✅
- [x] L3-MoE compact-LDS occupancy rewrite (BUILT + FALSIFIED, NO-GO) ✅
- [x] L15 sub-4-bit: quantize 122B->IQ2 proxy + operator-gated IQ2-vs-Q8 bench ✅ **2026-07-29 — the "PENDING" predates the run.**
  Both halves landed 2026-07-05: 122B UD-IQ2_M GPU-resident at 43.7 t/s single / 148.7 agg @B32, PPL 5.02
  (`progress/2026-07/2026-07-05-mi210-capability-kernel-rnd.md:23-24`), and the IQ2-vs-Q4 paired eval returned Δ0.0pp,
  McNemar p=1.000 (`progress/2026-07/2026-07-05-mi210-residency-and-cot-reframe.md:12`). Certified by read-certification (`auditor`).
- [ ] SoA-repack lever (only if coalescing measured poor - currently deemed healthy)
- [ ] Optional stream-K K-splitting for Q8-MMQ aggregate (separate bet)
- [x] Recompute the full quant ladder on one consistent basis (fp16 62.6 / Q8_0 50.2 / Q4_K 35.1 / MoE-Q8 21.3 / MoE-IQ2 10.3) ✅ 2026-08-03 — via /research-intake Stage-2b; reproduces the fable5 series to within 1 pp
- [x] Correct the IQ2_XXS access characterization: four INDEPENDENT gathers (single 8-byte memcpy, ILP≈4) plus FOUR sign-table gathers, not a dependent pointer chase with one sign read ✅ 2026-08-03
- [ ] **Item A — Q8_0 50→62 rung (achieved-bandwidth / occupancy).** The 2026-07-04 finding stands: no per-element fp dequant to hide. Continue on the async-prefetch/MLP track; do NOT reopen an iqk port for this rung
- [ ] **Item B — Q4_K 35→50 rung (k-quant superblock unpack).** A DIFFERENT mechanism from item A and the largest single banded win available (+38–43%, high confidence). Decisive first measurement: per-op wall share of superblock unpack inside `mul_mat_vec_q` at Q4_K vs Q8_0 on the same model, before any kernel is authored
- [ ] **Item C — architect MoE-IQ2 at 10.3%**, our worst rung by 2× and a production-serving model. Attach the kill-criterion first (below) — this is a probe, not yet a funded kernel
- [ ] Kill-criterion probe for item C: on gfx906 an optimised community fork **and** vLLM independently converge on ~10% bandwidth for MoE batch-1 — the same rung as ours. Two stacks hitting one wall means this may be an **architectural floor**; establish cheaply whether it is before funding a kernel
- [ ] Investigate the permanently-dead `z_HAVE_FANCY_SIMD` AVX512-VPOPCNTDQ IQ2 sign path on an EXPERIMENTAL branch only (production kernel is frozen; this is a CPU-side finding filed here for mechanism adjacency)
