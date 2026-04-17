# Multimodal

**Category**: `multimodal`
**Confidence**: verified
**Last compiled**: 2026-04-17
**Sources**: 31 documents

## Summary

The EPYC multimodal pipeline spans four modalities: speech-to-text (production), vision (code-complete), text-to-speech (blocked), and unified multimodal (downloaded/untested). The current voice loop has a gap: Mic -> Whisper (port 9000) -> text -> LLM -> response text -> NO TTS OUTPUT. Four TTS paths and two vision upgrade candidates are under evaluation.

Speech-to-text is the only multimodal component in production: faster-whisper large-v3-turbo running on port 9000 with int8 quantization at 2.8x real-time. The vision pipeline is code-complete at approximately 4,500 lines across 23 files with 1,234 tests passing, covering EXIF analysis, face detection/embedding (InsightFace), VL description (llama-mtmd-cli), CLIP embeddings, batch processing, video frame extraction, ChromaDB integration, and 11 API endpoints. It needs live validation with model servers running (Qwen2.5-VL-7B on 8086, Qwen3-VL-30B on 8087).

TTS has three existing paths, all blocked, plus one newly viable CPU-native candidate. Path A (Qwen3-TTS C++ port in llama.cpp) generates codec tokens at 1.5x real-time but outputs unintelligible noise -- the divergence point between PyTorch reference and C++ token generation has not been identified. Path B (MiniCPM-O 4.5 built-in CosyVoice2 TTS) requires the llama.cpp-omni fork and is untested. Path C (Qwen3-TTS as standalone PyTorch sidecar on port 8110) is viable for GPU-available deployments -- 97ms first-packet latency, 10-language support, voice cloning from 3 seconds of audio, Apache 2.0 licensed. Path D (ZipVoice-Distill / LuxTTS CPU sidecar) is the strongest candidate for CPU-only EPYC: the parent model (k2-fsa ZipVoice-Distill, ASRU 2025, Apache 2.0) achieves RTF=1.22 on a single Xeon thread at 4 flow-matching steps -- projected RTF of 0.15-0.22 on EPYC 9655 with 16 threads. LuxTTS is a thin fine-tune atop ZipVoice-Distill that adds a community-trained 48kHz Vocos vocoder; the 48kHz vocoder adds negligible overhead (<5% of total inference) and is not the bottleneck. Path D is a deployment exercise, not a research port -- upstream already ships ONNX export, INT8 quantization, and a sherpa-onnx C++ runtime. TADA (Hume AI, intake-402) introduces a distinct architectural approach (1:1 text-acoustic dual alignment over a Llama 3.2 backbone) suited for coherent long-form synthesis (up to 700 seconds), but is GPU-bound as shipped with no CPU benchmark or GGUF/ONNX path; it is shelved until long-form narration becomes a workload or GPU becomes available. Voicebox (intake-396) is a multi-engine TTS studio whose architecture patterns (TTSBackend Protocol, chunked_tts.py, serial asyncio queue) are directly reusable (~550 lines) for building an EPYC TTS sidecar; its claimed ROCm support is README-only with no implementation code.

Moondream 3 (9B total / 2B active MoE VLM) was evaluated and deferred. Despite interesting native detect/point capabilities, it is blocked by BSL 1.1 licensing, uncertain llama.cpp GGUF support for its novel MoE architecture (64 experts, learned attention temperature scaling), lack of tool calling (required for agentic vision), and preview-state unoptimized inference with no published standard benchmarks. The current Qwen2.5-VL-7B stack is more mature with full llama.cpp support and an escalation path to Qwen3-VL-30B-A3B.

MiniCPM-O 4.5 (9B dense, Qwen3-8B backbone + SigLip2 + Whisper-medium + CosyVoice2) offers unified multimodal capability. Vision + text works on mainline llama.cpp; audio features require the llama.cpp-omni fork. It scores 77.6 OpenCompass (vs Qwen2.5-VL-7B's 70.5) and 80.1 MathVista (vs 68.2), but lacks tool calling (0 vs Qwen3-VL-8B's 0.663 BFCL). The testing plan has four phases: mainline vision, spec decode investigation, omni fork audio, and orchestrator integration.

Gemma 4 (intake-251/252) introduces Any-to-Any multimodal models (text+image+audio unified). E4B (8B effective) could simplify the pipeline but is blocked by lack of GGUF support (MLX only). VoxCPM2 (intake-317) is a tokenizer-free multilingual TTS alternative requiring GPU (RTX 4090 for real-time), tracked for GPU upgrade path.

## Key Findings

- STT is production: faster-whisper large-v3-turbo, port 9000, int8, 2.8x RT [multimodal-pipeline.md]
- Vision is code-complete: 4,500 lines, 23 files, 1,234 tests, 11 API endpoints. Needs live validation [multimodal-pipeline.md]
- TTS Path C (PyTorch sidecar) is most viable for GPU-available deployments: 97ms latency, 10 languages, Apache 2.0, ~1-3 GB VRAM [multimodal-moondream3-qwen3tts.md]
- Qwen3-TTS llama.cpp port outputs noise -- codec token divergence unresolved [multimodal-pipeline.md]
- Moondream 3 DEFERRED: BSL 1.1 license, uncertain GGUF, no tool calling, preview state [multimodal-moondream3-qwen3tts.md]
- MiniCPM-O 4.5 beats Qwen2.5-VL-7B on OpenCompass (+7.1) and MathVista (+11.9) but lacks tool calling [multimodal-pipeline.md]
- Qwen3-TTS achieves 2.12% Chinese WER and 2.58% English WER with 0.89 speaker similarity, beating MiniMax, ElevenLabs, CosyVoice [multimodal-moondream3-qwen3tts.md]
- Moondream 3's "surpasses GPT-5" claims lack published numerical comparisons on standard benchmarks [multimodal-moondream3-qwen3tts.md]
- Gemma 4 E-series could unify modalities in single model but blocked by GGUF availability [intake-251/252]
- MMLBD-C (corrected long-document benchmark by LightOn) recommended for VL model evaluation [multimodal-pipeline.md]
- **Path D (ZipVoice-Distill / LuxTTS) is the only CPU-realistic TTS option currently available**: ZipVoice-Distill (123M, 4 NFE, ASRU 2025) achieves RTF=1.22 on 1 Xeon thread; projected RTF 0.15-0.22 on EPYC 9655 with 16 threads; WER=1.51 on LibriSpeech-PC (beats F5-TTS, E2, XTTS). Path D is a deployment exercise -- upstream ships ONNX + INT8 + sherpa-onnx C++. [luxtts-cpu-tts-candidate.md] `verified`
- **LuxTTS is a thin fine-tune of ZipVoice-Distill**, adding a community-trained 48kHz Vocos vocoder (36.7M, MIT); credibility of LuxTTS-as-product is 2/5 (single-author, no formal eval), but parent ZipVoice-Distill credibility is 4/5 (peer-reviewed, full code, ONNX/C++). Target upstream directly. [luxtts-cpu-tts-candidate.md] `verified`
- **Flow-matching is not CPU-hostile at small scale**: ZipVoice-Distill's 4×123M Zipformer structure (downsampling rates [1,2,4,2,1]) is ~18× fewer FLOPs than F5-TTS (32×336M). The Vocos 48kHz vocoder adds <5% to end-to-end CPU time and is not the bottleneck. [luxtts-cpu-tts-candidate.md] `inferred`
- **TADA (Hume AI) introduces 1:1 text-acoustic dual alignment** on a Llama 3.2 1B/3B backbone, enforcing strict token-to-acoustic-frame correspondence that eliminates content hallucination by construction (zero hallucinations/1000+ LibriTTSR samples). Achieves 2nd place on EARS long-form eval (sSIM 4.18, sMOS 3.78) with Online Rejection Sampling. [hume-tada-text-acoustic-alignment.md] `verified`
- **TADA is GPU-bound as shipped**: All RTF numbers (0.09) are on a single H100 with torch.compile+bf16. No CPU benchmark, no GGUF, no ONNX path exists. Speech Free Guidance doubles LLM forward passes; on CPU this is ~1.5-2× compute overhead, not the negligible 0.01 RTF claimed for GPU batch parallel. Shelved until long-form narration is a workload or GPU is available. [hume-tada-text-acoustic-alignment.md] `verified`
- **TADA's competitive EARS scores require Online Rejection Sampling** (3-5× inference cost multiplier); raw TADA-3B scores 67.0 speaker similarity vs Index-TTS's 76.9. "2nd place overall" is marketing-friendly -- TADA is competitive, not winning on any single metric. [hume-tada-text-acoustic-alignment.md] `verified`
- **Voicebox ROCm support is README-only**: No HSA/ROCm detection code exists anywhere in the repo (926 lines of Rust, all Python backends). CPU coverage is LuxTTS-specific only -- the only backend with explicit per-CPU thread tuning. Do not cite voicebox as ROCm prior art. [voicebox-multi-engine-tts-studio.md] `verified`
- **Voicebox chunked_tts.py is production-quality and directly reusable**: ~240 lines of pure numpy/regex implementing sentence-boundary splitting (with abbreviation list, CJK punctuation, decimal-number handling, bracket-tag atomicity), linear-crossfade concatenation, and per-chunk seed decorrelation. [voicebox-multi-engine-tts-studio.md] `verified`
- **Voicebox's serial asyncio queue is 40 lines** -- one worker, coroutine-per-item, no preemption. Adopt with a bounded queue size and reject-on-full policy. The TTSBackend Protocol (6-method typing.Protocol + ModelConfig dataclass registry) shapes a clean extension surface for adding future engines. [voicebox-multi-engine-tts-studio.md] `verified`

## Actionable for EPYC

- **Vision live validation (immediate)**: Start Qwen2.5-VL-7B on 8086 and Qwen3-VL-30B on 8087, run existing test suite with live model endpoints. This is the final step before production.
- **TTS Path D feasibility benchmark (highest TTS priority)**: `pip install zipvoice`, download k2-fsa/ZipVoice-Distill (~500MB), measure RTF + first-packet latency on EPYC 9655 with 16 threads (FP32, no GPU). Target: RTF < 0.35, first-packet < 400ms. If it passes, continue to ONNX path (Phase D2) and FastAPI sidecar (Phase D4). Decision criteria for promotion: RTF < 0.35, WER < 2.5, memory < 2 GB. [luxtts-cpu-tts-candidate.md]
- **Adopt voicebox chunking utilities**: Copy `chunked_tts.py` (~240 lines), `task_queue.py` (~40 lines), and `TTSBackend` Protocol + `ModelConfig` (~200 lines) into the EPYC TTS sidecar. Add bounded queue size. Voicebox license is MIT. [voicebox-multi-engine-tts-studio.md]
- **TTS Path C prototype (when prioritized)**: Build FastAPI wrapper around `Qwen3TTSModel.from_pretrained()` on port 8110. Benchmark VRAM and latency on EPYC hardware. Gate behind `ORCHESTRATOR_TTS_ENABLED` flag.
- **MiniCPM-O Phase 1 testing**: Run `llama-mtmd-cli` with Q4_K_M + vision mmproj. Compare vision quality against Qwen2.5-VL-7B on same prompts. No fork needed for vision-only.
- **Voice cloning guardrails**: Must be designed before enabling any TTS path. 3-second cloning raises ethical/misuse concerns.
- **Monitor Gemma 4 GGUF**: Once llama.cpp conversion is available, evaluate E4B as potential unified multimodal worker that replaces separate STT + Vision + TTS services.
- **Do NOT resume Qwen3-TTS C++ debugging** unless MiniCPM-O TTS and PyTorch sidecar both fail.
- **Add `worker_tts` role** to model_registry.yaml (gated behind feature flag) when TTS path is selected.
- **Shelve TADA** until: (a) long-form (>2 min) coherent narration becomes a required workload, OR (b) GPU becomes available in the EPYC deployment. Re-entry triggers: community llama.cpp port appears, or long-form use case is confirmed. [hume-tada-text-acoustic-alignment.md]
- **Do NOT run LuxTTS and TADA CPU evaluations in parallel**: TADA CPU viability requires porting three separate components (modified Llama backbone, flow-matching head, codec) before any measurement is possible; LuxTTS benchmark is a 1-day exercise. Sequential evaluation is cheaper. [hume-tada-text-acoustic-alignment.md]

## Open Questions

- Is MiniCPM-O 4.5's built-in TTS quality competitive with standalone Qwen3-TTS? (Untested)
- Can Qwen3-VL-8B (with tool calling) replace Qwen2.5-VL-7B as `worker_vision`?
- When will Gemma 4 GGUF conversion be available in llama.cpp?
- Does the vision pipeline's OpenAI-compat multimodal support (parsing image_url in message content) need to be completed before production use?
- What is the VRAM impact of running MiniCPM-O alongside existing model stack?
- Can VoxCPM2's tokenizer-free approach produce better quality than Qwen3-TTS's discrete codebook approach?
- Does ZipVoice-Distill's 0.657 SIM-o (speaker similarity) meet EPYC's voice-cloning quality bar? Qwen3-TTS reaches 0.789; the gap is meaningful for voice-identity use cases. [luxtts-cpu-tts-candidate.md]
- If Path D passes RTF threshold, is the 48kHz Vocos head upgrade (LuxTTS's main addition over upstream) worth the ~1.3× overhead? Requires A/B test on same text+reference. [luxtts-cpu-tts-candidate.md]
- If long-form TTS (>2 min) becomes a workload, would TADA's 700s context outperform voicebox-style chunk-and-crossfade using LuxTTS? No benchmark exists. [hume-tada-text-acoustic-alignment.md]

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
- [LuxTTS / ZipVoice-Distill deep dive](/workspace/research/deep-dives/luxtts-cpu-tts-candidate.md) -- CPU TTS feasibility assessment; ZipVoice-Distill architecture, RTF projections, integration plan for Path D
- [TADA deep dive](/workspace/research/deep-dives/hume-tada-text-acoustic-alignment.md) -- Text-acoustic dual alignment; CPU viability analysis; EARS benchmarks; comparison to LuxTTS for Path D
- [Voicebox deep dive](/workspace/research/deep-dives/voicebox-multi-engine-tts-studio.md) -- Multi-engine TTS studio architecture; reusable patterns (chunker, queue, TTSBackend Protocol); ROCm claim refutation
- [intake-251/252] Gemma 4 -- Any-to-Any multimodal models, pending GGUF
- [intake-317](https://github.com/OpenBMB/VoxCPM) VoxCPM2 -- Tokenizer-free TTS alternative, GPU-dependent
- [intake-396] Voicebox (jamiepine/voicebox) -- Multi-engine TTS studio; patterns adopted, ROCm discredited
- [intake-401] LuxTTS (YatharthS/LuxTTS) -- ZipVoice-Distill fine-tune with 48kHz vocoder; credibility 2/5 (fork), parent 4/5; Path D vehicle
- [intake-402] TADA (HumeAI/tada) -- Long-form TTS via text-acoustic dual alignment; GPU-only as shipped; shelved pending long-form workload or GPU access
