# Multimodal

**Category**: `multimodal`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 28 documents

## Summary

The EPYC multimodal pipeline spans four modalities: speech-to-text (production), vision (code-complete), text-to-speech (blocked), and unified multimodal (downloaded/untested). The current voice loop has a gap: Mic -> Whisper (port 9000) -> text -> LLM -> response text -> NO TTS OUTPUT. Three TTS paths and two vision upgrade candidates are under evaluation.

Speech-to-text is the only multimodal component in production: faster-whisper large-v3-turbo running on port 9000 with int8 quantization at 2.8x real-time. The vision pipeline is code-complete at approximately 4,500 lines across 23 files with 1,234 tests passing, covering EXIF analysis, face detection/embedding (InsightFace), VL description (llama-mtmd-cli), CLIP embeddings, batch processing, video frame extraction, ChromaDB integration, and 11 API endpoints. It needs live validation with model servers running (Qwen2.5-VL-7B on 8086, Qwen3-VL-30B on 8087).

TTS has three competing paths, all currently blocked. Path A (Qwen3-TTS C++ port in llama.cpp) generates codec tokens at 1.5x real-time but outputs unintelligible noise -- the divergence point between PyTorch reference and C++ token generation has not been identified. Path B (MiniCPM-O 4.5 built-in CosyVoice2 TTS) requires the llama.cpp-omni fork and is untested. Path C (Qwen3-TTS as standalone PyTorch sidecar on port 8110) is the most viable -- 97ms first-packet latency, 10-language support, voice cloning from 3 seconds of audio, Apache 2.0 licensed. The sidecar approach avoids llama.cpp integration entirely.

Moondream 3 (9B total / 2B active MoE VLM) was evaluated and deferred. Despite interesting native detect/point capabilities, it is blocked by BSL 1.1 licensing, uncertain llama.cpp GGUF support for its novel MoE architecture (64 experts, learned attention temperature scaling), lack of tool calling (required for agentic vision), and preview-state unoptimized inference with no published standard benchmarks. The current Qwen2.5-VL-7B stack is more mature with full llama.cpp support and an escalation path to Qwen3-VL-30B-A3B.

MiniCPM-O 4.5 (9B dense, Qwen3-8B backbone + SigLip2 + Whisper-medium + CosyVoice2) offers unified multimodal capability. Vision + text works on mainline llama.cpp; audio features require the llama.cpp-omni fork. It scores 77.6 OpenCompass (vs Qwen2.5-VL-7B's 70.5) and 80.1 MathVista (vs 68.2), but lacks tool calling (0 vs Qwen3-VL-8B's 0.663 BFCL). The testing plan has four phases: mainline vision, spec decode investigation, omni fork audio, and orchestrator integration.

Gemma 4 (intake-251/252) introduces Any-to-Any multimodal models (text+image+audio unified). E4B (8B effective) could simplify the pipeline but is blocked by lack of GGUF support (MLX only). VoxCPM2 (intake-317) is a tokenizer-free multilingual TTS alternative requiring GPU (RTX 4090 for real-time), tracked for GPU upgrade path.

## Key Findings

- STT is production: faster-whisper large-v3-turbo, port 9000, int8, 2.8x RT [multimodal-pipeline.md]
- Vision is code-complete: 4,500 lines, 23 files, 1,234 tests, 11 API endpoints. Needs live validation [multimodal-pipeline.md]
- TTS Path C (PyTorch sidecar) is most viable: 97ms latency, 10 languages, Apache 2.0, ~1-3 GB VRAM [multimodal-moondream3-qwen3tts.md]
- Qwen3-TTS llama.cpp port outputs noise -- codec token divergence unresolved [multimodal-pipeline.md]
- Moondream 3 DEFERRED: BSL 1.1 license, uncertain GGUF, no tool calling, preview state [multimodal-moondream3-qwen3tts.md]
- MiniCPM-O 4.5 beats Qwen2.5-VL-7B on OpenCompass (+7.1) and MathVista (+11.9) but lacks tool calling [multimodal-pipeline.md]
- Qwen3-TTS achieves 2.12% Chinese WER and 2.58% English WER with 0.89 speaker similarity, beating MiniMax, ElevenLabs, CosyVoice [multimodal-moondream3-qwen3tts.md]
- Moondream 3's "surpasses GPT-5" claims lack published numerical comparisons on standard benchmarks [multimodal-moondream3-qwen3tts.md]
- Gemma 4 E-series could unify modalities in single model but blocked by GGUF availability [intake-251/252]
- MMLBD-C (corrected long-document benchmark by LightOn) recommended for VL model evaluation [multimodal-pipeline.md]

## Actionable for EPYC

- **Vision live validation (immediate)**: Start Qwen2.5-VL-7B on 8086 and Qwen3-VL-30B on 8087, run existing test suite with live model endpoints. This is the final step before production.
- **TTS Path C prototype (when prioritized)**: Build FastAPI wrapper around `Qwen3TTSModel.from_pretrained()` on port 8110. Benchmark VRAM and latency on EPYC hardware. Gate behind `ORCHESTRATOR_TTS_ENABLED` flag.
- **MiniCPM-O Phase 1 testing**: Run `llama-mtmd-cli` with Q4_K_M + vision mmproj. Compare vision quality against Qwen2.5-VL-7B on same prompts. No fork needed for vision-only.
- **Voice cloning guardrails**: Must be designed before enabling any TTS path. 3-second cloning raises ethical/misuse concerns.
- **Monitor Gemma 4 GGUF**: Once llama.cpp conversion is available, evaluate E4B as potential unified multimodal worker that replaces separate STT + Vision + TTS services.
- **Do NOT resume Qwen3-TTS C++ debugging** unless MiniCPM-O TTS and PyTorch sidecar both fail.
- **Add `worker_tts` role** to model_registry.yaml (gated behind feature flag) when TTS path is selected.

## Open Questions

- Is MiniCPM-O 4.5's built-in TTS quality competitive with standalone Qwen3-TTS? (Untested)
- Can Qwen3-VL-8B (with tool calling) replace Qwen2.5-VL-7B as `worker_vision`?
- When will Gemma 4 GGUF conversion be available in llama.cpp?
- Does the vision pipeline's OpenAI-compat multimodal support (parsing image_url in message content) need to be completed before production use?
- What is the VRAM impact of running MiniCPM-O alongside existing model stack?
- Can VoxCPM2's tokenizer-free approach produce better quality than Qwen3-TTS's discrete codebook approach?

## Related Categories

- [Document Processing](document-processing.md) -- Vision pipeline feeds document preprocessing; OpenDataLoader provides structured context for VL models
- [Tool Implementation](tool-implementation.md) -- Vision API endpoints, TTS sidecar service design
- [MoE Optimization](moe-optimization.md) -- Moondream 3 uses 64-expert MoE; Gemma 4 26B-A4B is MoE
- [SSM Hybrid](ssm-hybrid.md) -- MiniCPM-O uses standard attention; relevant as architectural comparison

## Source References

- [Moondream 3 + Qwen3-TTS deep dive](/workspace/research/deep-dives/multimodal-moondream3-qwen3tts.md) -- Architecture analysis, benchmark review, integration assessment for both models
- [Multimodal pipeline handoff](/workspace/handoffs/active/multimodal-pipeline.md) -- Current state of all four modalities, testing plans, research intake updates
- [MiniCPM-O integration handoff](/workspace/handoffs/archived/minicpm-o-4_5-integration.md) -- Download status, benchmark comparison, testing phases
- [Vision pipeline handoff](/workspace/handoffs/archived/vision-pipeline.md) -- Historical vision implementation details
- [OpenDataLoader deep dive](/workspace/research/deep-dives/opendataloader-pdf-pipeline-integration.md) -- Structured context for VL models (Phase 2)
- [intake-251/252] Gemma 4 -- Any-to-Any multimodal models, pending GGUF
- [intake-317](https://github.com/OpenBMB/VoxCPM) VoxCPM2 -- Tokenizer-free TTS alternative, GPU-dependent
