# Multimodal Pipeline: Vision + TTS + ASR

**Created**: 2026-02-18 (consolidated from `vision-pipeline.md` + `qwen3-tts-voice-synthesis.md` + `minicpm-o-4_5-integration.md`)
**Status**: Mixed — Vision live-server/tool/API/OpenAI-compat path validated, TTS blocked, MiniCPM-O testing pending
**Priority**: LOW

---

## Current State Summary

| Modality | Status | Blocker |
|----------|--------|---------|
| **STT (ASR)** | Production | faster-whisper large-v3-turbo on port 9000, int8, 2.8x RT |
| **Vision** | Live-server analyzer path, tool registry, API endpoint smoke, and OpenAI-compatible `image_url` data-URL bridge passed | No active blocker; remote-image fetching or multi-image support would be a new feature |
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

### 2026-06-21 Live-Server Tool Checkpoint

Landed `epyc-orchestrator` changes for the production tool surface:

- `src/vision/analyzers/vl_describe.py` now prefers resident multimodal
  llama-server inference via `/v1/chat/completions`, with `llama-mtmd-cli`
  retained as `auto`/`cli` fallback. `ORCHESTRATOR_VISION_VL_BACKEND=server`
  forces server-only validation.
- `orchestration/tool_registry.yaml` now exposes `vision_analyze`,
  `vision_search`, and `vision_face_identify` in the central orchestrator
  registry; the plugin manifest already exposed the same handlers.
- `src/api/routes/vision_serving.py` recognizes legacy live stack-prior role
  IDs (`worker_vision`, `vision_escalation`) even when older generated priors
  omit explicit vision launch markers.

Live direct analyzer smokes, without restarting the API server:

- `worker_vision` port `8086`: healthy/idle, `VLDescribeAnalyzer(server_port=8086)`
  succeeded on `/mnt/raid0/llm/llama.cpp/tools/mtmd/test-1.jpeg` in `11402.1ms`.
- `vision_escalation` port `8087`: healthy/idle, `VLDescribeAnalyzer(server_port=8087)`
  succeeded on the same image in `5560.7ms`.

Validation:

- `uv run python -m py_compile src/api/routes/vision_serving.py src/vision/analyzers/vl_describe.py tests/unit/test_vision_tools.py`;
- `uv run ruff check src/api/routes/vision_serving.py src/vision/analyzers/vl_describe.py tests/unit/test_vision_tools.py`;
- `uv run pytest tests/unit/test_vision_tools.py -q` -> `15 passed`;
- `uv run pytest tests/unit/test_vision_tools.py tests/unit/test_tool_registry.py tests/test_tool_loader.py tests/unit/test_chat_vision.py tests/unit/test_vision_routing.py -q` -> `132 passed`;
- central registry smoke loads `59` tools including `ocr_extract`,
  `vision_analyze`, `vision_search`, and `vision_face_identify`.

Deployment follow-up (2026-07-03): later orchestrator API reloads picked up the
server-backed analyzer and registry config. Live `/v1/vision/analyze` smoke
against `/mnt/raid0/llm/llama.cpp/tools/mtmd/test-1.jpeg` with `vl_describe`
returned a correct New York Times moon-landing front-page description in
`8210.3ms` with `errors=[]`. Ports `8086` and `8087` also reported
`{"status":"ok"}`. The quiet-window API-restart blocker is closed.

OpenAI-compatible chat follow-through (2026-07-03): orchestrator `9833a5b8`
parses multipart `/v1/chat/completions` user content, extracts one
`data:image/...;base64` `image_url`, and routes real-mode image requests through
the existing `_handle_vision_request` path. Unsupported remote image URLs and
multi-image requests now fail explicitly instead of being silently dropped. API
reload PID `1859269` served the new parser; a no-inference smoke returned HTTP
400 with the expected `data:image` detail for a remote URL. Focused validation:
OpenAI compat unit/integration tests `20 passed`, broader API/import/chat-vision
slice `90 passed`, Ruff, py_compile, and diff-check.

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
- No active vision code tail. Future work here should be opened as a new scoped
  feature, e.g. remote image fetching, multiple images per OpenAI message, or
  a promotion-grade OpenAI image request quality/latency benchmark.

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
1. ✅ 2026-07-17: Run `llama-mtmd-cli` with local Qwen3-VL-8B Q4_K_M + vision mmproj on experimental v7. Rebuilt the experimental `llama-mtmd-cli` after a `--version` segfault; CPU shapes and MI210 OCR runtime/coherence smokes passed under `/mnt/raid0/llm/tmp/qwen3-vl8-image-smoke-20260717T115124Z/`.
2. ✅ 2026-07-17: Benchmark candidate vision lanes vs Qwen2.5-VL-7B on the fixed K35 OCR/chart prompts. Qwen3-VL-8B CPU passed but was slower than the alias; Qwen3-VL-8B MI210 failed the chart; MiniCPM-o `--reasoning off` passed CPU+MI210 and is the leading `vision_escalation` candidate; SuperGemma4 passed but is slower/heavier than MiniCPM-o. PaddleOCR-VL also passed first extraction smokes at about `487 t/s`, but it belongs to the document/OCR extraction path, not the general vision QA lane.
3. ⏸️ Defer Qwen3-0.6B draft/spec-decode testing for Qwen3-VL until a concrete
   chart-fixture or role-gap fix reopens the Qwen3-VL lane; do not run another
   speed-only extra-vision probe while MiniCPM-o is the leading escalation path.

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

- [x] Check Qwen3.5-Omni for open-weight release / GGUF availability on HuggingFace ✅ 2026-07-14 DD2 (2026-04-22): API-only, no weights/GGUF
- [ ] If available: estimate CPU inference cost for audio-codec path (ARIA pipeline) on one NUMA node
- [x] Decide whether Qwen3.5-Omni becomes a new TTS Path E or supersedes existing paths ✅ 2026-07-14 DD2 decided: Scenario C — no Path E, Path D stays primary

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

## Research Intake Update — 2026-04-30

### New Related Research

- **[intake-511] "KAME: Tandem Architecture for Enhancing Knowledge in Real-Time Speech-to-Speech Conversational AI"** (arxiv:2510.02327, Sakana AI, ICASSP 2026)
  - Companion artifacts processed in same intake batch: blog [intake-512], main inference repo [intake-513], finetune repo [intake-514], HF model card [intake-515].
  - Relevance: **low** to current EPYC scope. Tandem architecture pairs a Moshi-based real-time S2S front-end with an asynchronous text-LLM "oracle" stream that injects gradually-refined knowledge mid-utterance. MT-Bench-speech 2.05 (Moshi) → 6.43 (KAME). All five entries verdict = `not_applicable` because: (a) Moshi audio-codec stack (Mimi, dual-stream semantic+acoustic) has no GGUF/llama.cpp support — same blocker class as existing Path D / Path E TTS work; (b) reference impl uses OpenAI Chat Completions + Google STT, violating open-source-only policy; (c) GPU-only inference path; (d) no text-LLM contribution.
  - Transferable pattern (file-for-awareness only): **fast-S2S frontline + slow-LLM oracle** topology is the speech-domain analogue of our drafter/verifier and worker_explore/coder split. "Oracle stream injecting partial-LLM tokens into an in-flight speech generator" is the speech-streaming variant of speculative decoding's accept-and-rewrite.
  - Tier 2b: SHANKS (arxiv:2510.06917, "Simultaneous Hearing and Thinking for Spoken Language Models") is an adjacent same-quarter paper exploring similar simultaneous speak-while-thinking territory; not ingested separately, noted for future watch.
  - Action: none. Maintain awareness via this cross-ref; revisit only if Path D/E TTS unblock revives.

#### Deep-dive refinement (2026-04-30)

Deep-dive at [`/workspace/research/deep-dives/kame-tandem-s2s-architecture.md`](../../research/deep-dives/kame-tandem-s2s-architecture.md). Two corrections to the intake notes above:

1. **Closed-API claim was wrong.** `src/kame/server_oracle.py` instantiates `AsyncOpenAI()` with no args → honors `OPENAI_BASE_URL`. Backend swap to a self-hosted llama-server is one env var. The OpenAI/Google STT dependencies are *convenience defaults*, not architectural blockers. The real adoption blocker is the front-end (Moshi 4-stream joint transformer with KAME-specific simulated-oracle retraining) plus absence of CPU audio-codec stack. Intake-513 entry corrected.
2. **Genuinely transferable pattern identified**: oracle-stream-as-fourth-autoregressive-stream with most-recent-wins semantics, mid-decode update from a parallel slow path. Distinct from drafter/verifier (no token-level accept/reject), worker_explore (sequential), Hermes outer-shell (request-boundary), Trinity coordinator (per-turn dispatch). Worth recording as competitive intel; **not worth a stub** (no implementation path on EPYC text-domain stack).

Three concrete revival gates (any of these flips the verdict):
- (a) Mimi/Moshi-class neural codec lands in llama.cpp (this also unblocks Paths A/D/E together)
- (b) Sakana ships open-weight KAME checkpoint
- (c) An EPYC voice-interface use case appears

Watch list: SHANKS (arxiv:2510.06917) is sibling not supersession — different problem (interruption + tool-call-during-listen vs knowledge-grounded response).

## Research Intake Update — 2026-05-20

### New Related Research

- **[intake-575] "Marlin-2B — Dense Video Captioning + Temporal Grounding at 2B"** (HF: NemoStation/Marlin-2B)
  - Relevance: Extends this handoff's scope beyond the current frame-level ffmpeg-extraction approach (§1 "Video processing: ffmpeg frame extraction, frame-level analysis"). Marlin-2B does native video captioning AND second-precise temporal grounding via `.find(query) → (start, end)` span resolution — capabilities the existing vision pipeline does not have.
  - Key technique: Two-stage post-training — SFT on ~400K clip-level annotations, then SimPO (reference-model-free preference optimization) with Gemini-3-Flash as judge. BF16, 2B params, vLLM-compatible, single-H100-trained.
  - Reported results: tops CaReBench at 2B; sits between Tarsier-34B and Gemini-1.5-Pro on DREAM-1K; +6.4 mIoU over Qwen2.5-VL-7B on TimeLens-Bench (Charades/ActivityNet/QVHighlights), matching Gemini-2.0-Flash — all author-reported, no third-party replication yet.
  - Delta from current approach: Vision pipeline (Qwen2.5-VL-7B on 8086, Qwen3-VL-30B on 8087) is image-first with video as frame chunks; Marlin-2B is video-native at a much smaller parameter scale.
  - Caveats: (a) BF16-only — **no GGUF or quantized variant** at intake; would need either a small GPU host or a llama.cpp conversion. (b) Base architecture labeled "Qwen3.5-2B" on the card, but Qwen3.5 family is publicly 27B+ — likely a mislabel for Qwen2.5-VL-2B or an internal checkpoint; exact reproduction unclear. (c) Single-org (NemoStation) commercial product with fine-tuning service framing; credibility tier low. (d) No public ablations of SimPO vs DPO, no failure-mode catalogue.
  - Action: **None now** — no active video captioning workload. Re-evaluate if (i) a video-understanding workload appears, OR (ii) a small GPU is added to the stack, OR (iii) third-party benchmark replication appears for the TimeLens / DREAM-1K claims.

## Research Intake Update — 2026-06-04

### New Related Research

- **[intake-680] "LocateAnything-3B"** (HF: nvidia/LocateAnything-3B) + **[intake-683]** companion paper (arxiv:2605.27365)
  - Relevance: Direct instantiation of the "small specialist model as a tool for a brain model" pattern. NVIDIA's #1-trending generalist visual-grounding model returns precise bounding boxes / points (referring-expression, dense detection, GUI grounding, text/layout localization) from natural-language queries — the native detect/point capability this handoff noted as a gap vs prompting Qwen-VL. Candidate vision/grounding worker for document-processing, form-filling, and GUI-agent flows.
  - Key technique: Parallel Box Decoding (PBD) — predicts complete box coordinates as atomic length-6 blocks in a single parallel step (not autoregressive token-by-token), ~2.5× throughput, preserved intra-box geometric coherence. Built on Qwen2.5-3B-Instruct LM + MoonViT-SO-400M encoder. Fast/Slow/Hybrid decode modes.
  - **First-party EPYC demo (operator-submitted)**: Qwen3.6-35B-A3B (frontdoor / brain) orchestrated LocateAnything-3B as a callable "eyes" tool — brain asks "where's the email field?", model returns exact x,y,w,h — and completed a blank paper form, placing all fields (name, DOB, ID, gender, marital status, nationality, email, phone, address, postal code) in the correct field areas. Qwen alone cannot finish; the combo can. 9m10s, 224.5k input / 24.3k output tokens, 21 turns. Character-box alignment slightly loose; every value in the right field.
  - Delta from current approach: current vision pipeline (Qwen2.5-VL-7B on 8086, Qwen3-VL-30B on 8087) is image-first VLM prompting; LocateAnything is a purpose-built parallel-decode grounding specialist invoked as a tool, not a VLM replacement (distinct verdict from the Moondream-3 DEFER, intake-121).
  - Caveats / blockers: (a) all efficiency is single-H100 boxes-per-second — **no CPU/EPYC numbers**; (b) NVIDIA **non-commercial research license** (flag-not-block per project stance); (c) needs a thin OpenAI-compat worker wrapper + tool-registry registration to be callable. Tier-2b found only license/IP caveats, no failed replications — coverage is NVIDIA + uncritical tech-press, claims not independently reproduced.

  - **⚠ DEEP-DIVE CORRECTION (2026-06-04, read-only 3-agent investigation — supersedes the caveats/action above; intake relevance high→medium):**
    1. **MoonViT is NOT a blocker — it is already in mainline llama.cpp** (PR #15458, Kimi-VL, merged 2025-08-26; GGUF `ggml-org/Kimi-VL-A3B-Thinking-2506-GGUF`). The "same support-uncertainty that DEFERred Moondream 3" framing was stale.
    2. **The real, likely-fatal blocker is Parallel Box Decoding (PBD)** — a custom block-diffusion `generation_mode` inside `trust_remote_code` generate() that `llama-server` cannot express. A GGUF would run only the AR-fallback path, **forfeiting the ~2.5× PBD speedup that is the model's entire value** (cf. the Qwen3-TTS MTP-codec custom-decode-loop precedent). LocateAnything is **transformers-CPU-only by design**; a GGUF stack role needs a custom C++ PBD decode loop in our fork (a research project, not a spike).
    3. **Capability is largely redundant**: deployed Qwen3-VL-30B-A3B (:8087) and Qwen2.5-VL-7B (:8086) already return bounding boxes via prompt, and Qwen3-VL is a ScreenSpot-Pro grounding baseline.
    4. **The 9m10s demo wall-time is dominated by the 35B-A3B brain's prefill** (224.5k input tokens / 21 turns), not the grounding calls — it tells us little about per-grounding-call latency.
    - **Refined action:** FIRST benchmark the *deployed* Qwen3-VL-30B (:8087) / Qwen2.5-VL-7B (:8086) on the form-fill loop for field-placement IoU. **ONLY if Qwen-VL precision is inadequate**, spike a throwaway HF-transformers (eager/SDPA, BF16) LocateAnything worker on CPU as a *precision A/B* — never a GGUF stack role.

- **[intake-682] "unsloth/gemma-4-12b-it-GGUF"** (HF) — just-released, **benchmark candidate**
  - Relevance: dense 12B-it sibling of the deployed gemma-4-26B-A4B MoE worker_general; encoder-free unified text+image+audio+video GGUF. **llama.cpp already supports gemma-4 vision (PR #21309) and audio (PR #21421)**, so a multimodal spike is feasible.
  - Operator-raised angles are now parked unless they answer a concrete role gap: (a) **vision-escalation substitute** only if MiniCPM-o / worker_vision misses a fixture or service requirement; (b) **frontdoor substitute** only with a text-quality hypothesis, not a speed-only multimodal curiosity. NOTE: Google card numbers are only a weak prior — the frontdoor Qwen3.6 is *itself* multimodal, and on a BW-bound CPU host a dense 12B (reads ~12B params/token) likely decodes slower than the ~3B-active MoE frontdoor (measured 25.17 t/s). Any reopened probe must append to the model-probe scoreboard.
  - Caveat: the "drafter for the 26B-A4B" framing is structurally invalid (needs the purpose-built 4-layer ~500M Gemma4Assistant head; no deployed dense Gemma-4 target). Verdict: parked until a concrete vision/frontdoor role-gap hypothesis exists.

## Research Intake Update — 2026-06-12

### New Related Research (deep-dived)
- **[intake-691] "Holo-3.1-4B"** (HF: Hcompany/Holo-3.1-4B, Apache-2.0) — H Company GUI/computer-use VLM, `Qwen3_5ForConditionalGeneration` arch, AndroidWorld 4B 72% (self-reported), native function-calling. **Deep-dive 2026-06-12: PARKED (roadmap + runnability gated).** Ships **BF16 safetensors only — no GGUF/mmproj for the 4B** (only the 35B-A3B has official GGUF; the intake-694 roundup conflated the two); Qwen3.5 vision/mmproj on llama.cpp is still fragile (ggml-org #21268/#21271). Grounding capability is **redundant** with the deployed Qwen3-VL-30B (:8087) / Qwen2.5-VL-7B (:8086). **Only** if a GUI-agent workload appears AND the deployed Qwen-VLs prove inadequate on field-placement IoU: A/B Holo-3.1-4B (Apache-2.0, native fn-calling) vs LocateAnything-3B (intake-680) via a throwaway transformers-CPU worker — never a GGUF stack role. See `research/deep-dives/2026-06-12-holo-3.1-4b-gui-vlm.md`.

## Research Intake Update — 2026-07-16

### New Related Research — Qwen-Audio-3.0-Realtime (monitor-only)
- **[intake-826] "Qwen-Audio-3.0-Realtime (Plus + Flash)"** (X/Twitter promo; resolved via a Twitter mirror — third-party news account 智东西/@Chinazhidx, NOT the Qwen team)
  - Relevance: Alibaba announced two new realtime-audio models (Plus + Flash tiers) live on the **Bailian cloud console — API-only, no open weights / GGUF / checkpoints**. The post carries zero technical substance (no architecture, codec, latency, or benchmarks) — a contentless link-drop.
  - Verdict **not_applicable** (nothing to port to the CPU/llama.cpp path), but **not hard-rejected** per research-intake policy. Direct parallel to intake-432 (Qwen3.5-Omni), where the same API-only / no-CPU-path pattern led to non-adoption.
- [ ] Monitor-hook (operator-review candidate): watch for a **Qwen-Audio-3.0 open-weights / GGUF** release via this handoff's existing Alibaba audio/omni monitoring loop (alongside Qwen3-Omni-30B-A3B); re-intake the primary technical release note if/when Alibaba publishes weights or details.

### MiniCPM-o deterministic promotion runbook (filed 2026-07-23, operator-directed)

Operator directive: the MiniCPM-o/MI210 vision_escalation lane stays parked ("ignore for now") — but **when ready, promotion into the stack must be deterministic, not bespoke**.

- [x] **Write the vision_escalation → MiniCPM-o promotion runbook** ✅ 2026-07-23 — persisted at [docs/runbooks/vision-escalation-minicpmo-promotion.md](../../docs/runbooks/vision-escalation-minicpmo-promotion.md) (drafted + adversarially verified by workflow; 6 corrections applied; data-only + 3 constant lines, registry edit goes to the MASTER). Original spec: a single documented, gate-checked sequence covering (1) registry vision_escalation rebind (model + mmproj + HIP runtime lane, reversing the 2026-07-19 `91cf4033`/`dacd15a2` safe-alias rollback); (2) `stack_change_pipeline.py update` + `check` green; (3) rolling server swap on 8087 via `orchestrator_stack.py` (the 2026-07-23 additive `--numa-mode both` promotion path in `stack_commands.py` is the pattern: explicit-arg authority, skip-healthy, no-outage); (4) §H contention-matrix recert for the changed lane (the 2026-07-17 rebind shipped WITHOUT recert — flagged in v7-promotion.md:38 — the runbook must close that gap, not repeat it); (5) live-affinity + realized-first attestation; (6) smoke via the eval path (image + text probe) with the modality fence verified; (7) rollback = the same runbook with the safe-alias registry state. Prior evidence to cite: MiniCPM-o validation 2026-07-18 (110-127 t/s, 4/4 quality, 8/8 service matrix) vs the alias faster on the 07-19 long-decode slice — the runbook executes whichever model the operator picks; it is model-agnostic mechanics.


## Trigger Gate: worker_vision 4×-quarters recollection

**Status**: Recollection held OPEN "in principle" (operator, stack-lineup-dossier-2026-07-23 item 7). This gate defines the two conditions under which it converts to action. Until either trips, the 2026-05-24 revert stands and `test_worker_vision_stays_single_instance` stays pinned.

### 0. Evidence snapshot (measured 2026-07-23, read-only)

| Fact | Value | Source |
|---|---|---|
| Tap window | 2026-07-15T19:07 → 2026-07-23T17:28 (~7.9 days) | `/mnt/raid0/llm/tmp/inference_tap_events.jsonl` (940,083 events) |
| worker_vision request starts | **399 — ALL `batch_id:"evaltower-*"`; organic (`batch_id:null`) = 0** | grep of `"event":"start"` lines |
| vision_escalation events | **0** (any type, entire window) | same file |
| Per-request profile | mean 87–183 gen tokens, decode 26–31 t/s tap-observed (p50 26.2, p90 50.7), 4–10 s decode; `prompt_ms` recorded 0.0 (prefill/image-encode NOT captured) | `"event":"timings"` lines |
| Revert basis (2026-05-24) | 24t = 11.39 vs 48t = 11.30 t/s flat; +16 GB mlock; zero volume; 4×q lived ~90 min (`6657bbdc` → `92283a08`) | `stack_numa.py:198-204`, progress/2026-05/2026-05-24.md, dossier §row worker_vision |
| Current shape | ONE quarter Q0B (24-47,120-143) @8086, `-t 24`, `-np 2` slots | `stack_numa.py:205-208`, `orchestrator_stack.py:_build_vision_command` (slots fallback 2) |
| What changed since revert | **vl modality fence live 2026-07-23** (`src/api/routes/chat_pipeline/routing_decision.py`: image → `worker_vision` at line 142; text fenced OFF vision roles; failure-veto exemption for image requests). Pre-fence the lane was routing-dead (vl 0/376 — now STALE per core-v2-design-note §amendment) | routing_decision.py:30-83,142,195-208 |

**Consequence of the fence**: all demand data at or before 2026-07-23 — including the table above — *undercounts true organic vision demand* (routing was broken, then freshly fixed). The demand clock starts **2026-07-23**; first valid reading ≥ **2026-08-06** (14-day window).

### Trigger A — DEMAND (current model kept; quarters = replication for throughput)

Rationale: the 2026-05-24 flat-scaling finding kills quartering as a *latency* lever, but replication for *throughput* is orthogonal — extra independent quarter instances add aggregate capacity even for a thread-flat model. The real 2026-05-24 blocker was zero volume. So Trigger A is purely a volume/saturation gate.

**Capacity model (assumptions explicit)**:
- Service time S per organic request: 4–10 s decode (tap-observed 26–31 t/s × 90–180 tokens) + un-instrumented image-encode/prefill budget 3–10 s → **S ≈ 10–20 s**; worst-case floor using the Phase-0.5 protocol number (11.3 t/s, era pre-v7): **S ≈ 25 s**.
- One quarter, `-np 2` slots, co-run efficiency of 2 slots on 24t assumed 1.3–1.6× single-stream (J5 quarter-pair precedent; NOT measured for this role) → sustained capacity **C ≈ 2–5 req/min**; use **C_conservative = 2 req/min**.
- SLA assumed: p95 queue wait ≤ 30 s, p95 time-to-last-token ≤ 90 s; utilization target ρ ≤ 0.7.

**Trip condition (both sub-signals required — the AND makes the gate self-calibrating against the 11-vs-31 t/s uncertainty)**:
1. **Rate**: sustained organic arrival λ ≥ **2 req/min over any 30-min window**, recurring on **≥ 3 distinct days within 14 days** (all post-2026-07-23 data only), AND
2. **Saturation**: in-flight depth > 2 (both slots busy, requests queuing) for **> 10% of samples** in those windows, or p95 queue wait > 30 s.

Current reading vs threshold: **0 organic req in 7.9 days vs ≥ 2/min required** — not remotely close; the gate exists so this gets re-read post-fence, cheaply, on a cadence.

**Measurement (read-only, zero inference)**:
```bash
# A1 — organic arrivals per hour (excludes eval-tower batches)
grep '"role":"worker_vision"' /mnt/raid0/llm/tmp/inference_tap_events.jsonl \
  | grep '"event":"start"' | grep '"batch_id":null' \
  | grep -o '"ts":"[0-9T:-]*' | cut -c8-21 | sort | uniq -c

# A2 — saturation proxy: max/distribution of concurrent in-flight organic requests
grep '"role":"worker_vision"' /mnt/raid0/llm/tmp/inference_tap_events.jsonl \
  | grep '"batch_id":null' \
  | grep -oE '"event":"(start|end)"[^}]*?"ts_epoch":[0-9.]+' \
  | sed -E 's/"event":"(start|end)".*"ts_epoch":([0-9.]+)/\2 \1/' | sort -n \
  | awk '{d+=($2=="start")?1:-1; n++; if(d>2)over++; if(d>max)max=d}
         END{printf "max_inflight=%d over_2slots_frac=%.3f\n", max, (n?over/n:0)}'

# A3 — service-time check (recalibrate S if model/kernel changes)
grep '"role":"worker_vision"' /mnt/raid0/llm/tmp/inference_tap_events.jsonl \
  | grep '"event":"timings"' | grep '"batch_id":null' \
  | grep -o '"total_s":[0-9.]*' | cut -d: -f2 | sort -n \
  | awk '{a[NR]=$1} END{if(NR)print "n="NR, "p50="a[int(NR*.5)], "p95="a[int(NR*.95)]}'
```
Mind tap-file rotation (journal-rotation lesson: read all shards if `inference_tap_events_<n>.jsonl` appears). Cost: ~seconds of grep; run at each review checkpoint.

### Trigger B — CAPABILITY (model change on the role)

Trips when a **new VL model is a candidate for `worker_vision` on CPU** and, unlike the 7B, actually profits from the topology. All three sub-gates required:

1. **Quality gate first**: candidate passes the K35 fixed-fixture vision quality matrix at parity-or-better vs the current 7B alias (precedent: Qwen3-VL-30B was collapsed 5→1 on 2026-07-17, `139ba643`, for 3/4 vs the 7B's 4/4 — capacity for wrong answers is worthless).
2. **J5-style certified-affinity pair test**: quarter-pair **aggregate co-run ratio ≥ 1.2 mean, no pair < 1.0**, with **n ≥ 8 reps and CV ≤ 5% per pair** (the J5 vision -t48 re-bench was direction-robust but DIAGNOSTIC-GRADE at 5/8 pairs cv>5% — a decision gate needs the clean version), measured **only** under `live_affinity_verified` (`scripts/server/affinity_preflight.py`, role mode) — the 2026-05-26 lesson: uncertified affinity produced phantom blocks (0.40–0.46×) that certified re-bench overturned to 1.38–2.52× allow.
3. **Thread-scaling sanity**: single-instance 24t vs 48t delta > 10% (the 7B's 11.39-vs-11.30 flatline is the disqualifier this reverses), OR the model is large enough that a quarter is its minimum viable footprint.

**Measurement**: `python scripts/server/contention_matrix.py --roles worker_vision` (canonical J5 harness; writes `orchestration/contention_matrix.yaml` with topology-hash attestation) against a candidate 4×q shape on the experimental config — this **is inference on the EPYC and requires per-run operator approval** (MEASUREMENT.md; no-concurrent-inference policy). Record the result as a decision-gating tuple `(ratio, contention_matrix protocol, n, date, attestation ref)`.

**B alone does not trip the gate**: quartering buys *concurrent aggregate* throughput, which is worthless at zero concurrency. B additionally requires a demand floor of **≥ 0.5 req/min sustained organic** (25% of Trigger A's rate, measured the same way).

### Gate logic

```
RECOLLECT_4xq  =  ( A )  OR  ( B AND organic λ ≥ 0.5 req/min )
SUSPENDED whenever a certified MI210 vision lane is persistent-live (see below)
```

### Interaction with MiniCPM-o / MI210 (explicit)

State (dossier §Chain + item 3): MiniCPM-o-4.5 on MI210 fully validated 2026-07-18 (110–127 t/s, 4/4 quality, co-residency, 8/8 service matrix), rolled back 2026-07-19 to the CPU safe alias; the alias itself ran *faster* on MI210 long-decode (118.5 vs 109.2 t/s). The cutover is **decision-pending, not execution-pending**, with a deterministic promotion runbook task filed in multimodal-pipeline.md §"MiniCPM-o deterministic promotion runbook".

- One MI210 vision stream ≈ 110–127 t/s ≈ **4–10× a CPU quarter stream**. The marginal capacity of +3 CPU quarters (~+2–4 req/min, +16 GB mlock, new region-lock pressure on node0/Q0) is dwarfed by a single GPU lane (~15–40 req/min at the same S).
- **Rule**: if the operator executes any persistent-live MI210 vision cutover (MiniCPM-o *or* the alias-on-GPU variant), this gate is **SUSPENDED** — overflow vision demand routes to the GPU escalation lane instead, and the CPU 4×q case survives only as (i) GPU-lane retirement/contention fallback, or (ii) an operator-mandated CPU-resilience requirement (a different gate, operator-defined).
- **Caveat to re-verify at trip time**: the MI210 currently hosts the operator's Qwen3.5-122B UD-IQ2_M architect experiment (the port-18072 process — external, not a stack lane). Co-residency was validated 2026-07-18, but GPU headroom must be re-confirmed on the day either trigger trips.

### What un-pins `test_worker_vision_stays_single_instance` when tripped

The pin encodes a *decision*, so un-pinning = superseding the decision with an attested one, in **one commit**:

1. **Attestation first**: persist the trip evidence (Trigger A: tap-window counts + the A1/A2 command outputs + dates; Trigger B: `contention_matrix.yaml` ref + affinity attestation + K35 result) in the handoff and progress note, as a MEASUREMENT.md-grade tuple.
2. **Same commit, orchestrator repo**: (a) `scripts/server/stack_numa.py:205-208` — new `worker_vision` shape (mirror the `burst_prefer_quarters` pattern; rewrite the 198–204 comment block to cite the trip attestation, don't delete the history); (b) **replace** `tests/unit/test_orchestrator_stack_threads.py:84-92` — add `"worker_vision"` to the `test_quartered_roles_per_instance_thread_count` loop (line 71) and write a new pin asserting the NEW ratified shape with the attestation ref in its docstring; (c) registry `server_mode` update so the WP-12 fleet layer derives the endpoints (do NOT hand-copy URLs into `src/config/models.py` — fleet is SoT).
3. **Config gates**: `stack_change_pipeline.py update` + `check` green.
4. **Promotion**: additive, no-outage — `orchestrator_stack.py start --only worker_vision --numa-mode both` (`stack_commands._only_mode_transition_allowed` path); `affinity_preflight.py` role-mode green; **contention-matrix recert for the changed lane** (do not repeat the 2026-07-17 rebind-without-recert gap flagged at v7-promotion.md:38).
5. **Post**: dispatch verification on the new instances; re-run A1/A2 after 48 h to confirm the added capacity is actually absorbing queue.

### Review cadence

Re-run A1–A3 at each stack-review checkpoint (or ≥ every 14 days), first valid post-fence reading **2026-08-06**. If two consecutive checkpoints read λ ≈ 0 organic *and* the MI210 cutover executes, recommend converting "open in principle" → "closed: superseded by GPU lane" to the operator.