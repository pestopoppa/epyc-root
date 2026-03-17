# Multimodal Research Deep-Dive: Moondream 3 + Qwen3-TTS

**Date**: 2026-03-15
**Intake IDs**: intake-121 (Moondream 3), intake-123 (Qwen3-TTS)
**Status**: Research complete, integration assessment included

---

## Executive Summary

Two multimodal models assessed for potential integration into the EPYC orchestrator stack:

1. **Moondream 3 Preview** -- A 9B-total / 2B-active MoE vision-language model claiming frontier-level visual reasoning at edge-deployable size. Interesting as a potential replacement or complement to our Qwen2.5-VL-7B worker_vision role, but blocked by incomplete llama.cpp support and restrictive licensing.

2. **Qwen3-TTS** -- A 0.6B/1.7B dual-track text-to-speech system with 97ms first-packet latency, 10-language support, and voice cloning from 3 seconds of audio. Apache 2.0 licensed. Could add speech output as a new orchestrator modality with minimal VRAM overhead.

---

## Part 1: Moondream 3 Preview (intake-121)

### 1.1 Architecture

| Parameter | Value |
|-----------|-------|
| Total parameters | 9B |
| Active parameters | 2B (per token) |
| Architecture | MoE with GeGLU FFN |
| Total layers | 24 |
| Dense layers | First 4 |
| MoE layers | 20 (layers 5-24) |
| Experts per layer | 64 |
| Experts activated | 8 per token |
| Inner/gate dim | 1024 |
| Hidden dim | 2048 |
| Vision encoder | SigLIP with multi-crop channel concatenation |
| Context length | 32K tokens |
| Tokenizer | Custom SuperBPE ("starmie-v1") |
| Attention | Multi-head with learned position- and data-dependent temperature scaling |
| Precision | BF16 |

The model was initialized from Moondream 2 (a 2B dense model) via "drop upcycling" -- replicating the dense FFN into 64 expert copies and training the router on top. The first 4 layers remain dense, providing shared low-level feature extraction before the MoE routing kicks in.

**Vision pipeline**: SigLIP-based encoder with multi-crop channel concatenation for token-efficient high-resolution image processing. This is a well-proven approach (SigLIP is used by LLaVA-NeXT, InternVL, and others).

**Four integrated capabilities**:
- **Query** -- Open-ended VQA with optional reasoning mode
- **Caption** -- Short/normal/long image descriptions
- **Point** -- Object location identification (normalized x,y coordinates)
- **Detect** -- Bounding box detection (normalized 0-1 coordinates)

### 1.2 Benchmark Results

The Moondream team has published only preliminary benchmarks, with a note that "scores are expected to improve" and that some benchmarks used 100-question random samples (marked with *). The blog post shows a benchmark comparison image against frontier models but does not publish full numerical tables.

**Available scores**:

| Benchmark | Moondream 3 | Notes |
|-----------|-------------|-------|
| COCO object detection | 51.2 | +20.7 vs Moondream 2 |
| OCRBench | 61.2 | Up from 58.3 (Moondream 2) |
| ScreenSpot UI F1@0.5 | 60.3 | -- |
| ChartQA | 77.5 (82.2 w/ PoT) | Program-of-Thought prompting variant |

**Claims without published numbers**: The team claims Moondream 3 "surpasses GPT-5 and Claude 4 on multiple benchmarks" but does not provide numerical comparisons. Third-party coverage repeats these claims without independent verification. No published scores on MMMU, MathVista, DocVQA, or TextVQA were found.

**Assessment**: Without verified benchmark numbers, the "surpasses GPT-5" claims should be treated with skepticism. The model is a preview release and the team acknowledges it is still being trained.

### 1.3 Serving Requirements

| Metric | Value |
|--------|-------|
| VRAM (BF16, full) | ~19 GB |
| VRAM (Q4_K_M, estimated) | ~5-6 GB |
| Inference framework | transformers + FlexAttention |
| Compilation | `.compile()` required for fast decoding (includes warmup) |
| Quantized variants | 1 community GGUF variant exists |

The 2B active parameter count means that despite 9B total weights, inference compute is comparable to a 2B dense model. Memory, however, requires loading all 9B parameters since expert selection is dynamic per-token.

**Inference speed**: The blog states inference is "much slower than anticipated because the inference code hasn't been optimized yet." No published t/s numbers. For reference, Moondream 2 (2B dense, 4-bit) runs at ~184 t/s on RTX 3090.

### 1.4 llama.cpp / GGUF Compatibility

**Status: Partial / Uncertain**

- llama.cpp has historical support for Moondream 2 (the predecessor dense model)
- `llama-cpp-python` includes a `MoondreamChatHandler`
- Ollama lists `moondream` in its library (Moondream 2 only as of writing)
- The HuggingFace model card lists "llama.cpp, LM Studio, Jan, Ollama" as supported quantization formats
- However, Moondream 3 uses a novel MoE architecture with custom attention (learned temperature scaling) that may require architecture-specific support in llama.cpp
- Only 1 community GGUF quantization exists, suggesting limited adoption so far
- The `convert_hf_to_gguf.py` script in llama.cpp has been adding MoE support, but Moondream 3's specific MoE configuration (64 experts / 8 active with GeGLU) would need explicit architecture registration

**Verdict**: GGUF conversion may work if the architecture has been registered in recent llama.cpp builds, but this is unverified. The custom attention mechanism (learned temperature scaling) is a potential blocker. Needs hands-on testing.

### 1.5 Comparison to Current Stack (Qwen2.5-VL-7B)

| Dimension | Qwen2.5-VL-7B (current) | Moondream 3 Preview |
|-----------|------------------------|---------------------|
| Active params | 7B (dense) | 2B (MoE, 9B total) |
| VRAM (Q4_K_M) | 4.4 GB | ~5-6 GB (est.) |
| llama.cpp support | Full (native, mmproj) | Uncertain |
| Inference speed | ~44 t/s (our benchmarks) | Unknown (preview) |
| Tool calling | Yes (agentic vision) | No evidence |
| Bounding box / detection | Via prompt | Native `detect` mode |
| Object pointing | No | Native `point` mode |
| Context length | 32K | 32K |
| License | Apache 2.0 | BSL 1.1 + Use Grant |
| Escalation path | Qwen3-VL-30B-A3B | None |
| Production readiness | Mature, battle-tested | Preview, unoptimized |

**Key differences**:
- Moondream 3 has native detect/point capabilities that Qwen2.5-VL handles via prompting
- Moondream 3 has 2B active params (faster inference compute) but 9B total (similar or higher VRAM)
- Qwen2.5-VL has full llama.cpp support with mmproj, proven in our stack
- Qwen2.5-VL supports tool calls (agentic vision), which is critical for our orchestrator pipeline
- BSL 1.1 licensing on Moondream 3 is more restrictive than Apache 2.0

### 1.6 EPYC Integration Assessment

**Recommendation: DEFER -- not ready for integration**

Reasons:
1. **Licensing**: BSL 1.1 is restrictive for production use -- requires agreement for paid APIs and managed hosting
2. **llama.cpp support**: Unverified for Moondream 3's MoE architecture; would need testing
3. **No tool calling**: Our `worker_vision` role requires agentic capabilities (tool calls); Moondream 3 has no evidence of supporting this
4. **Preview state**: Team acknowledges unoptimized inference and incomplete benchmarks
5. **No escalation path**: We have Qwen3-VL-30B-A3B as vision_escalation; no equivalent exists for Moondream
6. **VRAM budget**: At ~19GB BF16 or ~5-6GB quantized, it does not offer significant VRAM savings over Qwen2.5-VL-7B (4.4GB Q4_K_M)

**When to re-evaluate**: If Moondream 3 reaches stable release with:
- Verified llama.cpp GGUF support
- Published benchmark tables with standard evals (MMMU, DocVQA, etc.)
- Tool calling capability
- License change to permissive (unlikely given M87's business model)

The native detect/point capabilities are interesting for specialized vision tasks (UI automation, object counting) but do not justify replacing our proven Qwen2.5-VL stack.

---

## Part 2: Qwen3-TTS (intake-123)

### 2.1 Architecture

Qwen3-TTS uses a **discrete multi-codebook language model** architecture that avoids the traditional LM + DiT (Diffusion Transformer) cascade, reducing compounding errors.

#### Dual-Track Tokenizer Design

| Component | Qwen-TTS-Tokenizer-25Hz | Qwen-TTS-Tokenizer-12Hz |
|-----------|--------------------------|--------------------------|
| Frame rate | 25 Hz | 12.5 Hz |
| Codebook design | Single-codebook | 16-layer multi-codebook |
| Semantic teacher | Qwen2-Audio (ASR task) | WavLM (first codebook) |
| Acoustic detail | Block-wise DiT reconstruction | 15-layer RVQ |
| Decoder | Block-wise flow matching | Lightweight causal ConvNet |
| First packet latency | ~190 ms (16 tokens needed) | **97 ms** (single frame) |
| Streaming support | Yes (block-wise) | Yes (causal, immediate) |
| Best for | High-fidelity, long-form | Ultra-low-latency, real-time |

**12Hz tokenizer details**:
- 12.5 frames per second
- 16 quantizers with 2048-entry codebook
- Semantic-acoustic disentanglement: first codebook = semantic (WavLM-supervised), codebooks 2-16 = acoustic (RVQ)
- Causal encoder/decoder: no look-ahead, processes frames sequentially
- Single-frame instant generation via MTP (Multi-Token Prediction) for residual codebooks

**25Hz tokenizer details**:
- Built on Qwen2-Audio encoder with VQ layer at intermediate position
- Two-stage training: (1) ASR continued pretraining, (2) semantic-acoustic joint optimization
- Better for long-form stability (lower WER on extended sequences)

#### Model Variants

| Model | Parameters | Size (est.) | Use Case |
|-------|-----------|-------------|----------|
| 1.7B-VoiceDesign | 1.7B | ~3.5 GB | Natural language voice descriptions |
| 1.7B-CustomVoice | 1.7B | ~3.5 GB | 9 premium timbres + style control |
| 1.7B-Base | 1.7B | ~3.5 GB | Voice cloning, fine-tuning capable |
| 0.6B-CustomVoice | 0.6B | ~1.2 GB | Lightweight, 9 timbres |
| 0.6B-Base | 0.6B | ~1.2 GB | Lightweight cloning |

**Note**: Only the 12Hz models are currently released on HuggingFace. The 25Hz models and tokenizer are requested by the community (GitHub issue #34) but not yet available.

### 2.2 Benchmark Results

#### Zero-Shot Voice Cloning (Seed-TTS Benchmark)

| System | Chinese WER | English WER | Speaker SIM |
|--------|------------|-------------|-------------|
| **Qwen3-TTS-1.7B** | **2.12%** | **2.58%** | **0.89** |
| MiniMax-Speech | Higher | Higher | Lower |
| ElevenLabs v2 | Higher | Higher | Lower |
| CosyVoice 3 | Higher | Higher | Lower |
| Seed-TTS | Higher | Higher | Lower |

(Exact competitor numbers not published in accessible tables, but paper states Qwen3-TTS achieves lowest WER and highest SIM across all 10 languages.)

#### Multilingual Performance (Average across 10 languages)

| Metric | Qwen3-TTS |
|--------|-----------|
| Average WER | 1.835% |
| Average Speaker SIM | 0.789 |
| Languages with best WER | 6 of 10 (CN, EN, IT, FR, KR, RU) |

#### Cross-Lingual Voice Cloning

The paper reports state-of-the-art cross-lingual performance, with particularly strong results in:
- Chinese-to-English: 4.82% WER (vs CosyVoice3's 14.4%)
- Robust across all source-target language pairs tested

#### Long-Form Stability

- Maintains consistent prosody over extended sequences
- Competing systems (e.g., Higgs-Audio-v2) show WER > 22% on long texts
- 25Hz variant outperforms 12Hz for long-form (semantic tokens better for stability)

#### Comparison with GPT-4o TTS

- Qwen3-TTS achieves lower WER in Japanese (3.88 vs 5.00) and Korean (1.74 vs 2.76)
- GPT-4o maintains slight edge in Italian, Portuguese, and French

### 2.3 Serving Requirements

| Metric | 0.6B Model | 1.7B Model |
|--------|-----------|------------|
| VRAM (BF16) | ~1-3 GB | ~3-5 GB |
| VRAM (with FlashAttention 2) | ~1-2 GB | ~2.5-4 GB |
| VRAM (INT4 quantized) | ~0.5-1.5 GB | ~1.5-2.5 GB |
| System RAM | Standard | Standard |
| First-packet latency (12Hz) | **97 ms** | **97 ms** |
| GPU minimum | 6 GB VRAM | 8 GB VRAM (comfortable) |
| Framework | PyTorch + qwen-tts package | PyTorch + qwen-tts package |
| FlashAttention 2 | Optional (30-40% speedup) | Optional (30-40% speedup) |

**Inference serving options**:
1. Direct Python (`Qwen3TTSModel.from_pretrained()`)
2. vLLM (compatible)
3. Gradio Web UI (local demo)
4. DashScope API (Alibaba cloud)

**Note**: No llama.cpp / GGUF support exists or is planned -- this is a PyTorch-native model with custom audio codec decoders that cannot be represented in GGUF format.

### 2.4 llama.cpp / GGUF Compatibility

**Status: Not applicable**

TTS models fundamentally differ from text LLMs:
- The output is not text tokens but audio codec tokens that must be decoded through a neural vocoder/ConvNet
- The 12Hz tokenizer uses a 16-layer multi-codebook with MTP (Multi-Token Prediction) that has no GGUF equivalent
- The causal ConvNet decoder is a separate neural network component
- Audio waveform reconstruction requires specialized DSP operations

Qwen3-TTS must run as a **separate service** with its own inference stack (PyTorch/vLLM), not through llama-server.

### 2.5 Comparison to Current Stack

We currently have **no TTS capability** in the EPYC orchestrator. The closest analog is the `worker_explore` role (Qwen2.5-7B on port 8082) used for web research synthesis, which is text-only.

Adding TTS would represent a **new output modality**, not a replacement for any existing role.

| Dimension | Current (none) | Qwen3-TTS-0.6B | Qwen3-TTS-1.7B |
|-----------|---------------|-----------------|-----------------|
| Speech output | None | 10 languages, 9 voices | 10 languages, 9 voices + voice design |
| Voice cloning | None | 3-second cloning | 3-second cloning + NL voice description |
| Latency | N/A | 97ms first packet | 97ms first packet |
| VRAM impact | 0 | ~1-3 GB | ~3-5 GB |
| License | N/A | Apache 2.0 | Apache 2.0 |
| Serving | N/A | Separate PyTorch service | Separate PyTorch service |

### 2.6 EPYC Integration Assessment

**Recommendation: VIABLE -- add as optional output modality**

#### Integration Architecture

Qwen3-TTS would not fit into the existing llama-server model slot pattern. Instead, it would be a **sidecar service**:

```
                                    +------------------+
                                    | Qwen3-TTS-0.6B   |
User request                        | (PyTorch service) |
    |                               | Port: 8110        |
    v                               +--------+---------+
+----------+    +-------------+              ^
| Frontdoor|--->| Orchestrator |----text----->|
+----------+    +-------------+              |
                       |                     v
                       +<----audio stream----+
                       |
                       v
                   [audio response to user]
```

**Proposed registry entry** (new role):

```yaml
worker_tts:
  tier: D
  port: 8110
  description: "Text-to-speech synthesis - streaming audio output"
  model:
    name: Qwen3-TTS-12Hz-0.6B-Base
    architecture: tts_codec_lm
    size_gb: 1.2
  server:
    endpoint: "http://localhost:8110"
    api_format: custom_tts  # Not OpenAI-compat
    framework: pytorch  # NOT llama-server
  capabilities:
    - streaming_audio
    - voice_cloning
    - multilingual_tts
  languages: [zh, en, ja, ko, de, fr, ru, pt, es, it]
```

#### Implementation Requirements

1. **New service launcher**: Cannot use `orchestrator_stack.py`'s llama-server pattern. Needs a dedicated PyTorch service script (similar to how LightOnOCR runs separately)
2. **API adapter**: Qwen3-TTS does not expose OpenAI-compatible endpoints. Need a thin FastAPI wrapper that accepts text + voice config, returns streaming audio
3. **Feature flag**: `ORCHESTRATOR_TTS_ENABLED` (default: false)
4. **Audio output path**: The orchestrator currently returns text only. Adding audio output requires:
   - New response field (`audio_url` or `audio_stream`)
   - Client-side audio playback support
   - Audio file storage/cleanup
5. **VRAM budget**: 0.6B model adds only ~1-3 GB, well within our headroom

#### Risks and Concerns

- **Scope creep**: TTS is a fundamentally different modality; adding it expands the orchestrator's surface area significantly
- **No llama-server integration**: Requires maintaining a separate inference stack
- **Quality validation**: No existing benchmark suite covers TTS; would need new evaluation infrastructure
- **Latency budget**: 97ms first-packet is excellent, but end-to-end through the orchestrator pipeline adds overhead
- **Voice cloning safety**: 3-second voice cloning raises ethical/misuse concerns that need policy guardrails

#### When to Proceed

TTS integration makes sense if:
1. There is a concrete user-facing product requirement for spoken output
2. The VRAM budget allows the additional ~1-3 GB
3. The API surface can be cleanly isolated behind a feature flag
4. Voice cloning is either disabled or gated behind explicit user consent

---

## Comparative Summary

| Dimension | Moondream 3 | Qwen3-TTS |
|-----------|------------|-----------|
| Modality | Vision input | Speech output |
| Replaces existing | Qwen2.5-VL-7B (partially) | Nothing (new capability) |
| Active params | 2B | 0.6B or 1.7B |
| VRAM cost | ~5-6 GB (Q4) / ~19 GB (BF16) | ~1-5 GB (BF16) |
| llama.cpp compat | Uncertain | Not applicable |
| License | BSL 1.1 (restrictive) | Apache 2.0 (permissive) |
| Integration effort | Medium (if GGUF works) | High (new service type) |
| Production readiness | Preview (not ready) | Released (1.0) |
| **Recommendation** | **DEFER** | **VIABLE (optional)** |

---

## Action Items

### Moondream 3
- [ ] Monitor for stable release with published benchmarks
- [ ] Test GGUF conversion when/if llama.cpp adds explicit moondream3 architecture support
- [ ] Re-evaluate if license changes to permissive

### Qwen3-TTS
- [ ] Prototype: standalone PyTorch service with FastAPI wrapper on port 8110
- [ ] Benchmark: measure actual VRAM usage and latency on our hardware (dual EPYC + RTX GPUs)
- [ ] Design: API adapter for streaming audio responses through orchestrator
- [ ] Policy: define voice cloning guardrails before enabling
- [ ] Registry: add `worker_tts` role definition (gated behind feature flag)

---

## Sources

- [Moondream 3 Preview - HuggingFace](https://huggingface.co/moondream/moondream3-preview)
- [Moondream 3 Preview Blog](https://moondream.ai/blog/moondream-3-preview)
- [Qwen3-TTS GitHub](https://github.com/QwenLM/Qwen3-TTS)
- [Qwen3-TTS Technical Report (arXiv:2601.15621)](https://arxiv.org/abs/2601.15621)
- [Qwen3-TTS Technical Report (HTML)](https://arxiv.org/html/2601.15621v1)
- [Qwen3-TTS-12Hz Tokenizer - HuggingFace](https://huggingface.co/Qwen/Qwen3-TTS-Tokenizer-12Hz)
- [Multimodal AI VLM Guide - BentoML](https://www.bentoml.com/blog/multimodal-ai-a-guide-to-open-source-vision-language-models)
- [Qwen3-TTS Performance Guide](https://qwen3-tts.app/blog/qwen3-tts-performance-benchmarks-hardware-guide-2026)
- [Qwen3-TTS Complete Guide - DEV Community](https://dev.to/czmilo/qwen3-tts-the-complete-2026-guide-to-open-source-voice-cloning-and-ai-speech-generation-1in6)
