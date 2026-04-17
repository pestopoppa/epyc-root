# Hume AI TADA — Text-Acoustic Dual Alignment Deep-Dive

**Intake**: `intake-402` (expanded from voicebox intake-396)
**Paper**: arXiv:2602.23068 — "TADA: A Generative Framework for Speech Modeling via Text-Acoustic Dual Alignment" (Dang, Rao, Gupta, Gagne, Tzirakis, Baird, Cłapa, Chin, Cowen — Hume AI, 2026)
**Blog**: https://www.hume.ai/blog/opensource-tada
**Code**: https://github.com/HumeAI/tada (MIT for code)
**Checkpoints**: `HumeAI/tada-1b`, `HumeAI/tada-3b-ml`, `HumeAI/tada-codec` (Llama 3.2 Community License)
**Initial verdict**: `worth_investigating` (novelty=high, relevance=medium, credibility=3)
**Deep-dive date**: 2026-04-17
**Related**: intake-401 (LuxTTS), intake-396 (voicebox), intake-123 (Qwen3-TTS), intake-317 (VoxCPM2), multimodal-pipeline.md (BLOCKED TTS)

---

## Executive Summary

TADA is a real research contribution with a rigorous architectural story, but on the key EPYC question — CPU viability for the blocked TTS path — it is **effectively a GPU model with a misleading "on-device" marketing claim**. The 1:1 text-acoustic alignment and flow-matching head are well-engineered, the zero-hallucination claim is architecturally grounded (not just a training artefact), and the paper shows ablations and independent-style baselines on EARS. But every published RTF number is on an **H100**, the weights ship **only in PyTorch under a Llama 3.2 Community License**, the flow-matching head runs **10 Euler steps per acoustic frame**, and there is **no GGUF/llama.cpp/ONNX path**. For our blocked Path D (CPU-native TTS), TADA is a worse starting point than LuxTTS and should be shelved until either (a) someone ports the codec + flow-matching head to llama.cpp/ONNX, or (b) long-form (>2 min) coherent synthesis becomes a primary EPYC workload.

---

## 1. Text-Acoustic Dual Alignment — Mechanism

TADA's core idea is to force a **strict 1:1 correspondence between text tokens and acoustic frames** at the LLM's autoregressive step level. From the paper (HTML version):

> "One continuous acoustic vector per text token. Each LLM step corresponds to exactly one text token and one audio frame."

Concretely, the pipeline is:

1. **Text-to-frame alignment (training time)**: a CTC acoustic model operates over the **LLM's own subword vocabulary**, and Viterbi forced alignment assigns an integer number of audio frames to each subword token.
2. **Frame-count encoding via Bit Diffusion with gray coding**: rather than emit a discrete "number of acoustic frames before/after this token" prediction, the flow-matching head predicts `2b` extra analog dimensions per step encoding pre- and post-blank frame counts. This converts the discrete duration-prediction problem into a continuous regression the flow-matching head already handles.
3. **Joint stream at inference**: one LLM step simultaneously produces (a) the next text-token logits, (b) a conditioning vector `c_i ∈ ℝ^{d_c}` for the flow-matching head which samples a 512-dim acoustic embedding plus the duration bits.
4. **Codec → waveform**: the separate `tada-codec` (released as a shared HF repo) decodes acoustic embeddings to PCM audio.

### How this differs from existing tokenisers

| Tokenisation style | Example | Rate | Stream structure | Failure mode |
|---|---|---|---|---|
| Discrete codec | Encodec, SNAC, Mimi (VALL-E, Fish Speech, XTTS) | 12.5 – 75 fps, multi-codebook | Text tokens, then N codebooks per audio frame | Token drift → hallucinated content, length divergence |
| Continuous acoustic | VALL-E 2 continuous, NaturalSpeech | 25 – 50 fps | Separate text prefix, then continuous acoustic stream | Same drift + exposure bias |
| Tokeniser-free diffusion | VoxCPM2 | Variable | Text → diffusion model | GPU-bound, no autoregression over audio |
| **TADA** | 1:1 per-text-token continuous | **2 – 3 fps** | **Single unified stream, one acoustic vector per text token** | Speaker drift past 10 min (different failure class) |

The architectural insight: **content hallucination is a length-mismatch failure**. If the model can decide how many acoustic frames to emit per text token independently of the text stream (or emits acoustic tokens faster than it consumes text), it can skip, repeat, or substitute content. TADA makes this impossible **by construction**: the LLM cannot advance the acoustic stream without advancing the text stream, because they are the same step.

### Is the hallucination-elimination claim rigorous?

**Yes, architecturally** — with caveats. Zero hallucinations on 1000+ LibriTTSR samples (CER > 0.15 threshold) is not the whole story: **EARS long-form expressive CER is 2.34 for TADA-3B (column heading "TADA-3B")**, better than FireRedTTS-2 (21.6) but not dramatically better than Index-TTS (1.90) or VibeVoice 1.5B (2.51). So "zero hallucinations" is a dataset-specific claim on read-speech short utterances. What *is* novel is that TADA gets there **without rejection sampling**, while the competitors rely on either massive training or inference-time filtering.

---

## 2. LLM Backbone Integration

**Llama 3.2 1B/3B — not standard, modified in five places** (from the arxiv HTML):

1. **Additive input fusion** — text and acoustic input embeddings are summed (not concatenated along sequence dim) at each step, so the LLM sees one combined stream.
2. **Position shift by K** — acoustic features are fed into position `i−K`, pairing text token `i` with lookahead-acoustic features from `K` steps back. This provides a controllable acoustic-context window without doubling sequence length.
3. **Dual output heads** — the final hidden state projects to both the text-token logit head and a flow-matching conditioning head.
4. **Acoustic masking** — stochastic audio-segment dropout during training with a learned `<acoustic_mask>` embedding (enables classifier-free / Speech Free Guidance).
5. **Regularisation against base Llama** — the objective adds cross-entropy loss `λ_CE=0.05` for text tokens and KL distillation `λ_KD=0.05` against the base Llama 3.2 model. This keeps the LLM from catastrophically forgetting language modelling during speech co-training.

### Implications for llama.cpp

- Llama 3.2 1B weights are structurally unchanged; the modified transformer blocks are **not a swap-in for standard Llama** because of the additive acoustic input fusion and the dual head on the final layer.
- A llama.cpp GGUF of the backbone alone is **not sufficient** — we would need custom ops for (a) additive acoustic input embedding, (b) the flow-matching conditioning projection, (c) the CTC encoder / tokenizer in the HF codec, (d) the flow-matching iterative solver.
- The official code uses a custom class `TadaForCausalLM` (not `LlamaForCausalLM`) inside the `hume-tada` package. It subclasses Llama but adds the fusion and heads inline.
- **No GGUF, no llama.cpp port, no ONNX export.** The March 2026 update reduced default flow-matching steps from 20 to 10 and mentions `torch.compile` — all still PyTorch+CUDA.

---

## 3. Flow-Matching Decoder — Analysis

The paper specifies:

| Field | Value |
|---|---|
| Solver | **Euler** |
| Steps (N_FM) | **10** (reduced from 20 in March 2026 update) |
| Target vector | `y_i ∈ ℝ^{d_c + 2b}` = [512-dim acoustic features, analog pre-blank-count bits, analog post-blank-count bits] |
| Conditioning | LLM hidden state `c_i` |
| Loss | Flow-matching loss mapping Gaussian `p_0` → target `p_1` |

The flow-matching head is invoked **once per acoustic frame** (one per text token), each with 10 Euler steps — so **10 forward passes through the flow-matching network per text token**. The flow head is smaller than the LLM, but it is non-trivial.

### CPU cost estimate (rough)

- Frame rate: 2–3 fps (say 2.5). For a 60-second utterance, that's ~150 text tokens / 150 acoustic frames.
- Flow head: 10 Euler steps × 150 frames = **1500 flow-head forward passes**.
- Each pass produces a 512-dim vector plus duration bits; the flow head is likely a small UNet or MLP stack (paper does not give FLOPs).
- The codec decoder (waveform synthesis) is **separate** from the flow-matching head — the codec is the `tada-codec` HF artefact, likely a mel → waveform decoder similar to Vocos / HiFi-GAN.

Without FLOP numbers, worst-case estimate: the flow head is probably ~100–300M params (typical for flow-matching acoustic heads in ZipVoice/NaturalSpeech-class systems). On EPYC CPU with 80 cores at int8/bf16, 1500 forward passes of a 200M-param head is still substantial — likely **2–4× wall-clock cost per second of audio** compared with the Llama backbone. This is the same CPU problem LuxTTS/ZipVoice have.

### Same CPU flow-matching bottleneck as LuxTTS?

**Yes, but worse**. LuxTTS is an engineering distillation: 4 flow-matching steps, tuned sampler, purpose-built for small-footprint CPU-friendly inference; LuxTTS's 150× RT CPU claim (vendor-reported) is plausible because the whole system is designed around that. TADA is a research architecture: 10 steps, generic Euler solver, H100-only benchmarks, and the flow-matching head is secondary to the LLM-integration story. No one at Hume optimised TADA for CPU.

---

## 4. Speech Free Guidance (SFG) — Inference Overhead

From the paper:

> `z_i = (1 − λ_SFG) · z_i^{text-only} + λ_SFG · z_i^{text-speech}`

This is classifier-free guidance applied to the LLM's output (both the text logits and the flow-matching conditioning), with `λ_SFG = 0.5` at eval time. Mechanically it requires **two forward passes of the Llama backbone per step** — one with the acoustic-mask embedding (text-only mode) and one with real acoustic features (text-speech mode).

**Paper claim**: *"negligible 0.01 RTF overhead for original batch size of 1"* via parallel execution.

This only holds with **batch-parallel GPU execution** where the two passes share a batch dimension. On CPU with a 1B/3B Llama, two serial forward passes effectively doubles LLM compute; batching them shares matmul K-cache and weight loads but CPU parallelism is not free. Real CPU SFG overhead is closer to **1.5–2× LLM compute**, not 0.01 RTF.

SFG is also the mechanism behind the EARS long-form improvement: without SFG, TADA-3B's EARS speaker similarity is 67.0; with it + online rejection sampling (sSIM 4.18, sMOS 3.78, 2nd place) the numbers become competitive. **Turning off SFG to save CPU cycles degrades quality meaningfully** — it's not optional for the quality claims.

---

## 5. EARS Eval Context

From Table 3 in the paper (long-form expressive speech):

| System | CER | SIM | oMOS | sSIM | sMOS |
|---|---|---|---|---|---|
| **Index-TTS** | 1.90 | 76.9 | 2.84 | **4.25** | 3.61 |
| **VibeVoice 1.5B** | 2.51 | 73.3 | 2.54 | 3.92 | **3.91** |
| FireRedTTS-2 | 21.6 | 73.8 | 2.84 | 3.98 | 3.58 |
| TADA-3B (base) | 2.34 | 67.0 | 2.86 | — | — |
| TADA-3B + Text-Free Guidance | 4.30 | 72.4 | 2.87 | — | — |
| **TADA-3B + Online RS** | 2.74 | 74.7 | 2.84 | **4.18** | **3.78** |

### What "2nd place overall" actually means

- **Speaker similarity (sSIM)**: Index-TTS wins (4.25), TADA 2nd (4.18), gap 0.07 — essentially tied.
- **Naturalness (sMOS)**: VibeVoice 1.5B wins (3.91), TADA 2nd (3.78), gap 0.13 — meaningfully behind.
- **CER**: Index-TTS best (1.90), TADA-3B base 2.34, **TADA-3B+Online RS 2.74** — *worse* than Index-TTS, VibeVoice, and even its own base variant because rejection sampling occasionally picks intelligibility-lower takes for speaker similarity.

So "2nd place" is accurate but marketing-friendly — TADA is **competitive**, not winning. The failure mode TADA fixes (hallucination) is one the EARS expressive eval doesn't even measure (FireRedTTS's CER 21.6 shows hallucination is real in expressive settings, and TADA dominates there — but Index-TTS and VibeVoice also don't hallucinate).

**Key caveat**: Online Rejection Sampling (Online RS) is not a pure-inference operation — it generates multiple candidates and picks the best via a speaker-embedding head. This **multiplies inference cost** (typical rejection sampling is 3–5×). The competitive TADA numbers are TADA+Online RS, not raw TADA. Raw TADA loses on every metric except CER-relative-to-FireRed.

---

## 6. CPU Viability Assessment

### The evidence

| Signal | Value |
|---|---|
| Hume's RTF=0.09 hardware | **H100** (single GPU, `torch.compile`, bf16) |
| Spheron third-party estimate | **~0.25 RTF on A100** (est., not measured) |
| HF README hardware requirement | `device = "cuda"`; 3B needs ~9GB bf16 |
| CPU RTF measurements published | **None** |
| Quantisation support | Not documented — only bf16 |
| GGUF/llama.cpp | **Not available** |
| ONNX | **Not available** |
| Codec format | Separate `tada-codec` HF artefact, PyTorch only |
| Emelia.io independent RTF test | **Not measured** (review reports only Hume's claim) |
| Flow-matching steps | 10 Euler steps per acoustic frame |
| SFG at inference | Doubles LLM forward passes |

### What "on-device" means in Hume's marketing

The blog says TADA is *"lightweight enough to run on mobile phones and edge devices"*. This is plausible for the **1B backbone** running on a modern phone NPU/GPU (Snapdragon 8 Gen 3, Apple A17/A18), **not** for CPU-only EPYC. "Edge device" in 2026 TTS marketing consistently means iPhone-class NPU, not server CPU.

### EPYC CPU back-of-envelope

- Llama 3.2 1B on EPYC (existing benches): ~200 tok/s at Q4_K_M in llama.cpp.
- TADA 1B with SFG = 2× backbone = effective 100 tok/s per acoustic frame.
- At 2.5 fps, each second of audio requires 1 text/acoustic step → 2 backbone forwards + 10 flow-head forwards.
- If we had a llama.cpp port + efficient flow-head + codec: optimistic **RTF ~0.5–1.0** on EPYC (usable but not dramatic).
- **Reality without the ports**: PyTorch CPU mode would be 5–15× slower — RTF ~2–5 (below realtime).

**Verdict**: TADA is GPU-bound as shipped. CPU viability requires a non-trivial port effort (weeks, not days) to get all three components — modified Llama backbone, flow-matching head, codec decoder — running efficiently on CPU, likely via llama.cpp for the backbone + ONNX/ggml for the flow head and codec.

---

## 7. Comparison to LuxTTS as Path D Candidate

| Dimension | LuxTTS (intake-401) | TADA-1B (intake-402) | Winner (Path D) |
|---|---|---|---|
| Architecture | Distilled ZipVoice flow-matching | Llama 3.2 1B + flow-matching head | Context-dependent |
| Research provenance | None (HF single-author distillation of ZipVoice 2506.13053) | Full arxiv paper + ablations | TADA |
| License | Apache 2.0 | Llama 3.2 Community + MIT code | **LuxTTS** (Apache unambiguously re-distributable) |
| CPU claim | 150× RT vendor-reported on CPU | None — H100-only numbers | **LuxTTS** |
| Flow-matching steps | **4** (distilled) | **10** (Euler) | **LuxTTS** |
| VRAM | <1GB | ~2.5GB (1B) / ~9GB (3B) | **LuxTTS** |
| Sample rate | 48 kHz | Not specified (codec-dependent) | LuxTTS |
| Voice cloning | Zero-shot from short ref | Zero-shot via encoder(audio, text) | Tie |
| Multilingual | English + ambiguous Chinese | 1B: en only; 3B: 9 langs | TADA-3B-ml |
| Long-form (>2 min) | Not claimed | **700s in 2048-token context** | TADA (unique) |
| Zero hallucinations | Not claimed | Architecturally guaranteed | TADA |
| Published MOS/SIM/WER | **None** | EARS + LibriTTSR tables | TADA |
| Formal quality benchmarks | None | Competitive (2nd place) | TADA |
| GGUF/llama.cpp path | None (ZipVoice has community ONNX work) | None | Tie (both absent) |
| Ecosystem maturity | Single HF author, no commits visible | 35 GitHub commits, Hume institutional | **TADA** |
| Sample quality pacing | Third-party review: "slightly mechanical" | Third-party review: naturalness behind ElevenLabs | Tie (both flagged) |
| Best fit | **Short utterances, CPU, fast realtime loop** | **Long-form narration, coherent speaker over minutes** | Different use cases |

### Path D re-assessment

The multimodal-pipeline handoff defines Path D as "CPU-native TTS". **LuxTTS is a better Path D candidate** because:

1. LuxTTS is **designed** for CPU (4 distilled steps, 48 kHz, <1GB, Apache 2.0).
2. TADA is **designed for** H100 + 10 Euler steps + SFG overhead + separate codec, with CPU only mentioned in marketing.
3. The voice-loop use case (Mic → Whisper → LLM → TTS → Speaker) wants short utterances and low first-packet latency — TADA's long-form advantage is wasted here.
4. LuxTTS has a clearer risk profile: either the vendor-reported CPU claim holds (adopt) or it doesn't (drop). TADA has a much larger integration surface area and definitely doesn't work CPU-native today.

### When TADA wins

If EPYC gains a workload needing **coherent narration over 2–10 minutes** — reading long responses, audio summaries of documents, podcast-style agent output — LuxTTS will drift or require chunking with crossfades (voicebox's approach), and TADA's 700s context becomes the right architecture. This is not a current workload.

---

## 8. Integration Path for EPYC

Assuming we decide to integrate TADA (e.g., because long-form becomes a priority and GPU is acceptable):

### Phase 1 — Standalone PyTorch sidecar (weeks: 1–2)
- FastAPI service on port 8111 (alongside proposed Qwen3-TTS Path C on 8110).
- `TadaForCausalLM.from_pretrained("HumeAI/tada-1b", torch_dtype=torch.bfloat16)` + `Encoder.from_pretrained("HumeAI/tada-codec")`.
- **GPU required** for acceptable RTF — CPU will not meet realtime.
- Streaming output not yet supported upstream; we'd wrap `model.generate()` and emit chunks.
- Accept Llama 3.2 Community License upstream.

### Phase 2 — CPU viability prototype (weeks: 2–4, speculative)
- Port the modified Llama backbone to llama.cpp via custom GGUF metadata for the additive-fusion fork. Effort is non-trivial because the model is not a vanilla Llama and has an extra head.
- Port the flow-matching head to ONNX + onnxruntime CPU; test Euler vs higher-order solvers to reduce steps below 10.
- Port `tada-codec` to ONNX / ggml.
- Measure actual CPU RTF and first-packet latency.
- **Risk**: If the quality claims depend on SFG + Online RS + 10 steps, CPU-viable config (no SFG, 4 steps) may regress to VoxCPM2/Qwen3-TTS-class numbers.

### Phase 3 — Long-form integration (if Phase 2 succeeds)
- Expose TADA as `worker_tts_longform` in model_registry.yaml, gated behind feature flag.
- Wire into hermes response path for long audio outputs; keep LuxTTS/Qwen3-TTS as short-form TTS.
- Compare against voicebox-style chunk-and-crossfade using LuxTTS for the same long-form use case.

### Files that would change
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml` (lean)
- `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml` (full)
- `/mnt/raid0/llm/epyc-orchestrator/src/` (new `tts_tada` sidecar module)
- `/mnt/raid0/llm/epyc-root/handoffs/active/multimodal-pipeline.md` (new Path E)
- Potentially `/mnt/raid0/llm/llama.cpp/` (custom backbone GGUF conversion + op)

---

## 9. Verdict Delta

### Initial intake (2026-04-17, pre-deep-dive)

```yaml
novelty: high
relevance: medium
credibility_score: 3
verdict: worth_investigating
```

### Post-deep-dive

```yaml
novelty: high                    # confirmed — 1:1 text-acoustic is architecturally distinct
relevance: medium                # slightly reduced — CPU story collapses, long-form not current workload
credibility_score: 3             # unchanged — paper is real but all RTF numbers H100, no independent CPU tests
verdict: worth_investigating     # unchanged — revisit when long-form matters OR when someone ports to CPU
```

### Deltas worth recording in `intake_index.yaml`

1. **Add to `contradicting_evidence`**:
   - "Every RTF number (0.09) is measured on a single H100 with torch.compile and bf16. HF README requires CUDA. No CPU benchmark exists in paper, blog, HF card, or third-party reviews as of 2026-04-17."
   - "EARS 2nd-place scores are TADA-3B + Online Rejection Sampling, which multiplies inference cost. Raw TADA-3B is 67.0 speaker similarity (vs Index-TTS 76.9) before rejection sampling."
   - "Flow-matching head runs 10 Euler steps per acoustic frame (reduced from 20 in March 2026 update); SFG doubles LLM forward passes. Both optimisations assume GPU batch parallelism."

2. **Refine `techniques`**:
   - Replace "Llama-based autoregressive LLM backbone with flow-matching acoustic head" with: "Llama 3.2 1B/3B with (a) additive acoustic input fusion, (b) K-step acoustic position shift, (c) dual text/acoustic output heads, (d) KL-distillation regularisation against base Llama, (e) 10-step Euler flow-matching head over 512-dim continuous acoustic vectors, (f) CTC+Viterbi forced alignment over LLM subword vocabulary at training."

3. **Add to `notes`**:
   - "License: Llama 3.2 Community License for weights, MIT for code. Requires accepting Meta Llama 3.2 license. Not a drop-in re-distributable Apache model."
   - "Languages (3B-ml): ar, ch, de, en, es, fr, it, ja, pl, pt (10 total, not 9). 1B is English-only."
   - "Ecosystem: 35 GitHub commits, 1 release (March 2026). Hume institutional backing. Commercial EVI product suggests open-sourcing as research PR, not long-term maintenance commitment."

4. **Flag for future revisit triggers**:
   - Long-form coherent synthesis becomes a first-class EPYC workload.
   - Community llama.cpp port appears (monitor `HumeAI/tada` issues and forks).
   - GPU becomes available in the EPYC deployment (TADA becomes immediately adoptable as a sidecar).

---

## 10. Head-to-Head Recommendation: LuxTTS vs TADA

**Benchmark LuxTTS first.** Rationale:

1. **Matches the blocked use case**. multimodal-pipeline.md Path D is defined as CPU-native TTS for the voice loop (Mic → Whisper → LLM → TTS → Speaker). Short utterances, low first-packet latency. LuxTTS is designed for exactly this; TADA is designed for long-form GPU inference.
2. **Cheaper failure mode**. A single CPU benchmark of LuxTTS on EPYC resolves to adopt/drop in a day. A TADA CPU evaluation requires porting three separate components (modified Llama, flow-matching head, codec) before we can even measure.
3. **License simplicity**. Apache 2.0 vs Llama 3.2 Community License; redistribution rights matter if we ship EPYC configurations.
4. **Clear risk signal**. If LuxTTS's 150× RT CPU claim is true (or even 2× RT), Path D unblocks immediately. If it fails (noise artefacts like Qwen3-TTS Path A), we've learned something concrete about CPU flow-matching viability that informs the TADA decision.

**TADA stays on the shelf** with two explicit re-entry triggers:

- Long-form (>2 min) coherent audio becomes a required EPYC workload.
- GPU becomes part of the EPYC deployment (sidecar viable without CPU port work).

**Do not run them in parallel.** TADA's CPU port work is weeks; LuxTTS's CPU benchmark is a day. Sequential evaluation is cheaper and more informative.

### Suggested benchmark protocol for LuxTTS on EPYC (for reference, not part of this deep-dive)

1. Install LuxTTS PyTorch on EPYC CPU (no CUDA).
2. Measure RTF, first-packet latency, WER on 20 LibriTTS-R clean samples.
3. Voice-clone WER on 5 reference voices × 10 target texts.
4. Qualitative: listen for the "mechanical pacing" third-party reviewers flagged.
5. Threshold for adoption: **RTF < 1.0 CPU**, WER within 20% of reference, no audible noise artefacts.

If LuxTTS fails, the next candidate is still not TADA — it's either chunk-and-crossfade with a GPU-optional engine (voicebox pattern), or revisit MiniCPM-O 4.5 Path B.

---

## Appendix — Open Questions

1. **TADA codec architecture.** `HumeAI/tada-codec` is shipped separately but the paper doesn't detail whether it's Encodec-style, Vocos-style, or novel. Worth inspecting if CPU viability becomes relevant — the codec is a fixed-cost per audio frame and dominates small-utterance latency.
2. **Does SFG survive CPU single-threading?** Paper claims 0.01 RTF overhead via parallel execution. On EPYC we can parallelise across cores but cache/memory bandwidth is often the bottleneck. A quick empirical test on a Llama 3.2 1B GGUF (no TADA changes) comparing 1× vs 2× batched forward passes would validate the overhead model.
3. **Is the 1B sufficient for our target use case?** All published EARS numbers are TADA-3B. The 1B is English-only and has no published benchmark table. Quality delta between 1B and 3B is unknown from available sources.
4. **Speaker drift mechanism.** Paper acknowledges drift past 10 min / 700s, mitigated by rejection sampling and context resets. Not mechanistically analysed. Suggests the 700s marketing claim is the upper bound, not typical behaviour.
5. **Upstream maintenance posture.** Hume's commercial product (EVI) is the revenue engine. Open-source TADA has 35 commits as of this deep-dive. Unclear whether bug-fixes and multilingual extensions continue at pace or this becomes a frozen research artefact.

---

## Sources

- Paper (arxiv HTML v1): https://arxiv.org/html/2602.23068v1
- Blog: https://www.hume.ai/blog/opensource-tada
- GitHub: https://github.com/HumeAI/tada
- HF tada-3b-ml README (raw): https://huggingface.co/HumeAI/tada-3b-ml/raw/main/README.md
- HF tada-1b README (raw): https://huggingface.co/HumeAI/tada-1b/raw/main/README.md
- Emelia.io review: https://emelia.io/hub/tada-tts-hume-ai-review
- Spheron deployment guide: https://www.spheron.network/blog/deploy-open-source-tts-gpu-cloud-2026/
- Related intake entries: intake-401 (LuxTTS), intake-396 (voicebox), intake-123 (Qwen3-TTS), intake-317 (VoxCPM2)
- Related handoff: `/mnt/raid0/llm/epyc-root/handoffs/active/multimodal-pipeline.md`
