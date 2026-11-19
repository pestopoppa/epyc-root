# INF48-GATEUP-PROBE: gate/up launch and activation-quantize share of 27B decode (2026-11-18)

Box: `handoffs/active/rocm-kernel-authoring.md` → INF48-GATEUP-PROBE. Source idea: gate/up paired launch,
from the BLACKFURY deep dive (`research/deep-dives/blackfury-tensorfold-20261117.md`, intake-2674#record).
Offline analysis of existing traces only. No inference, profiler or build was run.

## Question and decision rule

What share of decode time goes to the gate/up mul_mat launch(es) plus activation quantization? Open a
paired-launch candidate only if the share that pairing could remove is > 2% of decode.

## MI210 (answered)

- **Trace:** `/mnt/raid0/llm/tmp/c8-h17-profile-20261107/out/smoke-tg_d8192-1794053924/.hip-tmp/trace/prof_kernel_trace.csv`
  (rocprofv3 kernel trace, 62,306 dispatches). Model **Qwen3.8-27B-Q8_0**, build `62cb6a6af` (10558),
  llama-bench tg at depth 8192, about 32 decode tokens.
- **Method:** decode dispatches = every dispatch more than 40 dispatches away from a prefill GEMM
  (`Cijk_*` / `flash_attn_ext_f16`). That leaves 50,957 dispatches and 1052.4 ms of busy time. Shares below are
  kernel-time shares of that decode busy time. Scripts: `/mnt/raid0/llm/tmp/inf48-gateup-probe-20261118/{agg,decode,gaps}.py`.

| Item | Dispatches | Mean | Share of decode |
|---|---:|---:|---:|
| Gate+up: **already ONE fused launch** per layer (`mul_mat_vec_q<Q8_0,1,true,true>`, grid 278528 = 17408 rows, `ggml_cuda_mm_fusion_args`) | 2047 (64 layers × 32 tok) | 150.8 us | 29.34% |
| Quantize of the FFN input (`quantize_q8_1_1d`, 5120 wide; runs immediately before every gate+up launch) | 2047 | 4.5 us | ≈0.87% |
| All `quantize_q8_1` activation quantization (every mmvq input) | — | — | 3.56% |
| All `mul_mat_vec_q` | — | — | 71.74% |
| Idle gap before each gate+up launch | — | median 0 us | 0.00% |

**Reading.** Gate and up are already paired: one dispatch reads both weights, with the GLU fused in. A paired
launch has no launch left to remove. The 29% is weight bandwidth, not overhead. The only overhead tied to
gate/up is the separate FFN-input quantize, **≈0.87% of decode**. Even counting every activation-quantize
dispatch in the model (3.56%) would mean folding quantization into mmvq in general, not pairing gate/up.
That is a separate idea and not this candidate.

## CPU (no adequate trace)

No per-op CPU decode profile of the 27B exists under `/mnt/raid0/llm/tmp`. The only `ggml-cpu-prof/1`
decode profile (`c8-headroom-cpu-profile-20261108`, tg64 t24) is for a hidden-2560 MoE model, not the 27B.
On that model the ffn_gate/ffn_up nodes take 2.45% of wall time. The CPU profiler also folds activation
quantization into MUL_MAT, so it cannot be split out. A minimal trace row was designed but **not published**:
`/mnt/raid0/llm/tmp/inf48-gateup-probe-20261118/spec-draft-cpu-27b-tg-prof.json` (NOT-PUBLISHED marker).

## Verdict

**GPU: NO-GO** for a paired-launch candidate. Gate+up is already one fused launch, and the overhead that
remains (≈0.87%) is below the 2% bar. **CPU: unmeasured for the 27B.** The draft row above would answer it.
