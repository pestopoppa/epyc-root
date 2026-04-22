# Qwen3.5-Omni — TTS Unblock Feasibility Deep-Dive

**Date**: 2026-04-20
**Intake source**: `intake-432` (Qwen3.5-Omni Technical Report, arxiv:2604.15804)
**Status**: **REFERENCE ONLY — Scenario C (NOT open-weight)** triggered by closed-source release decision
**Blocked handoff addressed**: `handoffs/active/multimodal-pipeline.md` — TTS component (Paths A/B/C/D)
**Hardware target**: EPYC 9655 (96c/192t Zen 5, 1.1TB RAM, AVX-512, CPU-only)
**Adoption verdict**: **Not adoptable — file as reference architecture. Continue Path D (ZipVoice-Distill) as primary.**

---

## 1. Abstract

Qwen3.5-Omni is Alibaba's March-2026 omni-modal LLM that unifies text/audio/image/video understanding with streaming speech synthesis in a single Hybrid-Attention MoE Thinker–Talker stack. Headline claims: SOTA or parity with Gemini-3.1 Pro across 215 audio/AV benchmarks, 256K context, 400s of 720P video per request, 113-language ASR, 36-language TTS, 435 ms first-packet audio latency (Plus) and 235 ms (Flash). Architecturally the most interesting advance is **ARIA (Adaptive Rate Interleave Alignment)**, which replaces the fixed 1:1 text-speech interleave used in Qwen3-Omni with a dynamic speech-to-text ratio constraint, dissolving the tokenization-rate mismatch that causes number misreads, skipped words, and mispronunciations in streaming TTS. The paper positions Qwen3.5-Omni as the most capable end-to-end omni model to date. **However, Alibaba has departed from its Apache-2.0 tradition and released Qwen3.5-Omni as API-only with no weight release announced.** For EPYC's blocked TTS pipeline, this means Qwen3.5-Omni is a reference architecture, not an adoption candidate. Path D (ZipVoice-Distill) remains the primary unblock path.

## 2. Architecture Recap

### 2.1 Thinker–Talker Hybrid Attention MoE

Qwen3.5-Omni preserves the two-component Thinker–Talker structure introduced in Qwen2.5-Omni / Qwen3-Omni but upgrades **both** components from standard MoE to **Hybrid-Attention MoE** — a pattern where dense attention blocks are interleaved with MoE-attention blocks, giving the model a mix of parameter-efficient routing (for the common case) and full-rank attention (for modality transitions and long-range audio-visual alignment). Paper does not disclose the exact dense/MoE ratio per layer or total active parameter count.

**Thinker** (omni-modal encoder-decoder reasoner):
- Consumes text, audio, image, and video inputs, plus TMRoPE (time-aware rotary position embeddings) across modalities.
- Vision front-end: SigLIP2 encoder (reused from Qwen3-VL lineage).
- Audio front-end: **AuT (Audio Transformer)**, trained on 40M hours of audio-text pairs, producing 6.25 Hz representation tokens.
- 4× Conv2D blocks for 16× mel-spectrogram downsampling.
- 256K context window — 8× larger than Qwen3-Omni's 32K.
- Supports 10+ hours of audio or 400 s of 720P video in a single context.

**Talker** (streaming speech synthesizer):
- Generates multi-codebook RVQ tokens via a lightweight Multi-Token Prediction (MTP) module.
- Uses a causal ConvNet for waveform reconstruction (no diffusion head, no DiT stack).
- Consumes the Thinker's high-level textual intent plus ARIA-aligned speech-side positions.
- Streaming-native: single-stream formulation (ARIA unifies the dual-channel Qwen3-Omni scheme into one tape).

Model family variants: **Plus**, **Flash**, **Light**. The paper and derivative blog coverage do not disclose per-variant parameter counts; downstream coverage estimates Plus at >100B total parameters (consistent with the "hundreds of billions" phrasing in the report). Flash is the latency-optimized variant.

### 2.2 ARIA — Adaptive Rate Interleave Alignment

The concrete mechanism (paper, §3.2):

> ARIA enforces an adaptive rate constraint: for any prefix of the generated sequence, the cumulative speech-to-text token ratio must not exceed the corresponding item-level global ratio.

This is a **per-item dynamic rate cap** rather than a fixed interleave. In practical terms:

1. At generation start, the Talker estimates the ideal speech/text ratio for the language and style of the current utterance (e.g. English spoken narration ≈ 1.4 speech tokens per text token; Chinese ≈ 1.8; numerics require higher ratios).
2. At each decoding step, ARIA permits either a text-side or speech-side token. A speech token is allowed only if the running ratio stays under the item's cap.
3. Both streams share a single autoregressive tape (single-stream formulation), eliminating synchronization latency between dual channels.

Why this matters: Qwen3-Omni's fixed 1:1 interleave underruns when the text is "57329.42" (many phonemes per digit) and overruns during silent pauses. ARIA dissolves that coupling. This is the claimed root cause of Qwen3-Omni's number-misread and skipped-word failures, and ARIA resolves them in the report's ablations.

**Contrast with prior art**:
- **VALL-E / VALL-E-X**: fixed NAR codebook prediction — no adaptive interleave at all. Generates all acoustic codes as a fixed-length expansion of semantic codes.
- **Qwen3-Omni (predecessor)**: dual-stream with 1:1 forced interleave. Simple to implement but brittle under numerics, punctuation, or language switches.
- **Hume TADA (intake-402)**: 1:1 text-acoustic dual alignment — closest prior art to ARIA, but uses flow matching on the acoustic side rather than autoregressive codec tokens.
- **Qwen3.5-Omni ARIA**: single-stream tape, dynamic per-prefix rate cap, item-level global ratio computed from input text.

ARIA's practical advantage: a single KV cache, no separate per-stream synchronization, no speculative rollback when streams desync. For streaming TTS the single-stream formulation reduces first-packet latency by eliminating the second stream's startup overhead.

### 2.3 Dual-Tokenizer Audio Stack (Intake Brief vs. Paper)

The intake summary describes a 25 Hz semantic + 12 Hz acoustic dual-tokenizer audio front-end. **The paper as written does NOT describe that as Qwen3.5-Omni's front-end.** Instead:
- AuT (the Qwen3.5-Omni encoder) emits tokens at a single 6.25 Hz rate.
- The 25 Hz / 12 Hz duality lives in **Qwen3-TTS** (intake-123), not Qwen3.5-Omni.
- The intake-432 brief conflated Qwen3-TTS's dual-rate tokenizer with Qwen3.5-Omni's AuT.

**Correction**: Qwen3.5-Omni runs a unified 6.25 Hz AuT on the Thinker input side and a multi-codebook RVQ codec on the Talker output side. Streaming speech synthesis at ~25 Hz effective output rate comes from the RVQ codec, not from a semantic tokenizer.

### 2.4 Context & Media Limits

- 256K token context (8× the Qwen3-Omni 32K).
- 10+ hours of audio per request.
- 400 s of 720 P / 1 FPS video per request.
- TMRoPE aligns temporally-anchored audio frames against video frames against text positions in a single rotary embedding scheme.

## 3. Benchmark Claims

The paper reports SOTA or parity with Gemini-3.1 Pro across 215 audio/AV benchmarks. A representative sample (Qwen3.5-Omni-Plus vs Gemini-3.1 Pro unless noted):

### 3.1 Audio Understanding

| Benchmark | Qwen3.5-Omni-Plus | Gemini-3.1 Pro | Domain |
|-----------|-------------------|----------------|--------|
| MMAU | 82.2 | 81.1 | Audio understanding multi-task |
| MMSU | 82.8 | 81.3 | Music understanding |
| RUL-MuchoMusic | 72.4 | 59.6 | Music reasoning |

### 3.2 ASR (Automatic Speech Recognition)

| Benchmark | Qwen3.5-Omni-Plus WER |
|-----------|-----------------------|
| LibriSpeech clean | 1.11 |
| LibriSpeech other | 2.23 |
| Common Voice (English) | 4.83 |

113 ASR languages and dialects supported (74 languages + 39 Chinese dialects).

### 3.3 TTS (Zero-Shot, Seed-TTS Eval)

| Benchmark | Qwen3.5-Omni-Plus WER |
|-----------|-----------------------|
| Seed-TTS Chinese | 0.99 |
| Seed-TTS English | 1.26 |

For reference: Qwen3-TTS scored 2.12 / 2.58 on the same eval (intake-123). Qwen3.5-Omni advances WER by ~50 % on this benchmark. 36 TTS languages/dialects supported (29 languages + 7 Chinese dialects).

### 3.4 Speech Translation

| Benchmark | Score |
|-----------|-------|
| Fleurs En↔Zh | 30.2 (BLEU-equivalent) |
| Fleurs Xx↔Zh | 30.2 |

### 3.5 Audio-Visual

| Benchmark | Qwen3.5-Omni-Plus | Gemini-3.1 Pro | Domain |
|-----------|-------------------|----------------|--------|
| DailyOmni | 84.6 | 82.7 | Audio-visual daily scenes |
| Qualcomm IVD | 68.5 | 66.2 | In-vehicle dialogue |

### 3.6 Vision

| Benchmark | Score |
|-----------|-------|
| MMMU-Pro | 73.9 |
| MathVista | 86.1 |

### 3.7 Text

| Benchmark | Score |
|-----------|-------|
| MMLU-Pro | 85.9 |

### 3.8 Inference Latency

| Mode | Plus | Flash |
|------|------|-------|
| First-packet audio (single request) | 435 ms | 235 ms |
| First-packet video (single request) | 651 ms | 426 ms |
| Overall latency at 4-concurrent | 619 ms | 298 ms |
| Thinker TTFT (audio, 4-conc) | 183 ms | — |

All measured on Alibaba Cloud infrastructure — GPU-backed. No CPU figures published.

### 3.9 Training Data

Pretraining volume across modalities (paper §4.1):
- Text tokens: 0.92 T
- Audio tokens: 1.99 T
- Image tokens: 0.95 T
- Video tokens: 0.14 T
- Video-audio joint tokens: 0.29 T
- Total: ~4.29 T tokens

AuT audio encoder pretraining: 40 M hours of audio-text pairs. For reference, OpenAI Whisper-large was trained on 680 k hours — AuT is ~60× larger in audio pretraining, which is the single most credible reason to expect its ASR numbers to generalize (LibriSpeech-clean 1.11 WER rivals the best specialized ASR systems).

## 4. Existing EPYC TTS Landscape

Per `handoffs/active/multimodal-pipeline.md` and deep-dive cross-references:

| Path | Model | Status | Blocker |
|------|-------|--------|---------|
| **A** | Qwen3-TTS via llama.cpp port | **BROKEN** | C++ binary generates codec tokens at 1.5× RT but audio output is unintelligible noise. Next debug step: PyTorch-vs-C++ token divergence trace. Branch `feature/qwen3-tts-support` in llama.cpp-experimental. |
| **B** | MiniCPM-O 4.5 native TTS (CosyVoice2) | **UNTESTED** | Audio features require the `llama.cpp-omni` fork (tc-mb/llama.cpp-omni). Phase 3 blocked on fork build. |
| **C** | Qwen3-TTS PyTorch sidecar (port 8110) | **NOT STARTED** | GPU-leaning (BF16 VRAM 1–3 GB). Feasible on an A100 but out-of-scope for current CPU-only EPYC. |
| **D** | LuxTTS / ZipVoice-Distill CPU sidecar | **READY TO PROTOTYPE** | 123 M Zipformer, 4 NFE flow-matching, sherpa-onnx C++ runtime, INT8 ONNX, RTF projected 0.15–0.22 on 16 EPYC threads. Apache 2.0. |

Current voice loop: `Mic → Whisper(9000) → text → LLM(8080) → response text → ❌ NO TTS OUTPUT`. All four TTS paths are either broken, GPU-bound, untested, or un-prototyped.

## 5. Amend / Expand / Confirm

### 5.1 Confirm

Qwen3.5-Omni validates several architectural bets that the EPYC multimodal program has already made or considered:

1. **Thinker–Talker separation is the right abstraction.** Both Qwen3-Omni and Qwen3.5-Omni converge on a two-component split where a general reasoner emits textual intent and a specialized lightweight Talker synthesizes streaming audio. This mirrors Path A's original intent (Qwen3-TTS Talker + Code Predictor + Speech Tokenizer) and corroborates our Path C PyTorch-sidecar architecture.
2. **Streaming single-stream formulation beats dual-channel.** ARIA's collapse of dual channels into a single tape is consistent with our observation that sidecar TTS services work better as single-stream WebSocket endpoints than as parallel LLM+TTS pipelines. It also validates not over-engineering the Path D integration — a single-stream FastAPI/WebSocket endpoint is sufficient.
3. **MoE Talker is a viable architecture.** Qwen3.5-Omni's upgrade of the Talker from dense to Hybrid-Attention MoE confirms that MoE is not incompatible with streaming audio synthesis, addressing an open question implicit in our Qwen3.5-35B-A3B stack-assembly plan.
4. **ARIA solves the exact failure mode we saw in Path A.** The C++ Qwen3-TTS port generates noise — one plausible root cause is interleave-rate mismatch between the Talker's text-side prompting and the code predictor's expected phoneme pacing. ARIA's dynamic ratio cap is the principled fix, and even if we cannot adopt Qwen3.5-Omni itself, the ARIA idea can be **transplanted** into the Path A debug effort.
5. **10+ languages with emotional nuance is feasible at Talker scale.** Qwen3-TTS's 10-language support is confirmed as not an upper bound — Qwen3.5-Omni raises the TTS bar to 36.

### 5.2 Amend

Were Qwen3.5-Omni open-weight and CPU-feasible, it would displace Paths A/B/C as follows:

- **Path A (llama.cpp Qwen3-TTS port)**: retire. ARIA-equipped Talker in an open-weight Qwen3.5-Omni-Flash would supersede the 0.6 B Qwen3-TTS Talker that Path A is built on. The noise-output debug effort on Path A would become obsolete.
- **Path B (MiniCPM-O 4.5)**: retire. Qwen3.5-Omni offers strictly better multimodal performance (82.2 MMAU vs MiniCPM-O ~74, 84.6 DailyOmni, 1.11 WER LibriSpeech-clean vs MiniCPM-O's 3.37 long-English WER) **plus** better vision (86.1 MathVista vs MiniCPM-O 80.1). It's a straight upgrade on every axis.
- **Path C (Qwen3-TTS sidecar)**: retire or demote. The sidecar pattern is correct but Qwen3.5-Omni Flash's 235 ms first-packet beats Qwen3-TTS's 97 ms only on a GPU baseline — on CPU neither is viable; on GPU Qwen3.5-Omni wins by quality.
- **Path D (LuxTTS/ZipVoice-Distill)**: retain as CPU fallback. Qwen3.5-Omni is not CPU-feasible even if weights were open (see §6), so Path D remains the CPU-era primary and Qwen3.5-Omni would be reserved for a post-GPU hardware state.

**Path E (Qwen3.5-Omni)** as a theoretical 5th path would dominate A/B/C on quality, capability, and breadth. It would **not** dominate Path D on CPU-feasibility. However this analysis is moot because of the adoption blocker in §7 — Path E is not a real option.

### 5.3 Expand

Beyond TTS, Qwen3.5-Omni opens two capability classes that are not on any EPYC roadmap:

1. **Audio-Visual Vibe Coding.** The paper and downstream coverage (abit.ee, the-decoder.com) demonstrate emergent ability to generate code from spoken instructions plus a screen recording. "Qwen3.5-Omni learned to write code from spoken instructions and video without anyone training it to." This is a legitimate new agent front-end modality — if ever available in open weights, it would become the natural backend for an EPYC voice-driven coding agent. Reference architecture value: high.
2. **Omni-modal agent front-end.** 256 K context + 10 h audio + 400 s video + 113-language ASR is a front-door capability profile that no current EPYC component approaches. Even in closed form, it sets the target for what a future hermes-agent / EPYC assistant should support.

Neither capability is adoptable today, but both belong in the research compendium as forward targets.

## 6. CPU Feasibility on EPYC (Hypothetical — if weights were open)

This section estimates what adoption would look like **if Alibaba reversed the closed-source decision**. This is the critical analysis the intake requested.

### 6.1 Is a CPU-deployable GGUF available?

**No.** Confirmed via WebFetch of the HuggingFace Qwen collection and a WebSearch for llama.cpp support as of April 2026:
- `huggingface.co/collections/Qwen/qwen3-omni` lists only Qwen3-Omni (not 3.5) and contains three 30B-A3B checkpoints (Instruct, Thinking, Captioner).
- No Qwen-authored Qwen3.5-Omni repo exists on HuggingFace beyond demo Spaces.
- The only "Qwen3.5-Omni-GGUF" on HuggingFace is `mradermacher/MARTHA-2B-Qwen3.5-Omni-GGUF`, which is a **community 2B derivative fine-tune**, not an official conversion — and it rides on the fact that the `qwen35` text architecture is already registered in llama.cpp.
- llama.cpp mainline does not register an `omni` architecture. The Hybrid-Attention MoE combined with AuT audio encoder + RVQ codec Talker would require substantial llama.cpp work paralleling the Qwen3-Omni port (which has also not been completed in mainline — `ggml-org/llama.cpp/docs/multimodal.md` does not list Qwen3-Omni as supported).
- Even Qwen3-Omni, the older and open-weight sibling, only has Transformers + vLLM support per its GitHub README. No GGUF path exists there either.

### 6.2 Audio codec decode cost on CPU

The Talker emits RVQ tokens decoded by a causal ConvNet. The paper does not publish ConvNet depth, but by analogy to Qwen3-TTS's 8-layer transformer + ConvNet upsampler + 480× stride, CPU decode is tractable **for the codec head alone** — the bottleneck is always the Talker autoregressive pass, not the vocoder. An RVQ-style codec on EPYC with AVX-512 should run at 100–200× realtime, similar to Vocos on the Path D analysis.

### 6.3 NUMA 4-way split — can Thinker and Talker partition?

The EPYC 9655 is a single-socket CCX-rich part presented as four NUMA nodes via `numactl`. The proposed split:

- Thinker on NUMA-0+1 (half the cores, half the memory bandwidth).
- Talker on NUMA-2+3 (the other half).

**Obstacles**:
- Qwen3.5-Omni Plus is estimated at >100 B parameters total. Even at Q4_K_M (~3.5 GB per 10 B), Plus at 100 B ≈ 35 GB; Flash presumably half that. This fits EPYC's 1.1 TB RAM trivially but is larger than any Thinker–Talker split handled to date.
- Thinker–Talker are not independent: the Talker conditions on Thinker activations each decode step. Cross-NUMA activation transfer at every step adds latency that a GPU avoids through unified memory.
- llama.cpp's MoE routing across NUMA nodes has known inefficiencies (see `feedback_mmap_numa_sharing.md`); the scheduler evicts expert weights across nodes under pressure.

**Estimate (if it could be ported)**: Flash-size Thinker (~30 B, Q4_K_M) on 2 NUMA nodes should sustain 8–15 t/s text output — adequate. The Talker's 25-Hz effective output rate needs ~25 token/s sustained; at Q4_K_M on two NUMA nodes this is borderline and likely sub-realtime.

**Mitigation patterns (hypothetical)**:
- Quarter-schedule the Talker on 1 NUMA node with aggressive `numactl --membind=2 --cpunodebind=2`, mlock weights to prevent cross-node thrash, and reserve NUMA-3 as overflow.
- Use speculative decoding on the Thinker side (Qwen3-0.6B draft → Flash target) to amortize the serial decode dependency.
- Pre-encode voice prompts once (Thinker cold-path) and cache, so steady-state streaming is Talker-dominated.
- None of these have been validated empirically on an omni model — they are extrapolations from the Qwen3-30B-A3B and Qwen3-VL benchmarking experience.

### 6.4 Memory footprint at Q4_K_M

Rough estimates (no disclosed parameter counts, so these are upper bounds):

- Qwen3.5-Omni-Plus (~100 B total, ~15 B active by analogy to Qwen3-Omni-30B-A3B): Q4_K_M ≈ 55–70 GB weights + 10–15 GB activation + 10 GB codec + vision encoder ≈ 85–100 GB total. Fits.
- Qwen3.5-Omni-Flash (~30 B total, ~3 B active): Q4_K_M ≈ 17 GB + 5 GB activation + codec + vision ≈ 30 GB. Fits comfortably.
- Qwen3.5-Omni-Light (unknown, likely 7–10 B dense): Q4_K_M ≈ 5–7 GB. Fits trivially.

Memory is not the blocker; compute and latency are.

### 6.5 Streaming token rate feasibility

ARIA's effective output rate is ~25 speech tokens/second (the Talker needs to sustain this for realtime streaming). Required effective sustained decode:
- Text side of ARIA tape: ~15–20 t/s (language-dependent).
- Combined tape (interleaved): 35–45 t/s sustained.

EPYC 9655 CPU-only with 16 cores at Q4_K_M handles 30B-A3B models at ~28 t/s (Qwen3-30B-A3B benchmark). A Qwen3.5-Omni-Flash-sized MoE with Hybrid-Attention should land similarly — **sub-realtime for ARIA streaming TTS, approximately 0.7–0.8× realtime.** Flash would need 2 NUMA-node dedication (96 cores) plus favorable MoE routing to reach realtime.

Plus is out of the question on CPU for realtime streaming. Light might be realtime but capability would be degraded.

### 6.6 Net CPU verdict

**If weights were open**: Only Qwen3.5-Omni-Light would be realtime-streaming-feasible on EPYC CPU. Flash would be usable for non-realtime audio generation (file-mode synthesis). Plus would be memory-feasible but compute-infeasible for streaming. Thinker–Talker NUMA partitioning is theoretically sound but has cross-node latency penalties that need empirical measurement.

**Bottom line**: Even in the counterfactual open-weight scenario, Qwen3.5-Omni is **not obviously a CPU-realtime TTS win** for EPYC. Path D (ZipVoice-Distill) would still be the CPU primary, with Qwen3.5-Omni-Light as a quality-upgrade sidecar if weights appeared.

### 6.7 Comparison table — Qwen3.5-Omni vs existing paths (hypothetical)

| Dimension | Path D (ZipVoice-Distill) | Qwen3.5-Omni-Light (hypothetical) | Qwen3.5-Omni-Flash (hypothetical) |
|-----------|--------------------------|-----------------------------------|------------------------------------|
| Weights open | Yes (Apache 2.0) | **No** | **No** |
| Params | 123 M + 37 M vocoder | est. 7–10 B | est. 30 B MoE |
| Q4_K_M footprint | 250 MB | 5–7 GB | 17 GB |
| Predicted CPU RTF (EPYC 9655, 16 threads) | 0.15–0.22 | 0.6–0.9 | ~1.0–1.3 |
| Realtime streaming | Yes | Borderline | Sub-realtime |
| WER (headline) | 1.51 LS-PC | unknown (Light not evaluated separately in paper) | ~1.11–1.26 Seed-TTS |
| Languages | 2 (EN+ZH) | 10+ (expected) | 36 |
| llama.cpp arch support | Via ONNX/sherpa-onnx | None | None |
| Integration effort | 1 week | Multi-month port | Multi-month port |

Path D's appeal is unchanged. Qwen3.5-Omni is a quality-and-breadth upgrade that EPYC cannot access under present release policy.

## 7. Decision Framework

Three scenarios defined in the intake brief, evaluated against evidence gathered:

### 7.1 Scenario A — Open-weight GGUF available AND CPU-feasible

→ Path E becomes primary, retire A/B/C, monitor Path D as fallback.

**Not triggered.** Neither precondition holds: weights are closed, and CPU feasibility is marginal even under assumption.

### 7.2 Scenario B — Open-weight GGUF available BUT CPU too slow

→ Use as reference architecture, continue Path D as primary.

**Not triggered.** Would apply if only the CPU constraint were binding.

### 7.3 Scenario C — NOT open-weight

→ File as reference, no adoption.

**TRIGGERED.** Alibaba explicitly released Qwen3.5-Omni as API-only on March 30, 2026. `winbuzzer.com/2026/03/31/alibaba-qwen35-omni-closed-source-multimodal-ai-xcxwbn/`: "Alibaba has not published model weights or named a license for Qwen3.5-Omni, making it available only as an API service." No weight-release timeline announced. This departs from Qwen's Apache-2.0 tradition (Qwen3.5-397B-A17B, Qwen3.6-35B-A3B, Qwen3-Omni-30B-A3B all Apache 2.0).

### 7.4 Decision

**Qwen3.5-Omni is NOT adoptable for EPYC's TTS unblock.**

Actions:
1. File intake-432 as `reference_only` in the intake index.
2. Record ARIA as a transplantable technique for Path A debugging — the dynamic text/speech rate cap is a candidate fix for the Qwen3-TTS llama.cpp noise output.
3. Continue Path D (ZipVoice-Distill upstream) as primary TTS unblock, per `research/deep-dives/luxtts-cpu-tts-candidate.md` §10.
4. Monitor Qwen3.5-Omni for a future open-weight release (Qwen has done this before — e.g., early Qwen2.5-Max was API-only then weights followed months later). Re-evaluate if weights appear.
5. Track **Qwen3-Omni-30B-A3B-Instruct** (intake sibling, already open) as a concrete CPU-evaluation target: it's Apache 2.0, on HuggingFace, and tests the omni architecture pattern at a size we could benchmark. Its TTS quality will be strictly below Qwen3.5-Omni but may still beat Path D's ZipVoice on some metrics.

## 8. Risks and Tier 2b Contradicting Evidence

### 8.1 Alibaba self-benchmarking bias

All 215 audio/AV benchmarks in the paper are Alibaba-internal-run. Gemini-3.1 Pro comparisons are particularly vulnerable because:
- Google does not publish reproducible Gemini-3.1 Pro eval configs; Alibaba re-evaluated via API calls.
- MMAU (82.2 vs 81.1), DailyOmni (84.6 vs 82.7), and Qualcomm IVD (68.5 vs 66.2) are all within 2 absolute points — inside plausible re-evaluation noise.
- RUL-MuchoMusic (72.4 vs 59.6) is a 12-point gap that should be independently verified before trust.

Tier 2b assessment: Claims of across-the-board SOTA require independent third-party replication. No such replication exists as of April 20, 2026 — model is only 3 weeks old and API-only (precluding open reproduction).

### 8.2 Closed-source benchmark inflation risk

The API-only nature means external parties cannot reproduce any of the 215 benchmarks. Alibaba can in principle route bench-like queries to specialized internal handling without disclosing it. This is not alleged, but it's an unfalsifiable risk until weights are released.

### 8.3 ARIA novelty

The "Adaptive Rate Interleave Alignment" name suggests novelty, but rate-adaptive interleaving has prior art in VALL-E-style codec LMs and in Hume TADA's text-acoustic synchronization (intake-402, arxiv:2602.23068, RTF 0.09 with similar alignment goals). ARIA's specific contribution is the per-prefix item-level global-ratio cap — a concrete engineering choice, but not the leap the marketing implies. This is consistent with the observation that Qwen3.5-Omni's TTS gains over Qwen3-Omni are real but incremental.

### 8.4 Parameter-count omission

The paper declines to publish total and active parameter counts per variant. This is unusual for an open research report and makes CPU-feasibility analysis (§6) necessarily estimate-based. Readers should treat all memory/compute projections in §6 as upper-bound estimates with ±50 % uncertainty.

### 8.5 Intake-brief conflation

The intake-432 brief claimed "dual-tokenizer audio (25Hz semantic + 12Hz acoustic)" for Qwen3.5-Omni. The paper instead describes a single 6.25 Hz AuT encoder plus a multi-codebook RVQ Talker codec. The 25 Hz / 12 Hz duality belongs to **Qwen3-TTS** (intake-123). Corrected in §2.3. The intake record should be amended.

### 8.6 Proprietary shift implications

Alibaba breaking its Apache-2.0 pattern on its flagship omni model is itself a signal. It may presage closed-source treatment of future Qwen omni/audio releases, which would weaken the long-term reliability of Qwen-authored audio work as an EPYC dependency. Path D's choice to depend on k2-fsa (academic, ASRU-published, full code release) rather than on Qwen-TTS is validated in hindsight.

### 8.7 Quality-ceiling risk for Path D

The counter-risk: if Qwen3.5-Omni-class TTS becomes the quality expectation (1.26 WER Seed-TTS-English, 0.99 Seed-TTS-Chinese, natural prosody across 36 languages), Path D's ZipVoice-Distill (1.51 WER LibriSpeech-PC, EN+ZH only, "slightly mechanical pacing" per third-party reviews) may feel substandard once deployed and compared side-by-side. This is not a deal-breaker for agent voice responses (short, functional), but would matter for any long-form or multilingual production use case. Mitigation: treat Path D as a "minimum viable TTS" that unblocks the voice loop, and track Qwen3-Omni-30B-A3B (the open-weight 3.x sibling) as the first realistic quality-upgrade target for when EPYC gains GPU capacity. Path D → Qwen3-Omni-30B-A3B → Qwen3.5-Omni (if ever open) is a plausible three-step quality ladder.

## 9. Cross-References

- `handoffs/active/multimodal-pipeline.md` — **authoritative TTS state**; update Next Actions to mark intake-432 Decision-C (reference only).
- `research/deep-dives/luxtts-cpu-tts-candidate.md` — Path D analysis; **remains primary unblock path**.
- `research/deep-dives/multimodal-moondream3-qwen3tts.md` — Path C (Qwen3-TTS sidecar) and intake-123 context; ARIA supersedes Qwen3-TTS's fixed dual-rate tokenizer conceptually.
- `research/deep-dives/voicebox-multi-engine-tts-studio.md` — intake-396 multi-engine reference; Qwen3.5-Omni not present as a backend.
- `research/deep-dives/hume-tada-text-acoustic-alignment.md` — intake-402 TADA; closest prior art to ARIA.
- `wiki/hardware-optimization.md` — NUMA-partitioning patterns used in §6.3 feasibility estimates.
- `wiki/local-inference.md` — Thinker/Talker architectural pattern references.
- `wiki/ssm-hybrid.md` — Hybrid-attention MoE architectural pattern references.
- `research/intake_index.yaml` — amend `intake-432` from `worth_investigating` to `reference_only`; amend tokenizer description per §8.5.
- Intake siblings: **intake-121** Moondream 3 (deferred, BSL 1.1), **intake-123** Qwen3-TTS (Path C), **intake-161** OpenDataLoader (unrelated), **intake-251/252** Gemma 4 E-series (GGUF-blocked), **intake-317** VoxCPM2 (GPU-only), **intake-396** Voicebox (Path D discovery), **intake-401** LuxTTS (Path D primary), **intake-402** TADA (long-form shelved), **intake-435** PersonaVLM (not actionable).

## 10. Summary for Handoff

**Recommendation**: File Qwen3.5-Omni as reference architecture. **Do not pursue adoption.** Continue Path D feasibility prototyping per `luxtts-cpu-tts-candidate.md` §7 as the EPYC TTS unblock path. Extract ARIA's dynamic rate-cap idea as a candidate debug intervention for Path A's Qwen3-TTS llama.cpp noise output. Monitor Qwen3.5-Omni weight-release status quarterly.

**Risk if ignored**: spending weeks on a closed API that cannot run on EPYC hardware and cannot be audited.

**Opportunity if monitored**: an eventual weight release (plausible given Qwen's historical trajectory) would reopen this file with Path D still in place as a CPU fallback — no regret.

### 10.1 Concrete next actions (scoped)

1. **Amend intake-432** in `research/intake_index.yaml`:
   - `verdict`: `worth_investigating` → `reference_only`
   - Correct tokenizer description: `dual 25Hz+12Hz` → `unified 6.25Hz AuT + RVQ codec`
   - Add `adoption_blocker: closed_source_api_only`
   - Add `reference_value: high` (ARIA transplantable to Path A, omni architecture pattern)

2. **Update multimodal-pipeline.md "Next Actions" block** (appended to the 2026-04-22 intake update section):
   - Mark the three Qwen3.5-Omni next actions complete with verdict "Scenario C — file as reference, no adoption".
   - Keep Path D Phase D1 feasibility as the immediate TTS work item.

3. **Open a research note** in a future intake cycle tracking ARIA's transferability to Path A debugging. This is not a handoff stub (Research Intake rule: no intake entries via sub-agents), but a noted candidate for user approval.

4. **Monitor quarterly**: Qwen3-Omni-30B-A3B-Instruct is Apache 2.0 and on HuggingFace. It lacks ARIA but shares the overall Thinker–Talker architecture. If time permits a feasibility benchmark on EPYC, this would provide concrete ground-truth numbers for §6's estimates — and would be a genuine adoption candidate if results are favorable. This is a separate handoff-scoped effort, not part of intake-432's resolution.

### 10.2 What this document does NOT do

- Does not validate or refute the 215-benchmark SOTA claim empirically — that requires independent replication which nobody can do under the current release policy.
- Does not propose a Qwen3.5-Omni-specific llama.cpp port. Any such port would be multi-month and is pre-empted by the closed-source status.
- Does not close intake-432's sibling actionables. The ARIA transplant hypothesis for Path A is worth a dedicated bench, but only when/if Path A resumes.
- Does not alter the Path D rollout plan. Path D remains the primary unblock per prior deep-dive recommendation.

---

**Sources**:
- Paper (primary): https://arxiv.org/html/2604.15804v1 — Qwen3.5-Omni Technical Report
- Alibaba closed-source decision: https://winbuzzer.com/2026/03/31/alibaba-qwen35-omni-closed-source-multimodal-ai-xcxwbn/
- Derivative coverage: https://medium.com/data-science-in-your-pocket/qwen3-5-omni-the-best-multi-modal-llm-is-here-4bb4d4e4a809
- MarkTechPost release note: https://www.marktechpost.com/2026/03/30/alibaba-qwen-team-releases-qwen3-5-omni-a-native-multimodal-model-for-text-audio-video-and-realtime-interaction/
- Sibling reference (Qwen3-Omni open-weight): https://github.com/QwenLM/Qwen3-Omni
- Derivative GGUF check: https://huggingface.co/mradermacher/MARTHA-2B-Qwen3.5-Omni-GGUF (community derivative, not official)

---

## Tier 2b Contradicting-Evidence Sweep (2026-04-22)

**Purpose**: Challenge the self-reported SOTA numbers and probe whether API-only release is hiding weaknesses. Verdict (`not_applicable`, `adoption_blocker: closed_source_api_only`) is not revisited — this section strengthens the rationale and provides monitoring signals for the open-weight sibling Qwen3-Omni-30B-A3B.

### T2b.1 Queries Run

1. `"Qwen3.5-Omni" Gemini-3.1 comparison criticism`
2. `"Qwen3.5-Omni" reproduction OR independent evaluation`
3. `Alibaba Qwen benchmark selection bias audio`
4. `Qwen3-Omni 30B Apache open weights closed source strategy change 2026`

### T2b.2 Findings — Credibility of Self-Reported SOTA

**Finding 1: "215 SOTA results" is a marketing aggregate, not a unified benchmark.**
- Source: `buildfastwithai.com/blogs/qwen3-5-omni-multimodal-ai-review` (April 2026 review), `digitalapplied.com/blog/qwen-3-5-omni-vs-gemini-3-1-vs-gpt-5-4-comparison`.
- The 215 count aggregates across subtasks — individual language pairs, specific audio genres, narrow benchmark categories. A model can claim hundreds of SOTAs while losing on the specific benchmark that matters most for a given use case. This is a known pattern in multimodal research PR; Qwen3.5-Omni is not uniquely guilty, but the framing is marketing, not science.

**Finding 2: Gemini-3.1 Pro comparison is credible-but-narrow.**
- Qwen3.5-Omni-Plus genuinely wins on *general audio understanding, reasoning, recognition, and translation* and on *VoiceBench* (93.1 vs 88.9). These are consistent multi-source reports.
- Gemini-3.1 Pro still wins on *video understanding and long-context* (1M tokens, 1hr video / 8.4hr audio per prompt). Qwen3.5-Omni's "400s of 720P video in single pass" is ~15× less than Gemini's ceiling. The "10+ hours of audio" claim is plausibly real but untested independently.
- The audio-visual comprehension category is a *tie*, not a Qwen win. Intake's "surpasses Gemini-3.1 Pro on key audio tasks" is accurate but narrow.

**Finding 3: Gaps within 2 absolute points on critical benchmarks are inside re-evaluation noise.**
- MMAU 82.2 vs 81.1 (1.1pt), DailyOmni 84.6 vs 82.7 (1.9pt), Qualcomm IVD 68.5 vs 66.2 (2.3pt).
- Alibaba re-evaluated Gemini-3.1 Pro via the Google API; Google does not publish reproducible eval configs. Re-evaluation at <2pt gaps is reliably within reproducibility variance for audio LLMs.
- Only RUL-MuchoMusic (72.4 vs 59.6, 12.8pt) would survive noise — and that is the single largest gap, suspiciously so.

**Finding 4: No independent third-party reproduction exists yet.**
- Source: `buildfastwithai.com` review explicitly flags: *"benchmarks self-selected by the releasing lab tend to favor the releasing lab, and more neutral third-party evaluations will tell a clearer story over the next few weeks."*
- EvalScope / OmniBench framework for evaluating Qwen3-Omni exists but no public leaderboard result as of 2026-04-22. Artificial Analysis has begun adding Qwen3.5-Omni-Plus comparison pages but composite scores are not yet populated with independent-run numbers.
- Expected timeline for credible third-party numbers: 4–8 weeks post-release (late May / early June 2026).

### T2b.3 Findings — Why API-Only?

**Finding 5: Strategy shift is explicit and confirmed across multiple sources.**
- Qwen3-Omni-30B-A3B-Instruct / -Thinking / -Captioner: Apache 2.0 on HuggingFace.
- Qwen3.5-Omni **AND** Qwen3.6-Plus (April 2026): both released closed, API-only, no license, no weight-release timeline.
- Source: `digitalapplied.com/blog/open-weight-vs-closed-source-ai-models-q2-2026`: *"Alibaba ships Qwen 3.6 Plus and Qwen 3.5-Omni as closed weights even though earlier Qwen versions were open."*
- Alibaba's public statement: will "continue focus on open source" — but the flagship models are now closed. This is a two-tier strategy: flagship proprietary, smaller/older siblings open.

**Finding 6: Plausible motivations (ranked by likelihood).**
1. **Competitive hold** (high): Gemini-3.1 Pro and GPT-5.4 are closed; open-sourcing a model that competes with them would be uniquely disadvantageous. This is the straightforward commercial explanation.
2. **Speech pipeline reliability/safety** (medium): ARIA streaming TTS with voice cloning (10+ languages with emotional nuance) has obvious deepfake/fraud risk. Closed API allows Alibaba to rate-limit and audit. This would explain why the text-only Qwen3.5-397B-A17B (intake-387) was released open but the omni variant was not.
3. **Benchmark fragility** (low-medium): If some of the 215 SOTA numbers do not survive independent reproduction, an open-weight release would expose this quickly. This is **speculative** but consistent with the pattern of closing the flagship while keeping the smaller sibling open.
4. **Infrastructure coupling** (low): Qwen3.5-Omni may rely on Alibaba Cloud–specific serving infrastructure that is non-trivial to export. Less likely since Qwen3-Omni-30B-A3B runs via vLLM / Transformers.

None of these motivations are mutually exclusive, and none can be ruled out under the current API-only release.

### T2b.4 Historical Gap — Alibaba Self-Reported vs Independent

Search for "Alibaba Qwen benchmark selection bias audio" returned no specific controversy — unlike, e.g., the well-documented gaps on earlier text-only model benchmarks from some Chinese labs. The Qwen text models (Qwen2.5, Qwen3) have generally held up on independent evaluation (LMSYS Chatbot Arena, Artificial Analysis composite), with typical independent-eval regression of 3–8% vs self-reported headline scores — within normal industry range. **No evidence suggests Qwen audio numbers are systematically inflated relative to text.** However, the audio eval ecosystem is less mature (fewer independent benchmarks, smaller sample of third-party reproducers), so the gap could be larger here and simply not yet detected.

### T2b.5 Implications for Monitoring Qwen3-Omni-30B-A3B (Open-Weight Sibling)

The open-weight sibling `Qwen3-Omni-30B-A3B-Instruct` (Apache 2.0, on HuggingFace) is the concrete adoption candidate if the quality gap to Qwen3.5-Omni turns out to be smaller than the marketing implies.

**Monitoring signals to track**:
1. **Artificial Analysis composite**: when they populate Qwen3.5-Omni-Plus with independently-run audio-understanding numbers, compare against Qwen3-Omni-30B-A3B headline numbers. A narrow gap (< 5 absolute points on MMAU/DailyOmni) would make the 30B-A3B a credible adoption target with no quality regret.
2. **EvalScope OmniBench third-party runs**: watch for community-submitted Qwen3-Omni-30B-A3B numbers on the same audio benchmarks Alibaba reported for Qwen3.5-Omni-Plus. This gives a direct quality-delta measurement.
3. **Qwen3.5-Omni weight-release announcement**: Alibaba has historically followed API-first → weights-later on some prior flagships (Qwen2.5-Max took ~4 months). Reopen this file if weights drop.
4. **GGUF availability for Qwen3-Omni-30B-A3B**: llama.cpp mainline does not yet register an `omni` architecture. A community GGUF appearing would unblock CPU-feasibility testing on EPYC, providing concrete ground-truth for the §6 estimates.

### T2b.6 Net Effect on Verdict

**No change.** Verdict remains `not_applicable` with `adoption_blocker: closed_source_api_only`. Tier 2b evidence *strengthens* rather than weakens the downgrade rationale:
- The 215-SOTA framing is confirmed marketing-heavy.
- Gemini-3.1 Pro "wins" are narrow and noise-adjacent on critical benchmarks.
- Closed-source decision looks deliberate and structural (two-tier flagship/sibling strategy), not a short-term hold. Weight release is not imminent.
- The open-weight sibling Qwen3-Omni-30B-A3B becomes the concrete Tier-1 monitoring target; Qwen3.5-Omni drops to Tier-2 (watch quarterly for weight release, no active effort).

**Cross-reference update**: recommend adding `intake-432` to a future "closed-source flagship with open-weight sibling" monitoring list when that list is created (not created in this sweep per Research Intake governance — no sub-agent index modifications without user approval).

**Sources added in sweep**:
- https://www.buildfastwithai.com/blogs/qwen3-5-omni-multimodal-ai-review
- https://www.digitalapplied.com/blog/qwen-3-5-omni-vs-gemini-3-1-vs-gpt-5-4-comparison
- https://www.digitalapplied.com/blog/open-weight-vs-closed-source-ai-models-q2-2026
- https://artificialanalysis.ai/models/comparisons/qwen3-5-omni-plus-vs-gemini-3-pro
- https://evalscope.readthedocs.io/en/latest/best_practice/qwen3_omni.html
- https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct
