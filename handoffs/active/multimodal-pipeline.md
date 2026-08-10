# Multimodal Pipeline: Vision + TTS + ASR

**Created**: 2026-02-18 (consolidated from `vision-pipeline.md` + `qwen3-tts-voice-synthesis.md` + `minicpm-o-4_5-integration.md`)
**Status**: Mixed — Vision live-server/tool/API/OpenAI-compat path validated, ~~TTS blocked~~ **TTS SOLVED 2026-07-31 (qwentts.cpp, round-trip WER 0.0%)**, ~~MiniCPM-O testing pending~~ **MiniCPM-O DEPRECATED + DELETED 2026-07-31**, **ASR arm opened 2026-07-31 (Qwen3-ASR on MI210, config-broken)**
**Priority**: LOW

---

> ## ✅ TTS UNBLOCKED — 2026-07-31 — first working speech synthesis on this host, ever
>
> **The long-standing TTS blocker is resolved.** It was NOT resolved by the documented next step
> (diff C++ vs PyTorch codec tokens); it was resolved by replacing our port with the upstream one.
>
> **Root cause of the noise.** Our home-rolled Qwen3-TTS llama.cpp port hand-rolled the **codec
> half**. Upstream **`qwentts.cpp`** (ServeurpersoCom) implements the **full** stack — Talker, MTP
> CodePredictor, speaker encoder, and the complete SEANet / ConvNeXt / DAC codec. The unintelligible
> output came from the half we wrote ourselves. Cloned to `/mnt/raid0/llm/qwentts.cpp` (upstream tip
> `abab6b3`); builds **CPU** and now also **HIP for gfx90a**.
>
> **Measured — CPU, Qwen3-TTS-0.6B-base Q8_0 + qwen-tokenizer-12hz Q8_0** (1.19 GB total,
> `/mnt/raid0/llm/models/Qwen3-TTS-qwentts/`):
>
> | metric | value |
> |---|---|
> | **round-trip WER** (synthesize → transcribe with the incumbent whisper) | **0.0 % — word-perfect** |
> | **TTFA** (time to first audio) | **67.9 ms** — viable for streaming voice |
> | total wall for 5.84 s of audio | 6820.7 ms = **0.86× real-time** |
> | **`CodecDecode`** | **4362.9 ms = 64 % of total — THE bottleneck** |
> | Talker | 1313.7 ms |
> | CodePredictor | 1091.8 ms |
>
> The round-trip WER **is** the intelligibility check the archived handoff never got to run. The
> bottleneck is the **convnet vocoder, not the LM** — precisely the workload a GPU targets.
>
> **A GPU TTS bench is IN FLIGHT** (queued on the q3 GPU lane) → `/mnt/raid0/llm/tmp/tts_bench_results.txt`;
> harness `/mnt/raid0/llm/tmp/tts_bench.sh`. **No numbers exist yet — do not quote any.**
>
> **The one patch required is NOT a kernel change.** `qwentts.cpp/ggml/src/ggml-cuda/vendors/hip.h`
> guarded FP8 on `HIP_VERSION >= 60200000`, but the OCP-format `__hip_fp8_e4m3` type only exists from
> **ROCm 6.3**; we run **6.2.0-66**, which ships only `__hip_fp8_e4m3_fnuz` → `error: unknown type
> name '__hip_fp8_e4m3'`. Guard raised to `60300000`; free for us because **gfx90a has no FP8
> hardware**. This is a **third-party repo**. The frozen production kernel `production-consolidated-v8`
> @ `67a433bf4` is **untouched** and **no experimental-kernel handoff is needed** — CLAUDE.md's
> four-step workflow governs *our* kernel tree, which this patch is not in.
>
> **Do not revive the old C++ accelerator.** `llama-tts-qwen3` source is gone from the host; only a
> 2026-04-23 binary survives and it fails with `no backends are loaded`. Stock `llama-tts` misreads
> the weights as OuteTTS and emits unrelated tokens with no WAV.
>
> Historical blocker record: [`../archived/qwen3-tts-voice-synthesis.md`](../archived/qwen3-tts-voice-synthesis.md)
> (archived — carries a pointer to this resolution; do **not** resurrect it).

> ## ⛔ SUPERSEDING NOTE — 2026-07-31 — MiniCPM-o is DEPRECATED; weights DELETED
>
> **Everything in this file that presents MiniCPM-o-4.5 as a live candidate is superseded.**
> The `/mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/` tree (22 GB) has been deleted; nothing here
> is runnable without a re-download from `openbmb/MiniCPM-o-4_5-gguf`. Individual dated
> corrections are inline at §2 Recommendation, §3 Phase-1 (M-1), §3 vendor table, §Open
> Questions, and §MiniCPM-o promotion runbook. Historical text is left intact.
>
> **Vision — it is a downgrade, not an upgrade.** 42 questions (OCRBench + ChartQA), MI210,
> each arm at the best quant on disk, scored offline with a unit/whitespace-normalizing scorer:
>
> | model · quant | accuracy |
> |---|---|
> | Qwen3-VL-30B-A3B Q4_K_M | **36/42** |
> | Qwen2.5-VL-7B Q4_K_M (incumbent) | **35/42** |
> | Qwen3-VL-8B Q8_0 | 33/42 |
> | **MiniCPM-o-4.5 Q8_0** | **31/42** |
> | Qwen3-VL-4B Q8_0 | 29/42 |
>
> Raw `/mnt/raid0/llm/tmp/vlquality_results.json`; harness `/mnt/raid0/llm/tmp/vlquality.py`.
> Full context in [`numa-topology-cutover-resume-20260730.md`](numa-topology-cutover-resume-20260730.md)
> §"UPDATE 2026-07-31 — vision models evaluated".
>
> **The M-1 evidence does not survive.** The `+10pp` was ONE discordant question and that
> question was a **scoring artifact** — the incumbent answered `0.11 kWh` where the accepted
> answer was `0.11` (`vl_chart_test_0563`). Corrected, the arms tied 7/10. Honest framing:
> M-1 was `p=1.0` / `observation_only_unratified`, so the 42q run **supersedes on power** — it
> does not statistically contradict a result that never reached significance.
>
> **Read the 42q table with its caveat.** OCRBench+ChartQA is precisely the family where
> Qwen3-VL was *never* claimed to improve much (published vs the independent OpenVLM baseline:
> DocVQA +0.4, ChartQA +2.3, AI2D +1.8, OCRBench +8). Its real gains are MathVision +28.8,
> MMMU-Pro +17.6, MMMU +11.0, OmniDocBench −45% edit distance. Without this caveat the table
> reads as a Qwen3-VL regression, which it is not.
>
> **Speech — the last argument is also gone.** A dedicated Qwen3-TTS-12Hz-0.6B (Talker +
> CodePredictor Q8_0) is **1.14 GB** and already on disk, the PyTorch TTS path runs on **CPU**
> (`torch 2.6.0+cpu`, zero GPU VRAM), and Qwen3-ASR is already supported by the frozen v8
> kernel. MiniCPM-o's omni stack was **10.84 GB** resident — a **9.70 GB** delta for speech
> alone, on contested MI210. Note also that `scripts/voice/` **already contains** `tts_server.py`,
> `create_tts_sidecar.py`, `validate_tts_e2e.py` — the Path-A/B/C/D framing below predates that
> discovery.

---

## Current State Summary

| Modality | Status | Blocker |
|----------|--------|---------|
| **STT (ASR)** | Production | faster-whisper large-v3-turbo on port 9000, int8. ~~2.8x RT~~ **CORRECTED 2026-07-31 by first local measurement** (LibriSpeech test-clean, n=100): **WER 2.35%** (lower=better) · **xRT is length-dependent and the single figure was meaningless** — wall time is ~constant at **4.18s + 0.010xaudio_s**, i.e. a **~4.2s FIXED per-request floor** (whisper pads to 30s mel windows). Median xRT 0.80x for <5s utterances, 1.49x for 5-10s, 2.89x for 10-20s, 7.22x on a 57s clip. **The 4.2s floor makes CPU whisper unusable for conversational voice regardless of xRT.** Artifact: `/mnt/raid0/llm/tmp/stt_wer_results.json`, harness `stt_wer.py`. |
| **STT — offline** | **FIXED 2026-07-31** | `whisper_server.py` passed a model **NAME**, so `huggingface_hub` reached huggingface.co on every cold start; whisper is in `OPTIONAL_AUXILIARY_ROLES` so it failed **silently**. Now `local_files_only=True` in `whisper_server.py` + `HF_HUB_OFFLINE=1`/`TRANSFORMERS_OFFLINE=1` in `start_whisper_server.sh`, both overridable only by an explicit `WHISPER_ALLOW_DOWNLOAD=1`. Verified: loads in **1.42 s** with no network. Repo: `epyc-inference-research`. |
| **ASR (Qwen3-ASR, GPU)** | Runs; **configuration broken** | `ggml-org/Qwen3-ASR-1.7B-GGUF` serves on the MI210 via `llama-server` with **ZERO kernel change** — the frozen v8 kernel already ships `tools/mtmd/models/qwen3a.cpp` + `libmtmd.so.0.0.10107` (verified). **WER 72.14 % is NOT a model verdict**: every utterance over ~11 s degenerates to literal `????????` while short ones transcribe perfectly, and 8k→65536 context changed nothing (WER identical to 2 d.p.). **Next suspect: the Q8_0-quantized audio projector**; the bf16 projector is on disk and untested. Where it worked: xRT **4.02**, wall/request median **2.14 s** vs whisper's 4.2 s floor. |
| **Vision** | Live-server analyzer path, tool registry, API endpoint smoke, and OpenAI-compatible `image_url` data-URL bridge passed | No active blocker; remote-image fetching or multi-image support would be a new feature. **A vision finalization run on MMMU at production temperature is IN FLIGHT** → `/mnt/raid0/llm/tmp/vision_final_results.json` (no numbers yet). |
| **TTS** | ~~Blocked~~ **WORKING 2026-07-31** | Resolved via upstream **`qwentts.cpp`** — round-trip **WER 0.0 %**, **TTFA 67.9 ms**, 0.86× real-time on CPU; `CodecDecode` is 64 % of wall. See the ✅ banner above. Our own port's noise came from its hand-rolled codec half. ~~MiniCPM-O TTS untested~~ → MiniCPM-O TTS **abandoned 2026-07-31**. |
| ~~**Multimodal (MiniCPM-O)**~~ | **DEPRECATED + DELETED 2026-07-31** | Not a blocker — closed. Vision 31/42 vs incumbent 35/42; speech superseded by dedicated Qwen3-TTS + Qwen3-ASR. See banner above. |

```
Current voice loop (2026-07-31):
  Mic → Whisper(9000) → text → LLM(8080) → response text → TTS ✅ WORKS (qwentts.cpp, CPU, offline)
                                                              ⚠ not yet a managed service

Remaining gap is WIRING, not capability:
  - no start_tts() in orchestrator_stack.py  (port 9002 reserved)
  - GPU TTS bench in flight (CodecDecode is 64% of wall — the GPU target)
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

### Path A: Qwen3-TTS via llama.cpp (~~BLOCKED~~ → **SUPERSEDED 2026-07-31 by Path E, `qwentts.cpp`**)

> **SUPERSEDED 2026-07-31 — and the blocker is EXPLAINED, not merely bypassed.** Path A is our
> home-rolled port. It hand-rolled the **codec half**, which is where the noise came from. Upstream
> **`qwentts.cpp`** implements the full stack (Talker + MTP CodePredictor + speaker encoder +
> complete SEANet/ConvNeXt/DAC codec) and produces **round-trip WER 0.0 %** on this host. The
> documented "diff C++ vs PyTorch codec tokens" debug step is therefore **cancelled** — it would
> debug code we no longer need. Path A's binary is additionally unrebuildable (source lost). See the
> ✅ banner at the top of this file.

**Status (historical)**: C++ binary generates codec tokens at 1.5x RT, but audio output is unintelligible noise.

Architecture (3 sub-models):
- **Talker**: 28-layer Qwen3-style transformer (0.6B) — standard tensor layout, GGUF-convertible
- **Code Predictor**: 5-layer transformer — predicts 15 remaining codebook entries per frame
- **Speech Tokenizer**: Mimi codec decoder — 8-layer transformer + ConvNet upsampler (480x)

Artifacts on disk:
- `/mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-Talker-Q4_K_M.gguf`
- `/mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-CodePredictor-Q8_0.gguf`
- `/mnt/raid0/llm/models/qwen3-tts-sidecar.bin`
- C++ binary: ⛔ **PATH IS DEAD (verified 2026-07-31).** `/mnt/raid0/llm/llama.cpp-experimental/build/bin/llama-tts-qwen3` **does not exist**. The only surviving copy is `/mnt/raid0/llm/llama.cpp-experimental-preserved-20260724T135832Z/build-archive-2026-04-23/bin/llama-tts-qwen3` (418 KB, built 2026-04-23), and it **fails to run**: `no backends are loaded` even with `LD_LIBRARY_PATH` and `GGML_BACKEND_PATH` pointed at its own `.so`s. Worse, **the C++ SOURCE no longer exists anywhere on this host** — no `tts-qwen3*.cpp`, no `tools/tts-qwen3/` source dir, and branch `feature/qwen3-tts-support` in the production tree contains **none** of it (its tip is upstream commit `079feab9e`). Only stale CMake artifacts survive under the preserved tree's `build-*/tools/tts-qwen3/`. **This accelerator cannot be rebuilt from what is on disk.** It is also in a `-preserved-<timestamp>` directory, i.e. exactly the kind of path that gets reclaimed. USE THE PYTORCH PATH INSTEAD — `scripts/voice/tts_server.py` is a complete PyTorch implementation needing no C++ binary (see below).
- Branch: `feature/qwen3-tts-support` in llama.cpp-experimental

**Next debug step**: ~~Generate PyTorch reference codec tokens, compare vs C++ token-by-token to find divergence point.~~ **CANCELLED 2026-07-31** — superseded by `qwentts.cpp`, which already ships a correct codec. The divergence point is known structurally (our hand-rolled codec half); the diff has nothing left to teach.

```bash
# Quick test (codec tokens only)
OMP_NUM_THREADS=48 numactl --interleave=all /mnt/raid0/llm/llama.cpp-experimental/build/bin/llama-tts-qwen3 \
  --model-talker /mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-Talker-Q4_K_M.gguf \
  --model-cp /mnt/raid0/llm/models/Qwen3-TTS-12Hz-0.6B-CodePredictor-Q8_0.gguf \
  --sidecar /mnt/raid0/llm/models/qwen3-tts-sidecar.bin \
  -p "Hello world." --max-frames 5 --temp 0.9 --seed 42 -t 48
```

### Path B: MiniCPM-O 4.5 Built-in TTS (~~UNTESTED~~ → **ABANDONED 2026-07-31**)

> **ABANDONED 2026-07-31.** Path B is closed: MiniCPM-o is deprecated and its weights are
> deleted. M-2/M-2QA did prove the mechanics (a structurally valid 24 kHz mono PCM16 WAV,
> ASR-transcribed back to the requested sentence), so the vendor numbers below were never
> falsified — Path B is dropped on **cost**, not on failure. Carrying it meant carrying the
> whole 22 GB omni bundle for a model that loses on vision, versus a dedicated 1.14 GB
> Qwen3-TTS already on disk that runs on CPU. Retained below as the historical record.

MiniCPM-O has CosyVoice2 TTS built in. Key numbers:
- TTS Long English WER: **3.37%** (CosyVoice2 standalone: 14.80%)
- Emotion control: **82.1** (CosyVoice2: 53.4)
- Voice cloning WER: 2.38%

**Caveat**: Audio features require `llama.cpp-omni` fork, NOT mainline llama.cpp. See Section 3 below.

### Recommendation
~~Test Path B (MiniCPM-O) first — it's a complete package (ASR+TTS+Vision in one model). If audio quality is good, it may obviate the need for the Qwen3-TTS llama.cpp port entirely. Only resume Path A debugging if Path B fails or has unacceptable latency.~~

**SUPERSEDED 2026-07-31 — do NOT test Path B first; do not test it at all.** MiniCPM-o is
deprecated and its weights are deleted. The "complete package" argument is what justified
carrying a 22 GB omni bundle (10.84 GB resident), and it no longer pays: the vision half is a
*downgrade* (31/42 vs the 35/42 incumbent) and the speech half is beaten on footprint by a
dedicated **1.14 GB** Qwen3-TTS-12Hz-0.6B already on disk — a 9.70 GB saving for speech alone,
running on **CPU** at zero GPU VRAM. ASR is already production (faster-whisper large-v3-turbo,
port 9000, a managed service via `orchestrator_stack.py start_whisper()`), and Qwen3-ASR is
supported by the frozen v8 kernel.

~~**Revised recommendation**: the TTS path is the existing `scripts/voice/tts_server.py` (full
PyTorch: Talker + CodePredictor + Decoder, ~0.9× real-time at 48 CPU threads).~~ — **SUPERSEDED
2026-07-31 by Path E (`qwentts.cpp`), which is MEASURED where the PyTorch path is only estimated.**

### Path E: upstream `qwentts.cpp` — **THE PATH (measured 2026-07-31)**

| | Path E (`qwentts.cpp`) | Path C (`scripts/voice/tts_server.py`) |
|---|---|---|
| implementation | upstream C++/GGML, full stack incl. codec | our PyTorch wrapper |
| measured on this host | **yes** — WER 0.0 %, TTFA 67.9 ms, 0.86× RT | **no** — ~0.9× RT is an *estimate* |
| runtime deps | none beyond the build | `soundfile`, `fastapi`, `uvicorn`, `librosa`, `scipy` + a venv |
| GPU | HIP/gfx90a builds (bench in flight) | CPU torch only |

Path C is retained as a fallback, not the recommendation. The real remaining gap is **wiring**:
`start_tts()` was never added to `orchestrator_stack.py` (port 9002 reserved) — tracked as P0 in
[`numa-topology-cutover-resume-20260730.md`](numa-topology-cutover-resume-20260730.md) §Speech.
Do not rebuild the C++ accelerator — its source is lost and it never worked.

### Speech tasks — opened 2026-07-31

- [x] **S-1 — explain the Qwen3-TTS noise** ✅ 2026-07-31 — our port hand-rolled the codec half (SEANet/ConvNeXt/DAC); upstream `qwentts.cpp` implements it. Structural explanation, no token diff needed.
- [x] **S-2 — get working speech synthesis on this host** ✅ 2026-07-31 — `qwentts.cpp` @ `abab6b3`, CPU, Qwen3-TTS-0.6B-base Q8_0 + qwen-tokenizer-12hz Q8_0 (1.19 GB): **round-trip WER 0.0 %**, **TTFA 67.9 ms**, 6820.7 ms for 5.84 s audio = **0.86× RT**. `CodecDecode` 4362.9 ms = **64 %** of wall; Talker 1313.7 ms; CodePredictor 1091.8 ms.
- [x] **S-3 — build `qwentts.cpp` with HIP for gfx90a** ✅ 2026-07-31 — required one line: `ggml/src/ggml-cuda/vendors/hip.h` FP8 guard `60200000` → `60300000` (OCP `__hip_fp8_e4m3` is ROCm ≥6.3; we run 6.2.0-66 which has only `_fnuz`). **Third-party repo; production kernel untouched; no experimental-kernel handoff needed.**
- [x] **S-4 — verify Qwen3-ASR serves on the MI210 without a kernel change** ✅ 2026-07-31 — it does; frozen v8 already ships `tools/mtmd/models/qwen3a.cpp` + `libmtmd.so.0.0.10107`.
- [x] **S-5 — make STT survive a network outage** ✅ 2026-07-31 — `local_files_only` + `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE`, escape hatch `WHISPER_ALLOW_DOWNLOAD=1`; loads in 1.42 s offline. (`epyc-inference-research/scripts/voice/`.)
- [x] **S-6 — GPU TTS bench** ✅ 2026-07-31 — the hypothesis held, and then some. **xRT 0.86× → 5.47×** (6.4×), **TTFA 67.9 → 37.8 ms**, round-trip WER 1.49 % (0.0 % on the canonical sentence; under `--greedy` the GPU and CPU transcripts are *identical*). `CodecDecode` fell from **64 % → 10.4 %** of total wall — 39× faster per audio-second. New bottleneck: `CodePredictor` at 65.5 %.
- [x] **S-6a — fix the gfx90a `ARGSORT` defect that blocked the GPU path** ✅ 2026-07-31 — at `ne0=2048` it launched **2048 threads per block against gfx90a's 1024-thread cap**, 705× per utterance. Fixed with a thread-strided bitonic sort in the qwentts.cpp ggml fork. `test-backend-ops` now passes ARGSORT **74/74** and TOP_K **292/292**; it previously passed 46/46 and 170/170 **with the failing shapes silently skipped**, which is why a green suite hid the bug. **HIP graphs were never a separate defect** — the graph-capture abort was downstream of the invalid argsort launch; graphs now work, are **13.2 % faster**, and produce bit-identical output. Production kernel untouched (`67a433bf4`).
- [x] **S-7 — retest Qwen3-ASR with the bf16 audio projector** ✅ 2026-07-31 — **superseded; the projector was not the cause.** Extended normalization moved WER only 29.36 % → 28.88 %, so it is not a scoring artifact either. The real mechanism is a **degenerate repetition loop on 21 of 100 rows contributing 94.7 % of all errors**, duration-correlated (0 % of rows under 3 s, 50 % at 7–30 s). Clean rows score **2.27 %** — the model is sound, the deployment is broken.
- [x] **S-8 — bisect the degeneration by utterance length** ✅ 2026-07-31 — done as part of S-7 above; the duration correlation is the bisection result.
- [ ] **S-9 — wire `start_tts()` into `orchestrator_stack.py`** (port 9002 reserved). Capability now exists; only the service wiring is missing. Blocked on nothing except an inference-owning session's boundary.
- [x] **S-10 — decide whether Qwen3-ASR augments or replaces whisper** ✅ 2026-07-31 — **neither. Qwen3-ASR is DROPPED.** `whisper.cpp large-v3-turbo f16` on the MI210 wins outright: WER **2.35 %** (identical to the CPU incumbent), wall **median 0.124 s / max 0.218 s** versus the incumbent's 4.240 s median — the GPU *maximum* is **19× below the incumbent's minimum**. Encode 3751 ms → 110 ms. 2.56 GB VRAM, and it frees 48 CPU cores. Greedy decoding, not beam-5; `large-v3-turbo`, not `large-v3`. **The ~4.2 s fixed floor is gone**, which removes the entire reason Qwen3-ASR was being considered — so its deployment defect is moot and will not be debugged.
- [ ] **S-11 — register the Qwen3-TTS GGUF pair and the `qwentts.cpp` tree** in the model manifest/registry so the speech stack stops being discoverable only from progress logs. Applies MRG-1 (the registration gate every stack model must pass). Record the pins: qwentts.cpp `abab6b3b`, ggml fork `c044c6f0`, binary md5 `5b858d75614dfd2f696071212ae8f2e4`.
- [ ] **S-12 — register `whisper.cpp large-v3-turbo f16` (MI210) as the STT model** and retire the CPU whisper path from the stack definition. Same MRG-1 gate as S-11.
- [ ] **S-13 — carry the qwentts.cpp fork as a PINNED VERSIONED DEPENDENCY, not a merge.** Operator decision 2026-07-31: do **not** merge it into our llama.cpp; running our patched fork indefinitely is acceptable. This task is the pin record + the guard that stops a future session "consolidating" it into the production tree.
- [ ] **S-14 — upstream the gfx90a argsort fix** (thread-strided bitonic sort) to the qwentts.cpp / ggml fork as wrap-up hygiene. Operator-sanctioned; no dependency on our own kernel cycle.
- [ ] **S-15 — set `max_tokens ≥ 1024` on the vision role.** A `max_tokens=128` cap silently penalised reasoning models during vision evaluation (3 parse failures for the incumbent vs **41 and 50** for the Qwen3-VL arms — truncated mid-reasoning and scored wrong). Even at 2048 the Qwen3-VL models emit no letter on ~9 % of hard questions, so 1024 is a floor, not a target. This is a **production config change**, not an evaluation-harness change.
- [ ] **S-16 — promote `Qwen3-VL-30B-A3B Q4_K_M` to the vision role** and retire `Qwen2.5-VL-7B`. Evidence below (§ vision decision). Register per MRG-1; depends on S-15 landing first, or the promotion inherits the truncation defect.
- [ ] **S-17 — audit the GPU resident-set budget before any further GPU model lands.** 27B Q8_0 (27.0) + Qwen3-VL-30B-A3B (21.0) + whisper (2.6) + Qwen3-TTS (1.2) ≈ **51.8 GB of 64**, leaving ~12 GB for KV — the 27B tops out near **90k tokens** on `q8_0` KV. A KV-quantization quality test is in flight to establish whether `q4_0` buys ~180k; do not add a fifth resident model before it reports.

#### Vision decision — SETTLED 2026-07-31

MMMU val, 250 stratified multiple-choice questions, identical rows for every arm, `temp=0.2`, `seed=42`.
Raw: `/mnt/raid0/llm/tmp/vision_final_results.json`.

| arm | accuracy | vs incumbent | McNemar p | VRAM |
|---|---|---|---|---|
| **Qwen3-VL-30B-A3B Q4_K_M** | **63.6 %** | **+11.2 pp** | **0.0011** | 21.0 GB |
| Qwen3-VL-8B | 57.2 % | +4.8 pp | 0.21 (n.s.) | — |
| Qwen3-VL-4B | 54.0 % | +1.6 pp | 0.72 (n.s.) | — |
| Qwen2.5-VL-7B (incumbent) | 52.4 % | — | — | — |

Only the 30B-A3B is statistically separable from the incumbent. **The 8B and 4B are not, and must not
be described as upgrades.**

- [x] **V-1 — the 42-question OCRBench+ChartQA suite MIS-RANKED the field** ✅ 2026-07-31 — the incumbent placed **2nd** there and **last** on MMMU; the 8B inverted between the two suites. This is stronger than the usual saturation caveat: a saturated suite does not merely fail to separate arms, it can **order them wrongly**, so a decision taken on it is potentially backwards rather than merely under-powered. Every conclusion previously drawn from the 42q suite is retracted as a *ranking*.

---

## 3. MiniCPM-O 4.5 (Multimodal: Vision + ASR + TTS) — ⛔ DEPRECATED + DELETED 2026-07-31

**9B dense model** (Qwen3-8B backbone + SigLip2 + Whisper-medium + CosyVoice2). Apache 2.0.

> **⛔ SECTION CLOSED 2026-07-31.** Phase-1 reached its verdict and the verdict is **no**.
> Weights deleted (22 GB reclaimed); recoverable only by re-download from
> `openbmb/MiniCPM-o-4_5-gguf`. M-1/M-2/M-2QA are retained below as completed history; the
> remaining open items (M-2Q, M-3) are **CANCELLED** — see their lines.

### Phase-1 role assessment — operator-sequenced 2026-07-26 (GPU lane, AFTER the Laguna IQ2 architect bench)

Serving viability is already proven: MiniCPM-o smoked **4/4 on MI210 at 114.8–126.9 t/s decode** in the v7 final-cutover vision matrix (2026-07-19, `data/v7_final_cutover_smoke/vision_*/summary.json`). What has NEVER been produced is quality evidence vs the incumbent — that is this assessment:

**RESOLVED 2026-07-31 — the quality evidence was produced and it is negative.** Serving
viability was never the open question; it was answered and then over-weighted. On 42 questions
(OCRBench + ChartQA, MI210, best-on-disk quant per arm) MiniCPM-o Q8_0 scored **31/42** against
the Qwen2.5-VL-7B incumbent's **35/42**, ranking 4th of 5 arms behind Qwen3-VL-30B-A3B (36/42)
and Qwen3-VL-8B (33/42). Phase 1 is closed as a **decline**.

- [x] **M-1 — paired vision eval vs Qwen2.5-VL** ✅ 2026-07-26 — same-image/same-prompt objective-scored live observation in `artifacts/minicpm-o-phase1-v8-20260726/live-20260726T174112Z-O98PrJ/`: `worker_vision` MiniCPM-o `6/8` vs Qwen2.5-VL `5/8` (`+12.5pp`, exact two-sided McNemar `p=1.0`); `vision_escalation` MiniCPM-o `7/10` vs `6/10` (`+10pp`, `p=1.0`). This is `observation_only_unratified`; it asserts no decision threshold and takes **no lineup action**.
  - **⛔ SUPERSEDED 2026-07-31 — both margins are scoring artifacts, not quality.** The
    `vision_escalation` `+10pp` rested on exactly **one** discordant question out of ten
    (`vl_chart_test_0563`): the incumbent answered `0.11 kWh` where the accepted answer was
    `0.11`, and the scorer's `normalized_exact_accepted_alternative` method failed it on the
    unit. Corrected, the two **tied 7/10**. Re-verifiable from the persisted rows —
    `escalation-{baseline,candidate}-scored.json` carry a `score.pass` field per case; all nine
    other cases agree. The `worker_vision` `+12.5pp` is one question out of eight and is
    equally powerless. Honest framing: M-1 was `p=1.0` and `observation_only_unratified`, so the
    42-question run **supersedes on power** — it does not statistically contradict a result that
    never reached significance. This is the second time a bespoke scorer reproduced a
    comma/unit brittleness already fixed once in `debug_scorer.py`.
- [x] **M-2 — TTS Path-B feasibility test** ✅ 2026-07-27 — the pinned `llama.cpp-omni` server route completed CPU-only (`-ngl 0`, Token2Wav on CPU): exactly one HTTP-200 for init/prefill/decode, exact requested text at the TTS boundary, three generated WAV segments, and a structurally valid final 24 kHz mono PCM16 WAV (`0.68s`, `32,684` bytes, SHA-256 `9032de1ccc74d850cd25d47d9605c68354d77510c51f3d4c04191f10adcca9e3`). The completed run was sealed by deterministic recovery after a runner cleanup/reaping defect; **no inference was regenerated**. Evidence: `epyc-inference-research/artifacts/minicpm-o-phase1-v8-20260726/m2-tts/runs/20260727T170914Z/capture.json`. Classification is observation-only: this proves the Path-B mechanics, not intelligibility, quality, latency, MI210 behavior, or lineup suitability.
- [x] **M-2 pinned-interface feasibility** ✅ 2026-07-26 — the initial CLI-only probe at llama.cpp-omni `5202b7b2f4d11f50b9f996161e7a2f8b8571b890` was correctly blocked because that CLI exposed neither text-prompt input nor output-WAV. The 2026-07-27 M-2 successor used the pinned server's reviewed HTTP route; the original blocked artifact remains historical evidence: `epyc-inference-research/artifacts/minicpm-o-phase1-v8-20260726/M2_OMNI_FEASIBILITY_PROBE.md`.
- [x] **M-2QA — automated ASR intelligibility observation** ✅ 2026-07-27 — deterministic concatenation of the three sequential 24 kHz mono PCM16 chunks produced a `2.52s` utterance; cached local `faster-whisper-large-v3-turbo` on CPU transcribed it as `The mini CPM audio path is working.`, matching the requested sentence apart from capitalization. An independent replay reproduced the transcript and exact concatenated PCM payload SHA-256 `4b21d6175b95d59b65b605dc30dafc37596077c6c1c116038d7e8a5fee20802b`. Evidence: `epyc-inference-research/artifacts/minicpm-o-phase1-v8-20260726/m2-tts/asr-observation-20260727T173748Z/` at research commit `11a698f3`. This is an unratified automated intelligibility signal only, not MOS, voice quality, latency, production readiness, or lineup evidence.
- [x] **M-2 Path-B detached derivative v2 pin** ✅ 2026-07-28 — the original corrected-observation v1 failed only at finalization because it rejected the backend `wav_timing.txt` diagnostic. Detached derivative v2 `0a73b24e9244795b2b7052ed583023d91cc8df71`, tagged `minicpm-o-m2-path-b-derivative-v2-20260728`, accepts that exact diagnostic while retaining fail-closed WAV publication; build plus focused CTests are `2/2`. Research commit `0609e51a` pins the v2 observation runner on pushed `main`, with `21/21` tests. This is a derivative/harness repair, not a corrected M-2 observation.
- [x] **M-2 corrected Path-B structural observation** ✅ 2026-07-28 — the v2-pinned detached
  derivative completed on CPU q2 without preempting G3. It wrote a structurally valid `215,084`-byte
  PCM WAV: mono, 24 kHz, 16-bit, `4.48s`, SHA-256
  `aa6abfbfd2fdbfdae1de2789cabcc1667a50a5bf00a3d15c3d78662fa91f1ca4`.
  Evidence: `epyc-inference-research/artifacts/minicpm-o-phase1-v8-20260726/m2-tts/derivative-cli-observation-20260728T090347Z-v2-q2-2955758/observation.json`.
  This is a structural output-contract observation only, not a quality, intelligibility, latency,
  GPU, lineup, registry, service, deployment, or production claim.
- [x] **M-2Q — intelligibility/quality acceptance** — **CANCELLED ✅ 2026-07-31**. Reason: the model is deprecated and its weights are deleted, so there is no WAV to accept and no reason to spend an operator-audible/MOS instrument on it. MiniCPM-o's TTS is not the TTS path — a dedicated 1.14 GB Qwen3-TTS-12Hz-0.6B on CPU is. If an intelligibility/MOS instrument is built, build it against `scripts/voice/tts_server.py`. (Original text: use an operator-audible or separately ratified ASR/MOS-style instrument before claiming the emitted WAV is acceptable speech. The structural M-2 observation does not answer this question.)
- [x] **M-3 — role-swap gate** — **CANCELLED ✅ 2026-07-31**. Reason: there is no role swap to gate. The 42q vision result (31/42 vs the incumbent's 35/42) means promoting MiniCPM-o would be a quality regression, so the lineup change it gated will never be proposed. The three-gates discipline itself is unaffected and still governs any future vision change — which should be evaluated against Qwen3-VL-30B-A3B Q4_K_M (36/42), the only arm measured above the incumbent. (Original text: any actual lineup change is a stack-model change → REQUIRES the AutoPilot E8 baseline reseed to be complete first, then routes through the three-gates discipline (pipeline-green ≠ starts ≠ live==config) + orchestrator_stack lifecycle.)

### Files Downloaded — ⛔ ALL DELETED 2026-07-31

**The entire `/mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/` tree (22 GB) was deleted 2026-07-31.**
The table below is historical. Recoverable only by re-download from `openbmb/MiniCPM-o-4_5-gguf`.

Location: ~~`/mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/`~~ (removed)

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

**⛔ SUPERSEDED 2026-07-31 by a local measurement.** The table below is *vendor-published*
numbers, and it is what made MiniCPM-o look like a vision upgrade (OpenCompass 77.6 vs 70.5,
MathVista 80.1 vs 68.2). Measured on our own hardware against our own suite, the ordering
**inverts**. Local result — 42 questions (OCRBench + ChartQA), MI210, each arm at the best
quant present on disk, scored offline with a unit/whitespace-normalizing scorer:

| model · quant | local 42q accuracy |
|---|---|
| Qwen3-VL-30B-A3B Q4_K_M | **36/42** |
| Qwen2.5-VL-7B Q4_K_M (incumbent, port 8086) | **35/42** |
| Qwen3-VL-8B Q8_0 | 33/42 |
| **MiniCPM-o-4.5 Q8_0** | **31/42** |
| Qwen3-VL-4B Q8_0 | 29/42 |

Raw `/mnt/raid0/llm/tmp/vlquality_results.json`; harness `/mnt/raid0/llm/tmp/vlquality.py`.
Two caveats that keep this honest: **(a)** our suite is OCRBench+ChartQA, the *narrowest* slice
of what these models do — vendor OpenCompass/MathVista claims are not directly refuted, they are
simply not what we measured; **(b)** MiniCPM-o encodes images at ~750 tokens (architecturally
fixed — `--image-max-tokens`/`--image-min-tokens` are verified no-ops for it) where Qwen2.5-VL
spends 4103 on the same image, so part of the gap is input fidelity, not reasoning. Neither
caveat rescues it: what the stack needs is OCR/chart accuracy, and it is 4 below the incumbent.
Also note MiniCPM-o scores **0** unless run with `enable_thinking=false` / `--reasoning off` —
it emits `reasoning_content` with an empty `content`.

Historical vendor table (retained):

| Benchmark | MiniCPM-o 4.5 | Qwen2.5-VL-7B (port 8086) | Qwen3-VL-8B |
|-----------|---|---|---|
| OpenCompass | **77.6** | 70.5 | 76.5 |
| MathVista | **80.1** | 68.2 | 77.2 |
| DocVQA | 94.7 | **95.7** | **96.1** |
| OCRBench | 876 | 864 | **896** |
| Tool calling | None | None | **0.663** |

Caution on the Qwen3-VL side of any such table: the benchmark tables on the Qwen3-VL HF cards
are **JPEG images**, not text — a marketing graphic, not a machine-readable claim. Against the
*independent* OpenVLM baseline the Qwen3-VL OCRBench gain is **+8**, not the +32 the card
implies.

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
   - **SUPERSEDED 2026-07-31**: MiniCPM-o is deprecated/deleted and is no longer the
     leading escalation path — the premise of this deferral is void. The 42q result
     also *reopens the Qwen3-VL lane*: **Qwen3-VL-30B-A3B Q4_K_M scored 36/42**, above
     the 35/42 incumbent (Qwen3-VL-8B at 33/42 stays closed). Step 2's ranking above is
     likewise superseded — it rested on 4 fixed K35 fixtures, and on 42 questions the
     order inverts. Note the deferral's *other* half still holds: this must not become
     another speed-only probe, and a +1-question margin is not a promotion case.

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

1. ~~**Vision upgrade**: MiniCPM-O 4.5 vs Qwen3-VL-8B for `worker_vision`? Qwen3-VL has tool calling edge (+0.663 BFCL).~~ **ANSWERED 2026-07-31: neither.** Measured 42q OCRBench+ChartQA — MiniCPM-o 31/42, Qwen3-VL-8B 33/42, both *below* the incumbent Qwen2.5-VL-7B at 35/42. `worker_vision` stays on Qwen2.5-VL. The only arm that beat it is **Qwen3-VL-30B-A3B Q4_K_M at 36/42**; a +1-question margin on 42 questions is not on its own a promotion case, so if this is revisited it needs a wider suite (MathVision / MMMU-Pro / OmniDocBench, where Qwen3-VL's real gains are) before any lineup action.
2. ~~**TTS path**: Debug Qwen3-TTS C++ port vs test MiniCPM-O native TTS first?~~ **ANSWERED 2026-07-31: neither — the answer is upstream `qwentts.cpp` (Path E).** MiniCPM-o is deleted, and our own C++ accelerator's source is lost (and never worked). `qwentts.cpp` is **measured working on this host** — round-trip WER 0.0 %, TTFA 67.9 ms, 0.86× RT on CPU — where the PyTorch `scripts/voice/tts_server.py` figure was only ever an estimate. Path C is now the fallback. Remaining work is wiring `start_tts()` into `orchestrator_stack.py` (S-9) and the in-flight GPU bench (S-6).
5. **NEW 2026-07-31 — does Qwen3-ASR replace whisper?** OPEN, and deliberately not answerable yet: Qwen3-ASR serves on the MI210 with zero kernel change and is ~2× faster per request where it works, but its current WER is 72.14 % from a configuration defect. Decide only after S-7/S-8. Tracked as S-10.
3. **Port allocation**: 8088 for `audio_worker`? 8086 stays Qwen2.5-VL or gets replaced? — **partially answered 2026-07-31**: 8086 **stays Qwen2.5-VL** (it won the 42q comparison). The `audio_worker` port question is still open but is now a Qwen3-ASR / whisper question, not a MiniCPM-o one.
4. ~~**llama.cpp-omni**: When to build the fork? Blocks all MiniCPM-O audio features.~~ **ANSWERED 2026-07-31: never, for this purpose.** The fork existed solely to unlock MiniCPM-o audio/TTS. With MiniCPM-o deprecated and deleted there is nothing behind that gate. (The pinned detached derivative and its M-2 observation artifacts remain as historical record.)

---

## Resume Commands

```bash
# Vision validation
python3 -c "from src.vision.pipeline import get_pipeline; print('OK')"
pytest tests/vision/ -v

# MiniCPM-O vision test (mainline, no audio)
# ⛔ WILL NOT RUN — 2026-07-31: MiniCPM-o is deprecated and /mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/
# was deleted (22 GB). Both -m and --mmproj paths below no longer exist. Retained as history.
# /mnt/raid0/llm/llama.cpp/build/bin/llama-mtmd-cli \
#   -m /mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/MiniCPM-o-4_5-Q4_K_M.gguf \
#   --mmproj /mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/vision/mmproj.gguf \
#   -p "Describe this image in detail" --image /path/to/test.jpg

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

This represents a **third TTS path** alongside Path A (Qwen3-TTS C++ port, blocked) and Path B (MiniCPM-O built-in TTS, untested) — **note 2026-07-31: Path B is ABANDONED (MiniCPM-o deprecated/deleted) and Path A is unrebuildable (C++ accelerator source lost). Path C, the Qwen3-TTS PyTorch sidecar, is the surviving path and is already implemented at `scripts/voice/tts_server.py`:**

- **Path C**: Run Qwen3-TTS-0.6B as a standalone PyTorch sidecar service. No llama.cpp dependency. FastAPI wrapper accepting text + voice config, returning streaming audio. Feature-flagged behind `ORCHESTRATOR_TTS_ENABLED`.

**Advantage over Path A**: No C++ debugging needed — uses official PyTorch inference. **Advantage over Path B**: Independent service, doesn't couple TTS to a specific vision model. **Disadvantage**: Separate inference stack to maintain (PyTorch, not llama-server).

**Action items** (when TTS becomes a priority):
- [ ] Prototype: FastAPI wrapper around `Qwen3TTSModel.from_pretrained()` on port 8110
- [ ] Benchmark VRAM and latency on EPYC hardware
- [ ] Add `worker_tts` role to model_registry.yaml (gated behind feature flag)
- [x] Design voice cloning guardrails before enabling ✅ 2026-07-29 — **default deny; no cloning is enabled by this design.** Any future `worker_tts` must accept a reference only through an enrolled `voice_id`, not arbitrary request audio. Enrollment requires the rightsholder's recorded authorization, scope (approved uses, expiry, and languages), a SHA-256 of the source asset, and a revocable owner record; retain only the minimum needed reference material under a defined retention/deletion path. Refuse minors, public figures, and any voice lacking an auditable authorization record; do not accept prompts that request imitation of a named/identifiable person or an "in the style of" substitute. Each generated asset must carry synthetic-audio disclosure plus request/voice/authorization/model hashes in an access-controlled audit record; do not log raw reference audio or text more broadly than the approved retention policy. Before any feature-flag enable, require: authorization and expiry enforcement, negative/refusal tests, per-voice revocation and emergency global disable, rate limits, operator-visible audit/review path, and a signed operator decision covering the serving boundary. This is an operational control design, not a legal-compliance determination.

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
  - Delta from current approach: adds a **Path D** (CPU-native LuxTTS) option beyond current Path A (Qwen3-TTS llama.cpp — noise), Path B (MiniCPM-O — untested), Path C (Qwen3-TTS PyTorch sidecar). **Amended 2026-07-31: Path B is ABANDONED (MiniCPM-o deprecated/deleted) and Path A is unrebuildable (source lost); the live comparison is now Path C (implemented, `scripts/voice/tts_server.py`) vs Path D.**

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
- `inference-research-index.md` — Qwen3.5-Omni cross-ref row added 2026-04-22

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
  - Operator-raised angles are now parked unless they answer a concrete role gap: (a) **vision-escalation substitute** only if MiniCPM-o / worker_vision misses a fixture or service requirement **[amended 2026-07-31: MiniCPM-o is deprecated/deleted — read this gate as `worker_vision` (Qwen2.5-VL-7B, 35/42) alone. It is now a *measured* bar: a substitute must beat 35/42 on the 42q OCRBench+ChartQA set, or answer a gap that set does not cover]**; (b) **frontdoor substitute** only with a text-quality hypothesis, not a speed-only multimodal curiosity. NOTE: Google card numbers are only a weak prior — the frontdoor Qwen3.6 is *itself* multimodal, and on a BW-bound CPU host a dense 12B (reads ~12B params/token) likely decodes slower than the ~3B-active MoE frontdoor (measured 25.17 t/s). Any reopened probe must append to the model-probe scoreboard.
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

### MiniCPM-o deterministic promotion runbook (filed 2026-07-23, operator-directed) — ⛔ SUBJECT CANCELLED 2026-07-31

> **SUPERSEDED 2026-07-31.** The runbook was written and delivered (below, ✅ 2026-07-23) —
> that deliverable stands. What is cancelled is its **subject**: the MiniCPM-o promotion will
> never be executed. MiniCPM-o measured **31/42** on 42q OCRBench+ChartQA against the
> Qwen2.5-VL incumbent's **35/42**, so the promotion would have been a quality regression, and
> the weights have been deleted (runbook precondition **P4 "artifacts on disk" can no longer
> be satisfied**). The runbook file now carries a DEPRECATED banner.
>
> **The mechanics remain the reference pattern** — State-A/State-B choreography,
> edit-the-MASTER-registry rule, contention-matrix recert, rollback anchor — and are cited as
> such by `epyc-orchestrator/scripts/server/gpu_shadow_lane.py`. Reuse the *steps* for any
> future vision tenant; do not reuse the MiniCPM-o literals.

Operator directive: the MiniCPM-o/MI210 vision_escalation lane stays parked ("ignore for now") — but **when ready, promotion into the stack must be deterministic, not bespoke**. — **CLOSED 2026-07-31: "when ready" never arrives; the lane is not parked but cancelled.**

- [x] **Write the vision_escalation → MiniCPM-o promotion runbook** ✅ 2026-07-23 — persisted at [docs/runbooks/vision-escalation-minicpmo-promotion.md](../../docs/runbooks/vision-escalation-minicpmo-promotion.md) (drafted + adversarially verified by workflow; 6 corrections applied; data-only + 3 constant lines, registry edit goes to the MASTER). Original spec: a single documented, gate-checked sequence covering (1) registry vision_escalation rebind (model + mmproj + HIP runtime lane, reversing the 2026-07-19 `91cf4033`/`dacd15a2` safe-alias rollback); (2) `stack_change_pipeline.py update` + `check` green; (3) rolling server swap on 8087 via `orchestrator_stack.py` (the 2026-07-23 additive `--numa-mode both` promotion path in `stack_commands.py` is the pattern: explicit-arg authority, skip-healthy, no-outage); (4) §H contention-matrix recert for the changed lane (the 2026-07-17 rebind shipped WITHOUT recert — flagged in v7-promotion.md:38 — the runbook must close that gap, not repeat it); (5) live-affinity + realized-first attestation; (6) smoke via the eval path (image + text probe) with the modality fence verified; (7) rollback = the same runbook with the safe-alias registry state. Prior evidence to cite: MiniCPM-o validation 2026-07-18 (110-127 t/s, 4/4 quality, 8/8 service matrix) vs the alias faster on the 07-19 long-decode slice — the runbook executes whichever model the operator picks; it is model-agnostic mechanics.


## Research Intake Update — 2026-07-29 (Z-Image-Turbo)

### New Related Research — Z-Image-Turbo, a LATENCY candidate only

**Decoupled from quality by construction.** On the bilingual in-image text axis (LongText-Bench,
same benchmark, same splits, EN/ZH mean) the incumbent **ERNIE-Image-Turbo leads 0.9655 vs
Z-Image-Turbo 0.9215** — and Baidu's own model card reproduces Z-Image's per-split numbers exactly,
which is what makes the comparison legitimate rather than a vendor-vs-vendor mismatch. So the
quality question on the axis `image_generate` was selected for is already answered against Z-Image;
the only open question is wall-clock. Scope any trial accordingly: latency, never a quality swap.
(The quality-side resolution and the ERNIE swap decline live in
[`ernie-image-turbo-evaluation.md`](ernie-image-turbo-evaluation.md) — not this handoff.)

- [ ] Keep Z-Image-Turbo as a LATENCY candidate only, decoupled from quality (6B vs 8B, GGUF 2.59-6.58 GB, apache-2.0, runnable on today's binary) against the ~3 min @1024² CPU problem. Any trial must repeat the Q8-vs-Q4 A/B locally.
- [ ] Note the rank-32 distill-patch LoRA (476 BF16 tensors over all 34 blocks) as a Base↔Turbo conversion mechanism; alpha-scaling for step-vs-quality is an UNTESTED hypothesis, and sd.cpp `lora.hpp` key resolution for z_image is unverified.

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

**SUPERSEDED 2026-07-31 — the decision was made and it is NO.** MiniCPM-o is deprecated and its
weights are deleted; the MiniCPM-o cutover will not happen (42q OCRBench+ChartQA: 31/42 vs the
incumbent's 35/42). Consequences for the rule below: the **MiniCPM-o branch of the trigger is
dead**, but the *alias-on-GPU* branch is **not** — moving Qwen2.5-VL itself onto the MI210 lane
remains a live option and would still suspend this gate. So this section stays open, with a
narrower trigger. The "4–10× a CPU quarter stream" arithmetic is model-agnostic and unaffected.

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
- [x] **MiniCPM-o CPU assessment + promotion decision** — **CANCELLED ✅ 2026-07-31**. Reason: the promotion decision was resolved on GPU evidence before the CPU leg ran, and the answer is **do not promote**. On 42q OCRBench+ChartQA (MI210, best-on-disk quant per arm) MiniCPM-o scored 31/42 vs the Qwen2.5-VL-7B incumbent's 35/42 — a quality downgrade for both `worker_vision` and `vision_escalation`. A CPU speed bench cannot reverse a quality deficit, and the weights have been deleted, so the CPU leg is moot. `worker_vision` and `vision_escalation` both stay on Qwen2.5-VL-7B. (Original text: bench MiniCPM-o-4.5 Q4 on a CPU lane vs the current Qwen2.5-VL-7B worker — speed + K35-fixture quality — then DECIDE promotion per the runbook: vision_escalation only, or BOTH. CPU leg only — the operator runs the GPU leg in their parallel session.)

## 2026-08-03 — llama-mtmd-cli resolution: two latent defects fixed, follow-ups filed

_Found while auditing stale build trees; neither was live, both would have bitten the moment
`llama.cpp/build/` went missing. Orchestrator `5c2b33d0`._

The vision/OCR path resolves `llama-mtmd-cli` in **three** places — `services/lightonocr_llama_server.py`,
`vision/analyzers/vl_describe.py`, and `scripts/lib/env.sh`. All three had the same defect:

1. **`exists()` was treated as runnable.** `lightonocr` checked `exists() + X_OK`; `vl_describe`
   checked only `exists()`. Several build trees carry an executable `llama-mtmd-cli` that dies at
   startup on a missing `libomp.so`, and both resolvers would have selected one.
2. **Neither fallback chain contained a production build.** They listed only legacy trees, so a
   missing configured path would have silently selected llama.cpp **8219** or **8954** against current
   models — three release generations behind frozen production, nothing logged.

- [x] Probe `--version` instead of trusting `exists()`, with the binary's own dir on `LD_LIBRARY_PATH` so the probe mirrors the launch environment ✅ 2026-08-03
- [x] Put `build/` and `build-hip/` (both `10107`, ratified v8) first in all THREE chains, and log a warning naming the binary and version on any fallback ✅ 2026-08-03
- [ ] **Verify the fix after the OCR service's next restart.** `CLI_PATH` resolves at module import, so PID 3266570 is still running the old resolution. The fix is inert until whoever owns inference restarts it — no action needed *for* the restart, just confirm resolution afterwards
- [ ] **Unify the triplicated probe.** `_probe_mtmd_cli` (lightonocr), `_mtmd_runs` (vl_describe) and the inline shell probe (`env.sh`) are the same logic in three places and will drift
- [x] **`build-blis52` removed** ✅ 2026-08-03 — 143 MB. A THIRD copy of the same fallback chain was found in `scripts/lib/env.sh` and fixed first (orchestrator `2f57c2a2`); that was its last reference. All three chains verified resolving to `build/bin/llama-mtmd-cli` (10107) afterwards

**Host fact worth not re-deriving:** these build trees run different ggml generations, so a binary must
be invoked with its **own** directory on `LD_LIBRARY_PATH` or it fails with a symbol error that looks
like a broken build. Four working trees were misdiagnosed as dead this session for exactly that reason.
`_mtmd_subprocess_env` already does this at launch; any probe must mirror it.
