# Open-Weights Week Roundup — Per-Model EPYC Triage & Follow-Up Plan

**Date**: 2026-06-12
**Source intake**: intake-694 — "Open-weights week roundup" (Victor M / HF, 2026-06-05); digest of 25+ open-weight drops.
**Type**: Triage deep-dive (decision-grade). Analysis only — no inference/benchmark runs performed.
**Author role**: research-intake deep-dive refiner.

## Purpose

intake-694 is a news digest, not a technique. Its current recommendation is to "flag the individually-notable drops for separate intake." This deep-dive does the actual triage: for **each** genuinely-relevant model, decide whether it warrants its own future intake entry and at what priority, grounded in the **actual** EPYC stack (CPU/llama.cpp, NPS4, 1.1 TB RAM, self-speculation-only spec-dec) and the active handoffs. The clearly out-of-scope generative-media drops are dismissed in one line each.

A key correction surfaced during research: intake-694 frames **Nemotron 3 Ultra as "GPU/NVFP4-gated"**. That is **wrong** — full-precision BF16 weights and llama.cpp-compatible GGUFs (unsloth, DevQuasar) exist; Q4_K_M ≈ 300 GB RAM, which **fits our 1.1 TB host**. This materially raises its priority (see below).

---

## TL;DR / Prioritized follow-up table

| Model | EPYC fit | GGUF / CPU runnable? | Already indexed? | Recommended action | Priority |
|---|---|---|---|---|---|
| **PaddleOCR-VL-1.6** (1B doc-parsing VLM, Apache-2.0) | Direct — doc pipeline / opendataloader; ERNIE-4.5-0.3B backbone; OmniDocBench 96.33 SOTA | **Yes** — official `PaddleOCR-VL-1.6-GGUF` (model + mmproj), llama-mtmd path | No | **Own intake entry + refresh opendataloader handoff** | **P1 (highest)** |
| **Nemotron 3 Ultra** (550B/55B-A hybrid Transformer-Mamba MoE, Apache-derived) | SSM-hybrid readiness line; first full-scale Mamba2-hybrid MoE that **fits in RAM** | **Yes** — unsloth/DevQuasar BF16+Q4 GGUF; Q4_K_M ≈300 GB RAM (CPU path, `-DGGML_CUDA=OFF`); MTP unsupported in GGUF | Family yes (Nemotron-Cascade/Nemotron-3-Nano entries) but **not this 550B Ultra SKU** | **Own intake entry + refresh log-linear/SSM readiness handoff** (it's a concrete GGUF to smoke-test the hybrid-Mamba CPU path) | **P1** |
| **Step-3.7-Flash** (196B+1.8B-ViT MoE VLM, 11B active, Apache-2.0) | Coder/coder_escalation **eval candidate** (SWE-Bench Verified 76.5 / PRO 56.3); VLM | **Yes** — official `stepfun-ai/Step-3.7-Flash-GGUF` + bartowski/unsloth; llama.cpp arch supported; vendor targets ≥128 GB unified mem | No | **Own intake entry** (eval-only candidate vs current coder_escalation = Qwen3.6-35B-A3B Q8) | **P2** |
| **Mellum2-12B-A2.5B-Thinking/-Instruct** (coding MoE, Apache-2.0) | Cheap code-completion / IDE-FIM worker tier only; too small to beat coder_escalation | **Yes** — official JetBrains GGUF (Q8_0, Q4_K_M) + 30 community | No | **Own intake entry, low priority** (standalone cheap FIM tier; NOT a drafter — 98 304 vocab ≠ targets) | **P3** |
| **Gemma 4 12B** (dense any-to-any, 256k, AIME 77.5) | Already part of the Gemma 4 program | n/a (Gemma 4 family GGUF supported) | **Yes** — Gemma 4 family indexed (intake-256/257 + MTP deep-dive); 12B SKU specifically not | Add a one-line note to existing Gemma 4 thread; **no new entry needed** | **P4 (note only)** |
| **Liquid LFM2.5-8B-A1B** (edge MoE) | Standalone cheap tier only; vocab-mismatch → not a drafter | Yes (`lfm2moe` in our HEAD) | **Yes** — intake ~31504 + deep-dive; verdict standalone-only | **None** — already triaged | — |
| **PaddleOCR's siblings / dots.tts / Higgs Audio v3 / Nemotron-3.5 ASR** | TTS/ASR → multimodal-pipeline | Mixed | No | Track under multimodal-pipeline TTS/ASR shortlist (not individual entries unless prioritized) | **P3 (audio batch)** |
| Ideogram 4, Magenta RealTime 2, NVIDIA Cosmos3-Super, VAST TripoSplat, Baidu NAVA | **Out of scope** — image / music / world-video / 3D / joint AV generation | n/a | No | **Dismiss** (one-liners below) | — |

---

## Per-model assessment

### P1 — PaddleOCR-VL-1.6 (own entry + handoff refresh)

- **License**: Apache-2.0. **Size**: 1.0 B params; backbone is **ERNIE-4.5-0.3B** + a vision encoder. Finetuned from PaddleOCR-VL-1.5.
- **CPU runnability**: **Confirmed**. Official `PaddlePaddle/PaddleOCR-VL-1.6-GGUF` ships the model GGUF **and** an `mmproj` GGUF; PaddlePaddle announced llama.cpp-ecosystem support directly. Runs via `llama-cli/llama-mtmd-cli --mmproj … --image …`. At 1 B params it is trivially CPU-cheap.
- **Tasks**: OCR, table, formula, chart, layout analysis, seal/stamp, text spotting, full document parsing. **OmniDocBench v1.6 overall 96.33 (SOTA)**; SOTA across all 5 Real5 scenarios (scan/warp/screen-photo/illumination/skew). EN/ZH/multilingual.
- **EPYC fit**: **Direct.** The opendataloader handoff (`handoffs/active/opendataloader-pipeline-integration.md`) already lists PaddleOCR only as a *pluggable OCR HTTP backend* candidate competing with `pdftotext` for the Phase-1 born-digital slot. PaddleOCR-**VL**-1.6 is a different and stronger artifact: a **full VLM document parser** that produces structured layout + tables + formulas + reading order in one pass — i.e., it overlaps the current **LightOnOCR** slow-path role and ODL's structural-extraction goal, not just the fast-path OCR slot. It is the cheapest SOTA doc-parsing VLM we can run; it should be a benchmarked alternative to LightOnOCR + a structural-extraction complement to ODL JSON.
- **Recommendation**: **Own intake entry, P1.** Refresh the opendataloader handoff to distinguish "PaddleOCR (engine, HTTP backend)" from "PaddleOCR-VL-1.6 (1B VLM doc parser, GGUF+mmproj, candidate to bench vs LightOnOCR)". Eval-gated (no run here).

### P1 — Nemotron 3 Ultra (own entry + SSM-readiness handoff refresh)

- **License**: NVIDIA open model (Apache-derived community license; self-host OK — license is a non-blocker per project policy).
- **Architecture**: **Hybrid Transformer-Mamba MoE**, 550B total / **55B active**, 1M ctx, Latent MoE + Multi-Token Prediction. MMLU 89.1.
- **CPU runnability — the correction**: intake-694 says "NVFP4 ~5x on Blackwell" and tags it GPU-gated. Reality: **BF16 full-precision GGUFs exist** (`DevQuasar/…BF16-GGUF`, `unsloth/NVIDIA-Nemotron-3-Ultra-550B-A55B-GGUF`); unsloth's "Run Locally" doc gives explicit **CPU instructions** (`-DGGML_CUDA=OFF`) with RAM tiers: UD-IQ3_XXS ≈256 GB, **Q4_K_M ≈300 GB**, 8-bit ≈600 GB — all **within our 1.1 TB host**. Caveat: **MTP is not supported for the GGUFs** (loses the headline speedup; decode is the BW-bound base path). A known llama.cpp eval bug exists on the **Nemotron-3-Nano** Mamba GGUF (`mamba-base.cpp:173 GGML_ASSERT`, ggml-org/llama.cpp#20570) — must verify the Ultra SKU doesn't hit the same assert before trusting any run.
- **EPYC fit**: This is the **first production-scale hybrid-Mamba MoE that actually fits in our RAM and has a CPU GGUF path** — exactly the artifact the SSM-hybrid lines (`log-linear-gated-deltanet-readiness.md`, `multiscreen-attention-evaluation.md`) have been *waiting* for to exercise the Mamba2-hybrid serving path on llama.cpp/CPU. It does NOT satisfy the Log-Linear-GDN gate (it's Mamba2-hybrid, not Log-Linear Gated DeltaNet), so it does **not** activate that implementation plan — but it is a concrete checkpoint to validate hybrid-SSM CPU decode behavior, KV/state management, and the `mamba-base.cpp` assert class on our fork.
- **Recommendation**: **Own intake entry, P1**, explicitly **correcting the "GPU-gated" framing**. Refresh the log-linear/SSM readiness handoff with a "concrete Mamba2-hybrid GGUF now available for CPU smoke-test (does NOT fire the Log-Linear gate)" note. Smoke-test eval-gated (no run here; check #20570 assert first).

### P2 — Step-3.7-Flash (own entry; coder eval candidate)

- **License**: **Apache-2.0**. **Size**: 196B + 1.8B ViT, **11B active** MoE VLM. Context not stated on blog. Coding: **SWE-Bench Verified 76.5, SWE-Bench PRO 56.3, SWE-Bench-MTLG 72.4, Terminal-Bench 2.1 59.6**.
- **CPU runnability**: **Confirmed.** Vendor blog: "developers can use vLLM, SGLang, HF Transformers, **and llama.cpp**" and explicitly targets "high-memory devices … with at least 128 GB unified memory" — i.e., our regime. Official `stepfun-ai/Step-3.7-Flash-GGUF` + bartowski/unsloth conversions exist; NVIDIA dev-forum thread "Step-3.7-Flash on single Spark (llama.cpp only)" corroborates the CPU/llama.cpp path. At 11B active it decodes cheaply for its size; 196B total Q4 ≈ ~110-130 GB RAM (fits).
- **EPYC fit**: The only roundup model with a **plausible upgrade case for coder_escalation**. Current coder_escalation = **Qwen3.6-35B-A3B Q8** (97% internal coder eval, absorbed architect_coding); worker_coder = Qwen3-Coder-30B-A3B. Step-3.7-Flash's SWE-Bench Verified 76.5 is competitive with frontier coding agents, it's Apache-2.0, **and** it adds a VLM capability the current coder lacks. BUT: 196B total is heavier than the 35B-A3B incumbent, decode t/s on CPU must be measured, and tokenizer ≠ our targets so it is **standalone-only, not a drafter** (production spec-dec is self-speculation).
- **Recommendation**: **Own intake entry, P2 — eval-only candidate** vs coder_escalation. The bar is "beat Qwen3.6-35B-A3B Q8 on the internal coder/agentic suite at acceptable CPU decode t/s." Bench-gated (no run here).

### P3 — Mellum2-12B-A2.5B (own entry; low priority, cheap FIM tier)

- **License**: **Apache-2.0**. **Arch**: MoE, 12B total / **2.5B active** (8/64 experts), 28 layers, GQA 32Q/4KV, sliding-window(1024)+full hybrid, **vocab 98 304**, 131k ctx. Two variants: Thinking (`<think>` traces) and Instruct (low-latency). Thinking RL scores: LiveCodeBench v6 69.9, BFCL v3 69.4, AIME'25+'26 58.4, MMLU-Redux 86.2.
- **CPU runnability**: **Confirmed.** Official JetBrains GGUF repos (`…-Thinking-GGUF-Q8_0`, `…-Instruct-GGUF-Q4_K_M`) + 30 community quants. Tiny (2.5B active) → very fast on CPU.
- **EPYC fit**: JetBrains designed Mellum for **IDE code completion / FIM**, not agentic SWE. At 2.5B active it will not beat the 35B-A3B coder_escalation or the 30B-A3B worker_coder on hard coding. Realistic role = a **standalone cheap fast-completion / FIM worker tier** or a triage-first cheap coder. **NOT a drafter**: 98 304-token vocab ≠ Qwen3.6 / gemma4 tokenizers; production spec-dec is self-speculation only.
- **Recommendation**: **Own intake entry, P3.** Cheap-FIM-tier standalone candidate; explicitly strike any drafter rationale. Low priority — no current role gap, but Apache-2.0 + tiny + official GGUF makes it a cheap thing to keep on the shelf (per "don't dismiss creative cheap-worker uses" policy).

### P4 — Gemma 4 12B (note only, no new entry)

- Dense any-to-any, 256k ctx, encoder-free, AIME 77.5, 23-checkpoint QAT wave. **Gemma 4 family is already indexed** (intake-256 MLX, intake-257 Official, SuperGemma4 fine-tune entry, and the full gemma4-MTP-drafter deep-dive — and gemma4-26B-A4B MTP is our **deployed worker_general**). The 12B dense SKU specifically isn't called out, but it adds no new architecture and our worker is already a Gemma 4 MoE. **No new entry** — append a one-liner to the existing Gemma 4 thread if anyone wants the 12B-dense QAT checkpoint tracked.

### Already-triaged — Liquid LFM2.5-8B-A1B (no action)

Already intake ~31504 + companions, with `research/deep-dives/lfm2-lfm25-family-deep-dive.md`. Deep-dive (2026-05-29) downgraded it to **worth_investigating / standalone-only**: `lfm2moe` is in our llama.cpp HEAD (PR #16464), official Q4_K_M 5.16 GB GGUF — but **no production role gap** and **not a drafter** (own 128k `lfm2` vocab ≠ targets). **Nothing to do.**

### Audio/ASR batch — track under multimodal-pipeline (P3)

- **Boson Higgs Audio v3** (4B, 102 langs, 21 emotions), **RedNote dots.tts** (continuous no-codec TTS, Apache-2.0), **NVIDIA Nemotron-3.5 ASR** (600M streaming, 17× concurrent streams vs Parakeet RNNT 1.1B). These fit the **TTS/ASR** half of `multimodal-pipeline.md` (currently MiniCPM-O 4.5 / Qwen3-TTS path, TTS blocked). Recommend a **single TTS/ASR shortlist refresh** under that handoff rather than three separate entries, unless the user wants to prioritize the audio line. dots.tts (Apache-2.0, no-codec) and Nemotron-3.5 ASR (tiny, streaming) are the two worth a closer look first.

### Dismissed — out of scope (one line each)

- **Ideogram 4** — open-weights image-gen DiT (9.3B flow-matching); no text-inference / EPYC-role fit. Dismiss.
- **Google Magenta RealTime 2** — <200 ms real-time music generation; out of scope. Dismiss.
- **NVIDIA Cosmos3-Super** — 64B omnimodal *world model* (video/sim); GPU world-modeling, no EPYC role. Dismiss.
- **VAST TripoSplat** — single-image-to-3D Gaussian splats (MIT); 3D asset gen, out of scope. Dismiss.
- **Baidu NAVA** — 6.3B joint audio-video generation; generative AV, not an inference-serving fit. Dismiss (could note under multimodal only if AV *understanding* emerges, but it's framed as generation).

---

## What to actually intake next (prioritized)

1. **PaddleOCR-VL-1.6** (P1) — own entry; Apache-2.0, 1B, GGUF+mmproj confirmed; bench vs LightOnOCR in the opendataloader/doc pipeline. Refresh opendataloader handoff.
2. **Nemotron 3 Ultra 550B-A55B** (P1) — own entry; **correct the "GPU-gated" framing** (BF16/Q4 GGUF runs CPU, Q4_K_M ≈300 GB fits 1.1 TB); first in-RAM Mamba2-hybrid MoE for the SSM-readiness CPU smoke-test (does NOT fire the Log-Linear-GDN gate). Refresh log-linear/SSM readiness handoff. Check llama.cpp#20570 Mamba assert before any run.
3. **Step-3.7-Flash** (P2) — own entry; Apache-2.0 196B/11B-active VLM, GGUF + llama.cpp confirmed; eval-only candidate vs coder_escalation (must beat Qwen3.6-35B-A3B Q8 at acceptable CPU t/s).
4. **Mellum2-12B-A2.5B** (P3) — own entry, low priority; Apache-2.0, official GGUF, cheap FIM/completion tier; NOT a drafter (vocab 98 304 ≠ targets).
5. **Audio batch** (P3) — single multimodal-pipeline TTS/ASR shortlist refresh covering dots.tts + Nemotron-3.5 ASR (+ Higgs Audio v3); no individual entries unless the audio line is prioritized.

> Per CLAUDE.md governance: do **not** create these intake entries / handoff stubs without explicit user approval. This doc returns the snippets; the user authorizes the index edits.

## Cross-refs

- **intake-694** (this roundup) — `research/intake_index.yaml`.
- **Coder roles** — `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml` (coder_escalation = Qwen3.6-35B-A3B Q8; worker_coder = Qwen3-Coder-30B-A3B).
- **Doc pipeline** — `handoffs/active/opendataloader-pipeline-integration.md` (LightOnOCR slow-path; PaddleOCR HTTP-backend already referenced — distinguish from PaddleOCR-VL-1.6 VLM).
- **SSM-hybrid readiness** — `handoffs/active/log-linear-gated-deltanet-readiness.md`, `handoffs/active/multiscreen-attention-evaluation.md`; prior Nemotron line: intake-481, Nemotron-Cascade-2 / Nemotron-3-Nano entries.
- **LFM2.5** — intake ~31504; `research/deep-dives/lfm2-lfm25-family-deep-dive.md`.
- **Gemma 4** — intake-256/257; `research/deep-dives/gemma4-mtp-drafter-deep-dive.md`; deployed worker_general = gemma4-26B-A4B MTP.
- **Multimodal/TTS/ASR** — `handoffs/active/multimodal-pipeline.md`.
- **llama.cpp Mamba assert** — ggml-org/llama.cpp#20570 (Nemotron-3-Nano `mamba-base.cpp:173 GGML_ASSERT`).
