# A10 follow-up — IQ2_XXS VGPR: compiler-only A/B (2026-09-15)

**Zero GPU time. Classification: OBSERVATION (static register allocation), not a throughput result.**
Operator-directed ("run the compiler-only VGPR A/B on IQ2_XXS"), prompted by intake-1398 and the
operator's autocompiler question. Parent artifact: `a10_iq2_vgpr_lever_20260812.md`.

## Setup

- Source: frozen v9 `0db32c06e3e550065b78311a6031ef3dd2c4f27c`, detached worktree
  `/mnt/raid0/llm/worktrees/vgpr-compiler-ab-20260915` (production branch/tree never built or modified).
- Toolchain: ROCm 6.2 hipcc, `AMD clang 18.0.0git roc-6.2.0 24292 26466ce804ac`.
- Unit: one TU, `ggml/src/ggml-cuda/mmvq.cu`, compiled with the exact house command from
  `compile_commands.json` (`-funsafe-math-optimizations -O3 --offload-arch=gfx90a`, HIP defines as the
  champion `CMakeCache.txt`: GRAPHS, NO_VMM, ROCWMMA_FATTN). ~20-28 s per compile.
- Read-out: `.hip_fatbin` → offload bundle → gfx90a ELF → AMDGPU `.note` msgpack → per-kernel
  `.vgpr_count`, `.vgpr_spill_count`, `.sgpr_count`, `.wavefront_size` (=64). Instruction mix via
  `llvm-objdump -d`, `s_nop` excluded.
- Host hygiene: pinned to core 91 (not an SMT sibling of the running autokernel CPU anchor on even cores
  0-94), `nice 19`, `ionice -c3`, strictly serial. No GPU touched.
- Scripts and raw results: `.../vgpr-compiler-ab-20260915/ab/` (`run_variant.sh`, `run_src.sh`,
  `fatbin_vgpr.py`, `note_vgpr.py`, `summarize.py`, `sizes.py`, `sweep_results.txt`,
  `sweep2_results.txt`, `pragma_*.diff`).

## Reproduction gate (passed)

The rebuilt TU reproduces the shipped `libggml-hip.so.0.16.0` table exactly: IQ2_XXS
`<1,false,false>`=63, `<1,true,false>`=**78**, `<1,false,true>`=125, `<1,true,true>`=90; at
`<_,1,true,false>` Q8_0 25, Q4_K 44, IQ1_S 42, IQ4_XS 64, IQ3_XXS 71, Q3_K 88. Instruction counts
IQ2_XXS 1001 / IQ4_XS 564 (parent: 1002 / 565 incl. one boundary op). Device ELF bytes are **not**
reproducible build-to-build; register counts are. Compare counts, never hashes.

## Method traps found (recorded so nobody repeats them)

1. `-Xarch_device -mllvm ...` is rejected by the driver ("options requiring arguments are unsupported");
   `-Xarch_device -O1/-O2/-Os` is rejected too, while `-Xarch_device -O0` is accepted.
2. Plain `-mllvm --amdgpu-...` **does** reach the device `cc1 -triple amdgcn-amd-amdhsa` (verified in
   `clang -v`), which is where AMDGPU codegen + register allocation run. The device `lld` step only links.
3. `#pragma unroll` (62 sites in `vecdotq.cuh` + `mmvq.cu`) is a **no-op** in this compiler: removing
   all of them changes no count (positive control, `out_all`). The effective per-loop control is
   `#pragma clang loop unroll(disable)`.

## Results — `mul_mat_vec_q<T,1,true,false>` VGPR unless noted (spill = 0 in every successful row)

| variant | IQ2_XXS | IQ2 `<f,f>` | IQ2 `<f,t>` | IQ2 `<t,t>` | IQ3_XXS | IQ4_XS | Q3_K | Q4_K | Q8_0 |
|---|---|---|---|---|---|---|---|---|---|
| baseline -O3 | 78 | 63 | 125 | 90 | 71 | 64 | 88 | 44 | 25 |
| -O2 | 78 | 63 | 125 | 90 | 71 | 64 | 88 | 44 | — |
| -Os | 78 | 63 | 125 | 90 | 71 | 64 | 88 | 52 | — |
| **-O1** | **54** | 64 | 39 | 67 | **57** | 48 | 80 | 48 | 36 |
| `--unroll-count=1` (global) | **41** | 33 | 33 | 39 | **42** | 40 | 53 | 44 | — |
| `--amdgpu-sdwa-peephole=false` | 70 | 62 | 125 | 82 | 67 | 63 | 88 | 42 | — |
| `--amdgpu-load-store-vectorizer=false` | 75 | 63 | 125 | 87 | 72 | 65 | 90 | 44 | — |
| `--amdgpu-disable-clustered-low-occupancy-reschedule` | 78 | 63 | 104 | 90 | 71 | 64 | 81 | 44 | — |
| `--amdgpu-enable-max-ilp-scheduling-strategy` | 95 | 80 | 140 | 146 | 93 | 64 | 92 | 44 | — |
| `--unroll-threshold=0` | 79 | 63 | 126 | 99 | 71 | 64 | 84 | 47 | — |
| **`#pragma clang loop unroll(disable)` on IQ2_XXS loop only** | **44** | 34 | 39 | 49 | 71 | 64 | 88 | 44 | 25 |
| **same pragma on IQ2_XXS + IQ3_XXS + Q3_K loops** | **44** | 34 | 39 | 49 | **44** | 64 | **96** | 44 | 25 |

**No effect (identical to baseline):** `-fno-unsafe-math-optimizations` (Q4_K 43), `-fno-slp-vectorize`,
`-fno-vectorize`, `--amdgpu-schedule-metric-bias` 0/100, `--amdgpu-disable-unclustered-high-rp-reschedule`,
`--amdgpu-igrouplp-exact-solver`, `--enable-deferred-spilling`, `--split-spill-mode` speed/size,
`--amdgpu-unroll-threshold-local=600`, `--unroll-full-max-count=0`, `--amdgpu-stress-function-calls`, and
both polarities of `opt-vgpr-liverange`, `reassign-regs`, `dce-in-ra`, `enable-pre-ra-optimizations`,
`enable-rewrite-partial-reg-uses`, `dpp-combine`, `opt-exec-mask-pre-ra`, `early-ifcvt`,
`early-inline-all`, `enable-single-use-vdst`, `scalarize-global-loads`, `use-divergent-register-indexing`,
`vgpr-index-mode`, `prealloc-sgpr-spill-vgprs`. **Failed:** `--regalloc=basic` (compiler crash),
`--regalloc=pbqp` (not built in).

## Instruction mix (static, non-nop)

| kernel `<1,true,false>` | baseline insts / v / s / global | -O1 | pragma (IQ2+IQ3+Q3_K) |
|---|---|---|---|
| IQ2_XXS | 1001 / 758 / 209 / 18 | 1208 / 938 / 222 / 32 | **623 / 354 / 235 / 14** |
| IQ3_XXS | 1040 / 777 / 219 / 28 | 1246 / 973 / 221 / 36 | **640 / 367 / 237 / 16** |
| Q3_K | 761 / 490 / 222 / 33 | 862 / 584 / 225 / 37 | 803 / 517 / 241 / 29 |

## Findings

1. **The IQ2_XXS/IQ3_XXS register excess is a compiler decision, not an irreducible property of the
   source.** Clang's own full-unroll of the 4-iteration sign-unpack loop (`vecdotq.cuh:1000`, `:1124`)
   puts four copies of the sign-expansion state live at once. Disabling that unroll alone takes the
   production MoE-decode IQ2_XXS kernel from **78 → 44 VGPR** (6 → 8 waves/SIMD) and IQ3_XXS from
   **71 → 44**, with zero spill and no change to any other quant. This refines the 2026-08-12 reading
   ("the cost is sign unpacking"): the unpacking is the *payload*, the unroll is the *multiplier*.
2. **The AMDGPU register-allocator/scheduler knobs are not the lever.** ~30 RA/scheduling options moved
   nothing or moved the wrong way; the only allocator-side help was `sdwa-peephole=false` (−8). What
   moves VGPR here is the *IR shape handed to* the allocator (unrolling, optimisation level).
3. **Global levers are the wrong granularity.** `-O1` and `--unroll-count=1` both cross 64 for IQ2/IQ3
   but regress Q8_0/Q4_K; the pragma regresses Q3_K (88 → 96). The winning control is per-loop and
   per-quant — exactly a search space, not a single flag.
4. **Static ≠ throughput.** The pragma variant keeps a 4-trip loop: static IQ2_XXS instructions drop
   1001 → 623, but ~378 removed ≈ 3 × a ~126-instruction body, so *executed* instructions per block are
   probably ≈ unchanged, plus a per-iteration backward branch, against +2 waves/SIMD. That is
   necessary-not-sufficient; decode on this device is bandwidth/latency-bound (parent: 85.60 µs median).

## What this does and does not license

- It **does** establish a concrete, cheap, experimental-branch candidate: `pragma_iq2_only.diff`
  (sha256 prefix `a51189f917f8df91`) and the IQ2+IQ3 form (drop the Q3_K hunk).
- It **does not** show a decode speedup. The decisive test is AK-H-QL-1's second falsifier: an IQ2_XXS
  kernel below 64 VGPR whose measured batch-1 decode does or does not move into the ≥90 t/s band — a GPU
  micro/serving bench with a correctness pair, on a full experimental candidate build.
- It **does not** require a toolchain change or unpinning: every lever found works on the pinned ROCm
  6.2 compiler. No evidence here yet supports a toolchain move.
- Belief-kernel: this is a new measurement source (static compile-sweep register stats); wiring task to be
  filed per CLAUDE.md in the Stage-3 plan.

## Addendum — intake Stage 2/2b (2026-09-15)

- **Live payoff is zero today.** The ROCm0 residents (`repos/epyc-orchestrator/orchestration/launch_manifest.yaml`)
  are Qwen3.6/3.8-27B **Q8_0** (`<8,1,true,false>` = 25 VGPR) and Qwen3-VL-30B-A3B **Q4_K_M** (44 VGPR), both
  already at 8 waves/SIMD. The IQ2_XXS/IQ3_XXS lever is latent; it is filed under the mi210 handoff
  TRIPWIRE (INF37-IQ-2) and autokernel-research-loop AK-QL-7/AK-QL-8.
- **The 64-VGPR → 8/6-wave rule is not vendor-documented.** Neither the MI200 CDNA2 ISA (intake-1409) nor
  the MI250 microarchitecture docs (intake-1418) state it. The documented way to test it is the SPI
  resource-shortage counters (`SPI_RA_VGPR_SIMD_FULL_CSN` vs `SPI_RA_WAVE/SGPR_SIMD_FULL_CSN`,
  `SPI_VWC_CSC_WR`).
- **No toolchain reduces vector-ALU VGPR.** CoExec's VGPR→AGPR rewrite is MFMA-only (intake-1415/1421);
  device PGO acts on spill placement (intake-1417); LLVM 23 enables runtime unrolling (intake-1422).
- **Toolchain hazards** (now gates in `docs/runbooks/rocm-upgrade-checklist.md`): full offload-LTO default
  in LLVM 23 / TheRock 10.1 (intake-1407/1413); the ROCm 7.2.0 unroll cost-model bug (intake-1414/1424);
  runtime unrolling on upstream LLVM 23 (intake-1422/1423); profile-driven unrolling under device PGO.
- **`#pragma unroll` is emitted by AMD's own LLM kernel-generator prompts** (AMD-AGI `hip_kernel_llm_lab`
  @980faee8, intake-1419#04; GEAK-HIP, intake-678) and is a no-op on ROCm 6.2 hipcc (this artifact). Where
  VGPR binds, use `#pragma clang loop unroll(disable)` per loop and check every quant in the TU.
