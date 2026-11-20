# nari-labs/nari-llama.cpp (NariQ llama.cpp fork)

- **Intake**: intake-2733 (`intake-2733#record`)
- **Source**: https://github.com/nari-labs/nari-llama.cpp
- **Verification**: dive-verified · read depth PARTIAL
- **Disposition**: integrated; handoffs: quantization-and-low-bit.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Cite the codec identity with our EXL3 mul1 and the wrapper delta from the dive record. Do not build a NariQ loader now (EXL3 27B is parked); do not treat its README quality table as independent evidence.

## Key claims (anchored)

0. Stock llama.cpp cannot load NariQ files; the fork adds its own trellis tensor types and ops.
   - README intro: "Stock llama.cpp, Ollama and LM Studio cannot load these files yet"
1. The fork runs every coded operation on the CPU, but slowly for a 27B model.
   - README Hardware table, CPU row: "Every coded operation runs on the CPU, slowly for a 27B model"
2. AMD and Intel GPUs have no NariQ kernels, and NariQ files are slower than comparable stock GGUFs for now outside the tuned GPU.
   - README Hardware table, AMD row: "No NariQ kernels"
   - README Hardware note: "NariQ files are slower than comparable stock GGUFs for now"

## Dive record

2026-11-20 Stage-2b dive (sonnet; PARTIAL: README, nariq/FORMAT.md, nariq/NOTICE, ggml.h type ids, ggml-trellis.cpp dequant, ggml-cpu/trellis.cpp head/tile_mm/decode, libtrellis common.cuh read in a sparse clone @ 8e0e016e0cd1; gemm/gemv/decode/runtime .cu bodies and conversion/trellis.py not read). Repo evidence (not machine-anchorable): GGML_TYPE_TRL1..TRL6 = ids 44..49 (ggml/include/ggml.h:263-269 @8e0e016e0cd1), K=1..6. Codebook is exllamav3 mul1 only (multiplier 0x83DCD12D, 16-bit window, 16x16 tiles, mma A-fragment in-tile order), identical to our EXL3_1..8 mul1 arithmetic (exl3.cpp L57, ~L192-203 @ experimental/exl3-cpu-20261003 20192b81d); no mcg variant. Delta is the wrapper: output-tile-major tile order vs our band8; F16 per-16-input block scale plus F32 pre/post sign-scale vectors and optional gathers vs our fp16 suh/svh; per-side Hadamard descriptor (identity, block Sylvester, whole-slice m in {1,12,20,68}, up to 8 fused parts) vs our fixed 128-block Hadamard; banded lm_head/embedding with vocab gather; custom GGML_OP_TRELLIS ops. CPU path is fp32 dequant-then-FMA (AVX2/AVX-512F/BW tile decode, no VNNI), weaker than our EXL3 VNNI executor. No HIP path (libtrellis CUDA-only: dp4a, m16n8k16 mma). License MIT; vendored libtrellis Apache-2.0. Port estimate (inferred): CPU ~3-5 agent-days reusing exl3.cpp; gfx90a ~1.5-2 agent-weeks after EXL3-3a/3b close. Mixed-rate (2.5 bpw) semantics NOT-FOUND-IN-SOURCE. lane_head b5c5fe7b4e63
