# MI210 serving program: findings (archived 2026-11-05)

Source handoff: `handoffs/completed/mi210-serving-program.md` (INF-22). Results below are measured on the
champion candidate C6 `729599d69` unless stated; each links to its filed artifact.

## Serving recipes
- **HIP pinned host memory costs CPU decode ~1.9x when the GPU backend is merely loaded.** Fix: `GGML_CUDA_NO_PINNED=1`
  (NPD1-STEP4: idle TPOT 1.88x -> 1.028x vs CPU-only).
- **GPU prefill offload for a CPU-served model works:** Q38FN with `-ngl 0 -ub 2048` + `GGML_CUDA_NO_PINNED=1` gives
  2.61x (8k) / 2.87x (32k) TTFT at 1.05x idle TPOT (NPD1-STEP5; `artifacts/gpu-block-20261105/npd1-step5-summary.json`).
  Flash attention stays on the CPU in this mode (the scheduler's op offload skips FLASH_ATTN_EXT).
- **ROCm 10.1 is NO-GO** for the MI210 llama.cpp build: the decode "gain" was DFlash2 acceptance; FA prefill at depth -21..-25%.
- **Decode-aware prefill budget (KVU-16g-2):** 256 tokens / 460 ms protects decoders ~3x (worst step) and ~2x throughput
  while an 80k prompt arrives, with no solo cost, but costs the newcomer 1.68-1.73x TTFT (bound 1.30): REJECT as
  configured; re-tune in KVU-16g-3 (`kv-cache-program.md`).

## vLLM vs llama.cpp (Qwen3-4B-Instruct-2507 proxy)
| Run | Precision | Decode np1 | Decode np4 | Prefill 2k | Prefill 8k |
|---|---|---|---|---|---|
| Q38P-4, GPU | bf16 both | vLLM 1.26x | 1.43x | 3.31x | 3.43x |
| Q38P-4b, GPU | C6 Q8_0 vs vLLM INT8 W8A8 | **C6 1.47x** | **C6 1.18x** | vLLM 3.07x | vLLM 3.25x |
| Q38P-4c, CPU (1 quarter) | C6 Q8_0 vs vLLM INT8 W8A8 | **C6 2.06x** | **C6 1.98x** | vLLM 2.92x | vLLM 3.16x |

Reading: at the precision we serve, C6 wins decode on both devices; vLLM's advantage is prefill only. Decision
(operator 2026-11-05): **port the prefill techniques into llama.cpp, don't switch engines.** vLLM 0.33 cannot load our
production GGUFs (no `qwen4exp` implementation for Q38FN; the GGUF plugin lacks `qwen35`/`qwen35moe`), and on gfx90a its
only working 8-bit path is the Triton int8 scaled-mm (no FP8 kernel, AITER not built for gfx90a).

## Where C6's prefill gap comes from (identified 2026-11-05)
- **CPU:** C6 ships ik_llama's iqk Q8_0 prefill GEMM but it is env-gated off, so Q8_0 prefill runs llamafile's 4x4
  kernel; enabling it as the compiled default (branch `experimental/iqk-q8-prefill-default-20261105`) measured
  **2.03x pp2048 / 1.56x pp8192** with a passing quality screen (AK-CPU-INT8-PREFILL; decode check pending).
- **GPU:** C6's FLASH_ATTN_EXT reaches ~17% of MI210 bf16 peak. AITER's gfx942 FA-v3 fwd hd128 asm, retargeted to
  gfx90a (two MFMA renames, rebuilt descriptor, hazard padding), is correct and **3.87x faster** on the fair cells
  (AK-ASM-H5). All production GPU models are head_dim 256, so the payoff needs an hd256 kernel (CK-tile fmha; test
  queued under AK-ASM-H5-PORT). Report: `artifacts/analysis/mi300-to-mi210-portability-20261105.md`.

## Process lessons
- CPU rows must not open the GPU (STT5's HIP whisper contaminated two A/Bs) -> keeper GPU fence.
- GPU timing rows need a quiet device check before and during; correctness suites must not hold the GPU exclusively.
- A timing quarter must include its SMT siblings; q3's siblings are the GPU host lane.
