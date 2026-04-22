# Multimodal Pipeline: Vision + TTS + ASR

**Created**: 2026-02-18 (consolidated from `vision-pipeline.md` + `qwen3-tts-voice-synthesis.md` + `minicpm-o-4_5-integration.md`)
**Status**: Mixed — Vision code-complete, TTS blocked, MiniCPM-O testing pending
**Priority**: LOW

---

## Current State Summary

| Modality | Status | Blocker |
|----------|--------|---------|
| **STT (ASR)** | Production | faster-whisper large-v3-turbo on port 9000, int8, 2.8x RT |
| **Vision** | Code complete, needs live validation | No blocker — just needs model servers running |
| **TTS** | Blocked | Qwen3-TTS llama.cpp port outputs noise; MiniCPM-O TTS untested |
| **Multimodal (MiniCPM-O)** | Downloaded, untested | Needs Phase 1 testing |

```
Current voice loop:
  Mic → Whisper(9000) → text → LLM(8080) → response text → ❌ NO TTS OUTPUT

Target:
  Mic → Whisper(9000) → text → LLM(8080) → response text → TTS(9002) → Speaker
```

---

## 1. Vision Pipeline (Code Complete)

**~4,500 lines across 23 files. Phases 1-7 complete. Chat pipeline integration done.**

### What's Done
- Full analysis pipeline: EXIF, face detection/embedding (InsightFace), VL description (llama-mtmd-cli), CLIP embeddings
- Batch processing with job queue, progress reporting
- Face recognition: detect, embed, cluster (HDBSCAN), label, search
- Video processing: ffmpeg frame extraction, frame-level analysis
- ChromaDB integration for persistent face/image storage
- `/chat` pipeline integration: DocumentPreprocessor, DocumentREPLEnvironment
- 11 API endpoints under `/v1/vision/*`
- 1234 tests passing

### What Remains
- **Live validation** with model servers running (Qwen2.5-VL-7B on 8086, Qwen3-VL-30B on 8087)
- OpenAI-compat multimodal support (parse image_url in message content)
- Register vision tools in tool registry for proactive delegation

### Key Files
- `src/vision/pipeline.py` (385 lines) — core pipeline
- `src/vision/analyzers/` — 6 analyzer modules
- `src/api/routes/vision.py` — API endpoints
- `tests/vision/` — test suite

### Validation Commands
```bash
# Test basic imports
python3 -c "from src.vision.pipeline import get_pipeline; print('OK')"

# Test with API running + model servers
curl -X POST localhost:8000/v1/vision/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/path/to/test.jpg", "analyzers": ["vl_describe"]}'
```

---

## 2. TTS: Two Competing Paths

### Path A: Qwen3-TTS via llama.cpp (BLOCKED)

**Status**: C++ binary generates codec tokens at 1.5x RT, but audio output is unintelligible noise.

Architecture (3 sub-models):
- **Talker**: 28-layer Qwen3-style transformer (0.6B) — standard tensor layout, GGUF-convertible
- **Code Predictor**: 5-layer transformer — predicts 15 remaining codebook entries per frame
- **Speech Tokenizer**: Mimi codec decoder — 8-layer transformer + ConvNet upsampler (480x)

Artifacts on disk:
- `/mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-Talker-Q4_K_M.gguf`
- `/mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-CodePredictor-Q8_0.gguf`
- `/mnt/raid0/llm/models/qwen3-tts-sidecar.bin`
- C++ binary: `/mnt/raid0/llm/llama.cpp-experimental/build/bin/llama-tts-qwen3`
- Branch: `feature/qwen3-tts-support` in llama.cpp-experimental

**Next debug step**: Generate PyTorch reference codec tokens, compare vs C++ token-by-token to find divergence point.

```bash
# Quick test (codec tokens only)
OMP_NUM_THREADS=48 numactl --interleave=all /mnt/raid0/llm/llama.cpp-experimental/build/bin/llama-tts-qwen3 \
  --model-talker /mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-Talker-Q4_K_M.gguf \
  --model-cp /mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-CodePredictor-Q8_0.gguf \
  --sidecar /mnt/raid0/llm/models/qwen3-tts-sidecar.bin \
  -p "Hello world." --max-frames 5 --temp 0.9 --seed 42 -t 48
```

### Path B: MiniCPM-O 4.5 Built-in TTS (UNTESTED)

MiniCPM-O has CosyVoice2 TTS built in. Key numbers:
- TTS Long English WER: **3.37%** (CosyVoice2 standalone: 14.80%)
- Emotion control: **82.1** (CosyVoice2: 53.4)
- Voice cloning WER: 2.38%

**Caveat**: Audio features require `llama.cpp-omni` fork, NOT mainline llama.cpp. See Section 3 below.

### Recommendation
Test Path B (MiniCPM-O) first — it's a complete package (ASR+TTS+Vision in one model). If audio quality is good, it may obviate the need for the Qwen3-TTS llama.cpp port entirely. Only resume Path A debugging if Path B fails or has unacceptable latency.

---

## 3. MiniCPM-O 4.5 (Multimodal: Vision + ASR + TTS)

**9B dense model** (Qwen3-8B backbone + SigLip2 + Whisper-medium + CosyVoice2). Apache 2.0.

### Files Downloaded
Location: `/mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/`

| File | Size | Purpose |
|------|------|---------|
| `MiniCPM-o-4_5-Q4_K_M.gguf` | 5.0 GB | Fast inference |
| `MiniCPM-o-4_5-Q5_K_M.gguf` | 5.9 GB | Balanced |
| `MiniCPM-o-4_5-Q8_0.gguf` | 8.7 GB | Near-lossless |
| `vision/*` | ~660 MB | SigLip2 encoder |

Also downloaded: `Qwen3-VL-8B-Instruct` (5.03 GB + mmproj) as direct competitor for vision.

### What Works (mainline llama.cpp)
- Vision + text inference via `llama-mtmd-cli`
- Estimated 35-50 t/s text generation on EPYC 9655

### What Requires llama.cpp-omni Fork
- Audio input (ASR / Whisper-medium)
- Speech output (TTS / CosyVoice2)
- Full-duplex streaming
- Fork: https://github.com/tc-mb/llama.cpp-omni

### Vision Benchmarks vs Current Models

| Benchmark | MiniCPM-o 4.5 | Qwen2.5-VL-7B (port 8086) | Qwen3-VL-8B |
|-----------|---|---|---|
| OpenCompass | **77.6** | 70.5 | 76.5 |
| MathVista | **80.1** | 68.2 | 77.2 |
| DocVQA | 94.7 | **95.7** | **96.1** |
| OCRBench | 876 | 864 | **896** |
| Tool calling | None | None | **0.663** |

### Eval Resource: MMLBD-C (Corrected Long-Document Benchmark)

LightOn released **MMLBD-C**, a manually corrected version of MMLongBenchDoc that fixes annotation errors in the original benchmark which inflate scores for models that hallucinate correct-seeming answers. Published alongside their OriOn 32B long-context VLM (344K context, ~250 pages). Consider using for end-to-end document pipeline evaluation when validating long-document QA accuracy across our VL models (Qwen2.5-VL-7B, Qwen3-VL-30B, MiniCPM-O).

- Paper: [arXiv:2602.15257](https://arxiv.org/abs/2602.15257)
- Blog: [lighton.ai/lighton-blogs/introducing-orion](https://www.lighton.ai/lighton-blogs/introducing-orion)
- OriOn itself (32B document QA model) evaluated but **not recommended** for our pipeline — we already use LightOn's OCR-2-1B for extraction and route QA to larger models. See assessment in progress log 2026-02-19.

### Proposed Role: `audio_worker` (Tier D)
- Port: 8088
- Primary: speech frontend (ASR + TTS)
- Secondary: potential `worker_vision` upgrade

### Testing Plan

**Phase 1** (mainline llama.cpp — vision+text only):
1. Run `llama-mtmd-cli` with Q4_K_M + vision mmproj
2. Benchmark vs Qwen2.5-VL-7B on same prompts
3. Test spec decode with Qwen3-0.6B draft

**Phase 2** (spec decode investigation):
```bash
python3 scripts/utils/check_draft_compatibility.py \
  /mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf \
  /mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/MiniCPM-o-4_5-Q8_0.gguf
```

**Phase 3** (llama.cpp-omni — audio):
1. Build llama.cpp-omni fork in `/mnt/raid0/llm/llama.cpp-experimental/`
2. Test ASR: audio file → text
3. Test TTS: text → speech
4. Compare ASR with standalone Whisper (9000)

**Phase 4** (orchestrator integration):
1. Add `audio_worker` to model_registry.yaml
2. Build speech frontend → orchestrator → speech response pipeline

---

## Decisions Needed

1. **Vision upgrade**: MiniCPM-O 4.5 vs Qwen3-VL-8B for `worker_vision`? Qwen3-VL has tool calling edge (+0.663 BFCL).
2. **TTS path**: Debug Qwen3-TTS C++ port vs test MiniCPM-O native TTS first?
3. **Port allocation**: 8088 for `audio_worker`? 8086 stays Qwen2.5-VL or gets replaced?
4. **llama.cpp-omni**: When to build the fork? Blocks all MiniCPM-O audio features.

---

## Resume Commands

```bash
# Vision validation
python3 -c "from src.vision.pipeline import get_pipeline; print('OK')"
pytest tests/vision/ -v

# MiniCPM-O vision test (mainline, no audio)
/mnt/raid0/llm/llama.cpp/build/bin/llama-mtmd-cli \
  -m /mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/MiniCPM-o-4_5-Q4_K_M.gguf \
  --mmproj /mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/vision/mmproj.gguf \
  -p "Describe this image in detail" --image /path/to/test.jpg

# Qwen3-TTS debug (if resuming Path A)
cd /mnt/raid0/llm/llama.cpp-experimental && git branch --show-current
```

## Research Intake Update — 2026-03-14

### New Related Research
- **[intake-123] "Qwen3-TTS"** (arxiv:2601.15621)
  - Relevance: Open-source TTS directly relevant to the blocked TTS component of this pipeline
  - Key technique: Dual-track language model architecture with two speech tokenizers — 25Hz for semantic content (streaming) and 12Hz for ultra-low-latency (97ms first-packet)
  - Reported results: 1.835% WER across 10 languages, 0.789 speaker similarity; outperforms MiniMax and ElevenLabs
  - Delta from current approach: TTS was blocked on voice synthesis integration. Qwen3-TTS is Apache 2.0, supports voice cloning with 3s reference audio, and has a HuggingFace Space demo. Could unblock the TTS component.

- **[intake-121] "Moondream 3 Preview"**
  - Relevance: Compact MoE VLM (9B total / 2B active) could serve as an efficient vision worker
  - Key technique: 64 experts / 8 activated per token, first 4 layers dense, SigLIP vision encoder, 32K context
  - Delta from current approach: Vision pipeline uses larger models. Moondream3's 2B active params with MoE efficiency could be a faster alternative for simple vision tasks.

### Deep-Dive Findings (2026-03-15)

**Source**: `research/deep-dives/multimodal-moondream3-qwen3tts.md`

#### Moondream 3: DEFER

Full assessment confirms deferral. BSL 1.1 license is restrictive for production. llama.cpp GGUF support unverified for Moondream 3's novel MoE architecture (64 experts, learned attention temperature scaling). No tool calling capability (our `worker_vision` requires agentic tool calls). Preview state with unoptimized inference and no published standard benchmarks (MMMU, DocVQA, TextVQA). No escalation path (we have Qwen3-VL-30B-A3B for vision_escalation). The native detect/point capabilities are interesting but don't justify replacing our proven Qwen2.5-VL stack.

**Re-evaluate if**: Stable release with verified GGUF, published benchmarks, tool calling, or license change.

#### Qwen3-TTS: VIABLE as PyTorch Sidecar (Alternative Path C)

The deep-dive confirms Qwen3-TTS cannot run through llama-server (audio codec decoder, multi-codebook MTP, ConvNet upsampler are all non-GGUF). However, it works well as a **standalone PyTorch service**:

| Attribute | Value |
|-----------|-------|
| Model | Qwen3-TTS-12Hz-0.6B-Base |
| VRAM | ~1-3 GB (BF16) |
| First-packet latency | 97 ms |
| Languages | 10 (zh, en, ja, ko, de, fr, ru, pt, es, it) |
| Voice cloning | 3-second reference audio |
| License | Apache 2.0 |
| Serving | PyTorch + FastAPI wrapper on port 8110 |

This represents a **third TTS path** alongside Path A (Qwen3-TTS C++ port, blocked) and Path B (MiniCPM-O built-in TTS, untested):

- **Path C**: Run Qwen3-TTS-0.6B as a standalone PyTorch sidecar service. No llama.cpp dependency. FastAPI wrapper accepting text + voice config, returning streaming audio. Feature-flagged behind `ORCHESTRATOR_TTS_ENABLED`.

**Advantage over Path A**: No C++ debugging needed — uses official PyTorch inference. **Advantage over Path B**: Independent service, doesn't couple TTS to a specific vision model. **Disadvantage**: Separate inference stack to maintain (PyTorch, not llama-server).

**Action items** (when TTS becomes a priority):
- [ ] Prototype: FastAPI wrapper around `Qwen3TTSModel.from_pretrained()` on port 8110
- [ ] Benchmark VRAM and latency on EPYC hardware
- [ ] Add `worker_tts` role to model_registry.yaml (gated behind feature flag)
- [ ] Design voice cloning guardrails before enabling

## Research Intake Update — 2026-03-17

### New Related Research
- **[intake-161] "OpenDataLoader PDF - PDF Parser for AI-ready data"** (repo: opendataloader-project/opendataloader-pdf)
  - Relevance: Direct alternative/upgrade for the orchestrator's document processing pipeline (`pdf_router.py` → pdftotext/LightOnOCR → document_chunker)
  - Key technique: XY-Cut++ reading order algorithm, hybrid local+AI extraction, 0.93 table accuracy
  - Reported results: 0.90 overall accuracy (#1 vs docling 0.86, marker 0.83, pymupdf4llm 0.57); 0.05s/page local, 0.43s/page hybrid
  - Delta from current approach: Current pipeline splits born-digital (pdftotext) vs scanned (LightOnOCR) with no dedicated table extraction. OpenDataLoader provides unified extraction (text + tables + figures + bboxes) with built-in prompt injection filtering. Trade-off: Java dependency vs current pure Python+CLI stack. Python SDK available (`langchain-opendataloader-pdf`).
  - Evaluation path: Benchmark against current `pdf_router.py` on real document workloads, especially multi-column and table-heavy PDFs

## Research Intake Update — 2026-04-04

### New Related Research
- **[intake-251] "Gemma 4 MLX Collection"** (HuggingFace mlx-community)
  - Relevance: Gemma 4 E2B/E4B are Any-to-Any multimodal models (text+image+audio)
  - Key technique: E4B (8B effective) and E2B (5B effective) with multimodal I/O
  - Delta from current approach: Our multimodal pipeline uses separate STT/Vision/TTS models. Gemma 4 E-series unifies modalities in a single model — could simplify the pipeline
  - Blocker: No GGUF available yet (MLX only). Need llama.cpp conversion to evaluate on EPYC
- **[intake-252] "Gemma 4 Official — DeepMind"** (deepmind.google)
  - Additional context: 26B-A4B is MoE (4B active) — comparable to our Qwen3.5-35B-A3B slot. FunctionGemma variant relevant to tool-use/agentic tasks

## Research Intake Update — 2026-04-12

### New Related Research
- **[intake-317] "VoxCPM2: Tokenizer-Free Multilingual TTS"** (OpenBMB/VoxCPM)
  - Relevance: Alternative TTS system — tokenizer-free diffusion autoregressive, 30 languages, Apache 2.0
  - Key technique: Four-stage pipeline (LocEnc→TSLM→RALM→LocDiT), AudioVAE V2, MiniCPM-4 backbone
  - RTF ~0.13 on RTX 4090, 48kHz studio quality, voice cloning + voice design from text descriptions
  - Delta from current approach: Our Qwen3-TTS is blocked (outputs noise in llama.cpp). VoxCPM2 is tokenizer-free (avoids discrete token ceiling) but requires GPU (RTX 4090 for real-time). Blocked by same GPU constraint. Worth tracking for GPU upgrade path.

## Research Intake Update — 2026-04-17

### New Related Research

- **[intake-396] "Voicebox — Open-Source Voice Synthesis Studio (local-first ElevenLabs alternative)"** (repo: jamiepine/voicebox)
  - Relevance: directly addresses the BLOCKED TTS component. Bundles 5 engines behind a unified interface with AMD ROCm + CPU backends.
  - Key technique: unified multi-engine adapter, sentence-boundary auto-chunking with crossfade for unlimited-length synthesis, Spotify pedalboard DSP post-processing chain.
  - Reported results: LuxTTS claim of ~1GB VRAM and 150x realtime on CPU at 48kHz (self-reported). Chatterbox Turbo with inline paralinguistic tags.
  - Delta from current approach: adds a **Path D** (CPU-native LuxTTS) option beyond current Path A (Qwen3-TTS llama.cpp — noise), Path B (MiniCPM-O — untested), Path C (Qwen3-TTS PyTorch sidecar).

- **[intake-401] "LuxTTS — Lightweight ZipVoice-Distilled TTS with 48kHz Voice Cloning"** (HF: YatharthS/LuxTTS, discovered via voicebox)
  - Relevance: **strongest candidate for unblocking TTS on CPU-only EPYC**. Distilled ZipVoice (arxiv:2506.13053) with 4 flow-matching steps, <1GB VRAM, faster-than-realtime CPU claim.
  - Key technique: flow distillation to 4 steps, custom 48kHz vocoder, improved sampler over Euler.
  - Reported results: self-reported 150x RT GPU, faster-than-RT CPU, no published WER/MOS. Apache 2.0 license.
  - Caveats: single-author HF upload, no formal benchmarks, third-party reviews note "slightly mechanical pacing" vs heavier models, language coverage ambiguous (English-only per model card).
  - Delta: if CPU RTF <1.0 holds in our measurement, replaces Path A/C with a simpler sidecar.

- **[intake-402] "Opensourcing TADA: Fast, Reliable Speech Generation Through Text-Acoustic Synchronization"** (Hume AI, arxiv:2602.23068, discovered via voicebox)
  - Relevance: **long-form (700s+) coherent synthesis** unique candidate for future long-document/narration use cases.
  - Key technique: 1:1 text-acoustic dual alignment on a Llama-3.2-1B backbone with flow-matching decoder; Speech Free Guidance (SFG).
  - Reported results: RTF 0.09 (>5x peer LLM-TTS), 0 hallucinations/1000+ LibriTTSR samples, 4.18/5.0 speaker similarity, 3.78/5.0 naturalness on EARS eval (2nd overall), ~700s in 2048-token context.
  - Caveats: speaker drift beyond ~700s, limited multilingual (9 langs), commercial-vendor self-reported benchmarks, audio-head non-trivial to port to GGUF/llama.cpp.
  - Delta: if long-form TTS becomes a workload, 1B checkpoint fits EPYC's CPU profile; otherwise shelve until blocked pipeline is revisited.

### Recommended Next Steps
1. Run CPU benchmark of LuxTTS on EPYC: measure RTF, first-packet latency, voice-clone WER → decide Path D viability.
2. Inspect voicebox's engine-adapter code (Tauri/TypeScript) for a unified-interface pattern to reuse across Paths A–D.
3. Flag TADA for review when multimodal pipeline unblocks — it addresses a distinct long-form use case not solvable by shorter-context TTS models.

## Research Intake Update — 2026-04-22

### New Related Research

- **[intake-432] "Qwen3.5-Omni Technical Report"** (arxiv:2604.15804)
  - Relevance: Potential unblock for Path A/B/C/D TTS work. Native end-to-end omni-modal (text+audio+image+video) at hundreds-of-billions scale with ARIA (Adaptive Rate Interleave Alignment) for stable streaming speech synthesis.
  - Key technique: Hybrid Attention MoE Thinker+Talker components; ARIA dynamic text-speech alignment; dual-tokenizer audio (25Hz semantic + 12Hz acoustic).
  - Reported results: SOTA across 215 audio/AV benchmarks; surpasses Gemini-3.1 Pro on key audio tasks; 10 languages with emotional nuance; 400s of 720P video in single context.
  - Delta from current approach: Existing TTS paths A/B/C/D are blocked or CPU-infeasible. Qwen3.5-Omni is a candidate if (a) open weights / GGUF are available, (b) audio-codec decode is CPU-feasible on NUMA 4-way, (c) inference budget fits. Worth a feasibility probe before committing to any existing TTS path.

- **[intake-435] "PersonaVLM: Long-Term Personalized Multimodal LLMs"** (arxiv:2604.13074)
  - Relevance: Cross-reference only. Single-user EPYC design per `project_autopilot_stack_assembly` makes direct personalization work low priority. Chronological multimodal memory extraction and 128k context patterns are reference material for any future multi-user work.
  - Key technique: Proactive memory extraction + multi-turn reasoning + personality-aligned generation + Persona-MME benchmark (2,000+ cases, 7 aspects, 14 tasks).
  - Delta: Not actionable under current single-user constraint; file as reference.

### Next Actions (scoped for this handoff)

- [ ] Check Qwen3.5-Omni for open-weight release / GGUF availability on HuggingFace
- [ ] If available: estimate CPU inference cost for audio-codec path (ARIA pipeline) on one NUMA node
- [ ] Decide whether Qwen3.5-Omni becomes a new TTS Path E or supersedes existing paths

## Deep-Dive Integration — 2026-04-22 (DD2 verdict)

**Source**: `/workspace/research/deep-dives/qwen35-omni-tts-unblock.md` (401 lines). Adoption decision: **Scenario C — NOT open-weight, file as reference, no adoption.**

Alibaba broke its Apache-2.0 tradition and released Qwen3.5-Omni on 2026-03-30 as **API-only** (Alibaba Cloud / Qwen Chat / HF demo Space). No weight release is announced; no GGUF path exists; the only `Qwen3.5-Omni-GGUF` on HF is a 2B community derivative fine-tune, not official.

**Decision**: **Path D (ZipVoice-Distill / LuxTTS) remains the primary EPYC TTS unblock path.** No Path E added.

**Corrections to intake-432 entry**:
- Tokenizer description was wrong: paper uses unified 6.25Hz AuT + RVQ codec, NOT dual 25Hz+12Hz (that's Qwen3-TTS's design; the intake brief conflated them). Correction applied 2026-04-22.
- Intake-432 verdict updated: `new_opportunity` → `reference_only` with `adoption_blocker: closed_source_api_only`.

**Preserved patterns (transplantable ideas)**:
- **ARIA dynamic rate-cap**: even without weights, the ARIA mechanism (adaptive per-prefix text/speech ratio cap to prevent cascading generation errors) is a candidate **debug intervention for Path A** if Path A's noise-output issue is ever revisited. Pattern documented here for future reference.
- **Thinker+Talker split**: generic pattern (generator + speech head) is already in our existing Path C plan; Qwen3.5-Omni validates it at scale.

**Monitor**: **Qwen3-Omni-30B-A3B (Apache 2.0)** is the open-weight sibling to Qwen3.5-Omni. Quarterly check for CPU-viable GGUF conversions. If it lands, it supersedes Path D and becomes a credible Path E.

**Cross-references**:
- `/workspace/research/deep-dives/qwen35-omni-tts-unblock.md` (full analysis)
- `/workspace/research/deep-dives/luxtts-cpu-tts-candidate.md` (Path D baseline)
- `inference-acceleration-index.md` — Qwen3.5-Omni cross-ref row added 2026-04-22
