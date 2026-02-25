# MiniCPM-O 4.5 Integration Handoff

**Created**: 2026-02-10
**Status**: Active — model downloading, testing pending
**Priority**: Medium (future capability, not blocking)

## Model Summary

| Attribute | Value |
|-----------|-------|
| Model | MiniCPM-O 4.5 (openbmb/MiniCPM-o-4_5) |
| Parameters | 9B (Qwen3-8B + SigLip2 + Whisper-medium + CosyVoice2) |
| Architecture | Dense (NOT MoE) — end-to-end multimodal |
| License | Apache 2.0 |
| Modalities | Text + Vision + Audio in; Text + Speech out |
| Context | 40,960 tokens |
| GGUF repo | `openbmb/MiniCPM-o-4_5-gguf` |

## Files Downloaded

Location: `/mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/`

| File | Size | Purpose |
|------|------|---------|
| `MiniCPM-o-4_5-Q4_K_M.gguf` | 5.0 GB | Fast inference |
| `MiniCPM-o-4_5-Q5_K_M.gguf` | 5.9 GB | Balanced quality/speed |
| `MiniCPM-o-4_5-Q8_0.gguf` | 8.7 GB | Near-lossless |
| `vision/*` | ~660 MB | Vision encoder (SigLip2) |
| `audio/*` | TBD | Audio encoder (Whisper-medium) |
| `tts/*` | TBD | Speech decoder (CosyVoice2) |
| `token2wav-gguf/*` | TBD | Vocoder for speech output |

## Proposed Role: `audio_worker` (Tier D)

**Primary purpose**: Speech frontend for future voice interaction with orchestrator.

```
Mic → MiniCPM-O (ASR + intent) → text → Orchestrator API (:8000) → Specialist → response text → MiniCPM-O (TTS) → Speaker
```

**Secondary purpose**: Upgraded `worker_vision` (beats Qwen2.5-VL-7B by +7-12 points on most vision benchmarks).

### Proposed Registry Entry

```yaml
audio_worker:
  model: MiniCPM-o-4_5-Q4_K_M  # or Q5_K_M for quality
  port: 8088
  tier: D
  role: speech_frontend
  capabilities: [asr, tts, voice_cloning, emotion_control, vision]
  acceleration: none  # 8B dense — no MoE, spec decode unverified
  estimated_speed: 35-50 t/s (text), TBD (audio pipeline)
  memory: ~5-8 GB (depends on quant + multimodal components)
  framework: llama.cpp-omni  # NOT mainline llama.cpp for audio
  binary: llama-mtmd-cli  # mainline — vision+text only
```

## Key Findings

### What Works (mainline llama.cpp)
- Vision + text inference via `llama-mtmd-cli` (build b7712 supports it)
- All MiniCPM bugfixes included in production-consolidated
- Estimated 35-50 t/s text generation on EPYC 9655

### What Requires llama.cpp-omni Fork
- Audio input (ASR / Whisper-medium)
- Speech output (TTS / CosyVoice2)
- Full-duplex streaming
- Fork: https://github.com/tc-mb/llama.cpp-omni

### What's Untested
- Speculative decoding with Qwen3-0.6B draft (tokenizer matches, but multimodal pathway unknown)
- CPU inference speed for audio pipeline
- Quality at different GGUF quantization levels
- Integration with orchestration API

### What Won't Work
- MoE expert reduction (dense model)
- Audio in mainline llama.cpp (feature request #17634, no timeline)
- Replacing LightOnOCR for document_formalizer (LightOnOCR is SOTA at 1B, faster, better at raw OCR)

## Spec Decode Investigation

Qwen3-8B backbone shares tokenizer with Qwen3-0.6B (vocab 151,936, gpt2 tokenizer).

**Draft candidates on disk:**

| Model | Size | Expected Compatibility |
|-------|------|----------------------|
| Qwen3-0.6B-Q8_0 | 768 MB | High (same family) |
| Qwen3-1.7B-Q8_0 | 1.8 GB | High (31% acceptance w/ Qwen3-32B) |
| Qwen2.5-Coder-0.5B-Q8_0 | 507 MB | Maybe (same vocab, different family) |

**Test after download:**
```bash
python3 scripts/utils/check_draft_compatibility.py \
  /mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf \
  /mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/MiniCPM-o-4_5-Q8_0.gguf

# Functional test (text only, via llama-speculative):
timeout 60 /mnt/raid0/llm/llama.cpp/build/bin/llama-speculative \
  -m /mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/MiniCPM-o-4_5-Q8_0.gguf \
  -md /mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf \
  --draft-max 16 -t 96 -n 50 -p "Hello, how are you?"
```

## Benchmark Comparison vs Current VL Models

| Benchmark | MiniCPM-o 4.5 | Qwen2.5-VL-7B (port 8086) | Qwen3-VL-8B |
|-----------|---|---|---|
| OpenCompass | **77.6** | 70.5 | 76.5 |
| MathVista | **80.1** | 68.2 | 77.2 |
| MMMU | 67.6 | 58.6 | **69.6** |
| DocVQA | 94.7 | **95.7** | 96.1 |
| OCRBench | 876 | 864 | **896** |
| IFEval | **84.7** | ~80 | 83.7 |
| Tool calling | None | None | **0.663** |

## Speech Capabilities (Key Numbers)

| Metric | MiniCPM-O 4.5 | Standalone Equivalent |
|--------|---|---|
| ASR English WER | 2.5% | Whisper-large-v3: ~2.0-2.7% |
| ASR Chinese CER | 0.9% | — |
| TTS Long English WER | **3.37%** | CosyVoice2: 14.80% |
| Emotion control (ESD) | **82.1** | CosyVoice2: 53.4 |
| Voice cloning (seedtts-en WER) | 2.38% | CosyVoice2: 2.57% |
| Full-duplex | Yes | N/A |
| Languages (speech) | EN + ZH only | Whisper: 99 languages |

## Testing Plan

### Phase 1: Basic Vision+Text (mainline llama.cpp)
1. Run `llama-mtmd-cli` with Q4_K_M + vision mmproj
2. Test image description, OCR, document understanding
3. Measure text generation speed (t/s)
4. Compare quality with Qwen2.5-VL-7B on same prompts

### Phase 2: Spec Decode Investigation
1. Run `check_draft_compatibility.py` with Qwen3-0.6B
2. Attempt `llama-speculative` with text-only prompts
3. Measure acceptance rate and effective t/s

### Phase 3: Audio Pipeline (requires llama.cpp-omni)
1. Build llama.cpp-omni fork in `/mnt/raid0/llm/llama.cpp-experimental/`
2. Test ASR: audio file → text transcription
3. Test TTS: text → speech output
4. Measure end-to-end latency
5. Compare ASR quality with standalone Whisper

### Phase 4: Orchestrator Integration
1. Add `audio_worker` to model_registry.yaml
2. Create API route for audio requests
3. Build speech frontend → orchestrator → speech response pipeline
4. Test full-duplex streaming if supported on CPU

## Also Downloaded: Qwen3-VL-8B-Instruct

Location: `/mnt/raid0/llm/models/Qwen3-VL-8B-Instruct-GGUF/`
- `Qwen3-VL-8B-Instruct-Q4_K_M.gguf` (5.03 GB)
- `mmproj-Qwen3VL-8B-Instruct-F16.gguf`

**Why**: Closest competitor to MiniCPM-O for worker_vision upgrade. Beats MiniCPM-O on OCR (+20), DocVQA (+1.4), Video-MME (+1.0). Critically, **has tool calling support** (BFCL-v3: 0.663) which MiniCPM-O lacks. Should be tested head-to-head.

## Decisions Needed

1. **Priority**: When to start Phase 3 (llama.cpp-omni fork build)?
2. **Port allocation**: 8088 for audio_worker? Or repurpose 8086 (current worker_vision)?
3. **Dual role**: Should MiniCPM-O serve as both audio_worker AND worker_vision, or keep Qwen2.5-VL-7B for vision?
4. **Vision upgrade**: MiniCPM-O 4.5 vs Qwen3-VL-8B for worker_vision — test both, Qwen3-VL has tool calling edge.
