# Deep Dive: ERNIE-Image-Turbo (Baidu, 8B distilled DiT text-to-image)

**Intake ID**: intake-528
**Date**: 2026-05-06
**Status**: Pre-deployment assessment — model not yet downloaded
**Trigger**: User asked whether image generation should join the toolkit; Q8 vs BF16 decision pending

---

## Executive Summary

ERNIE-Image-Turbo is Baidu's open-weight (Apache 2.0, unmodified) **single-stream Diffusion Transformer text-to-image model**, ~8B DiT parameters distilled from a 50-step base via DMD + an undocumented RL polish pass to run in **8 inference steps**. Unsloth has published GGUF quantizations spanning Q2_K (3.18 GB) through BF16 (16.1 GB) using ComfyUI-GGUF (city96) tooling.

**Why it merits a closer look despite being far from EPYC's CPU-LLM core:**

1. **Real differentiator is bilingual long-form in-image text rendering.** LongTextBench (X-Omni team, [arXiv:2507.22058](https://arxiv.org/abs/2507.22058)) places ERNIE-Image-Turbo at **0.9655 avg (w/ PE)** — second only to closed-source Seedream 4.5 (0.9882) and decisively above FLUX.2 (0.5413), FLUX.1-dev (0.306), HiDream-I1 (0.284), Kolors (0.294). FLUX collapses to ~0 on Chinese text. ERNIE is the only OSS model with a credible claim to dense English+Chinese in-image text — posters, infographics, multi-panel comics.
2. **Apache 2.0 with no RAIL clauses.** Aligns with the repo's open-source-only constraint; could replace the cloud `image_generate (FAL)` tool currently disabled in `hermes-outer-shell.md`.
3. **GENEval 0.8667 is competitive but the benchmark is saturated** — [GenEval-2 (arXiv:2512.16853)](https://arxiv.org/abs/2512.16853) shows top-4 models drift up to 17.7% from human judgment on the original GENEval. Treat 0.86+ scores as "frontier-tier" not "wins."

**Why it is not actionable today:**

- **Diffusers / ComfyUI-GGUF backend, not llama.cpp.** Out-of-band from EPYC's inference stack.
- **Host has no GPU.** EPYC 9655 96-core CPU realistic expectation: 30–120 s/image, batch-only, not interactive (extrapolated from stable-diffusion.cpp on Sapphire Rapids; no ERNIE-on-CPU benchmarks exist).
- **DGX Spark GB10 is the natural home** but is not yet acquired (per memory `project_dgx_spark_target`). On Spark realistic expectation is 6–12 s/image at BF16, 3–5 s at NVFP4 if a quant lands.

The honest assessment is "interesting-and-prep-worthy, not deploy-now." This deep dive exists so that when the GPU lands or image generation enters product scope, we have prior art.

---

## 1. Architecture

ERNIE-Image follows a **single-stream DiT** in the [Peebles & Xie](https://arxiv.org/abs/2212.09748) lineage: text and noise tokens travel through one shared transformer trunk with cross-attention to text features. This contrasts with the **dual-stream MM-DiT** in SD3/FLUX, which gives text and image streams separate parameters and only periodically joins them via joint attention. The declared module class is `ErnieImageTransformer2DModel`.

| Field | Value |
|---|---|
| Layers | 36 |
| Hidden dim | 4,096 |
| FFN hidden | 12,288 (FFN ratio 3.0 — low side for modern DiTs) |
| Attention heads | 32 |
| In/out channels | 128 each |
| DiT params | ~8B |

The **8B figure is DiT-only.** The full pipeline includes:

- **Text encoder**: `Mistral3Model` config, 3,072 hidden, ~3B params. Bilingual via the Mistral3 tokenizer and Baidu-curated training. The `config.json` carries an unused Pixtral-style `vision_config` (14 patch size); image conditioning is not exposed in `ErnieImagePipeline`.
- **Prompt enhancer**: separate `Ministral3ForCausalLM`, 3,072 hidden, 26 layers, 131K vocab — a small distilled rewriter that turns short user prompts into structured longform descriptions. Text-only despite the VLM-style API hint.
- **VAE**: non-standard **128-channel latent** (vs the now-common 16-channel SD3/FLUX arrangement). Specifics undocumented. **This has portability implications** if anyone tries to port outside `diffusers` — the latent encode/decode is non-trivial to re-implement.
- Diffusion objective (epsilon, v, or rectified-flow): **undisclosed**.

The 24 GB-VRAM target in the model card therefore covers DiT + Mistral3 encoder + Ministral3 enhancer + VAE + activations — not just the DiT. Comfortable headroom requires 32 GB; tight on 24 GB without quantization.

## 2. DMD + RL Distillation

**DMD** = [Distribution Matching Distillation](https://arxiv.org/abs/2311.18828) (Yin, Gharbi, Park, Zhang, Shechtman, Durand, Freeman; MIT + Adobe; CVPR 2024). Mechanism: a few-step student generator is trained so that the gradient of an *approximate KL divergence* between the student-induced distribution and the teacher diffusion's distribution can be expressed as the **difference of two score functions** — one for the real/teacher distribution, one for the synthetic/student distribution. Each score is parameterized as a small auxiliary diffusion model trained alongside the student. Critically, DMD has **no real-image regression target** — the student is never asked to reproduce specific samples, only to match the teacher's distribution at the score level. This is what preserves diversity at 1–8 steps.

[DMD2](https://arxiv.org/abs/2405.14867) (NeurIPS 2024 Oral) drops the regression term and adds a GAN loss; given timing, DMD2 is the more likely actual basis for ERNIE-Image-Turbo even though Baidu just says "DMD."

**The "RL" half is undocumented.** Both the [HF model card](https://huggingface.co/baidu/ERNIE-Image-Turbo) and the [GitHub README](https://github.com/baidu/ernie-image) only say "*optimized by DMD and RL, achieves faster speed and higher aesthetics in only 8 inference steps*." No paper, no reward model, no algorithm, no reward signal source. The third-party deep-dive at [ernie-image.github.io](https://ernie-image.github.io/) is explicit: *"the reward model, the reward signal, and the RL algorithm are not documented."* Reasonable prior given the "higher aesthetics" framing and 2025-era practice: a reward-weighted SFT or DPO-style polish over an aesthetic / human-preference reward model, applied after DMD distillation. **Treat anything beyond that as speculation.** This is a reproducibility gap worth noting.

## 3. Benchmark Positioning

### 3.1 GENEval

GENEval ([Ghosh et al., NeurIPS 2023, arXiv:2310.11513](https://arxiv.org/abs/2310.11513)) is an **automated, object-detection-based** framework — not human eval. Six axes (single object, two object, counting, colors, position, attribute binding). Detection uses Mask2Former trained on MS COCO at confidence threshold 0.3; color and attribute checks chain in CLIP/discriminative classifiers. At publication GENEval had 83 % agreement with human annotators (vs 88 % inter-annotator).

| Model | GENEval Overall |
|---|---|
| PixArt-α | 0.48 |
| SDXL 1.0 | 0.55 |
| FLUX.1-dev | 0.66 |
| DALL-E 3 | 0.67 |
| CogView4-6B | 0.73 |
| SD3-Medium | 0.74 |
| Janus-Pro-7B | 0.80 |
| HiDream-I1 | 0.83 |
| FLUX.2-klein-9B | 0.8481 |
| **ERNIE-Image-Turbo (no PE)** | **0.8667** |
| Qwen-Image | 0.8683 |
| Qwen-Image 2.0 | 0.91 |
| ERNIE-Image (SFT, 50 steps) | 0.8856 |

Sources: [HiDream-I1 paper Table 2](https://arxiv.org/html/2505.22705v1), [Janus-Pro paper](https://arxiv.org/html/2501.17811v1), [ERNIE-Image card](https://huggingface.co/baidu/ERNIE-Image-Turbo), [Qubrid Qwen-Image-2.0 writeup](https://www.qubrid.com/blog/qwen-image-2-0-qwen-image-edit-2-0-explained-architecture-benchmarks-api-on-qubrid-ai).

**Critical caveat — benchmark drift.** [GenEval-2 (arXiv:2512.16853, Dec 2025)](https://arxiv.org/abs/2512.16853) shows GENEval has drifted up to 17.7 % from human judgment for current frontier models. It systematically over-rewards compositional matching while ignoring aesthetics and prompt-following nuance. Models trained with prompt-rewriters (which describes ERNIE-Image-Turbo with its prompt enhancer) game GENEval. **ERNIE-Turbo's 0.8667 is "competitive frontier-tier on a saturated benchmark," not "beats FLUX/Qwen by a wide margin."**

### 3.2 LongTextBench (the load-bearing benchmark)

LongTextBench was introduced by the X-Omni team ([arXiv:2507.22058](https://arxiv.org/abs/2507.22058), Jul 2025) and is publicly released at [HuggingFace X-Omni/LongText-Bench](https://huggingface.co/datasets/X-Omni/LongText-Bench). 160 prompts (80 EN + 80 ZH) across 8 text-rich scenarios (signboards, labels, printed materials, web pages, slides, posters, captions, dialogues), short and long variants. Evaluation is **VLM-based** (not OCR), 4 samples per prompt.

X-Omni paper leaderboard:

| Model | LongTextBench Avg |
|---|---|
| Seedream 4.5 (closed source) | 0.9882 |
| ERNIE-Image (50 steps, w/ PE) | 0.9733 |
| **ERNIE-Image-Turbo (8 steps, w/ PE)** | **0.9655** |
| Qwen-Image | 0.9445 |
| Seedream 3.0 | 0.887 |
| X-Omni | 0.857 |
| GPT-4o | 0.788 |
| FLUX.2-klein | 0.5413 |
| FLUX.1-dev | 0.306 (ZH ≈ 0.005) |
| HiDream-I1-Full | 0.284 |
| Kolors | 0.294 |

**Qualifier:** ERNIE-Turbo's 0.9655 is **self-reported on the model card**, not re-validated by the X-Omni team. Treat as Baidu-claimed-leadership pending independent re-run.

### 3.3 Counter-intuitive prompt-enhancer effect

The model card itself shows the prompt enhancer **lowers** GENEval Overall (0.8510 w/ PE vs 0.8667 w/o PE) for Turbo, while it **raises** LongTextBench (0.9655 w/ PE vs 0.9639 w/o PE). The enhancer trades attribute binding for counting/position. **Practical implication: this is not "always on" — it's a per-scene setting**, with PE on for production poster/infographic use and off for compositional benchmarks.

## 4. Quantization Quality on DiT

### 4.1 ComfyUI-GGUF (city96) loader semantics

Reading the loader source ([city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF), [DeepWiki](https://deepwiki.com/city96/ComfyUI-GGUF/5.1-gguf-loaders)): **weights stay quantized in VRAM**. Tensors are wrapped in a `GGMLTensor` (subclass of `torch.Tensor`) holding the packed bytes plus `tensor_type` metadata. A custom ops layer (`GGMLOps`) overrides `Linear`, `Conv2d`, `Embedding`, `LayerNorm`, `GroupNorm`. At forward time, `GGMLLayer.get_weight()` calls `dequantize_tensor()` to materialize a BF16/F16 view **just-in-time per layer**, runs the matmul/conv in BF16, and frees the temporary. **There is no INT8 GEMM kernel** — the dequant target is always BF16/F16.

Consequences:

- **VRAM footprint ≈ file size** (Q8 ERNIE-Turbo ≈ 8.7 GB resident DiT weights, plus encoder, VAE, activations on top).
- **Speed is flat-to-slightly-worse than native BF16** on consumer GDDR. Community measurement: Q5_K_M FLUX.1-dev at 53 s/image vs FP16 48 s/image on RTX 4090 ([zanno.se](https://zanno.se/quantization-and-quality-degradation/)). GGUF saves VRAM, not time, on GDDR-class GPUs.
- **On a 128 GB unified-memory Spark (LPDDR5x ~273 GB/s) the value prop inverts** — lower-precision quants benefit *more* from bandwidth savings because the dequant overhead is a smaller fraction of a slower BW budget. Q8 vs BF16 has a roofline ~1.8× ceiling speedup on Spark vs ~1.0× on a 4090.

**Architecture support gap.** The upstream city96 [supported-architectures list](https://deepwiki.com/city96/ComfyUI-GGUF/1.1-supported-models-and-architectures) covers FLUX, SD3, AuraFlow, HiDream, Cosmos, LTXV, HyVid, Wan, Lumina2, Qwen-Image. **ERNIE-Image is NOT in the upstream list** as of the May 2026 scan. Unsloth's GGUF release implies an out-of-tree patch or a recent commit. **This must be verified before download** — the loader is what determines whether the file is usable.

### 4.2 Unsloth Dynamic 2.0 on diffusion: marketing-tier evidence only

Unsloth's [Dynamic 2.0 documentation](https://docs.unsloth.ai/basics/unsloth-dynamic-2.0-ggufs) is **LLM-focused** — calibration corpus described in tokens, headline benchmark is Gemma-3 27B MMLU/KL-divergence. The doc never names DiT, UNet, attention-out, FFN-gate, or patchify layers. For their FLUX/ERNIE GGUF cards the model card simply restates "important layers are upcasted to higher precision" and links back to the LLM doc. **No DiT-specific A/B tests have been published by Unsloth or independently for UD- variants vs vanilla Q4_K_M / Q3_K_M.**

UD- variants cost 13–25 % more disk than vanilla peers (UD-Q4_K_M 5.78 vs Q4_K_M 5.02 GB; UD-Q3_K_M 4.8 vs Q3_K_M 3.91 GB). Treat the diffusion UD claim as **plausible-by-analogy but unverified.**

### 4.3 Empirical Q4 vs Q5 vs Q6 vs Q8 vs BF16 on DiT (community consensus)

Synthesis across [civitai writeups](https://civitai.com/models/711483/flux-dev-q5km-gguf-quantization-a-nice-balance-of-speed-and-quality-in-under-9-gigabytes), [city96 HF discussion #15](https://huggingface.co/city96/FLUX.1-dev-gguf/discussions/15), [SECourses comparison](https://huggingface.co/blog/MonsterMMORPG/bf16-vs-gguf-fp8-scaled-nvfp4-speed-quality-compar), [zanno.se](https://zanno.se/quantization-and-quality-degradation/):

| Quant | Quality vs BF16 | Notes |
|---|---|---|
| BF16 / FP16 | reference | |
| Q8_0 | visually indistinguishable | "Same quality tier" in seeded A/B on FLUX.1-dev / FLUX.2 / Z-Image-Turbo |
| Q6_K | ~95 % retention | minor softening |
| Q5_K_M | ~90 %, "best cost-benefit" | "barely noticeable" loss |
| Q4_K_M / Q4_K_S | first noticeable degradation | softening, fine-texture loss, hand/anatomy artifacts |
| Q3 | "rough but usable" | 75–85 % retention |
| Q2_K | "nobody should use this" | |

**No FID / CLIP / human-pref numbers exist for any DiT-GGUF comparison.** All reports above are seeded-prompt visual A/B with pixel-diff overlays.

### 4.4 Distilled-model penalty hypothesis (load-bearing for ERNIE-Turbo)

Multiple secondary sources ([Apatero FLUX guide](https://apatero.com/blog/flux-gguf-quantization-8gb-vram-guide-2026), [digitalcreativeai.net](https://www.digitalcreativeai.net/en/post/use-high-performance-gguf-comfyui-flux-1-schnell)) state that quantizing schnell-class distilled DiTs **compounds** distillation loss — *"GGUF for schnell is generally not recommended unless absolutely necessary"; a Q5 dev at 20 steps reportedly beats schnell-Q5 at 4 steps.* No controlled FID study. The mechanism is plausible: a 4–8-step schedule has tight per-step error budgets, and dequant rounding noise that 50-step samplers integrate over many denoise steps cannot be averaged out in 8.

**Practical translation for ERNIE-Image-Turbo (distilled, 8 steps): assume Q8 stays safe but the Q8→Q4_K_M cliff arrives sooner than on FLUX.1-dev.** The Unsloth UD-Q4_K_M variant would be the most plausible mitigation precisely here, but nobody has measured it on a DiT.

## 5. Performance Expectations

### 5.1 DGX Spark GB10 (target hardware, not yet acquired)

Spark spec: NVIDIA Blackwell, 128 GB unified LPDDR5x at ~273 GB/s, ~250 TFLOPs FP16, ~1 PFLOPs FP4. Published reference points:

- **FLUX.1-schnell at NVFP4: 2.6 s/image @ 1024² (~23 img/min)** — [NVIDIA Spark blog](https://developer.nvidia.com/blog/how-nvidia-dgx-sparks-performance-enables-intensive-ai-tasks/)
- **SDXL 1.0 BF16: 7 img/min ≈ 8.6 s/image @ 1024²** — same source
- **FLUX.1-dev BF16, 50 steps in ComfyUI: ~97 s/image** vs ~37 s on RTX 6000 Ada — [NVIDIA dev forums](https://forums.developer.nvidia.com/t/dgx-spark-performance/356716). Spark is ~2.6× slower than a workstation GPU on heavy diffusion.

Extrapolating to ERNIE-Turbo (8B params, 8 steps) from FLUX-schnell-at-NVFP4 (12B, 4 steps, 2.6 s):
- 8 steps vs 4 = 2× more compute
- 8B vs 12B = 0.67×
- BF16 vs NVFP4 = ~2–3× memory throughput penalty per [Avarok NVFP4 analysis](https://blog.avarok.net/we-unlocked-nvfp4-on-dgx-spark-and-its-20-faster-than-awq-72b0f3e58b83)

→ **Expect 6–12 s/image at BF16 on Spark, 3–5 s/image if NVFP4 lands.** Plus a 1–3 s first-call latency for the prompt enhancer.

### 5.2 Current EPYC 9655 host (CPU only)

Arithmetic floor: 8B × 2 (matmul) × 8 steps × ~1000 op-multiplier per token ≈ 128 TFLOP per image minimum, before attention quadratic costs. At sustained ~15–20 TFLOPS BF16 realistic CPU throughput (AVX-512 + VNNI, single-NUMA-node 96 threads, BW-bound), that's **6–9 s pure compute lower bound**. In practice, [stable-diffusion.cpp on Sapphire Rapids 32-core reports 30–90 s/image at SDXL scales](https://huggingface.co/blog/stable-diffusion-inference-intel) — DiT attention has different access patterns from LLM decode and may not scale to 96 threads.

**Realistic EPYC 9655 expectation: 30–120 s/image, BW-bound and thread-scaling-limited.** Feasible for batch / overnight, **not interactive**. Do not plan on CPU as anything beyond a smoke-test path.

## 6. Self-Hosted Alternatives Shortlist

| Model | Params | Steps | RTX 4090 sec/img | Strengths | Weaknesses |
|---|---|---|---|---|---|
| FLUX.1-schnell | 12B | 4 | 2–5 | Best ecosystem, many LoRAs, Apache-2.0 | Weak EN-long-text, ZH ≈ 0 |
| FLUX.1-dev | 12B | 28–50 | 15–30 | Best aesthetics in OSS | Slow, non-commercial license |
| SD3.5-Medium | 2.5B | 28 | 3–6 | Lightest VRAM | Poor anatomy, weak prompt adherence |
| Qwen-Image 2.0 | 7B | 20 | 6–10 | GENEval 0.91, top open-weight composition | Slower than schnell |
| HiDream-I1-Full | 17B | 28 | 20–25 | Best anatomy in OSS | Needs FP8 to fit 24 GB; LongTextBench 0.28 |
| Sana 1.5 | 1.6B | 20 | 1–2 | Tiny, fast | Lower fidelity, weak text |
| **ERNIE-Image-Turbo** | **8B + 3B PE** | **8** | **est. 3–6** | **Top LongTextBench EN+ZH, comp. GENEval, Apache-2.0** | **Recent, ComfyUI-buggy, possible CN content filter** |

**ERNIE-Turbo's distinctive niche is bilingual long in-image text rendering** — only OSS model claiming > 0.96 LongTextBench-ZH. If we don't need Chinese text or dense paragraph rendering, FLUX.1-schnell is the safer default. If we want the strongest pure compositional score, Qwen-Image 2.0.

## 7. Known Issues & Risks

- **ComfyUI integration is documented-buggy as of Apr 2026**:
  - [workflow_templates#802](https://github.com/Comfy-Org/workflow_templates/issues/802) — model filename mismatch (`ernie-image.safetensors` vs `ernie-image-turbo.safetensors`); even unchecking `prompt_enhancement` still routes through the LLM, wasting time.
  - [ComfyUI#13417](https://github.com/Comfy-Org/ComfyUI/issues/13417) — image inputs ignored by prompt-enhancement node.
  - [Unsloth GGUF discussion #2](https://huggingface.co/unsloth/ERNIE-Image-Turbo-GGUF/discussions/2) — `AttributeError: 'Ministral3_3B' object has no attribute 'generate'` when text-generation node fires.
- **ERNIE arch support in upstream city96 ComfyUI-GGUF is unverified** (see §4.1). Unsloth implies compatibility; verify before relying on it.
- **"RL" half of the distillation is undocumented** by Baidu (see §2). Reproducibility gap; flagged for any future fine-tuning attempts.
- **Possible baked-in content filtering** — Baidu's prior model ERNIE-ViLG had heavy political-content censorship ([MIT TR, 2022](https://www.technologyreview.com/2022/09/14/1059481/baidu-chinese-image-ai-tiananmen/)). No empirical NSFW/political-filter testing on ERNIE-Image-Turbo surfaced; assume similar baked-in filters until verified.
- **Self-reported leadership numbers** — ERNIE-Turbo's LongTextBench 0.9655 is on Baidu's own scorecard, not re-validated by the X-Omni team that owns the benchmark. Plan to re-run on a held-out subset before treating Baidu's claims as deployment-grade.
- **Counter-intuitive prompt-enhancer effect** — w/ PE *lowers* GENEval (0.8510 vs 0.8667 w/o PE) for Turbo; treat as per-scene setting.
- **Distilled-model quantization penalty** is community folklore not measured (see §4.4); plan to A/B Q8 vs BF16 on real prompts before committing to Q8 as the production path.

## 8. License

Apache 2.0 unmodified, `Copyright 2025 Baidu, Inc.` Per project policy, licenses are not blockers — recorded for completeness.

## 9. Variant-Selection Recommendation

**Download Q8_0 (8.69 GB) only.** Skip BF16 and UD- variants for now.

Rationale:

- **Q8 is the production runtime.** Community-confirmed BF16-equivalent quality on FLUX.1-dev / FLUX.2 / **Z-Image-Turbo** (a distilled DiT in the same class as ERNIE-Image-Turbo). On Spark's LPDDR5x bandwidth budget Q8 has a ~1.8× roofline ceiling speedup vs BF16 because the per-layer dequant tax is a smaller fraction of a slower BW budget.
- **The case for BF16 was overstated.** Earlier draft argued BF16 was needed as a calibration reference for the "distilled few-step DiTs amplify quantization degradation" hypothesis (§4.4). Closer reading of the cited evidence: the strongest "distilled penalty" claim is about FLUX.1-**schnell** at 4 steps (more aggressive step compression than ERNIE's 8 steps), and SECourses' image-slider A/B explicitly clusters BF16 / Q8 / FP8-Scaled in **one quality tier on Z-Image-Turbo** — direct counter-evidence on a comparable distilled DiT. The hypothesis is partially falsified for the regime ERNIE-Turbo lives in.
- **BF16 is a future option, not a now option.** HF doesn't expire. If Q8 wobbles in actual testing on ERNIE-Turbo specifically (model-specific behavior the SECourses A/B doesn't cover), pull BF16 then. Pre-paying 16 GB and ~20 minutes of bandwidth for a hypothesis the most-analogous evidence pushes against is over-engineering.
- **Storage is not a constraint** (8.7 GB on 430 GB free SSD), but neither is it a license to grab everything by default.
- **UD-Q4_K_M (5.78 GB) becomes attractive only if** (a) we measure a visible Q8-vs-BF16 gap on Turbo's 8-step schedule, **and** (b) Spark VRAM pressure materializes from a co-resident workload. Absent both, vanilla Q8 dominates and UD's unverified-on-DiT claim isn't worth the 13 % size premium over Q4_K_M (and the size advantage over Q8 only matters under co-residency pressure that doesn't exist today).

**Decision history kept here intentionally** — initial draft of this deep dive recommended Q8 + BF16; user pushback ("do we really need BF16 if community confirms Q8 is virtually as good?") prompted re-reading of §4.3 and §4.4 and the revision above. Recording so future-me does not re-add BF16 without first checking whether the conditions actually changed.

---

## Sources

### Architecture & training
- [baidu/ERNIE-Image-Turbo on Hugging Face](https://huggingface.co/baidu/ERNIE-Image-Turbo)
- [ERNIE-Image technical deep-dive (ernie-image.github.io)](https://ernie-image.github.io/)
- [baidu/ernie-image GitHub](https://github.com/baidu/ernie-image)
- [DiT (Peebles & Xie), arXiv:2212.09748](https://arxiv.org/abs/2212.09748)
- [DMD (Yin et al.), arXiv:2311.18828](https://arxiv.org/abs/2311.18828)
- [DMD2 (Yin et al.), arXiv:2405.14867](https://arxiv.org/abs/2405.14867)

### Benchmarks
- [GENEval paper (Ghosh et al.), arXiv:2310.11513](https://arxiv.org/abs/2310.11513)
- [GenEval-2 (benchmark drift), arXiv:2512.16853](https://arxiv.org/abs/2512.16853)
- [HiDream-I1 paper, arXiv:2505.22705](https://arxiv.org/html/2505.22705v1)
- [Janus-Pro paper, arXiv:2501.17811](https://arxiv.org/html/2501.17811v1)
- [X-Omni / LongTextBench, arXiv:2507.22058](https://arxiv.org/abs/2507.22058)
- [LongText-Bench dataset](https://huggingface.co/datasets/X-Omni/LongText-Bench)
- [Qubrid Qwen-Image 2.0 writeup](https://www.qubrid.com/blog/qwen-image-2-0-qwen-image-edit-2-0-explained-architecture-benchmarks-api-on-qubrid-ai)
- [Artificial Analysis T2I leaderboard](https://artificialanalysis.ai/image/leaderboard/text-to-image)

### Quantization tooling
- [Unsloth Dynamic 2.0 docs](https://docs.unsloth.ai/basics/unsloth-dynamic-2.0-ggufs)
- [unsloth/ERNIE-Image-Turbo-GGUF model card](https://huggingface.co/unsloth/ERNIE-Image-Turbo-GGUF)
- [unsloth/FLUX.2-dev-GGUF model card](https://huggingface.co/unsloth/FLUX.2-dev-GGUF)
- [city96/ComfyUI-GGUF GitHub](https://github.com/city96/ComfyUI-GGUF)
- [DeepWiki: ComfyUI-GGUF loaders](https://deepwiki.com/city96/ComfyUI-GGUF/5.1-gguf-loaders)
- [DeepWiki: supported architectures](https://deepwiki.com/city96/ComfyUI-GGUF/1.1-supported-models-and-architectures)
- [city96/FLUX.1-dev-gguf discussion #15 (all-K-quants A/B)](https://huggingface.co/city96/FLUX.1-dev-gguf/discussions/15)
- [zanno.se: quantization & quality degradation](https://zanno.se/quantization-and-quality-degradation/)
- [SECourses BF16 vs GGUF vs FP8 vs NVFP4](https://huggingface.co/blog/MonsterMMORPG/bf16-vs-gguf-fp8-scaled-nvfp4-speed-quality-compar)
- [Apatero FLUX GGUF guide](https://apatero.com/blog/flux-gguf-quantization-8gb-vram-guide-2026)
- [digitalcreativeai.net schnell GGUF guide](https://www.digitalcreativeai.net/en/post/use-high-performance-gguf-comfyui-flux-1-schnell)

### Performance & hardware
- [NVIDIA DGX Spark performance blog](https://developer.nvidia.com/blog/how-nvidia-dgx-sparks-performance-enables-intensive-ai-tasks/)
- [NVIDIA DGX Spark dev forums](https://forums.developer.nvidia.com/t/dgx-spark-performance/356716)
- [Avarok NVFP4 unlock on Spark](https://blog.avarok.net/we-unlocked-nvfp4-on-dgx-spark-and-its-20-faster-than-awq-72b0f3e58b83)
- [LMSYS DGX Spark review](https://www.lmsys.org/blog/2025-10-13-nvidia-dgx-spark/)
- [Salad FLUX.1-schnell benchmark](https://blog.salad.com/flux1-schnell/)
- [HF blog: Stable Diffusion on Intel CPUs](https://huggingface.co/blog/stable-diffusion-inference-intel)

### Issues / community
- [ComfyUI workflow_templates#802](https://github.com/Comfy-Org/workflow_templates/issues/802)
- [ComfyUI#13417](https://github.com/Comfy-Org/ComfyUI/issues/13417)
- [Unsloth GGUF discussion #2](https://huggingface.co/unsloth/ERNIE-Image-Turbo-GGUF/discussions/2)
- [MIT TR — Baidu image-AI political censorship (2022)](https://www.technologyreview.com/2022/09/14/1059481/baidu-chinese-image-ai-tiananmen/)
- [Diffusion Doodles model rundown](https://medium.com/diffusion-doodles/model-rundown-z-image-turbo-qwen-image-2512-edit-2511-flux-2-dev-fc787f5e87ad)

---

## Cross-references

- [`research/intake_index.yaml`](../intake_index.yaml) — intake-528
- [`handoffs/active/ernie-image-turbo-evaluation.md`](../../handoffs/active/ernie-image-turbo-evaluation.md) — testing handoff (created alongside this deep dive)
- [`handoffs/active/multimodal-pipeline.md`](../../handoffs/active/multimodal-pipeline.md) — image generation is currently out of scope but this is the natural future home
- [`handoffs/active/hermes-outer-shell.md`](../../handoffs/active/hermes-outer-shell.md) — `image_generate (FAL)` cloud tool currently disabled; ERNIE-Image-Turbo is a self-hosted replacement candidate
- [`handoffs/active/gpu-acceleration-path.md`](../../handoffs/active/gpu-acceleration-path.md) — DGX Spark acquisition is the gating event for this entry becoming actionable
