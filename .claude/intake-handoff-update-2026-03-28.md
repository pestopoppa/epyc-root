# Handoff Update Staging — 2026-03-28

## kv-cache-quantization.md — append to References section:

```
- TurboQuant llama.cpp CUDA fork: https://github.com/spiritbuun/llama-cpp-turboquant-cuda
- TurboQuant upstream discussion: https://github.com/ggml-org/llama.cpp/discussions/20969
- TurboQuant upstream feature request: https://github.com/ggml-org/llama.cpp/issues/20977
- ik_llama.cpp TurboQuant PR: https://github.com/ikawrakow/ik_llama.cpp/issues/1509
- vLLM TurboQuant feature request: https://github.com/vllm-project/vllm/issues/38171
```

## kv-cache-quantization.md — append new section:

```markdown
## Research Intake Update — 2026-03-28

### New Related Research
- **[intake-194] "llama-cpp-turboquant-cuda"** (github:spiritbuun/llama-cpp-turboquant-cuda)
  - Relevance: Direct CUDA implementation of TurboQuant 3-bit KV cache quantization in llama.cpp fork
  - Key technique: TurboQuant turbo3 with Flash Attention CUDA kernels for NVIDIA GPUs
  - Reported results: 98.8% of q8_0 prefill speed, norm correction makes turbo3 PPL beat q8_0
  - Delta from current approach: We have turbo_q3 hybrid at 16.21 t/s (Qwen2.5-7B) but no CUDA kernels; this fork provides production CUDA path

### Ecosystem Status (via expansion)
- **Upstream llama.cpp**: Feature request open (issue #20977), discussion active (#20969)
- **ik_llama.cpp**: Working CPU+CUDA implementation ready for review (issue #1509), 18/18 tests passing, MSE matches paper
- **vLLM**: Feature request open (issue #38171)
- **Multiple independent forks** validating TurboQuant claims: TQ3 MSE=0.034, TQ4 MSE=0.009, 4.9x compression vs FP16
- **700K+ token context** demonstrated on single RTX 5090 (32GB) with turbo3
```
