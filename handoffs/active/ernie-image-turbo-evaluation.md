# ERNIE-Image-Turbo Evaluation

**Status**: production (sd-server backend, Q8 + conv-direct; ~3 min/image @ 1024² 8-step CPU)
**Created**: 2026-05-06 (via research intake)
**Updated**: 2026-05-07 (ComfyUI → sd-server swap, 2.54× speedup; distilled-model penalty verified)
**Priority**: MEDIUM — operational. Remaining latency (~3 min @ 1024²) acceptable for non-interactive use; Spark/GPU is the next big lever (~10-20× free).
**Categories**: multimodal, quantization, local_inference

## Objective

Evaluate Baidu's ERNIE-Image-Turbo (8B distilled DiT, Apache 2.0) as a self-hosted text-to-image generation tool to replace the cloud `image_generate (FAL)` adapter currently disabled in `hermes-outer-shell.md`. The model's distinctive niche is **bilingual (EN+ZH) long-form in-image text rendering** — LongTextBench 0.9655 vs FLUX.1-dev 0.306 — relevant for poster / infographic / multi-panel comic outputs that the orchestrator's tool surface might want.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|---|---|---|---|
| intake-528 | unsloth/ERNIE-Image-Turbo-GGUF (8B DiT distilled, Apache 2.0) | medium | worth_investigating → promote to new_opportunity once GPU lands |

Deep dive: [`research/deep-dives/ernie-image-turbo-dit-text-to-image.md`](../../research/deep-dives/ernie-image-turbo-dit-text-to-image.md) — full architecture, distillation method (DMD + undocumented RL polish), benchmark positioning (GENEval saturated, LongTextBench load-bearing), GGUF tooling semantics, perf expectations on Spark vs CPU, alternatives shortlist, and the variant-selection rationale.

## Status of Prep

| Step | State | Notes |
|---|---|---|
| Deep dive written | ✅ done | 2026-05-06 — `research/deep-dives/ernie-image-turbo-dit-text-to-image.md` |
| Q8_0 downloaded | ✅ done | At `/mnt/raid0/llm/models/diffusion/ernie-image-turbo-gguf/ernie-image-turbo-Q8_0.gguf` (8.1 GB). BF16 deferred per deep-dive §9. |
| ComfyUI-GGUF arch support verified | ✅ done | GGUF declares `general.architecture=wan` which IS in upstream city96 supported list. Loaded as `ErnieImage` model class via ComfyUI's diffusion-models registry. **Gate cleared 2026-05-06.** |
| Prompt enhancer + text encoder + VAE downloaded | ✅ done | At `/mnt/raid0/llm/models/diffusion/ernie-image-turbo-comfy/` — `text_encoders/ministral-3-3b.safetensors`, `text_encoders/ernie-image-prompt-enhancer.safetensors`, `vae/flux2-vae.safetensors` (from `Comfy-Org/ERNIE-Image`). |
| ComfyUI installed + custom node wired | ✅ done | At `/mnt/raid0/llm/comfyui-ernie-test/ComfyUI/` with `.venv` + `ComfyUI-GGUF` custom node. Models symlinked into `models/{diffusion_models,text_encoders,vae}/`. |
| ComfyUI as stack-managed service | ✅ done | `start_comfyui()` + `start_whisper()` in `orchestrator_stack.py` (port 8188 + port 9000). Launcher `scripts/diffusion/start_comfyui_server.sh` (numactl --interleave=all). Whisper promoted from sidecar in same change. |
| Client + generator code | ✅ done | `src/services/comfyui_client.py`, `src/services/image_generator.py`, `src/models/image.py`. End-to-end smoke test 2026-05-06: 512² @ 4 steps in 65 s; 1024² @ 8 steps in 478 s. |
| Frontdoor + dispatcher wired | ✅ done | `task_type=image` added to `src/dspy_signatures/frontdoor.py`; `image_worker` virtual role + variants added to `src/orchestration/dispatcher.py:ROLE_MAPPING`. |
| Model registries updated | ✅ done | Added `comfyui` + `image_worker` entries; promoted `voice_server` (Whisper) to `managed_by: orchestrator_stack`. Both lean (epyc-orchestrator) and comprehensive (epyc-inference-research) registries updated. |
| Hermes plugin replacing FAL | ✅ done | `/workspace/scripts/hermes/plugins/local-image-generate/` (symlinked to `~/.hermes/plugins/`). Registers `image_generate` with same name as FAL implementation; Hermes' tools.registry uses dict assignment so plugin wins. |
| Hermes Python env installed | ✅ done | `uv sync --frozen` at `/mnt/raid0/llm/hermes-agent/` provisioned `.venv` with all 100+ deps including the previously-missing `firecrawl-py>=4.16.0`. Hermes tool registry now loads cleanly (52 tools registered). |
| End-to-end through real Hermes registry | ✅ done | Verified 2026-05-06: `discover_plugins()` auto-discovers our plugin, `image_generate` handler resolves to `hermes_plugins.local_image_generate._handle_image_generate` (NOT FAL), invocation produces a saved PNG end-to-end. Test artifact at `/mnt/raid0/llm/output/images/2026-05-06/d7da4364-7781-4ca7-9906-b91f92232920.png`. |
| **Backend swapped: ComfyUI → sd-server (stable-diffusion.cpp native ggml)** | ✅ done 2026-05-07 | Discovered upstream sd.cpp already ships full ERNIE-Image-Turbo support (`src/ernie_image.hpp`, 441 lines). Built sd-server, replaced ComfyUI in stack. Measured **2.54× wall-clock speedup** at production scale (~188 s vs 478 s @ 1024² 8 steps extrapolated). `--vae-conv-direct` was the high-ROI flag (7.1× on VAE alone). Hermes plugin chain unchanged — `ImageGenerator` interface preserved, internals swapped to `SDServerClient`. Old ComfyUI infra retained for rollback at `/mnt/raid0/llm/comfyui-ernie-test/`. |
| Distilled-model quantization-penalty hypothesis verified | ✅ done 2026-05-07 | Q4_K_M A/B at 832×1248 8 steps, same prompt + seed. **Penalty real**: 17% wall-clock win comes with visible Korean-text-rendering corruption on the model's signature differentiator. Q8 stays as production point. Q4 file deleted post-test. Deep-dive §4.4 hypothesis empirically confirmed. |
| GPU host available | ❌ blocked | DGX Spark GB10 not yet acquired — see `gpu-acceleration-path.md`. CPU is functional at ~3 min/image at 1024² post-swap (down from ~8 min on ComfyUI baseline). |

## Open Questions

1. **Loader compatibility (blocking).** Does the current city96 ComfyUI-GGUF release actually load `unsloth/ERNIE-Image-Turbo-GGUF` files, or does Unsloth ship a fork? If a fork — pinned commit, upstream-PR status, maintenance signal? Resolve before treating the download as usable.
2. **Distilled-model quantization penalty (deferred-until-needed).** Z-Image-Turbo data (SECourses A/B, deep dive §4.3) suggests Q8 is BF16-equivalent on distilled DiTs in this class, so the test isn't a Day-1 priority. Do this only if production Q8 outputs look subtly off vs the model-card samples — at that point pull BF16 and run a 30-prompt seeded A/B (EN+ZH mix, posters / portraits / scenes / dense-text) before considering UD-Q4_K_M as a fallback.
3. **Prompt-enhancer policy.** Model card shows w/ PE *raises* LongTextBench (0.9655 vs 0.9639) but *lowers* GENEval (0.8510 vs 0.8667). Per-scene toggle needed: on for poster/infographic prompts, off for compositional. Define a heuristic for the Hermes adapter.
4. **Content-filter audit.** Baidu's prior model ERNIE-ViLG had heavy political-content censorship. Run a probe set covering political topics, copyrighted characters, NSFW boundaries, and bilingual edge cases — note what is silently filtered or transformed before treating as a general-purpose tool.
5. **LongTextBench self-reported score validation.** ERNIE-Turbo's 0.9655 is on Baidu's own scorecard, not re-validated by the X-Omni team. Re-run on a held-out subset (or a curated 20-prompt local set covering EN/ZH typography stress cases) before trusting Baidu's leadership claim.
6. **Spark performance reality check.** Deep dive §5.1 extrapolates 6–12 s/image at BF16, 3–5 s at NVFP4 from FLUX-schnell numbers. Re-bench on actual hardware once Spark lands; the 8-step distilled DiT has no published Spark numbers.
7. **Alternative re-evaluation.** If LongTextBench-ZH is not actually needed by the product, FLUX.1-schnell (12B, 4-step, Apache 2.0, mature ecosystem) is the simpler default. Re-litigate the choice against actual product requirements before committing.
8. **Hermes integration shape.** ComfyUI exposes a `/prompt` REST API. Sketch the adapter: `image_generate(prompt, n_images=1, size="1024x1024", style=None, lang=None)` → POST workflow JSON → poll `/history` → return image bytes. Authentication, error handling, queue management on the Hermes side.

## Notes

- **Variant decision**: download **Q8_0 (8.69 GB) only**, skip BF16 and UD- variants for now. Reasoning lives in deep dive §9 — short version: Q8 is the production runtime, and the case for BF16 as a calibration reference was over-engineered against evidence (SECourses' Z-Image-Turbo A/B already shows Q8 ≡ BF16 in quality on a comparable distilled DiT). HF doesn't expire — pull BF16 later only if Q8 wobbles on actual ERNIE-Turbo prompts.
- **Backend is NOT llama.cpp** — out-of-band from EPYC's inference stack. Runs through diffusers (`ErnieImagePipeline`), SGLang, or ComfyUI-GGUF. Plan to use ComfyUI-GGUF as the primary backend (smallest VRAM footprint, native to the Unsloth release).
- **CPU smoke-test**: technically possible at 30–120 s/image (deep dive §5.2) via diffusers on CPU but not interactive. Useful only to validate the model loads and produces outputs; not a deployment path. **Not** worth deploying via stable-diffusion.cpp port unless we want to do non-trivial llama.cpp engineering for a tool that's better served on GPU.
- **`feedback_dont_dismiss_creative_uses` memory** is what prevented this from being marked `not_applicable` at intake — the legitimate reframing is "self-hosted T2I to replace disabled FAL cloud tool, gated on GPU." Promote intake-528 verdict to `new_opportunity` once GPU acquisition is on the immediate roadmap.

## Files

- Deep dive: `research/deep-dives/ernie-image-turbo-dit-text-to-image.md`
- Intake: `research/intake_index.yaml` → `intake-528`
- Upstream model: https://huggingface.co/unsloth/ERNIE-Image-Turbo-GGUF
- Upstream Baidu model: https://huggingface.co/baidu/ERNIE-Image-Turbo
- Eventual download target: `/mnt/raid0/llm/models/diffusion/ernie-image-turbo-gguf/`

## Reporting Instructions

After any work in this handoff:
1. Update the **Status of Prep** table.
2. If the loader-compatibility verification (Q1) resolves, document the result here and unblock downstream work.
3. If Q8-vs-BF16 A/B is run, append the result to the deep dive (§4.4 and §9) and update the variant recommendation if needed.
4. When this handoff transitions from `stub` to `active` (image-generation enters scope OR GPU lands), promote intake-528 to `new_opportunity`.
5. If superseded by an alternative (FLUX.1-schnell, Qwen-Image 2.0), move to `handoffs/completed/` with a one-paragraph closing note explaining the choice.
