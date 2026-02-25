# Qwen3-TTS Voice Synthesis Integration

**Goal**: Add TTS to the orchestrator voice stack via Qwen3-TTS, ported to llama.cpp GGUF for CPU inference.

**Status**: Phase 4 BLOCKED — C++ binary generates codec tokens at 1.5x RT, but **audio output is unintelligible noise**. Whisper transcription confirms garbled output. Need PyTorch reference comparison to find divergence.

**Priority**: MEDIUM — Fills the last missing piece (TTS) in the voice pipeline

**Last Updated**: 2026-02-15

**Sources**:
- Qwen3-TTS repo: https://github.com/QwenLM/Qwen3-TTS
- HuggingFace collection: https://huggingface.co/collections/Qwen/qwen3-tts
- 0.6B Base: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base
- Audio codec: https://huggingface.co/Qwen/Qwen3-TTS-Tokenizer-12Hz
- Technical report: arXiv 2601.15621
- Pipecat (audio transport): https://github.com/pipecat-ai/pipecat
- OuteTTS reference (llama.cpp TTS): `kernel-dev/llama-cpp-dev/tools/tts/`
- Community GGUF (different model): https://huggingface.co/mradermacher/Qwen3-1.7B-Multilingual-TTS-GGUF
- Source code inspected: `qwen-tts==0.1.1` (extracted to `/mnt/raid0/llm/tmp/qwen-tts-pkg/qwen_tts_src/`)

---

## Resume Command

```bash
# Check handoff state
cat /mnt/raid0/llm/claude/handoffs/active/qwen3-tts-voice-synthesis.md

# Check artifacts
ls -la /mnt/raid0/llm/models/Qwen3-TTS*.gguf /mnt/raid0/llm/models/qwen3-tts-sidecar.bin

# Check C++ binary
/mnt/raid0/llm/llama.cpp-experimental/build/bin/llama-tts-qwen3 --help

# Check branch
cd /mnt/raid0/llm/llama.cpp-experimental && git branch --show-current  # should be feature/qwen3-tts-support

# Quick test (generates codec tokens to stdout, stderr has timing)
OMP_NUM_THREADS=48 numactl --interleave=all /mnt/raid0/llm/llama.cpp-experimental/build/bin/llama-tts-qwen3 \
  --model-talker /mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-Talker-Q4_K_M.gguf \
  --model-cp /mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-CodePredictor-Q8_0.gguf \
  --sidecar /mnt/raid0/llm/models/qwen3-tts-sidecar.bin \
  -p "Hello world." --max-frames 5 --temp 0.9 --seed 42 -t 48

# End-to-end WAV generation (requires venv with qwen-tts)
source /mnt/raid0/llm/venv/bin/activate && HF_HOME=/mnt/raid0/llm/cache/huggingface \
  python3 scripts/voice/validate_tts_e2e.py --text "Hello world." --output /mnt/raid0/llm/tmp/tts_test.wav --max-frames 30

# KEY ISSUE: Audio is noise. Debug next step:
# Generate PyTorch reference codec tokens, compare vs C++ tokens token-by-token.
# See PyTorch model source: /mnt/raid0/llm/tmp/qwen-tts-pkg/qwen_tts_src/qwen_tts/core/models/modeling_qwen3_tts.py
# Talker forward: line 1636, Code Predictor: line 1249
```

---

## Why This Matters

### The Missing Piece

Our voice stack has STT and LLM but no TTS output:

```
STT:  ✅ faster-whisper large-v3-turbo (port 9000, int8, 2.8x RT)
LLM:  ✅ Orchestrator (ports 8080-8087, production)
TTS:  ❌ MISSING — no voice output capability
```

Adding Qwen3-TTS completes the half-duplex voice loop:

```
Mic → Whisper(9000) → text → LLM(8080) → response → Qwen3-TTS(9002+9003) → Speaker
```

This also partially unblocks the PersonaPlex handoff (`handoffs/archived/personaplex_voice_interface.md`) — the "pseudo full-duplex" alternative described there requires TTS to exist.

### Why Qwen3-TTS Specifically

1. **Same model family** — all our Tier A-D models are Qwen. Shared tokenizer lineage, HF tooling, team familiarity
2. **Tiny footprint** — 0.6B model sits in Tier D alongside Qwen2.5-Coder-0.5B draft (~400MB quantized)
3. **Streaming-native** — dual-track architecture, 97ms first-packet latency
4. **10 languages** — covers our existing EN/IT/DE/FR Whisper config plus JA/KO/ES/PT/RU/ZH
5. **Voice cloning** — 3-second voice samples, useful for persona consistency

---

## Prior Art: Successful Ports

### LightOnOCR-2 (PyTorch VLM → GGUF, 19x speedup)
- **Pattern**: `convert_hf_to_gguf.py` + `--mmproj` for vision encoder + `llama-quantize`
- **Result**: Two GGUFs (text Q4_K_M 379MB + vision F16 782MB), FastAPI worker pool
- **Handoff**: `handoffs/completed/lightonocr_slowdown.md`, `handoffs/archived/lighton_ocr_integration.md`
- **Relevance**: Identical two-component pattern (LLM + codec vs LLM + vision encoder)

### OuteTTS in llama.cpp (TTS already supported)
- **Pattern**: `llama-tts` binary, two-server (LLM port 8020 + codec port 8021)
- **Conversion**: `convert_hf_to_gguf.py` for both OuteTTS-0.2-500M and WavTokenizer
- **Location**: `kernel-dev/llama-cpp-dev/tools/tts/`
- **Relevance**: Direct template. If Qwen3-TTS architecture is convertible, the serving pattern is proven.

---

## Qwen3-TTS Architecture (Source Code Verified)

> Verified from `qwen-tts==0.1.1` Python package source inspection (2026-02-14)

### Model Variants

| Model | Params | HuggingFace ID | Use Case |
|-------|--------|----------------|----------|
| Qwen3-TTS-12Hz-0.6B-Base | 0.6B | `Qwen/Qwen3-TTS-12Hz-0.6B-Base` | Voice cloning, fine-tuning |
| Qwen3-TTS-12Hz-0.6B-CustomVoice | 0.6B | `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` | 9 preset speakers |
| Qwen3-TTS-12Hz-1.7B-Base | 1.7B | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | Voice cloning, fine-tuning |
| Qwen3-TTS-12Hz-1.7B-CustomVoice | 1.7B | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | 9 preset speakers |
| Qwen3-TTS-12Hz-1.7B-VoiceDesign | 1.7B | `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` | NL voice descriptions |
| Qwen3-TTS-Tokenizer-12Hz | ~80M? | `Qwen/Qwen3-TTS-Tokenizer-12Hz` | Audio codec (encode/decode) |

### Full Architecture (3 Sub-Models)

```
Qwen3TTSForConditionalGeneration (model_type: "qwen3_tts")
│
├── talker: Qwen3TTSTalkerForConditionalGeneration (model_type: "qwen3_tts_talker")
│   ├── model: Qwen3TTSTalkerModel
│   │   └── 28-layer Qwen3-style transformer
│   │       hidden=1024, heads=16, kv_heads=8, intermediate=3072
│   │       MROPE (interleaved, sections=[24,20,20]), SiLU, RMSNorm, GQA — STANDARD QWEN3 TENSOR LAYOUT
│   ├── text_projection: MLP (2048 → 1024) — projects from text model
│   ├── codec_head: Linear (1024 → 3072) — predicts 1st codebook token
│   └── code_predictor: Qwen3TTSTalkerCodePredictorModel
│       └── 5-layer Qwen3-style transformer (model_type: "qwen3_tts_talker_code_predictor")
│           hidden=1024, heads=16, kv_heads=8, vocab=2048, intermediate=3072
│           Autoregressively predicts remaining 15 codebook entries
│
├── speaker_encoder: Qwen3TTSSpeakerEncoder (ECAPA-TDNN, only for "base" variant)
│   └── Conv1d + Res2Net + SqueezeExcitation blocks → 1024-dim embedding
│   └── mel_dim=128, enc_channels=[512,512,512,512,1536]
│   └── ~5M params estimate — TINY, NOT A TRANSFORMER
│
└── speech_tokenizer: Qwen3TTSTokenizerV2 (loaded from speech_tokenizer/ subdir)
    model_type: "qwen3_tts_tokenizer_12hz"
    ├── encoder: MimiModel (!!!) — Kyutai Mimi codec
    │   └── SAME architecture blocking PersonaPlex handoff
    │   └── Only needed for ENCODING audio (voice cloning reference)
    │   └── NOT needed for text→speech generation path
    └── decoder: Qwen3TTSTokenizerV2Decoder
        └── 8-layer transformer (1024 hidden, 16 heads, sliding_window=72)
        └── + ConvNet upsampler (8×5×4×3 = 480× upsample to waveform)
        └── 16 quantizers, 2048 codebook_size
        └── LayerScale (0.01 initial)
```

### Generation Flow (text → audio)

```
1. Text tokenized by Qwen3 tokenizer → input_ids
2. Text embeddings → text_projection (2048→1024)
3. Talker transformer (28 layers) → hidden states
4. codec_head predicts 1st codebook token
5. Code Predictor (5 layers) autoregressively generates 15 more codebook tokens
6. Repeat steps 3-5 for each audio frame (12.5 frames/sec)
7. All 16 codebook tokens per frame → Tokenizer Decoder → waveform
```

### Key Technical Details

| Property | Value |
|----------|-------|
| model_type (top-level) | `"qwen3_tts"` |
| model_type (talker) | `"qwen3_tts_talker"` |
| model_type (code predictor) | `"qwen3_tts_talker_code_predictor"` |
| model_type (tokenizer) | `"qwen3_tts_tokenizer_12hz"` |
| Talker tensor layout | `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj` — standard Qwen3 |
| num_code_groups | 16 (16 codebook entries per audio frame) |
| Codec vocab | 2048 per codebook |
| Streaming | Dual-track: text prefix → codec generation interleaved |
| 3D RoPE | Uses `get_rope_index()` with 3D position_ids (temporal, height, width) |
| Speaker conditioning | Via ECAPA-TDNN embedding injected into talker |

### Critical Finding: Mimi Connection

The audio codec encoder is **`MimiModel` from `transformers`** — Kyutai's Mimi, the EXACT same architecture that blocks the PersonaPlex handoff. However:

- **For TTS (text→audio)**: We only need the **decoder** path. Mimi encoder is NOT involved.
- **For voice cloning**: Mimi encoder is needed to encode the reference audio into codes. This is a one-time operation per voice, not real-time.
- **Implication**: The Mimi blocker does NOT block TTS deployment. It only affects real-time voice cloning during inference.

### Community GGUF (Different Model)

`mradermacher/Qwen3-1.7B-Multilingual-TTS-GGUF` is NOT official Qwen3-TTS:
- Base: `malaysia-ai/Qwen3-1.7B-Multilingual-TTS` (fine-tune of standard `Qwen3-1.7B-Base`)
- Uses NeuCodec (not Qwen3-TTS-Tokenizer-12Hz)
- Speech tokens as `<|s_{index}|>` in standard LM vocabulary
- model_type is standard `"qwen3"` → converts trivially to GGUF
- Available in Q2_K through F16 (889MB - 3.72GB)
- **Potential fallback** if official Qwen3-TTS GGUF port fails

---

## GGUF Convertibility Assessment

| Component | Architecture | GGUF Feasibility | Effort | Strategy |
|-----------|-------------|-------------------|--------|----------|
| **Talker** (28 layers, ~600M) | Qwen3-style transformer | ✅ **DONE** — extracted as Qwen3ForCausalLM facade | — | Tensor remapping + vocab padding, standard converter |
| **Code Predictor** (5 layers, ~50M) | Qwen3-style transformer | **HIGH** — nested but standard | Medium | Must be extracted/handled with Talker |
| **Speaker Encoder** (~5M) | ECAPA-TDNN (ConvNet) | **NONE** — not a transformer | N/A | Keep in PyTorch (tiny, CPU-cheap) |
| **Tokenizer Encoder** | MimiModel (Kyutai) | **BLOCKED** — same as PersonaPlex | N/A | Keep in PyTorch, only for cloning |
| **Tokenizer Decoder** (8 layers + ConvNet) | Transformer + upsampler | **LOW** — hybrid arch | High | Keep in PyTorch |

### Recommended Hybrid Architecture

```
llama.cpp (GGUF, CPU-optimized):
  └── Talker (28 layers, Q4_K_M 462MB) — generates 1st codebook token per frame
      → 168 t/s generation = 13.5x real-time headroom
      → Standard Qwen3 tensor layout via facade extraction

PyTorch (CPU, tiny models):
  ├── Code Predictor (5 layers, ~50M) — generates remaining 15 codebook tokens/frame
  ├── Speaker Encoder (ECAPA-TDNN, ~5M) — one-time per voice
  └── Tokenizer Decoder (8 transformer layers + ConvNet) — 16 codes/frame → waveform
      → Not the bottleneck (runs once per frame, small model)
      → ConvNet upsampler has no GGUF equivalent

Orchestration:
  FastAPI server wraps both, exposes single /v1/tts endpoint
  llama.cpp generates codes → PyTorch decoder converts to audio
  Pattern: identical to LightOnOCR (llama.cpp worker + Python wrapper)
```

### Conversion Challenges

1. **New model_type**: `"qwen3_tts_talker"` not in `convert_hf_to_gguf.py`. Needs handler.
2. **Nested code predictor**: The 5-layer Code Predictor lives inside Talker. Either:
   - Extract as separate GGUF (two llama-server instances), or
   - Custom inference loop calls llama.cpp for Talker, then Code Predictor
3. **32 codebook output**: Each audio frame produces 32 tokens via autoregressive Code Predictor.
   The `llama-tts` binary handles multi-codebook for OuteTTS — need to verify compatibility.
4. **3D RoPE**: Talker uses 3D position_ids (temporal/height/width). Unusual for TTS.
   May need custom RoPE handling in llama.cpp.
5. **text_projection MLP**: Projects from external text model (2048→1024). Extra weight tensors.

### Fallback: Community Approach

If official Qwen3-TTS GGUF conversion is too complex, the `malaysia-ai` approach works:
- Standard Qwen3-1.7B fine-tuned with speech tokens → converts to GGUF trivially
- Uses NeuCodec instead of Qwen3-TTS-Tokenizer-12Hz
- Lower quality but proven GGUF path (mradermacher already has Q2_K-F16)

---

## Investigation Plan

### Phase 1: Source Code Inspection ✅ COMPLETE (2026-02-14)

- [x] Inspect architecture — identified 3 sub-models via source code
- [x] Identify model_type — `"qwen3_tts"` (composite), NOT standard `"qwen3"`
- [x] Identify audio codec — MimiModel encoder + custom transformer decoder
- [x] Determine dense vs MoE — **Dense** (both Talker and Code Predictor)
- [x] Identify tensor layout — standard Qwen3 `q/k/v/o_proj, gate/up/down_proj`
- [x] Identify speaker encoder — ECAPA-TDNN ConvNet, ~5M params
- [x] Check community GGUFs — mradermacher has malaysia-ai variant (different model)

### Phase 2: Download & Convert ✅ COMPLETE (2026-02-14)

- [x] Downloaded `Qwen/Qwen3-TTS-12Hz-0.6B-Base` (1.8GB main + 651MB speech tokenizer)
- [x] Inspected config.json: 28 layers (not 20!), 16 heads, 8 kv_heads, hidden=1024, intermediate=3072
- [x] Inspected safetensors: 478 total tensors, 316 talker, 162 speaker_encoder
- [x] Confirmed `convert_hf_to_gguf.py` has NO `qwen3_tts` handler
- [x] **Extraction approach**: Extracted Talker as standalone Qwen3-compatible model
- [x] **GGUF conversion successful** via tensor remapping + Qwen3ForCausalLM facade

#### Conversion Method (Reproducible)

1. Extract `talker.model.*` → `model.*`, `talker.codec_head` → `lm_head`
2. Rename `model.codec_embedding` → `model.embed_tokens`
3. Remove `model.text_embedding` (151936×2048, external text model)
4. Remove `text_projection.*` (MLP, handled in PyTorch wrapper)
5. Pad `embed_tokens` and `lm_head` from 3072→151936 (match Qwen3 tokenizer)
6. Use standard Qwen3 tokenizer files + `Qwen3ForCausalLM` architecture string
7. Convert with `convert_hf_to_gguf.py` (standard Qwen3 path)

**Config correction**: Actual Talker has **28 layers** (not 20 as in default config class).

#### GGUF Files Produced

| File | Size | Location |
|------|------|----------|
| Talker F16 | 1.5 GB | `/mnt/raid0/llm/tmp/qwen3-tts-talker-f16.gguf` |
| Talker Q8_0 | 768 MB | `/mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-Talker-Q8_0.gguf` |
| Talker Q4_K_M | 462 MB | `/mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-Talker-Q4_K_M.gguf` |

#### Benchmark Results (llama-bench, EPYC 9655, numactl --interleave=all)

| Quant | Size | Prompt (pp32) | Generation (tg64) | RT Headroom (12.5 Hz) |
|-------|------|---------------|--------------------|-----------------------|
| Q8_0 | 768 MB | 223.6 t/s | **135.1 t/s** | **10.8x real-time** |
| Q4_K_M | 462 MB | 118.5 t/s | **168.2 t/s** | **13.5x real-time** |

Real-time requirement: 12.5 tokens/sec (Talker generates 1 token per 12.5 Hz audio frame).
With Code Predictor (15 additional tokens/frame): total ~200 t/s needed for sequential pipeline.
Both quantizations comfortably exceed real-time requirements.

- **Q4_K_M recommended** for production (smaller + faster generation)
- Model loads and runs in `llama-cli` on `llama.cpp-experimental` (`feature/qwen3-tts-support` branch, off upstream master `079feab9e`)

#### What's NOT in the GGUF (stays in PyTorch)

| Component | Reason |
|-----------|--------|
| `text_projection` (2048→1024 MLP) | Projects text embeddings into talker space |
| `text_embedding` (151936×2048) | Text token embeddings from external Qwen3 text model |
| Code Predictor (5 layers, 15 lm_heads, 15 embeddings) | Generates remaining 15 codebook entries per frame |
| Speaker Encoder (ECAPA-TDNN) | Voice cloning embedding extraction |
| Tokenizer Decoder (8 transformer layers + ConvNet) | Codes → waveform |

#### Extraction Script Location

`/mnt/raid0/llm/hf/Qwen3-TTS-12Hz-0.6B-Talker-Extracted/` — standalone Qwen3-compatible checkpoint

### Phase 3: Hybrid Server Prototype ✅ COMPLETE (2026-02-14)

- [x] Built FastAPI TTS server: `scripts/voice/tts_server.py`
- [x] Tested `llama-tts` binary — **INCOMPATIBLE**: Qwen3-TTS uses non-standard embedding injection
- [x] Full PyTorch bfloat16 server works end-to-end on CPU
- [x] Measured: latency, thread scaling, profiled decode vs generation bottleneck

#### Critical Discovery: llama-server API Cannot Drive TTS

The Talker's forward pass uses **custom input embeddings** — each step takes the SUM of all 16 code embeddings from the previous frame + text hidden states. Standard llama-server completion API expects token IDs, not pre-computed embedding vectors. This means:

- **llama-server's `/completion` endpoint**: ❌ Cannot inject custom embeddings
- **`llama-tts` binary**: ❌ Designed for OuteTTS single-code-per-frame pattern
- **CTranslate2**: ❌ KeyError on MROPE `rope_scaling` (no `factor` key)
- **torch.compile()**: ❌ No speedup (0.82x RT vs 0.89x baseline)

#### Server Details

- **Location**: `scripts/voice/tts_server.py`
- **Endpoints**: `POST /v1/tts` (WAV/PCM), `GET /health`, `GET /v1/models`
- **Language mapping**: ISO codes (en, zh, ja, ...) → full names (english, chinese, japanese, ...)
- **Concurrency**: asyncio.Lock (model not thread-safe)
- **Model load time**: 0.72s

#### Performance Benchmarks (EPYC 9655, numactl --interleave=all)

| Threads | dtype | Config | RTF | Speed |
|---------|-------|--------|-----|-------|
| 24 | bf16 | default | 1.35 | 0.74x RT |
| **48** | **bf16** | **greedy subtalker** | **1.11** | **0.90x RT** ← optimal |
| 96 | bf16 | default | 1.43-1.82 | 0.55-0.70x RT (contention) |
| 48 | f32 | default | 3.85 | 0.26x RT |

**Bottleneck analysis**:
- Talker generation (28 layers, autoregressive): ~90% of time
- Code Predictor (5 layers × 15 steps/frame): ~8% of time
- Tokenizer Decoder (codes → waveform): ~2% (0.67s for 7.7s audio)

**Root cause**: PyTorch autoregressive loop overhead. GGUF Talker benchmarks at 168 t/s (13.5x RT) but PyTorch can only achieve 0.9x RT with the same model — a **15x gap** from Python/PyTorch overhead (KV cache management, sampling, embedding injection between steps).

#### What's NOT in GGUF (Stays in PyTorch)

The Code Predictor has **15 separate lm_heads and 15 separate input embeddings** — one per codebook group. This multi-head architecture is not standard and would need custom handling in llama.cpp.

### Phase 4: llama.cpp Native TTS Pipeline — IN PROGRESS

**Approach chosen**: Option A — Custom C++ binary

**Branch**: `feature/qwen3-tts-support` in `llama.cpp-experimental` (off upstream master)

**Files**:
- `tools/tts-qwen3/tts-qwen3.cpp` — Main C++ binary
- `tools/tts-qwen3/CMakeLists.txt` — Build config
- `scripts/voice/create_tts_sidecar.py` — Sidecar weight generator (v2 format)

**Artifacts**:
- Talker GGUF: `/mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-Talker-Q4_K_M.gguf` (462 MB)
- Code Predictor GGUF: `/mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-CodePredictor-Q8_0.gguf` (395 MB)
- Sidecar weights: `/mnt/raid0/llm/models/qwen3-tts-sidecar.bin` (1463 MB, QWTTS02 format)

**Results** (with multi-head CP, 2026-02-15):
- Talker prefill: 405 t/s (21 tokens in 52ms, with embeddings enabled)
- Generation: **1.5x real-time** (8 sec audio in 5.2 sec) with temp=0.9, top_k=50
- End-to-end (C++ codec gen + Python Tokenizer Decoder): 4s audio in 3.8s = **1.06x RT**
- vs PyTorch baseline: **1.7x faster** (0.9x RT → 1.5x RT)
- Tokenizer Decoder: 0.74s for 4s audio (very fast, not bottleneck)
- Audio validated: 24kHz WAV, RMS=0.20, full dynamic range, 99.1% non-zero

**Bugs fixed during development**:
1. Sidecar header size mismatch: Python wrote 32 bytes, C struct was 36 (`reserved[2]` → `reserved`)
2. CP vocab size mismatch: CP uses 2048 vocab, not 3072 (added `cp_vocab` field to header v2)
3. `llama_kv_cache_clear` API removed → `llama_memory_clear(llama_get_memory(ctx), true)`
4. Logging not initialized → added `llama_backend_init()` + fprintf diagnostics
5. Multi-head CP: GGUF lm_head was lm_head[0] for all steps → enabled embeddings, apply correct sidecar lm_head[step]
6. Talker hidden states: CP now gets actual Talker hidden states via `llama_get_embeddings_ith()`

**BLOCKER: Audio output is unintelligible noise**

Whisper transcription of C++ output: "Assistant. Hello? This is the day of assistance!"
Expected: "Hello, this is a test of the text to speech system."

Suspects (ordered by likelihood):
1. **Chat template/prompt format wrong** — "assistant" audible in output = template leaking into audio
2. **Text embedding injection wrong** — projected text_embeds may not match what Talker expects
3. **Embedding sum formula wrong** — combination of 16 code embeds + text hidden may diverge from reference
4. **Float32 vs bf16 drift** — sidecar is float32, PyTorch uses bf16 (unlikely to cause this level of failure)

**Next action**: Generate PyTorch reference codec tokens for identical text, compare token-by-token to find first divergence point.

**Other known limitations**:
1. Text conditioning uses projected text embeddings (trailing_hidden approximation)
2. EOS relies on stale-frame heuristic (5 repeats) + max-frames
3. lm_head matmul for CP is single-threaded CPU float32

- [x] Extract Code Predictor as GGUF
- [x] Choose acceleration path → Option A
- [x] Implement native inference pipeline
- [x] Benchmark against PyTorch baseline (1.5x RT vs 0.9x RT)
- [x] Fix multi-head CP (apply correct lm_head[step] from sidecar via embeddings)
- [x] Extract Talker hidden states for CP past_hidden input
- [x] EOS detection (stale-frame heuristic + CODEC_EOS check)
- [x] End-to-end audio pipeline (C++ → Tokenizer Decoder → WAV)
- [ ] **BLOCKED: Debug audio quality** — compare C++ vs PyTorch codec tokens
- [ ] Fix whatever divergence is found
- [ ] Re-validate with Whisper round-trip test
- [ ] Cherry-pick to production-consolidated

### Phase 5: Integration

- [ ] Add to `orchestration/model_registry.yaml`
- [ ] Add to `docs/reference/models/QUIRKS.md`
- [ ] Create `scripts/voice/start_tts_server.sh` (launch wrapper)
- [ ] Test end-to-end: Whisper(9000) → LLM(8080) → TTS(9002) → audio

### Phase 6: Audio Transport (Deferred)

- [ ] Evaluate Pipecat for WebRTC/VAD/mic/speaker plumbing
- [ ] Or: minimal FastAPI WebSocket for streaming PCM chunks
- [ ] Update PersonaPlex handoff — pseudo-full-duplex with async VAD

---

## Resolved Questions

1. **Codec architecture**: ✅ RESOLVED — Encoder is **MimiModel** (Kyutai Mimi), same as PersonaPlex blocker. Decoder is custom transformer + ConvNet. Neither is WavTokenizer.
2. **Dense vs MoE**: ✅ RESOLVED — **Dense**. Both Talker (28 layers) and Code Predictor (5 layers) are dense transformers.
3. **Separate or embedded codec**: ✅ RESOLVED — **Separate model** (`Qwen/Qwen3-TTS-Tokenizer-12Hz`), loaded from `speech_tokenizer/` subdirectory inside the HF repo.
4. **Community GGUF status**: ✅ RESOLVED — mradermacher's GGUF is a **different model** (malaysia-ai fine-tune of vanilla Qwen3-1.7B, not official Qwen3-TTS).
5. **llama-server compatibility**: ✅ RESOLVED — **INCOMPATIBLE**. Talker needs custom embedding injection (sum of 16 code embeds + text hidden). Standard completion API only accepts token IDs.
6. **CTranslate2 Qwen3 support**: ✅ RESOLVED — **BLOCKED** by MROPE `rope_scaling` config (missing `factor` key).
7. **Optimal thread count**: ✅ RESOLVED — **48 threads** on EPYC 9655. 24 threads too few, 96 causes contention.
8. **PyTorch dtype**: ✅ RESOLVED — **bfloat16** is 3.5x faster than float32 on EPYC Zen 5 (native AVX-512 BF16).

## Unresolved Questions

1. ~~**GGUF handler**~~: ✅ RESOLVED — Bypassed entirely via Qwen3ForCausalLM facade extraction + tensor remapping
2. ~~**3D RoPE in llama.cpp**~~: ✅ RESOLVED — MROPE with sections [24,20,20] works via standard Qwen3 GGUF path; llama.cpp has MROPE support from Qwen2-VL
3. **Code Predictor GGUF extraction**: Has 15 separate lm_heads and 15 separate input embeddings. Not standard — needs custom architecture handler or multi-model serving approach.
4. **Embedding injection in llama.cpp**: Can `llama_decode()` accept `inputs_embeds` instead of token IDs? If yes, Option C (llama-cpp-python bindings) becomes viable.
5. **Audio quality under quantization**: TTS is perceptually sensitive. Q4_K_M vs Q8_0 vs F16 needs ABX testing.
6. **Streaming TTS**: Current server returns full WAV. Streaming needs chunked frame-by-frame decode with WebSocket transport.

---

## Model Registry Entry (Draft — Hybrid Architecture)

```yaml
# To be added to orchestration/model_registry.yaml after Phase 3
tts_server:
  url: http://localhost:9002
  port: 9002
  model_role: tts_generation
  description: "Qwen3-TTS voice synthesis (hybrid: llama.cpp Talker + PyTorch decoder)"
  model: Qwen/Qwen3-TTS-12Hz-0.6B-Base  # Full PyTorch for now; GGUF Talker at /mnt/raid0/llm/models/
  model_type: pytorch_tts  # Full PyTorch bfloat16, Phase 4 → llama.cpp native
  memory_gb: ~1.5  # ~1.2GB model + ~300MB runtime
  tier: warm
  languages: [chinese, english, japanese, korean, german, french, russian, portuguese, spanish, italian]
  acceleration:
    type: none  # Dense model, streaming precludes spec decode
  throughput: 0.9  # measured: 0.9x real-time (48t, bf16, EPYC 9655)
  latency_target_ms: 1100  # ~1.1x RTF → 1s audio takes 1.1s
  launch_script: scripts/voice/start_tts_server.sh
  notes: >
    Hybrid server: FastAPI wraps llama.cpp (Talker+CodePredictor → codes)
    and PyTorch (Tokenizer Decoder → waveform). Speaker Encoder (ECAPA-TDNN)
    loaded in PyTorch for voice cloning. Single endpoint, two inference backends.
    Pattern matches LightOnOCR (llama.cpp worker + Python wrapper).
```

---

## Target Voice Stack (Post-Integration)

```
┌─────────────────────────────────────────────────────────────┐
│                    VOICE PIPELINE                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐   │
│  │ Whisper  │    │   LLM    │    │   Qwen3-TTS          │   │
│  │ STT      │───→│ Orch.    │───→│ LLM(9002)+Codec(9003)│   │
│  │ :9000    │    │ :8080    │    │                      │   │
│  └──────────┘    └──────────┘    └──────────────────────┘   │
│       ↑                                    ↓                 │
│      Mic                               Speaker               │
│                                                              │
│  Transport: Pipecat (WebRTC) or FastAPI WebSocket (TBD)      │
├─────────────────────────────────────────────────────────────┤
│  Mode: Half-duplex (upgradeable to pseudo-full-duplex        │
│         with async VAD monitoring + generation cancellation) │
└─────────────────────────────────────────────────────────────┘
```

---

## Related Handoffs

| Handoff | Relationship |
|---------|-------------|
| `handoffs/archived/personaplex_voice_interface.md` | TTS fills missing piece; enables Option D alternative |
| `handoffs/archived/voice_recognition_setup.md` | STT component (COMPLETE, port 9000) |
| `handoffs/completed/lightonocr_slowdown.md` | Porting precedent (PyTorch → GGUF, 19x speedup) |
| `handoffs/active/ui-consolidated.md` | References Moshi GGUF as Phase E blocker |

---

## Blockers

| Blocker | Status | Unblock Condition |
|---------|--------|-------------------|
| `convert_hf_to_gguf.py` handler for `qwen3_tts_talker` | ✅ **RESOLVED** | Bypassed via Qwen3ForCausalLM facade extraction |
| PyTorch autoregressive loop overhead (0.9x RT) | ✅ **RESOLVED** | C++ pipeline at 1.5x RT (Phase 4) |
| Code Predictor multi-head extraction to GGUF | ✅ **RESOLVED** | Single GGUF + sidecar with 15 lm_heads/embeddings |
| Embedding injection in llama.cpp | ✅ **RESOLVED** | `llama_batch_init(n, n_embd, 1)` with `batch.embd` works |
| **C++ codec tokens produce noise audio** | **ACTIVE** | Need PyTorch reference token comparison to find divergence |
| Tokenizer Decoder stays PyTorch | **ACCEPTED** | Hybrid approach — not a blocker, by design |
| MimiModel encoder (for voice cloning) | **ACCEPTED** | Keep in PyTorch for cloning; pre-compute embeddings |

### Non-Blockers (Resolved)
| Item | Resolution |
|------|-----------|
| Architecture identification | Fully mapped from source code |
| Dense vs MoE | Dense — no MoE acceleration available, but also no MoE complexity |
| Codec architecture | MimiModel encoder + custom decoder. Decoder stays PyTorch. |

---

## References

- Qwen3-TTS announcement: https://github.com/QwenLM/Qwen3-TTS
- Pipecat framework: https://github.com/pipecat-ai/pipecat
- OuteTTS llama.cpp TTS: `kernel-dev/llama-cpp-dev/tools/tts/README.md`
- llama.cpp new arch guide: https://github.com/ggml-org/llama.cpp/discussions/16770
- LightOnOCR porting precedent: `handoffs/completed/lightonocr_slowdown.md`
- Whisper STT server: `scripts/voice/whisper_server.py`
