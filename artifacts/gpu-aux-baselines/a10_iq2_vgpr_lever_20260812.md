# A10 follow-up — IQ2_XXS VGPR pressure, read from the shipped code object (2026-08-12)

**Zero GPU time.** Register allocation read statically out of `libggml-hip.so.0.16.0` from the clean
frozen-v9 tree at `0db32c06e`. Method: `llvm-objcopy --dump-section=.hip_fatbin`, then parse **all 135**
concatenated `__CLANG_OFFLOAD_BUNDLE__` headers (the section holds one bundle per translation unit —
parsing only the first yields 8 KB of a 3 MB section and the wrong answer), extract each `gfx90a` ELF,
and read `.vgpr_count` from the AMDGPU msgpack note. Classification: **OBSERVATION**.

## The four IQ2_XXS instantiations

| variant | VGPR | AGPR | SGPR | spill | scratch | LDS | waves/SIMD |
|---|---|---|---|---|---|---|---|
| `<IQ2_XXS,1,false,false>` (synthetic op path) | **63** | 0 | 28 | 0 | 0 | 256 | **8** — max |
| `<IQ2_XXS,1,true,false>` (**production MoE decode**) | **78** | 0 | 46 | 0 | 0 | 512 | **6** |
| `<IQ2_XXS,1,false,true>` | 125 | 0 | 28 | 0 | 0 | 512 | **4** |
| `<IQ2_XXS,1,true,true>` | 90 | 0 | 50 | 0 | 0 | 1024 | **5** |

This also explains a small discrepancy in the earlier report: `rocprof` reported 64 and 80, the ISA says
63 and 78. **`rocprof` reports the allocation-granularity rounding, the note reports the true count.**
Occupancy follows the rounded figure, so the wave counts are unchanged.

## The cross-quant comparison — this is the actionable part

All at the identical `<_,1,true,false>` wrapper, so the wrapper is held constant and only the quant's
dequant state varies. Zero spill in every one.

| VGPR | ggml_type | quant |
|---|---|---|
| 25 | 8 | **Q8_0** |
| 28 | 2, 3 | Q4_0, Q4_1 |
| 38 | 20 | IQ4_NL |
| 42 | 19 | IQ1_S |
| 44, 46 | 12, 14 | Q4_K, Q6_K |
| 55, 57 | 13, 10 | Q5_K, Q2_K |
| **64** | 23 | **IQ4_XS** — exactly 8 waves |
| 71 | 18 | IQ3_XXS |
| **78** | **16** | **IQ2_XXS** |
| 78, 80, 82 | 22, 21, 17 | IQ2_S, IQ3_S, IQ2_XS |
| 88 | 11 | Q3_K |

**Findings:**

1. **The mm_ids wrapper is not the cost.** Q8_0 runs the same wrapper in **25** VGPRs. The 78 is
   dominated by IQ2_XXS's own dequant state, not by the MoE indirection. My earlier framing — "inherent
   to the codebook gather, or incidental to the mm_ids wrapper?" — resolves toward the former.
2. **But "codebook ⇒ expensive" is wrong too.** IQ4_NL sits at 38 and IQ1_S at 42, while the block quant
   Q3_K is the most expensive kernel in the table at 88. Register pressure tracks the *complexity of the
   per-block state machine*, not the presence of a lookup table.
3. **IQ4_XS at exactly 64 is an existence proof.** An IQ-family kernel on this exact wrapper already
   achieves the 8-wave threshold. IQ2_XXS is **14 registers over**, and the target is concrete and
   known-reachable rather than hypothetical.
4. **Zero spill everywhere is the constraint, not a bonus.** `scratch = 0` and `vgpr_spill_count = 0` in
   every row, so there is no slack: forcing IQ2_XXS below 64 risks converting an occupancy win into
   scratch traffic, which on a bandwidth-bound decode kernel would be a clear net loss. Any attempt must
   report spill counts alongside occupancy or it is not evidence.

## What this does and does not license

It does **not** show that +2 waves would yield throughput. Decode here is bandwidth/latency-bound
(median 85.60 µs with a 6% spread across 6,063 dispatches), and higher occupancy only helps if there is
latency left to hide. It does establish that the lever is **real, bounded (14 registers), reachable
(IQ4_XS proves the target), and cheap to attempt** — and that the measurement to justify it costs no
GPU time at all.

Suggested next step, still zero-GPU: diff the disassembly of `<IQ2_XXS,1,true,false>` against
`<IQ4_XS,1,true,false>` to find where the extra live values are held. Reproduce with
`/workspace/tmp/` extraction above; code objects under `/workspace/tmp/co/`, target `0035.elf`.
