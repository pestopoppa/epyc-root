# Brief (for the orchestrator / CPU session): two zero-code MoE-on-GPU aggregate wins

**Status**: MEASURED role→config recommendations, **no kernel change**. From the MI210 GPU campaign (2026-07-04, gemma-4-26B-A4B, the clean MoE-no-GDN test vehicle). All numbers **OBSERVATION** (no P-GPU-1) — gate any production enablement through `/workspace/MEASUREMENT.md`. **Applies IF/when a MoE role is hosted on the MI210 (the residency bet, findings-02 Gate R)** — this is not a change to the current CPU production stack.

## Win 1 — FA-decode for aggregate (`-fa 1` at B≥8)
For MoE-on-GPU decode, `-fa 1` is a WIN at aggregate batch — the **OPPOSITE** of the dense-hybrid 27B (where `-fa 1` hurt everywhere, because gfx90a FA is prefill-only for that path). Measured (gemma-26B-A4B, S_TG t/s):

| B | Q8 `-fa0→-fa1` | bf16 `-fa0→-fa1` |
|--:|:--|:--|
| 1 | 96.2 → 85.0 (−12%) | 72.6 → 67.4 (−7%) |
| 8 | 243.8 → 251.9 (+3%) | 177.4 → 182.9 (+3%) |
| 32 | 563 → 652 (**+16%**) | 744 → 875 (**+18%**) |
| 128 | 851 → 1107 (**+30%**) | 1083 → **1548 (+43%)** |

**Rule: `-fa 1` for aggregate serving (B≥8); `-fa 0` for single-stream latency (crossover ≈ B=8).** FA fuses the KV mat-vec and avoids the V-cache padding `-fa 0` forces on gemma's uneven-V-size layers (the 18% attention tail seen in the B=32 profile). Coherent output confirmed.

## Win 2 — bf16-for-aggregate / Q8-for-single-stream (role→precision)
bf16-vs-Q8 crossover ≈ **B=16–24**: Q8 wins single-stream / low-batch (+27–37% at ≤B8), bf16 wins high-concurrency (+27–43% at ≥B32). Scaling B1→B128: **Q8 8.85× vs bf16 14.9×** (high-batch GEMM is compute-bound; bf16 runs native on CDNA2 matrix cores with no dequant tax).

**Rule: a high-concurrency fan-out MoE role (B≥16–32) → bf16; a latency / single-stream role → Q8.** HBM-fit-gated: bf16-26B @B128 / 32k-ctx = **56.6 GB of 65.5** (fits, ~9 GB headroom); a larger MoE would not fit at B128 on the 64 GB card.

## Combined peak
**bf16 + `-fa 1` @ B=128 = 1548 t/s** aggregate (gemma-26B-A4B, fully GPU-resident) — ~2.75× the prior aggregate anchor (Q8 `-fa0` @B32 = 563), entirely config, zero kernel work.

## What is NOT a lever (measured — do not attempt)
- **L1-MoE `mmid` dispatch threshold** — forcing experts to MMQ at low batch is net-negative (B2 −30%, B4 −21%, B8 −10.5%; it inverts the dense `ne11<=1` fix). Low-batch experts have ~1 token each → MMQ's 16/32-wide tiles waste ~31/32; `mul_mat_vec_q_moe` (MMVQ) is the correct kernel, and the default threshold (8) is already optimal. Experts already run MMQ at B≥16, so zero surface area at the aggregate sweet spot.
- **MTP for MoE-on-GPU decode** — net-negative (−12%, head-quant-independent; it's MoE-verify overhead on already-fast plain MoE decode).

## Still open (GPU-kernel, our side)
The real aggregate ceiling is the **Q8-MMQ GEMM efficiency** (61% of B=32 decode; the `quantize_mmq_q8_1` + per-tile dequant tax is why bf16 beats Q8 +32%). If a feasibility probe shows closeable headroom, a Q8-MMQ fused-dequant kernel would make Q8 aggregate-competitive at half the HBM — tracked in `mi210-q8-dequant-gemv-roofline.md` (L3-MoE). Until then, **bf16 is the aggregate precision** per Win 2.
