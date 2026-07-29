# ERNIE-Image-Turbo Evaluation

**Status**: REFRESHED 2026-05-28 — production via sd-server Q8 + conv-direct; active only for operational QA and GPU/Spark rebench
**Created**: 2026-05-06 (via research intake)
**Updated**: 2026-05-28 (executor-facing remaining-work gate clarified)
**Priority**: MEDIUM — operational. Remaining latency (~3 min @ 1024²) acceptable for non-interactive use; **the GPU rebench lever (~10-20× est) is now UNBLOCKED — the MI210 (gfx90a, 64 GB) landed 2026-07-02** (the "Spark/GPU next big lever" gate fired). Runnable: build sd-server/ComfyUI on the ROCm/HIP path and rebench the 8-step distilled DiT on the MI210 (operator-approved; no published gfx90a numbers exist, so this is a measure-not-extrapolate task). Sequence behind the frontdoor-residency GPU program (findings-02) — image-gen is a latency-tolerant tenant, not a residency competitor.
**Categories**: multimodal, quantization, local_inference

## Objective

Evaluate Baidu's ERNIE-Image-Turbo (8B distilled DiT, Apache 2.0) as a self-hosted text-to-image generation tool to replace the cloud `image_generate (FAL)` adapter currently disabled in `hermes-outer-shell.md`. The model's distinctive niche is **bilingual (EN+ZH) long-form in-image text rendering** — LongTextBench 0.9655 vs FLUX.1-dev 0.306 — relevant for poster / infographic / multi-panel comic outputs that the orchestrator's tool surface might want.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|---|---|---|---|
| intake-937 | unsloth/ERNIE-Image-Turbo-GGUF (8B DiT distilled, Apache 2.0) | high | already_integrated (deployed as the `image_generate` backend) |

> **Intake-ID correction, 2026-07-29.** This handoff and the deep dive previously cited **intake-528**.
> That ID belongs to an unrelated entry (Kolinko, *"Effort Engine: a possibly new algorithm for LLM
> Inference (bucketMul)"*, 2024-03-26) — ERNIE-Image-Turbo had **no intake row at all** for its entire
> deployed life. The row was created on 2026-07-29 as **intake-937**, filed directly at
> `already_integrated`. All references below have been repointed.

Deep dive: [`research/deep-dives/ernie-image-turbo-dit-text-to-image.md`](../../research/deep-dives/ernie-image-turbo-dit-text-to-image.md) — full architecture, distillation method (DMD + undocumented RL polish), benchmark positioning (GENEval saturated, LongTextBench load-bearing), GGUF tooling semantics, perf expectations on Spark vs CPU, alternatives shortlist, and the variant-selection rationale.

## 2026-05-28 Audit Reset — Executor Start Here

This is not a model-loading handoff anymore. The local `image_generate` replacement is production-functional on CPU; remaining work is quality/operational validation and future GPU latency work.

| Current question | Executor rule |
|---|---|
| Loader/backend compatibility | Resolved. sd-server is the production backend; ComfyUI remains rollback-only. |
| Q8 vs Q4 | Resolved for now. Q4_K_M corrupts the model's signature text-rendering niche; Q8 stays production. |
| What remains before routine use? | Prompt-enhancer policy, content-filter audit, and local LongTextBench-style typography spot-check. |
| What changes the latency story? | Actual GPU/Spark hardware. CPU is acceptable for non-interactive use but should not be sold as interactive. |
| Alternative model decision | Reopen only if the product does not need bilingual long-form in-image text; otherwise ERNIE's niche is still the rationale. |

Recommended next slice:

1. Build a 20-prompt local spot-check: EN/ZH typography, poster, infographic, scene, portrait, political/content-filter probes.
2. Run with prompt enhancer on/off where applicable; record seed, dimensions, steps, wall-clock, and qualitative failure tags.
3. Update this handoff and the deep dive only if the production recommendation changes.

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
| Hermes plugin replacing FAL | ✅ done | `/workspace/scripts/hermes/plugins/local-image-generate/` (symlinked to `~/.hermes/plugins/`). Registers `image_generate` with same name as FAL implementation; Hermes' tools.registry uses dict assignment so plugin wins. Updated 2026-06-27 in root `948fbdbc` to remove stale ComfyUI/8188 wording and pass through the supported `auto`/`true`/`false` enhancer policy to the orchestrator sd-server path. |
| Hermes Python env installed | ✅ done | `uv sync --frozen` at `/mnt/raid0/llm/hermes-agent/` provisioned `.venv` with all 100+ deps including the previously-missing `firecrawl-py>=4.16.0`. Hermes tool registry now loads cleanly (52 tools registered). |
| End-to-end through real Hermes registry | ✅ done | Verified 2026-05-06: `discover_plugins()` auto-discovers our plugin, `image_generate` handler resolves to `hermes_plugins.local_image_generate._handle_image_generate` (NOT FAL), invocation produces a saved PNG end-to-end. Test artifact at `/mnt/raid0/llm/output/images/2026-05-06/d7da4364-7781-4ca7-9906-b91f92232920.png`. |
| **Backend swapped: ComfyUI → sd-server (stable-diffusion.cpp native ggml)** | ✅ done 2026-05-07 | Discovered upstream sd.cpp already ships full ERNIE-Image-Turbo support (`src/ernie_image.hpp`, 441 lines). Built sd-server, replaced ComfyUI in stack. Measured **2.54× wall-clock speedup** at production scale (~188 s vs 478 s @ 1024² 8 steps extrapolated). `--vae-conv-direct` was the high-ROI flag (7.1× on VAE alone). Hermes plugin chain unchanged — `ImageGenerator` interface preserved, internals swapped to `SDServerClient`. Old ComfyUI infra retained for rollback at `/mnt/raid0/llm/comfyui-ernie-test/`. |
| Distilled-model quantization-penalty hypothesis verified | ✅ done 2026-05-07 | Q4_K_M A/B at 832×1248 8 steps, same prompt + seed. **Penalty real**: 17% wall-clock win comes with visible Korean-text-rendering corruption on the model's signature differentiator. Q8 stays as production point. Q4 file deleted post-test. Deep-dive §4.4 hypothesis empirically confirmed. |
| GPU host available | ✅ MI210 (2026-07-02) | The DGX Spark was never acquired; the **MI210 (gfx90a, 64 GB HBM2e)** is the GPU — see `gpu-acceleration-path.md`. GPU rebench of the DiT is now runnable via the ROCm/HIP path (operator-approved). CPU remains functional at ~3 min/image at 1024² post-swap. |

## Remaining Operational Questions

1. **Content-filter audit live run.** Baidu's prior model ERNIE-ViLG had heavy political-content censorship. The no-inference harness is ready in orchestrator `ed6f65f5` (`scripts/diffusion/ernie_content_filter_audit.py`) with 10 cases across political-neutral, copyrighted-character, NSFW-boundary, bilingual-text, and sensitive-current-event categories. Next clean window: run it with `--execute` and review outputs for refusal, silent transform, unsafe output, or error.
2. **LongTextBench self-reported score validation.** ERNIE-Turbo's 0.9655 is on Baidu's own scorecard, not re-validated by the X-Omni team. Re-run a curated 20-prompt local set covering EN/ZH typography stress cases before relying on the leadership claim. **Still open after the 2026-07-29 dive** — that dive resolved only the *cross-model comparability* of the number (see the 2026-07-29 section below), not its validity.
3. **Spark performance reality check.** Deep dive §5.1 extrapolates 6–12 s/image at BF16, 3–5 s at NVFP4 from FLUX-schnell numbers. Re-bench on actual hardware once Spark lands; the 8-step distilled DiT has no published Spark numbers.
4. **Alternative re-evaluation.** If LongTextBench-ZH is not actually needed by the product, FLUX.1-schnell (12B, 4-step, Apache 2.0, mature ecosystem) is the simpler default. Re-litigate the choice against actual product requirements before committing.

Resolved questions:
- Loader/backend compatibility: resolved by sd-server native ERNIE support.
- Distilled-model quantization penalty: verified; Q4_K_M corrupts text rendering enough to reject for production.
- Hermes integration shape: resolved through the local `image_generate` plugin and `ImageGenerator`/`SDServerClient` interface.
- Prompt-enhancer policy: resolved in orchestrator `f4b4cebe` with a deterministic `auto` policy that turns on for text-heavy surfaces and simple short prompts, turns off for compositional/spatial scenes and already-rich prompts, and records the policy decision in result metadata while the sd-server backend still passes prompts through verbatim. Hermes root `948fbdbc` now forwards only the supported tri-state policy.
- Content-filter audit preparation: no-inference manifest/runner landed in orchestrator `ed6f65f5`; live generation and human review remain open.

## Notes

- **Variant decision**: download **Q8_0 (8.69 GB) only**, skip BF16 and UD- variants for now. Reasoning lives in deep dive §9 — short version: Q8 is the production runtime, and the case for BF16 as a calibration reference was over-engineered against evidence (SECourses' Z-Image-Turbo A/B already shows Q8 ≡ BF16 in quality on a comparable distilled DiT). HF doesn't expire — pull BF16 later only if Q8 wobbles on actual ERNIE-Turbo prompts.
- **Backend is NOT llama.cpp** — out-of-band from EPYC's inference stack. Runs through diffusers (`ErnieImagePipeline`), SGLang, or ComfyUI-GGUF. Plan to use ComfyUI-GGUF as the primary backend (smallest VRAM footprint, native to the Unsloth release).
- **CPU smoke-test**: technically possible at 30–120 s/image (deep dive §5.2) via diffusers on CPU but not interactive. Useful only to validate the model loads and produces outputs; not a deployment path. **Not** worth deploying via stable-diffusion.cpp port unless we want to do non-trivial llama.cpp engineering for a tool that's better served on GPU.
- **`feedback_dont_dismiss_creative_uses` memory** is what prevented this from being marked `not_applicable` at intake — the legitimate reframing is "self-hosted T2I to replace disabled FAL cloud tool, gated on GPU." That reframing was vindicated — the model shipped to production on CPU without waiting for a GPU, so the intake row filed on 2026-07-29 (`intake-937`) skipped `new_opportunity` entirely and went straight to `already_integrated`.

## Files

- Deep dive: `research/deep-dives/ernie-image-turbo-dit-text-to-image.md`
- Intake: `research/intake_index.yaml` → `intake-937`
- Upstream model: https://huggingface.co/unsloth/ERNIE-Image-Turbo-GGUF
- Upstream Baidu model: https://huggingface.co/baidu/ERNIE-Image-Turbo
- Eventual download target: `/mnt/raid0/llm/models/diffusion/ernie-image-turbo-gguf/`

## Reporting Instructions

After any work in this handoff:
1. Update the **Status of Prep** table.
2. If the loader-compatibility verification (Q1) resolves, document the result here and unblock downstream work.
3. If Q8-vs-BF16 A/B is run, append the result to the deep dive (§4.4 and §9) and update the variant recommendation if needed.
4. Keep `intake-937` in sync with this handoff. Its verdict is already `already_integrated` (the stub→active transition and the GPU arrival both fired long ago); what still needs pushing back into the index are *outcome* changes — the LongText-Bench self-report validation, the content-filter audit result, the MI210 rebench, or a decision to displace ERNIE with an alternative (which would move the row to `superseded`).
5. If superseded by an alternative (FLUX.1-schnell, Qwen-Image 2.0), move to `handoffs/completed/` with a one-paragraph closing note explaining the choice.

## 2026-07-29 — intake Stage-2 dive corrections (intake-918 / intake-928)

_Via `/research-intake` Stage-2 2026-07-29. Two record corrections that bear on this handoff's backend and its selection axis._

**1. The "stale backend" premise is STRUCK — our pinned checkout already supports Z-Image.** The Stage-1
assertion that `/mnt/raid0/llm/stable-diffusion.cpp` at `90e87bc` (2026-05-06) has **no** z_image support is
**FALSE**: that checkout contains `src/z_image.hpp` (**646 lines**) and `docs/z_image.md`, fully wired
(`diffusion_model.hpp:479` `ZImageModel`, `model.h:45` `VERSION_Z_IMAGE`, `stable-diffusion.cpp:502-507`,
`name_conversion.cpp:621`, `rope.hpp:627` `gen_z_image_ids`), and **`build-hip/bin/sd-server` (gfx90a, built
2026-07-19) was compiled from that source** — Z-Image runs on today's binary, no rebuild required. Consequently
the **claimed ERNIE-regression risk of a forced backend upgrade collapses with it**: no upgrade is needed to
trial a second model, so nothing touches the live ERNIE role. (We are ~202 commits / ~2.7 months behind
upstream, tree clean — that is a separate, non-blocking currency question.)
*Also withdrawn:* using Z-Image as a diagnostic control for the MI210 blank-PNG bug is **confounded** —
`z_image.hpp:51-53` carries an explicit ROCm workaround that `ernie_image.hpp` lacks entirely. A
mitigation-matched control would be `qwen_image` (Vulkan-only guard at our pin). The ERNIE ROCm-f32 patch
candidate is tracked on `gpu-acceleration-path.md`, not here.

**2. LongText-Bench comparability RESOLVED — the incumbent leads on its own selection axis.** Same benchmark,
same splits, aggregation = EN/ZH arithmetic mean. Baidu's own ERNIE-Image-Turbo card carries a three-column
table that **includes the competitor and reproduces Z-Image's per-split numbers exactly** — which is what makes
the comparison legitimate. Harmonized: **ERNIE-Image-Turbo 0.9655 (w/ PE) > ERNIE 0.9639 (w/o PE) > Z-Image
base 0.9355 > Z-Image-Turbo 0.9215** — ERNIE leads by **4.4 points**, and leads **even without its prompt
enhancer**. This does **NOT** validate ERNIE's own 0.9655: both sides are vendor self-reports, and the
20-prompt local spot-check (Remaining Operational Question 2) still stands as the only thing that can.

## Progress checklist

- [x] Production functional on CPU via sd-server Q8 + conv-direct; Q4 rejected (text corruption) ✅
- [ ] Record the LongText-Bench resolution in the deep dive (§ benchmark positioning) — harmonized ranking,
      identical splits, EN/ZH-mean aggregation, ERNIE +4.4 over Z-Image-Turbo even w/o prompt enhancer; and
      that ERNIE's own 0.9655 remains vendor-self-reported (see the 2026-07-29 section above)
- [ ] Run content-filter audit live with --execute (harness ready in orchestrator ed6f65f5) and review outputs
- [ ] Run 20-prompt local LongTextBench-style EN/ZH typography spot-check to validate 0.9655 self-report
- [ ] GPU/MI210 rebench of the 8-step distilled DiT via ROCm/HIP path (operator-approved, measure-not-extrapolate)
- [ ] Re-litigate FLUX.1-schnell alternative if bilingual long-form in-image text not needed by product
