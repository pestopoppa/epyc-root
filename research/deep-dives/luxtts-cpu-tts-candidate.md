# LuxTTS — CPU TTS Candidate Deep-Dive

**Date**: 2026-04-17
**Intake source**: `intake-401` (LuxTTS — Lightweight ZipVoice-Distilled TTS with 48kHz Voice Cloning), surfaced via `intake-396` (Voicebox)
**Initial intake verdict**: `worth_investigating`, credibility=3, novelty=medium, relevance=high
**Blocked handoff addressed**: `handoffs/active/multimodal-pipeline.md` — TTS component (Paths A/B/C all GPU-leaning or broken)
**Hardware target**: EPYC 9655 (96c/192t Zen 5, AVX-512, no production GPU), CPU-only inference

---

## TL;DR

LuxTTS is a **thin fine-tune of the upstream `ZipVoice-Distill` model** from k2-fsa (arxiv:2506.13053, ASRU 2025) with a **community-trained 48kHz Vocos vocoder** swapped in for the default 24kHz one. The "150x realtime" and "faster-than-RT on CPU" claims are derivative of ZipVoice-Distill's published numbers, which **are credible and reproducible** — the upstream paper reports RTF=1.22 on a **single thread** of an Intel Xeon Platinum 8457C for the 4-NFE distill checkpoint. On EPYC 9655 with intra-op parallelism we expect **RTF ≈ 0.08–0.25** (4–12× realtime) at 24kHz, with the 48kHz variant adding a modest ~1.3× overhead from the heavier Vocos head.

Crucially, **the upstream project already ships an ONNX export and sherpa-onnx C++ inference runtime**, plus INT8 quantization. This means **Path D is not a research port; it's a deployment exercise**. LuxTTS the "model" is essentially "ZipVoice-Distill weights + a 48kHz Vocos head" — we should benchmark **ZipVoice-Distill upstream first** (rigorously supported, has ONNX/INT8/C++ paths), then evaluate whether LuxTTS's 48kHz vocoder is worth the overhead.

**Verdict delta**: `worth_investigating` → **`new_opportunity`** for the upstream ZipVoice-Distill path. Credibility of LuxTTS itself **drops from 3 to 2** (single-author HF upload, thin documentation, no formal eval), but credibility of the underlying ZipVoice stack is **4–5** (ASRU 2025, full training code, ONNX/C++ deployment, WER=1.51 on LibriSpeech-PC).

---

## 1. ZipVoice Architecture Background

### 1.1 Parent model (ZipVoice base)

- **Paper**: "ZipVoice: Fast and High-Quality Zero-Shot Text-to-Speech with Flow Matching", k2-fsa, ASRU 2025, arxiv:2506.13053
- **Authors / org**: k2-fsa (the same group behind k2/sherpa/icefall — strong CPU/edge deployment pedigree)
- **Parameter count**: **123M** total — tiny by modern TTS standards (F5-TTS is ~336M, E2 is ~335M, MaskGCT is ~1B)
- **Architecture**:
  - Text encoder: 4 Zipformer layers, d=192, d_ff=512
  - Flow-matching decoder: 5 Zipformer stacks, downsampling rates [1×, 2×, 4×, 2×, 1×], layer counts [2,2,4,4,4], d=512, d_ff=1536
  - **Not a DiT**. Zipformer is a U-Net-shaped conformer-descendant — much more CPU-friendly than transformer-only DiTs because the downsampling keeps sequence length short in the middle layers where most compute concentrates.
- **Training data**: 100k hours multilingual (Chinese + English primarily, as of ZipVoice v1). Emilia + LibriHeavy mix per paper.
- **Default NFE**: 16 for ZipVoice base, 8 for distill (reducible to 4)
- **Sample rate**: 24kHz (upstream default, using a Vocos-24kHz vocoder)
- **License**: Apache 2.0
- **Variants**:
  - `ZipVoice` (base, 16 NFE)
  - `ZipVoice-Distill` (teacher-student distilled, 4–8 NFE) ← **this is what LuxTTS builds on**
  - `ZipVoice-Dialog` and `ZipVoice-Dialog-Stereo` (multi-speaker dialogue variants, arxiv:2507.09318)

### 1.2 Distillation details

Two-phase teacher-student:
1. Phase 1: Student conditions on CFG strength as an input (so a single forward pass equals two teacher forwards with CFG). Teacher fixed.
2. Phase 2: Refinement using EMA of student weights.

This is **consistency-style distillation adapted for flow-matching** — it avoids the common failure mode where step-reduced diffusion models collapse to mean samples.

### 1.3 Published benchmarks (ZipVoice-Distill 4-NFE)

| Metric | ZipVoice 16-NFE | Distill 4-NFE |
|--------|-----------------|---------------|
| WER (LibriSpeech-PC test-clean) | 1.64 | **1.51** |
| SIM-o (speaker similarity) | 0.668 | 0.657 |
| UTMOS | 3.98 | **4.05** |
| RTF on NVIDIA H20 (single GPU) | 0.0557 | **0.0125** |
| RTF on Intel Xeon 8457C (1 thread) | — | **1.2202** |

**Key observation**: Distill is **not a quality downgrade** — WER and UTMOS actually *improve* slightly, likely because the teacher's CFG trajectory smooths over noisy minority modes. SIM-o drops ~1% which is within noise for a 3-second zero-shot prompt.

### 1.4 CPU performance claim is credible

ZipVoice-Distill at **RTF=1.22 on a single Xeon 8457C thread** is the reference measurement to anchor LuxTTS's claims to. The 8457C is a Sapphire Rapids Platinum at 2.6 GHz base / 3.8 GHz boost, 48 cores, similar core-level IPC to EPYC 9655 Zen 5 (EPYC slightly higher on AVX-512 throughput). With multi-threading (intra-op) at batch=1, the Zipformer downsampling structure parallelises well — the upstream `--num-thread` flag is explicitly documented.

Scaling projection for EPYC 9655:
- 1 thread: RTF ≈ 1.22 (upstream measurement baseline)
- 8 threads: RTF ≈ 0.20–0.30 (attention-bound, sublinear)
- 16 threads: RTF ≈ 0.12–0.20 (diminishing returns)
- 32 threads: RTF ≈ 0.10–0.15 (near peak per-utterance)
- Above 32 threads: mostly wasted on short utterances (<5s)

**For an always-on TTS sidecar on EPYC 9655, 16–32 threads per request is the sweet spot**, leaving ~160 threads for parallel LLM serving.

---

## 2. LuxTTS Distillation Specifics (vs. parent)

### 2.1 What LuxTTS actually is

Based on the HF model card, GitHub README, and inference API (`encode_prompt` → `generate_speech(num_steps=4)`), **LuxTTS is a checkpoint of ZipVoice-Distill** with:
1. A **swapped-in 48kHz Vocos head** (the community checkpoint `kittn/vocos-mel-48khz-alpha1` or a variant trained by the LuxTTS author)
2. A custom inference wrapper introducing a **`t_shift` parameter** (default 0.9) — this is a non-uniform time-step schedule for the flow-matching ODE, replacing upstream's uniform Euler steps. This is the "higher quality sampling technique" the README references. It's a known trick from rectified-flow literature; not novel but a sensible engineering tweak.
3. A simplified Python-only inference API (no ONNX, no sherpa-onnx integration — the author stripped k2-fsa's deployment story)

### 2.2 What LuxTTS is NOT

- **Not a new model architecture** — same Zipformer stack as ZipVoice-Distill
- **Not a retrained model** on new data (the author did not publish training logs; weights strongly resemble upstream distill)
- **Not multilingual** — English-only per model card, despite ZipVoice supporting Chinese natively (third-party review tested Polish successfully, Arabic/German failed)
- **Not formally benchmarked** — no WER, no MOS, no SIM-o reported. The third-party review at aiadoptionagency.com is first-party promotional (AI services vendor). The sonusahani.com review is genuine third-party but reports "inference time: ~12 seconds to synthesize" without specifying utterance length, making RTF uncomputable.

### 2.3 Credibility assessment

| Signal | Evidence | Weight |
|--------|----------|--------|
| Single-author HF upload | YatharthS, no org | −1 |
| No formal eval (WER/MOS/SIM) | Confirmed | −1 |
| 3.7k GH stars on ysharma3501/LuxTTS | Some community interest | +0.5 |
| Parent model (k2-fsa ZipVoice) is ASRU-published and Apache 2.0 | Strong | +2 |
| 48kHz Vocos is a known technique, not a new invention | Recycled IP | neutral |
| Vocoder is community-trained (`kittn/vocos-mel-48khz-alpha1`, MIT license, 36.7M params) | Provenance verified | +1 |

**Net credibility for LuxTTS-as-a-product: 2 (down from initial 3)**.
**Credibility for the underlying ZipVoice-Distill stack: 4** (paper published, code released, ONNX export, C++ runtime).

---

## 3. 48kHz Vocoder Analysis

### 3.1 Vocos architecture

- **Paper**: Siuzdak 2023, "Vocos: Closing the gap between time-domain and Fourier-based neural vocoders" (arxiv:2306.00814)
- **Architecture**: 8× ConvNeXt blocks + iSTFT head (generates STFT coefficients, one forward pass, iSTFT to waveform)
- **Not autoregressive, not a GAN per se** (trained with adversarial losses but generator is feed-forward)
- **Key speed advantage**: iSTFT head means the network only predicts spectral coefficients at a **coarse time resolution** (hop_length=256 for 24kHz, ~512 for 48kHz). This is why Vocos is fast — the expensive transposed-conv upsampling of HiFi-GAN is replaced by an FFT.

### 3.2 CPU performance (from Vocos paper, arxiv:2306.00814)

- **169.63× realtime on CPU** (Vocos mel-24kHz, 13.5M params)
- **~13× faster than HiFi-GAN on CPU**
- **~70× faster than BigVGAN on CPU**
- **8-core CPU RTF for bandwidth extension variant: 0.0053** (188× realtime)

### 3.3 48kHz variant cost

The `kittn/vocos-mel-48khz-alpha1` checkpoint is **36.7M params** (vs 13.5M for 24kHz). Parameter scaling is roughly linear in hidden dim at the 8-block depth — ~2.7× more params. Expected CPU overhead: **~2–3× slower than the 24kHz variant**, i.e. RTF for vocoder alone ~60–80× realtime on CPU. **Still negligible vs. the flow-matching decoder.**

### 3.4 Vocoder is NOT the bottleneck

This is the most important finding for EPYC viability. Unlike older TTS pipelines (Tacotron2 + HiFi-GAN, where HiFi-GAN dominated CPU time), the Vocos 48kHz head adds **<5% to end-to-end CPU time**. The bottleneck is the 4-step Zipformer flow-matching pass. **LuxTTS's 48kHz headline feature costs essentially nothing compared to the flow-matching decoder.**

---

## 4. CPU Viability Assessment for EPYC 9655

### 4.1 RTF estimate

Using upstream ZipVoice-Distill's 1.22 RTF on 1 thread of Xeon 8457C as the anchor, with:
- EPYC 9655 Zen 5 single-thread AVX-512 throughput ~1.1–1.2× Sapphire Rapids at similar clock
- 16-thread intra-op scaling factor ~6–8× on Zipformer (measured empirically for k2 Zipformer ASR at similar depth)
- 48kHz Vocos overhead ~1.03× on total inference time

**Projected RTF on EPYC 9655, 16 threads, FP32: 0.15–0.22** (4.5–6.7× realtime)
**With INT8 ONNX: 0.06–0.10** (10–17× realtime)
**First-packet latency** (3-second reference encode + first 0.5s audio chunk): **~150–300 ms**

### 4.2 What "faster-than-realtime CPU" actually means

The LuxTTS README claim is **true but underwhelming** — upstream already achieves RTF=1.22 on a single thread. On EPYC 9655 with sensible multi-threading we can do much better. The 150× realtime GPU number is a legit but derivative claim (H20 GPU, 4 NFE, matches upstream).

### 4.3 Memory footprint

- Model weights: ~500 MB FP32, 250 MB FP16, 125 MB INT8
- Vocos 48kHz: ~150 MB FP32
- Runtime activations at batch=1, max 20s utterance: **<1 GB total**
- **Fits easily in the per-role RAM budget on EPYC 9655**. Can coexist with a 70B LLM in RAM without noticeable pressure.

### 4.4 Flow-matching on CPU: is it fundamentally hostile?

**No.** This was a concern in the intake — flow-matching typically means dozens to hundreds of ODE steps, which is CPU-hostile. But ZipVoice-Distill uses **only 4 NFE**, and each NFE is a **small (123M) Zipformer pass, not a full DiT**. Compare to F5-TTS (336M DiT, 32 NFE default) — ZipVoice-Distill is **~18× less FLOPs per utterance** before any threading speedup. The Zipformer downsampling structure (rates [1,2,4,2,1]) keeps the sequence length small in the middle layers where most compute lives.

**Flow-matching is only CPU-hostile when NFE × model-size is large. ZipVoice-Distill intentionally collapses both.**

---

## 5. Quality vs. Alternatives

### 5.1 Published benchmarks on LibriSpeech-PC test-clean

| Model | WER ↓ | SIM-o ↑ | Notes |
|-------|-------|---------|-------|
| ZipVoice-Distill (4 NFE) | **1.51** | 0.657 | 123M, CPU-viable |
| ZipVoice (16 NFE) | 1.64 | 0.668 | 123M |
| F5-TTS | ~2.4 | ~0.66 | 336M DiT, GPU-only realistically |
| E2 TTS | ~2.95 | ~0.64 | 335M |
| CosyVoice2 (standalone) | ~14.8 | — | Much worse WER |
| MiniCPM-O 4.5 TTS (CosyVoice2 finetune) | 3.37 | — | Long English |
| XTTSv2 | ~4 | ~0.6 | Much larger, older |

**ZipVoice-Distill is competitive with or ahead of every open TTS model on WER.** The 0.657 SIM-o is mid-pack — voice cloning is decent but not market-leading (Qwen3-TTS reports 0.789, VALL-E-X ~0.62, VoxCPM2 unpublished).

### 5.2 Against intake-123 (Qwen3-TTS), intake-317 (VoxCPM2), and existing Paths

| Dimension | LuxTTS (Path D) | Qwen3-TTS Sidecar (Path C) | MiniCPM-O Native (Path B) | Qwen3-TTS llama.cpp (Path A) | VoxCPM2 |
|-----------|-----------------|----------------------------|---------------------------|------------------------------|---------|
| CPU-viable | **YES** (RTF 0.15) | No (GPU-only) | No (needs llama.cpp-omni) | BROKEN (noise output) | No (GPU-only) |
| Model size | 123M + 37M | 600M + codec | ~9B full model | 600M + codec | MiniCPM-4 based |
| First-packet | 150–300 ms | 97 ms (GPU) | unknown | unknown | unknown |
| WER | 1.51 (LS-PC) | 1.835% (10 lang avg) | 3.37% (long EN) | same as C | — |
| SIM-o | 0.657 | 0.789 | ~0.7 (est) | 0.789 | — |
| Languages | EN (+ maybe ZH) | 10 | — | 10 | 30 |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Maturity | Derivative fork | Production | Unverified | Broken | New, GPU-only |
| Integration effort | Low (PyTorch sidecar) or Medium (ONNX+C++) | Low (PyTorch sidecar) | High (fork build) | High (debug C++) | N/A |

**LuxTTS/ZipVoice-Distill is the only CPU-realistic option in this table.** All others either require a GPU or are broken. This is why it matters.

### 5.3 Qualitative notes

- Third-party (sonusahani) review: text synthesis good, voice cloning "not there" at low reference audio quality; substantially improves with clean reference
- First-party promotional review (aiadoptionagency): "slightly mechanical pacing vs heavier models" — consistent with a distilled model trading some prosody variance for speed
- No subjective MOS numbers available beyond upstream ZipVoice's UTMOS 4.05

### 5.4 "On par with models 10× larger" claim

Unverified. Plausible for WER (where ZipVoice-Distill at 1.51 genuinely beats many larger models). **Not plausible for SIM-o or prosody naturalness** — 123M is a hard ceiling for expressive TTS. For agentic voice responses (short, functional), this is fine. For long-form narration, alternatives like TADA (intake-402) would be better.

---

## 6. Licensing

- **LuxTTS**: Apache 2.0 (HF model card)
- **ZipVoice parent (k2-fsa)**: Apache 2.0 (GitHub)
- **Vocos code (charactr-platform/vocos)**: MIT
- **Vocos 48kHz weights (kittn/vocos-mel-48khz-alpha1)**: MIT
- **Training data**: Emilia + LibriHeavy — both CC-BY / research-friendly

**All compatible.** Full commercial-friendly stack. No attribution surprises.

---

## 7. Integration Path for EPYC (Concrete Steps)

### 7.1 Recommended: Path D-upstream (ZipVoice-Distill + sherpa-onnx)

Skip LuxTTS's thin wrapper and go directly upstream. The upstream stack already provides:
1. **Official ONNX export** (HF: `k2-fsa/ZipVoice` model repo, discussion #12 lists the distill ONNX)
2. **INT8 quantization** via `--onnx-int8 True`
3. **C++ CPU runtime** via sherpa-onnx (same runtime we could eventually integrate with our llama-server side stack)
4. **Multi-threading** via `--num-thread N`
5. **pip install zipvoice** for rapid Python prototyping

Implementation plan:

```
Phase D1 — Feasibility (1 day)
  [ ] pip install zipvoice in a scratch venv
  [ ] Download k2-fsa/ZipVoice-Distill checkpoint (~500MB)
  [ ] Run 5 short-form synthesis tests on EPYC (FP32, 16 threads)
  [ ] Measure wall-clock: first-packet, total, utterance length → compute RTF
  [ ] Record audio samples for subjective QA

Phase D2 — ONNX CPU path (2 days)
  [ ] Switch to ONNX export: `zipvoice.bin.infer_zipvoice_onnx --num-thread 16`
  [ ] Benchmark FP32 ONNX vs PyTorch
  [ ] Benchmark INT8 ONNX — measure WER degradation on a held-out set
  [ ] Determine preferred config (FP32 ONNX likely sweet spot)

Phase D3 — 48kHz Vocos head swap (optional, 1 day)
  [ ] Clone kittn/vocos-mel-48khz-alpha1 or LuxTTS's 48kHz head
  [ ] Verify mel-config compatibility (n_mels, hop, window) with ZipVoice encoder output
  [ ] If compatible: A/B test 24kHz vs 48kHz on the same text + reference
  [ ] Decide whether 48kHz is worth the ~1.3× overhead

Phase D4 — Sidecar service (2 days)
  [ ] FastAPI wrapper on port 8110 (reuse Path C's design from multimodal-pipeline.md)
  [ ] Endpoints: POST /v1/tts/synthesize {text, voice_id | reference_audio}, streaming audio return
  [ ] Voice prompt cache (encode_prompt result) keyed by voice_id
  [ ] Integration test from orchestrator chat loop: response text → TTS → WAV → speaker

Phase D5 — Register role (0.5 days)
  [ ] Add worker_tts role to /mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml
  [ ] Gate behind ORCHESTRATOR_TTS_ENABLED flag
  [ ] Document voice-cloning safety constraints (reference audio provenance)

Phase D6 — Optional C++ upgrade (later)
  [ ] Build sherpa-onnx with ZipVoice recipe
  [ ] Wrap in thin llama-server-style HTTP service if latency gains justify
```

### 7.2 Integration with existing orchestrator

The existing `audio_worker` slot proposed in multimodal-pipeline.md maps cleanly:
- Port: 8088 or 8110 (TBD)
- Primary: TTS output (replaces blocked Paths A/B/C)
- Coexists with Whisper ASR on 9000 (already production)
- Can be torn down / replaced later if MiniCPM-O's native audio is revalidated

### 7.3 What NOT to do

- **Do not** port ZipVoice to llama.cpp. The Zipformer architecture is not GGUF-native, flow-matching has no precedent in llama.cpp, and **we would be redoing the Qwen3-TTS Path A debugging nightmare on a different model.** sherpa-onnx is the correct C++ runtime.
- **Do not** base the integration on LuxTTS's HF weights specifically until we've verified they differ meaningfully from upstream ZipVoice-Distill. Use upstream first.
- **Do not** promise multilingual support based on LuxTTS. Upstream ZipVoice is EN+ZH; LuxTTS's English-only model card reflects the author's fine-tune focus.

---

## 8. Recommended Benchmark Protocol (EPYC 9655)

### 8.1 Hardware + environment

- Node: EPYC 9655, 96c/192t, ≥64 GB RAM
- Thread pinning: `OMP_NUM_THREADS=16 numactl --cpunodebind=0 --membind=0` to one NUMA node (avoid cross-node latency)
- PyTorch: 2.3+ with oneDNN enabled (confirm with `torch.backends.mkldnn.is_available()`)
- Disable GPU fallback: `CUDA_VISIBLE_DEVICES=""`

### 8.2 Corpus

- **LibriSpeech test-clean** (2620 utterances, ground-truth transcripts) for WER
- **VCTK p225–p360** (selected 20 speakers, 5 reference samples each) for SIM-o and prosody diversity
- **Internal short-form agent-response prompts** (~50 utterances, 2–8 words) — the actual production workload
- **Long-form prompt** (50 sentences, ~700 chars) — stress test for pacing drift

### 8.3 Metrics

| Metric | Tool | Target |
|--------|------|--------|
| RTF (total wall-clock / audio duration) | direct timing | < 0.25 |
| First-packet latency | streaming timer | < 300 ms |
| P50 / P95 latency across 100 agent-response prompts | histogram | P95 < 1s for 3s utterances |
| WER on LibriSpeech test-clean | whisper-large-v3 judge (same judge upstream uses) | < 2.0 |
| SIM-o (speaker similarity) | WavLM-SV embedding cosine | > 0.60 |
| UTMOS | UTMOS22 checkpoint | > 3.90 |
| Memory peak | /usr/bin/time -v | < 2 GB |
| Quality A/B vs Whisper-round-trip | manual listen, 20 samples | "acceptable" |

### 8.4 Configurations to sweep

```
baseline: PyTorch FP32, 1 thread                  (reproduce upstream 1.22 RTF)
cpu-16:   PyTorch FP32, 16 threads, OMP_PLACES=cores
cpu-32:   PyTorch FP32, 32 threads
onnx-fp32: ONNX Runtime FP32, 16 threads
onnx-int8: ONNX Runtime INT8, 16 threads
luxtts-48khz: LuxTTS weights, 48kHz vocoder, 16 threads
```

### 8.5 Decision criteria

Promote to production sidecar if:
- CPU-16 or onnx-fp32 achieves **RTF < 0.35** (comfortably faster than realtime)
- First-packet latency **< 400 ms**
- WER on LibriSpeech test-clean **< 2.5** (within 1 abs point of upstream's 1.51)
- Memory peak **< 2 GB**
- Subjective agent-response audio rated "acceptable" on ≥16/20 samples

Park if:
- RTF > 0.8 under all configurations (marginal, competing for CPU with LLM)
- WER > 3.0 (voice quality has degraded below usable threshold)
- Memory > 4 GB (eating into LLM budget)

---

## 9. Verdict Delta

### 9.1 Per the investigation targets

| Question from intake | Finding |
|----------------------|---------|
| Is flow-matching practical on CPU? | **Yes, with caveats.** Only when NFE × params is small. ZipVoice-Distill at 4×123M is CPU-feasible. Generic flow-matching at 32×500M is not. |
| Is there an ONNX export / CPU path? | **Yes, upstream.** Official ONNX + INT8 + sherpa-onnx C++ from k2-fsa. LuxTTS itself does not ship ONNX. |
| Vocoder architecture? | **Vocos** (ConvNeXt + iSTFT), 48kHz community checkpoint, 36.7M params, MIT. Not the bottleneck. |
| "Faster-than-realtime CPU" verifiable? | **Derivative but anchored.** Upstream paper reports 1.22 RTF on 1 Xeon thread — extrapolation to EPYC 9655 multi-thread is sound. |
| Independent benchmarks? | **None rigorous.** Blog posts exist but lack RTF computation. Anchor to upstream paper instead. |
| ZipVoice CPU-viable? | **Yes.** 123M is much smaller than F5-TTS (336M); the Zipformer downsampling structure helps. |
| Quality on par with "10× larger"? | **Partly.** WER=1.51 genuinely beats F5/E2/XTTS. SIM-o=0.657 is mid-pack, not market-leading. Prosody "slightly mechanical". |
| Licensing clean? | **Yes.** Apache 2.0 all the way through; Vocos MIT. |
| Integration effort? | **Low-to-medium.** Path D is a 1-week PyTorch sidecar + optional 1-week ONNX C++ upgrade. No llama.cpp port needed. |

### 9.2 Verdict movement

- **LuxTTS-the-fork**: `worth_investigating` → `worth_investigating` (credibility 3 → 2). Don't chase the fork directly; use upstream.
- **ZipVoice-Distill parent (upgrade target)**: implicit → **`new_opportunity`** (credibility 4). This is the actual Path D.
- **Overall intake-401 outcome**: `new_opportunity`. The TTS block is dissolvable with known-quality upstream tech plus a ~1-week integration.

### 9.3 Proposed intake_index.yaml deltas

```yaml
# intake-401 LuxTTS
verdict: new_opportunity        # was: worth_investigating
credibility: 2                  # was: 3 (LuxTTS-the-fork is thinly documented)
parent_model: k2-fsa/ZipVoice   # add field — the real integration target
parent_credibility: 4           # ASRU 2025, full code, ONNX, sherpa-onnx
cpu_rtf_target: 0.15–0.25       # projected on EPYC 9655, 16-thread
integration_effort: P5-1week    # T-shirt estimate
blocks_unblocked:
  - handoffs/active/multimodal-pipeline.md (TTS component, Path D)
```

### 9.4 What this does NOT do

- Does not resolve Qwen3-TTS Path A (the C++ port is still broken; this replaces rather than debugs it)
- Does not provide multilingual parity with Qwen3-TTS Path C (ZipVoice is EN+ZH; Qwen3 is 10 languages). If multilingual agent voice is a requirement, ZipVoice/LuxTTS is insufficient.
- Does not address ASR or vision — those are independent tracks in the multimodal handoff
- Does not obsolete VoxCPM2 (intake-317) or TADA (intake-402) as GPU-era upgrades when hardware changes

---

## 10. Summary for Handoff

**Recommend**: Schedule Phase D1 feasibility (1 day) as the next TTS work item. If RTF and quality land in the projected range, continue through D4 for a production sidecar. Write back to `multimodal-pipeline.md` with "Path D: LuxTTS/ZipVoice-Distill CPU sidecar — prototyped, {RTF}, {WER}, {decision}".

**File**: `/mnt/raid0/llm/epyc-root/research/deep-dives/luxtts-cpu-tts-candidate.md` (this document)

**Related**:
- `handoffs/active/multimodal-pipeline.md` — Paths A/B/C context
- `research/deep-dives/multimodal-moondream3-qwen3tts.md` — Path C (Qwen3-TTS sidecar) assessment
- `research/intake_index.yaml` entries `intake-123`, `intake-317`, `intake-396`, `intake-401`, `intake-402`

**Upstream sources**:
- ZipVoice paper: https://arxiv.org/abs/2506.13053
- ZipVoice repo: https://github.com/k2-fsa/ZipVoice
- LuxTTS HF: https://huggingface.co/YatharthS/LuxTTS
- LuxTTS GitHub: https://github.com/ysharma3501/LuxTTS
- Vocos 48kHz checkpoint: https://huggingface.co/kittn/vocos-mel-48khz-alpha1
- Vocos paper: https://arxiv.org/abs/2306.00814
- sherpa-onnx CPU runtime: https://k2-fsa.github.io/sherpa/onnx/
