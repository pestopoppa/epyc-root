# Multimodal

**Category**: `multimodal`
**Confidence**: verified
**Last compiled**: 2026-06-05
**Sources**: 34 documents (added 2026-06-05 LocateAnything/Gemma 4 benchmark-first update)

## Summary

The EPYC multimodal pipeline spans four modalities: speech-to-text (production), vision (code-complete), text-to-speech (blocked), and unified multimodal (downloaded/untested). The current voice loop has a gap: Mic -> Whisper (port 9000) -> text -> LLM -> response text -> NO TTS OUTPUT. Four TTS paths and two vision upgrade candidates are under evaluation.

Speech-to-text is the only multimodal component in production: faster-whisper large-v3-turbo running on port 9000 with int8 quantization at 2.8x real-time. The vision pipeline is code-complete at approximately 4,500 lines across 23 files with 1,234 tests passing, covering EXIF analysis, face detection/embedding (InsightFace), VL description (llama-mtmd-cli), CLIP embeddings, batch processing, video frame extraction, ChromaDB integration, and 11 API endpoints. It needs live validation with model servers running (Qwen2.5-VL-7B on 8086, Qwen3-VL-30B on 8087).

TTS has three existing paths, all blocked, plus one newly viable CPU-native candidate. Path A (Qwen3-TTS C++ port in llama.cpp) generates codec tokens at 1.5x real-time but outputs unintelligible noise -- the divergence point between PyTorch reference and C++ token generation has not been identified. Path B (MiniCPM-O 4.5 built-in CosyVoice2 TTS) requires the llama.cpp-omni fork and is untested. Path C (Qwen3-TTS as standalone PyTorch sidecar on port 8110) is viable for GPU-available deployments -- 97ms first-packet latency, 10-language support, voice cloning from 3 seconds of audio, Apache 2.0 licensed. Path D (ZipVoice-Distill / LuxTTS CPU sidecar) is the strongest candidate for CPU-only EPYC: the parent model (k2-fsa ZipVoice-Distill, ASRU 2025, Apache 2.0) achieves RTF=1.22 on a single Xeon thread at 4 flow-matching steps -- projected RTF of 0.15-0.22 on EPYC 9655 with 16 threads. LuxTTS is a thin fine-tune atop ZipVoice-Distill that adds a community-trained 48kHz Vocos vocoder; the 48kHz vocoder adds negligible overhead (<5% of total inference) and is not the bottleneck. Path D is a deployment exercise, not a research port -- upstream already ships ONNX export, INT8 quantization, and a sherpa-onnx C++ runtime. TADA (Hume AI, intake-402) introduces a distinct architectural approach (1:1 text-acoustic dual alignment over a Llama 3.2 backbone) suited for coherent long-form synthesis (up to 700 seconds), but is GPU-bound as shipped with no CPU benchmark or GGUF/ONNX path; it is shelved until long-form narration becomes a workload or GPU becomes available. Voicebox (intake-396) is a multi-engine TTS studio whose architecture patterns (TTSBackend Protocol, chunked_tts.py, serial asyncio queue) are directly reusable (~550 lines) for building an EPYC TTS sidecar; its claimed ROCm support is README-only with no implementation code.

Moondream 3 (9B total / 2B active MoE VLM) was evaluated and deferred. Despite interesting native detect/point capabilities, it is blocked by BSL 1.1 licensing, uncertain llama.cpp GGUF support for its novel MoE architecture (64 experts, learned attention temperature scaling), lack of tool calling (required for agentic vision), and preview-state unoptimized inference with no published standard benchmarks. The current Qwen2.5-VL-7B stack is more mature with full llama.cpp support and an escalation path to Qwen3-VL-30B-A3B.

MiniCPM-O 4.5 (9B dense, Qwen3-8B backbone + SigLip2 + Whisper-medium + CosyVoice2) offers unified multimodal capability. Vision + text works on mainline llama.cpp; audio features require the llama.cpp-omni fork. It scores 77.6 OpenCompass (vs Qwen2.5-VL-7B's 70.5) and 80.1 MathVista (vs 68.2), but lacks tool calling (0 vs Qwen3-VL-8B's 0.663 BFCL). The testing plan has four phases: mainline vision, spec decode investigation, omni fork audio, and orchestrator integration.

Gemma 4 (intake-251/252) introduces Any-to-Any multimodal models (text+image+audio unified). E4B (8B effective) could simplify the pipeline but is blocked by lack of GGUF support (MLX only). VoxCPM2 (intake-317) is a tokenizer-free multilingual TTS alternative requiring GPU (RTX 4090 for real-time), tracked for GPU upgrade path.

## Key Findings

- **Benchmark deployed Qwen-VL field placement before adding LocateAnything (2026-06-05).** The LocateAnything-3B form-fill demo is dominated by the 35B-A3B controller's huge prefill and turn count, not by the 3B visual grounding model alone. Because the stack already has Qwen3-VL-30B and Qwen2.5-VL-7B vision roles, the correct next step is a field-placement IoU benchmark on the deployed VLMs first; LocateAnything becomes a CPU-transformers precision A/B only if the existing VLMs miss the needed grounding precision. Sources: [progress 2026-06-05](../progress/2026-06/2026-06-05.md), [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md).
- **Gemma 4 should stay a benchmark candidate, not be dismissed from model-card priors.** The June 5 deep-dive corrected an overreach: Gemma 4 was newly released and had not been evaluated locally, so frontdoor/vision replacement claims must wait for EPYC suite results. The card metric previously read as MMMU was actually multilingual MMLU text; vision comparison should use the appropriate vision numbers and local tasks. Sources: [progress 2026-06-05](../progress/2026-06/2026-06-05.md), [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md).

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

## KAME — tandem speech-to-speech with parallel oracle injection (2026-04-30)

**TL;DR**: KAME (Sakana AI, ICASSP 2026, intake-511..515) pairs a Moshi-class real-time S2S front-end with a parallel text-LLM oracle stream that injects gradually-refined knowledge mid-utterance. MT-Bench-speech 2.05 (Moshi) → 6.43 (KAME). **Verdict: not_applicable for current EPYC scope** — Moshi audio-codec stack has no GGUF/llama.cpp support (same blocker class as existing Path D / Path E TTS work) and the front-end weights are tied to a specific Moshi base + KAME-specific simulated-oracle retraining recipe.

### Architecture (clarification: oracle is a fourth autoregressive stream, NOT an external API call)

The oracle stream is **not** an external API call into a frozen Moshi — it is a **fourth autoregressive stream within a 4-stream Moshi-style joint transformer**, sitting alongside input-audio / output-audio / inner-monologue streams. The front-end was specifically retrained on simulated-oracle-augmented data with a 6-level hint progression (Table 1 of the paper) to handle oracle text that progressively converges to ground-truth as user speech completes.

**Implication**: "back-end agnostic" is genuine — backend LLM (GPT-4.1 / Claude Opus 4.1 / Gemini 2.5 Flash in the reference impl) can be swapped via `OPENAI_BASE_URL` to a self-hosted llama-server. **But the front-end is fixed weights tied to a specific Moshi base + this specific training recipe.** You can swap Claude for GPT, but you cannot graft this onto an arbitrary Moshi without re-training.

### Closed-API claim correction

An earlier intake draft cited cloud-API dependencies (OpenAI Chat Completions + Google STT) as a verdict driver. Direct repo audit of `src/kame/server_oracle.py` shows `AsyncOpenAI()` instantiated with **no args**, which transparently honors `OPENAI_BASE_URL`. Backend swap to local llama-server is **one env var**. The closed-API dependency is convenience, not architecture. The real adoption blocker is (1) Moshi audio-codec stack absence in llama.cpp, (2) front-end retraining on simulated-oracle data, (3) GPU-only inference path, (4) no EPYC voice-interface use case on roadmap.

### Transferable pattern (recorded as competitive intelligence)

The "fourth autoregressive stream with most-recent-wins semantics, mid-decode update from a parallel slow path" is genuinely distinct from existing EPYC patterns:

| Pattern | Difference from KAME oracle stream |
|---------|-----------------------------------|
| Drafter / verifier speculative decoding | No token-level accept/reject; KAME oracle does not vote on tokens, it conditions generation |
| `worker_explore` → `coder` routing | Sequential, not parallel mid-stream |
| Hermes outer-shell + worker | Request-boundary coordination, not mid-utterance |
| Trinity learned coordinator | Per-turn dispatch, not intra-turn |

**Not worth a stub** — pattern is interesting but speculative without near-term implementation path. Recorded for awareness.

### Three concrete revival gates

In order of likelihood:

1. **CPU-only audio codec stack** lands — Mimi/Moshi-class neural codecs port to llama.cpp/GGUF, OR a credible CPU PyTorch path (AVX-512 BF16) exists. Same prerequisite as Paths A/D/E. If this resolves, multiple TTS systems unblock together and KAME becomes one of several candidates with an unusually clean backend-swap story.
2. **Open-weight KAME checkpoint** ships from Sakana (HF model card intake-515 exists; check periodically). Without weights, training requires GPU compute we don't have plus the audio + simulated-oracle pipelines.
3. **An EPYC voice-interface use case appears** that justifies the integration effort. Currently `multimodal-pipeline.md` is LOW priority; voice S2S has no production driver.

Items 1 and 2 are strongly coupled: if Sakana ships weights AND the codec stack ports, KAME becomes the first TTS Path with a fully-defined adoption sequence.

### Watch list

- **SHANKS** (arxiv:2510.06917, "Simultaneous Hearing and Thinking for Spoken Language Models") — adjacent same-quarter paper exploring similar speak-while-thinking territory but solving a *different problem* (interruption + tool-call-during-listen vs knowledge-grounded response). Tracked as sibling, NOT supersession. Ingest separately if it gains adoption.

### Sources

- [intake-511](https://arxiv.org/abs/2510.02327) KAME paper — Sakana AI, ICASSP 2026
- [intake-512](https://pub.sakana.ai/kame/) Sakana AI blog post (MT-Bench numbers, hot-swappable backends)
- [intake-513](https://github.com/SakanaAI/kame) Reference inference repo
- [intake-514](https://github.com/SakanaAI/kame_finetune) Finetune workflow (DeepSpeed, GPU-only)
- [intake-515](https://huggingface.co/SakanaAI/kame) HF model card
- [`research/deep-dives/kame-tandem-s2s-architecture.md`](../research/deep-dives/kame-tandem-s2s-architecture.md) — full deep-dive with paper analysis, oracle-mechanism audit, EPYC mapping, SHANKS comparison
- [`handoffs/active/multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md) — Research Intake Update 2026-04-30 + deep-dive refinement

## ERNIE-Image-Turbo (Baidu, 2026-05-06)

8B distilled DiT (Diffusion Transformer) text-to-image model evaluated for the multimodal pipeline. Apache-2.0. Distilled from a larger ERNIE-Image base via consistency distillation; targets fast inference (single-step or few-step generation) at competitive quality.

**Relevance to EPYC stack**: candidate for image generation in the multimodal pipeline (alongside Qwen3-VL for vision-understanding and faster-whisper for ASR). DiT inference on CPU is bandwidth-bound; quantized variants would need to land first to be production-viable on the EPYC 9655 host.

Sources: [research/deep-dives/ernie-image-turbo-dit-text-to-image.md](../research/deep-dives/ernie-image-turbo-dit-text-to-image.md), [handoffs/active/ernie-image-turbo-evaluation.md](../handoffs/active/ernie-image-turbo-evaluation.md).

## Multimodal pipeline (Vision + TTS + ASR) handoff

Coordinating handoff [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md) tracks the integrated multimodal stack: vision (Qwen2.5-VL-7B at port 8086 + Qwen3-VL-30B-A3B at port 8087), ASR (faster-whisper large-v3-turbo at port 9000), and TTS (planned). Image generation candidates (ERNIE-Image-Turbo, others) feed into this handoff via intake.

Source: [handoffs/active/multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md).

## Image generation deployment (production 2026-05-07)

ERNIE-Image-Turbo Q8 GGUF runs in production via stable-diffusion.cpp's native ggml backend (`sd-server`, port 8190), replacing an initial ComfyUI + ComfyUI-GGUF + PyTorch deployment. The swap delivered **2.54× wall-clock speedup** at production scale (~188 s vs 478 s @ 1024² 8 steps) without quality cost, by skipping ComfyUI-GGUF's per-layer dequant-to-BF16 step in favor of ggml's native Q8 GEMM kernels (AVX-512BW + VNNI on Zen 5).

Stack integration mirrors the document_formalizer (OCR) pattern: `start_sd_server()` in `orchestrator_stack.py`, launcher script at `scripts/diffusion/start_sd_server.sh`, registry entry `sd_server` (managed_by: orchestrator_stack), API exposed via `/sdapi/v1/txt2img` (sd-webui-compatible). The Hermes plugin path (`scripts/hermes/plugins/local-image-generate/`) routes through `ImageGenerator` → `SDServerClient` and replaces the disabled cloud `image_generate` (FAL) tool.

### Production tunings

| Flag | Effect | Notes |
|---|---|---|
| `--diffusion-fa` | Flash attention in DiT | enabled |
| `--diffusion-conv-direct` | `ggml_conv2d_direct` for DiT convs | enabled, within-noise on sampling but no downside |
| `--vae-conv-direct` | `ggml_conv2d_direct` for VAE convs | **enabled** — single biggest win, **7.10× on VAE decode alone** (76 s → 10.7 s at 832×1248), no quality cost |
| `numactl --interleave=all`, `-t 96` | Full-host pinning + thread span | canonical CPU baseline |
| Q8_0 weights | quantization | distilled-model penalty CONFIRMED at Q4_K_M (visible Korean-text corruption at 8 steps); Q8 is the production point |

### Empirical findings worth recording

- **stable-diffusion.cpp upstream already ships ERNIE-Image-Turbo support** (`src/ernie_image.hpp`, 441 lines). The "C++ port" we'd estimated as multi-week work was already done by upstream maintainers. Lesson: when a project moves at sd.cpp's pace and ERNIE-Image-Turbo is on huggingface, scan the upstream source before planning the port.
- **IPEX is a no-op on the ComfyUI-GGUF path**: `ipex.optimize()` cannot bind onto `GGMLTensor` parameters (which materialize to BF16 just-in-time inside `GGMLLayer.forward`). The dequant tax IS the bottleneck and IPEX cannot reach it. Confirmed via 2026-05-07 A/B at 512² 4-step (0–4% delta, measurement noise). [ernie-image-turbo-evaluation.md, progress/2026-05-07.md]
- **Distilled-model quantization-penalty hypothesis is real**: Q4_K_M at 8 steps delivers 17% wall-clock win at the cost of visible degradation on dense text rendering — exactly the model's signature differentiator (LongTextBench 0.9655 vs FLUX.1-dev 0.306). Mechanism prediction held: tight 8-step error budget cannot integrate out dequant noise the way a 50-step sampler would. Trade is bad for ERNIE specifically. [progress/2026-05-07.md]
- **ggml CPU backend is at the kernel ceiling on Zen 5 stock**: `-march=native` already emits AVX-512BW + VNNI (387 explicit `vpdpbusd`/`vpdpwssd` instructions in the binary). Further sampler win on CPU requires either porting our llama.cpp fork's AVX-512BW 8x8 Q8 kernel (estimate +10-20%, multi-day work) or waiting for GPU.
- **Hermes plugin path survived backend swap unchanged**: thin-interface discipline paid off — `ImageGenerator.generate(request) → result` interface was preserved across the ComfyUI → sd-server transition. Plugin code, Hermes tool registry, and dispatcher mapping all unchanged.

Sources: [progress/2026-05-07.md](../progress/2026-05/2026-05-07.md), [handoffs/active/ernie-image-turbo-evaluation.md](../handoffs/active/ernie-image-turbo-evaluation.md), [research/deep-dives/ernie-image-turbo-dit-text-to-image.md](../research/deep-dives/ernie-image-turbo-dit-text-to-image.md).

## Marlin-2B — video captioning + temporal grounding at 2B (NemoStation, 2026-05-20)

2B VLM fine-tune (base stated as "Qwen3.5-2B" but Qwen3.5 family is publicly 27B+ — likely Qwen2.5-VL-2B mislabel) trained via SFT on ~400K clip-level annotations followed by SimPO (reference-model-free preference optimization) with Gemini-3-Flash as the teacher/judge. Two convenience methods on the HF wrapper: `.caption()` returns scene + temporally-stamped events, `.find(query)` resolves natural-language queries to `(start, end)` spans. Apache-2.0, BF16, vLLM-compatible, single-H100-trained, 125 downloads/mo at intake.

**Author-reported benchmarks** (no third-party replication at intake time): tops CaReBench at 2B; positioned between Tarsier-34B and Gemini-1.5-Pro on DREAM-1K; +6.4 mIoU over Qwen2.5-VL-7B on TimeLens-Bench (Charades / ActivityNet / QVHighlights aggregate), matching Gemini-2.0-Flash.

**Relevance to EPYC stack**: low — no active video-captioning or temporal-grounding workload. The multimodal pipeline currently handles video only as ffmpeg-extracted frames fed through image-VLMs. Marlin-2B is BF16-only (no GGUF), so any deployment would require either a small dedicated GPU host or a llama.cpp conversion. Held at `worth_investigating` rather than `not_applicable` per the project's "consider creative deployment roles" policy — a small dense video model could plausibly serve as a frame-level event detector inside `src/vision/` if a GPU is added. Three revival gates documented: (i) a video-understanding workload appears, (ii) a small GPU is added, (iii) third-party benchmark replication of the +6.4 mIoU TimeLens claim. Base-architecture ambiguity should be resolved with NemoStation before any deployment.

Sources: [research/intake_index.yaml#intake-575](../research/intake_index.yaml), [handoffs/active/multimodal-pipeline.md#research-intake-update--2026-05-20](../handoffs/active/multimodal-pipeline.md).

## Intake deep-dives: Holo-3.1-4B & open-weights VLM/doc follow-ups (2026-06-12)

**Holo-3.1-4B (intake-691) — PARKED (runnability-gated).** H Company's 4B GUI-grounding/computer-use VLM (`Qwen3_5ForConditionalGeneration` arch, native function-calling, AndroidWorld 4B 58→71% self-reported, Apache-2.0). The deep-dive corrected a key intake error: **the 4B ships BF16 safetensors only — no GGUF/mmproj** (the intake-694 roundup conflated this with the 35B-A3B's official GGUF), and Qwen3.5 vision/mmproj on llama.cpp is still fragile (ggml-org #21268/#21271). Its grounding capability is **redundant** with the deployed Qwen3-VL-30B (:8087) / Qwen2.5-VL-7B (:8086). It remains a legitimate A/B contender vs LocateAnything-3B (intake-680) — better-licensed (Apache-2.0 vs NVIDIA non-commercial), native function-calling — **only if** a GUI-agent/screenshot workload enters the roadmap AND the deployed Qwen-VLs prove inadequate on field-placement IoU; even then, measure via a throwaway transformers-CPU worker, never a GGUF stack role.

**Open-weights roundup follow-ups (intake-694).** Triaging the 2026-06-05 HF roundup against the actual stack surfaced two VLM/doc-relevant P-items: **PaddleOCR-VL-1.6** (P1, Apache-2.0, 1B doc-parsing VLM on an ERNIE-4.5-0.3B backbone, OmniDocBench 96.33 SOTA, **official GGUF + mmproj** → CPU-runnable) is a candidate vs LightOnOCR for the doc pipeline (see document-processing / opendataloader handoff); and **Step-3.7-Flash** (P2, Apache-2.0, 196B/11B-active MoE VLM, SWE-Bench Verified 76.5, official GGUF) is a coder_escalation eval candidate. Image/video/music/3D generators (Ideogram 4, Magenta RT 2, Cosmos3-Super, TripoSplat, NAVA) are out of scope.

Sources: [`research/deep-dives/2026-06-12-holo-3.1-4b-gui-vlm.md`](../research/deep-dives/2026-06-12-holo-3.1-4b-gui-vlm.md), [`research/deep-dives/2026-06-12-open-weights-roundup-followups.md`](../research/deep-dives/2026-06-12-open-weights-roundup-followups.md), [`handoffs/active/multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md), intake-691/694.
