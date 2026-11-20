# NVlabs/SOLAR: Speed of Light Analysis for ML Model Runtime

- **Intake**: intake-2742 (`intake-2742#record`)
- **Source**: https://github.com/NVlabs/SOLAR
- **Verification**: dive-verified · read depth PARTIAL
- **Disposition**: integrated; handoffs: autokernel-akx-program.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Do not adopt SOLAR as our bound engine (no GGUF quants, no AMD/CPU profiles, torch frontend). Reuse only the assumption-reporting vocabulary; never use a sparse-peak bound for dense kernels.

## Key claims (anchored)

0. A SOLAR speed-of-light number is conditional on its operation counts, access model and hardware assumptions, and the tool treats translation agreement, counting and the hardware model as three separate checks.
   - README intro: "A SOL number is conditional on its operation counts, its access model and its hardware assumptions"
   - README intro: "Numerical agreement of a translation, correct counting and a valid hardware model are three separate checks"
1. The perf model reports unfused and fused speed-of-light per architecture and precision.
   - README flow: "Perf model: unfused and fused SOL per arch and precision"
2. Each architecture profile carries both dense and structured-sparsity tensor-core peaks, and the sparse-peak bound is one no dense kernel can reach.
   - README SOL assumptions: "carries both the dense and the structured-sparsity tensor-core peak for every precision it declares, with their sources"
   - README SOL assumptions: "is a lower bound no dense kernel can reach"
3. The code is Apache-2.0 licensed.
   - README badge: "Apache-2.0 license"

## Dive record

2026-11-20 Stage-2b wave-2 dive (sonnet; PARTIAL: README to ~9k chars; docs/SOL_GUIDE.md, configs/arch/README.md, H100_SXM.yaml, solar/perf/arch_rates.py and constants read @ 62dab7534931; perf_model.py/graph_analyzer.py bodies only grepped). Fused bytes = unique external reads once plus output writes, not capacity-aware; fused_prefetched equals fused (no prefetch credit); whole-graph max(compute, memory) (docs/SOL_GUIDE.md L63-L75, L186-L364, L594-L601). Peaks in flat per-arch YAML (DRAM_byte_per_cycle, dense/sparse MAC rates); seven NVIDIA profiles only; --arch-config accepts a path, so an MI210 YAML is ~30 lines, but the frontend needs a torch.nn.Module or einsum DSL, not ggml graphs. Quantization is dtype width only (constants.py L29-L38: fp32/tf32/fp16/bf16/int8/fp64/fp8/nvfp4); no GGUF block-quant model. Sparse peak is the default headline. Decision: do not adopt SOLAR as a Tsol engine; compute Tsol from GGUF per-tensor bytes over measured achievable bandwidth (cpu-decode-roofline-program.md:L70-L80, rocm-kernel-authoring.md:L2820-L2827 @901b3fe); adopt only its assumption-reporting vocabulary (dense peak, compulsory I/O, stated exclusions). lane_head 901b3fe44a30
