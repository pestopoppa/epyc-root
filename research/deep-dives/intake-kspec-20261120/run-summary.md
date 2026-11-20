# Research intake intake-kspec-20261120 (kernel PRs, NariQ, spec-decode draft heads, harness)

Fourteen operator-supplied sources (intake-2718..2731) were dived; two Stage-2b waves added fifteen dive-surfaced sources (intake-2732..2746). A third wave was not needed. Stage 3 went through two plan revisions; the operator approved r2 with amendments (r2a) on 2026-11-20 and Stage 4 filed 46 boxes plus one in-place amendment across 11 handoffs.

Main findings: PR #32613 is not the XFER-4b row; every served CPU quant already has an iqk or repack kernel. PR #32266's few-row principle becomes a gfx90a MFMA small-M Q8_0 verify kernel (27B W12 61.3 -> ~44 ms target). C14 lacks the n_used=10 MoE helper (7.33% of Q38FN MI210 hybrid prefill kernel time). Measured drafter share: 27B 14.8%, A3B 20.0% of the round. The #25725 DFlash collapse was a rotation bug, not a draft-KV layout effect. NariQ uses our EXL3 mul1 codec; its new part is model-written-token KL calibration, now a boxed experiment. RSIBench-Infra is PDF-only and stays unverified.

| Entry | Title | Verification | Disposition |
|---|---|---|---|
| [intake-2718](intake-2718.md) | llama.cpp PR #32613: Q8_0 - Block Interleaving Implementation for x86 SIMD (AVX512/AVX2) | dive-verified | integrated |
| [intake-2719](intake-2719.md) | llama.cpp PR #32505: CUDA: implement support for duplicate expert IDs | dive-verified | integrated |
| [intake-2720](intake-2720.md) | llama.cpp PR #32266: ggml-cuda : hip few mmq on non wmma arch | dive-verified | integrated |
| [intake-2721](intake-2721.md) | NariQ: Sub-3-Bit Quantization for Long-Horizon Agentic Tasks | dive-verified | integrated |
| [intake-2722](intake-2722.md) | nari-labs/Qwen3.8-27B-NariQ-GGUF (model card) | dive-verified | declined |
| [intake-2723](intake-2723.md) | RSIBench-Infra: Can Agents Optimize Their Own Training and Inference Infrastructure at Pro | stage1-unverified | monitor |
| [intake-2724](intake-2724.md) | ROCm 10.2.0: Advancing Performance, Stability, and Developer Experience (AMD blog) | dive-verified | integrated |
| [intake-2725](intake-2725.md) | NarrowSpec: Draft Hidden Width Need Not Match the Target in Speculative Decoding | dive-verified | integrated |
| [intake-2726](intake-2726.md) | Memory-Efficient Speculative Decoding with Quantized Draft KV Cache | dive-verified | integrated |
| [intake-2727](intake-2727.md) | Efficient and Robust Drafting with Multi-Token Prediction | dive-verified | integrated |
| [intake-2728](intake-2728.md) | Budget Internalization: Fixed-Budget RLVR Trades Test-Time Scaling for In-Budget Accuracy | dive-verified | integrated |
| [intake-2729](intake-2729.md) | Forget Freely, Grep Later: Lossless, Index-Free Memory for Long-Horizon LLM Agents | dive-verified | integrated |
| [intake-2730](intake-2730.md) | QDA: Closed-Loop LLM Quantization Design with Agents | dive-verified | integrated |
| [intake-2731](intake-2731.md) | On-Policy Morphing into Hybrid Attention Models | dive-verified | knowledge_only |
| [intake-2732](intake-2732.md) | SOL-ExecBench: Speed-of-Light Benchmarking for Real-World GPU Kernels Against Hardware Lim | dive-verified | integrated |
| [intake-2733](intake-2733.md) | nari-labs/nari-llama.cpp (NariQ llama.cpp fork) | dive-verified | integrated |
| [intake-2734](intake-2734.md) | Skills catalog - AMD Skills documentation | dive-verified | integrated |
| [intake-2735](intake-2735.md) | FlyDSL documentation (landing page) | dive-verified | integrated |
| [intake-2736](intake-2736.md) | FlyDSL: Expert GPU Kernel Development with the Ease of MLIR Python Native DSL on AMD GPUs | dive-verified | knowledge_only |
| [intake-2737](intake-2737.md) | When Your Agent Opens the Chat App: Agent-Controlled Search over Raw Chat Logs Rivals Stru | dive-verified | integrated |
| [intake-2738](intake-2738.md) | Is Grep All You Need? How Agent Harnesses Reshape Agentic Search | dive-verified | integrated |
| [intake-2739](intake-2739.md) | Windowed-MTP: Removing the Full-Context Draft-KV Tax at Million-Token Context | dive-verified | integrated |
| [intake-2740](intake-2740.md) | SlimSpec: Low-Rank Draft LM-Head for Accelerated Speculative Decoding | dive-verified | integrated |
| [intake-2741](intake-2741.md) | DynaSpec: Context-aware Dynamic Speculative Sampling for Large-Vocabulary Language Models | dive-verified | monitor |
| [intake-2742](intake-2742.md) | NVlabs/SOLAR: Speed of Light Analysis for ML Model Runtime | dive-verified | integrated |
| [intake-2743](intake-2743.md) | BM25 Wins at Scale: A Scaling Study of Retrieval-Augmented Generation Paradigms | dive-verified | integrated |
| [intake-2744](intake-2744.md) | Attention Drift: What Autoregressive Speculative Decoding Models Learn | dive-verified | integrated |
| [intake-2745](intake-2745.md) | amd/skills: Official AMD catalog of AI agent skills | dive-verified | integrated |
| [intake-2746](intake-2746.md) | MOAT: Migration Orchestration via Automated Translation (AMD-Ecosystem/moat) | dive-verified | integrated |
