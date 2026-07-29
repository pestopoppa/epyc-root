# PersonaPlex Voice Interface - Handoff Document

**Goal**: Evaluate PersonaPlex-7B for full-duplex speech-to-speech voice interface (Alexa/Siri-like home assistant).

**Status**: BLOCKED - Moshi architecture not supported in llama.cpp

**Priority**: MEDIUM - Voice interface is future scope, not immediate

**Last Updated**: 2026-01-26

**Source**: https://huggingface.co/nvidia/personaplex-7b-v1

---

## Resume Command

```bash
# Check llama.cpp Moshi support status
grep -r "moshi" /mnt/raid0/llm/llama.cpp/src/ /mnt/raid0/llm/llama.cpp/ggml/ 2>/dev/null | head -5

# Check for community GGUF conversions
python -c "
from huggingface_hub import list_models
for m in list_models(search='personaplex gguf'):
    print(m.id)
"

# Read this handoff
cat /mnt/raid0/llm/claude/handoffs/active/personaplex_voice_interface.md
```

---

## Why This Matters

### Current Voice Stack
- **STT**: Whisper (faster-whisper server on port 9000)
- **LLM**: Orchestrator (various models)
- **TTS**: Not implemented (could use Coqui, Piper, etc.)
- **Mode**: Half-duplex (listen → process → speak)

### PersonaPlex Advantage
- **Full-duplex**: Listen AND speak simultaneously
- **Natural interruption**: User can interrupt, model handles gracefully
- **Persona control**: Text prompt defines personality, audio prompt defines voice
- **Low latency**: Designed for real-time conversation

### Use Case
Home assistant that:
- Responds naturally without "wake word → wait → response" cycle
- Handles interruptions ("Actually, never mind, do X instead")
- Maintains consistent voice/personality
- Supports EN/IT/DE/FR (matches Whisper multilingual)

---

## Architecture Comparison

### Current (Half-Duplex)
```
User speaks → Whisper STT → Text → LLM → Text → TTS → Audio
                  ↓
            [Full pause while processing]
```

### PersonaPlex (Full-Duplex)
```
User speaks ─────────────────────────────────→
            ↘ Audio tokens ↘
              PersonaPlex (streaming)
            ↗ Audio tokens ↗
Model speaks ←────────────────────────────────
            [Can overlap, interrupt, respond in real-time]
```

---

## Blocker: Moshi Architecture in llama.cpp

### Current Status

PersonaPlex is based on **Moshi** (Kyutai), which uses:
- Mimi Speech Encoder/Decoder (audio → tokens → audio)
- Moshi Temporal Transformer (text understanding)
- Moshi Depth Transformer (generation)

**llama.cpp does NOT support Moshi architecture.**

### Options to Unblock

| Option | Effort | Notes |
|--------|--------|-------|
| **A: Wait for community** | Low | Monitor llama.cpp issues/PRs for Moshi support |
| **B: Implement Moshi arch** | Very High | Would need to add new arch to llama.cpp |
| **C: Use PyTorch directly** | Medium | Works but requires GPU, loses CPU benefit |
| **D: Alternative model** | Medium | Find speech-to-speech model with llama.cpp support |

### Monitoring for Option A

```bash
# Check llama.cpp for Moshi discussions
# https://github.com/ggml-org/llama.cpp/issues?q=moshi
# https://github.com/ggml-org/llama.cpp/discussions?q=moshi

# Check for Kyutai Moshi GGUF conversions
# https://huggingface.co/models?search=moshi+gguf
```

---

## Phase 1: Validate Weights Downloadable

```bash
# PersonaPlex weights ARE available (confirmed 2026-01-26)
# https://huggingface.co/nvidia/personaplex-7b-v1

# Test download
export HF_HOME=/mnt/raid0/llm/cache/huggingface
python -c "
from huggingface_hub import snapshot_download
snapshot_download('nvidia/personaplex-7b-v1', local_dir='/mnt/raid0/llm/hf/PersonaPlex-7B')
"
```

---

## Phase 2: Test with PyTorch (GPU Required)

If GPU becomes available, test native inference:

```bash
# Clone PersonaPlex repo
git clone https://github.com/NVIDIA/personaplex /mnt/raid0/llm/personaplex

# Install dependencies
pip install -r /mnt/raid0/llm/personaplex/requirements.txt

# Run demo (requires NVIDIA GPU)
python /mnt/raid0/llm/personaplex/demo.py \
  --model nvidia/personaplex-7b-v1 \
  --voice-prompt sample_voice.wav \
  --text-prompt "You are a helpful home assistant"
```

**Note**: This project is CPU-only (AMD EPYC 9655). PyTorch test would require temporary GPU access.

---

## Phase 3: llama.cpp Moshi Implementation (If Pursuing)

### Reference: Adding New Architecture

See: https://github.com/ggml-org/llama.cpp/discussions/16770

Required work:
1. Add Moshi arch to `llama.cpp/src/llama-arch.cpp`
2. Implement Mimi codec in GGML
3. Add temporal + depth transformer support
4. Create `convert_hf_to_gguf.py` handler for Moshi
5. Test with PersonaPlex weights

**Estimated effort**: 2-4 weeks for experienced llama.cpp contributor.

---

## Alternative: Whisper + LLM + TTS Pipeline

If PersonaPlex remains blocked, enhance current stack:

### Components Needed

| Component | Status | Candidate |
|-----------|--------|-----------|
| STT | ✅ Done | faster-whisper (port 9000) |
| LLM | ✅ Done | Orchestrator |
| TTS | ❌ Missing | Coqui TTS, Piper, XTTS |
| VAD | ✅ In Whisper | Silero VAD |
| Interruption | ❌ Missing | Need async audio monitoring |

### Pseudo Full-Duplex

```python
# Run STT continuously in background
# Cancel LLM generation on new speech detection
# Achieves ~80% of full-duplex UX without Moshi
```

---

## Exploration Checklist

- [x] Confirm weights downloadable (HuggingFace)
- [ ] Check llama.cpp Moshi support status
- [ ] Monitor llama.cpp issues/PRs for Moshi
- [ ] If GPU available: test PyTorch inference
- [ ] Evaluate effort to implement Moshi in llama.cpp
- [ ] If blocked: design Whisper+LLM+TTS pseudo-duplex alternative
- [ ] Add TTS component to voice stack

---

## Success Criteria

1. **Full-duplex conversation**: User can interrupt mid-response
2. **Latency**: <200ms response initiation
3. **CPU inference**: Must run on EPYC 9655 (no GPU)
4. **Persona persistence**: Consistent voice across sessions

---

## Blockers

| Blocker | Status | Unblock Condition |
|---------|--------|-------------------|
| Moshi arch in llama.cpp | ACTIVE | Community implements OR we implement |
| GPU for PyTorch test | ACTIVE | Temporary GPU access for validation |

---

## References

- PersonaPlex: https://huggingface.co/nvidia/personaplex-7b-v1
- PersonaPlex GitHub: https://github.com/NVIDIA/personaplex
- Moshi (base): https://huggingface.co/kyutai/moshiko-pytorch-bf16
- llama.cpp new arch guide: https://github.com/ggml-org/llama.cpp/discussions/16770
- License: NVIDIA Open Model License + CC-BY-4.0
