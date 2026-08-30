# MiniMax-H3 Video Generation Evaluation

**Status**: OPEN — created 2026-08-30 from operator session research (no intake row yet; see Task 7)
**Created**: 2026-08-30
**Updated**: 2026-08-30
**Priority**: LOW-MEDIUM — exploratory. New omni-modal capability (video + native stereo audio) with no
identified product demand yet; the first gate is a scope decision, not a download.

## Objective

Evaluate MiniMax-H3 as a self-hosted video-generation capability: omni-modal (text/image/video/audio in →
video + native stereo audio out), 4–15 s, 24 FPS, 768p local (2K only via hosted API). The concrete
deployment path under consideration: **Ref2VA base variant + TenStrip/10Eros-Max transformer drop-in**,
served via SGLang/diffusers/ComfyUI on the MI210 stack. This is out-of-band from the llama.cpp kernel
tree — same status as ERNIE-Image-Turbo (sd-server/diffusers backend), not a llama.cpp serving role.

## Model facts (from model card, 2026-08-30)

| Item | Value |
|---|---|
| Publisher / license | MiniMaxAI; MiniMax H3 Community License (Excluded Territories: EU, UK, KR, US — US-based use is **unauthorized** without application via platform.minimax.io/h3-license) |
| Output | 4–15 s video, 24 FPS, 32 kHz stereo audio, 21:9…9:16 aspects; 768p default, 2K via H3-Regenerate-2K (API-only) |
| Architecture | H3-Omni-Transformer **33B dense** (~13B in cacheable AdaLN branches; inference prunable → ~20B); H3-Encoder = **Qwen3-VL-32B dense** (layer-50 hidden states, extended tokenizer with `<d>` tokens); VisualVAE f16t4d24 + ViT decoder; AudioVAE stereo 40 Hz latents; MM-RoPE (t,h,w); sparse attention trained but not released |
| Variants | H3-Base-FL2VA (0/1/2 images) and H3-Base-Ref2VA (≤9 images, ≤3 videos, ≤3 audio clips, ≤12 files, 2–15 s each) — same 33B architecture, task-specialized checkpoints |
| Repo size | 498 GB total (both variants, original + diffusers formats, F32+BF16); single variant ~144 GB |
| Components (per variant) | transformer/ (~66 GB), text_encoder/ (~64 GB, stock Qwen3-VL-32B weights), audio_vae/, video_vae/, processor/, tokenizer/, scheduler/ |
| Serving | SGLang (reference: 4 GPUs, ulysses-degree 4) or vLLM or diffusers or ComfyUI (R2V/T2V templates). NOT llama.cpp. |

## Community quantization landscape (56 quantized models, 2026-08-30)

- **GGUF**: `unsloth/MiniMax-H3-GGUF`, `Abiray/MiniMax-H3-Pruned-GGUF`, `molbal`, `leejet` (~20B —
  AdaLN pruned, inference-only); full-33B: `joeygambino/MiniMax-H3-GGUF` (+ `-encoder-GGUF`)
- **NVFP4**: `Abiray/Minimax-H3-nvfp4-INT4-INT8-Convrot`, `rockerBOO`, `ModelsLab` ref2va-NVFP4
- **FP8**: `unsloth/MiniMax-H3-FP8`, `rzgar` fl2va-fp8-e4m3fn
- **INT4/INT8 mixed**: `Ar4ikov` W4A16-RTN, `starsfriday` w4a8, `tsolful` INT4MixedConvRot
- **MLX 4/8-bit**: `gabrielrocco/MiniMax-H3-Ref2VA-MLX-Serve-4bit/8bit`, `ddalcu` FL2VA
- **NF4**: `Rudra-ai/MiniMax-H3-NF4`

## NSFW-capability evidence (weights, not license)

The base weights carry no refusal circuit (diffusion model); the restriction is training-data filtering —
adult content was filtered out, so the base is **weak at explicit content**, not refusing. Evidence:
`TenStrip/10Eros-Max` (403 likes, the main NSFW finetune) states explicitly that fine-tuning H3 toward
NSFW is "clearly problematic" — the author had to **graft NSFW attention-layer weights from Wan 2.2 /
LTX 2.3 / Krea 2** into H3. The "UNCENSORED" LoRAs (e.g. `Pepe104/MiniMax-H3-Turbo-Lora-UNCENSORED`)
add absent capability rather than removing a refusal mechanism. Hosted guardrails (H3-Context-IR
moderation) are API-side only and do not apply to local weights. Content-filter audit of local output
is warranted before any production use (mirror the ERNIE audit pattern, PIP-03).

## Deployment path under consideration

**Files**: `MiniMaxAI/MiniMax-H3` `Ref2VA/` (144 GB) + `TenStrip/10Eros-Max`
`10Eros_Max_h3_TURBO-hybrid_beta4_int8_convrot.safetensors` (21 GB INT8 transformer — the
recommended pick for an MI210 stack; BF16 40.2 GB exists too). Total **~165 GB**.

**Disk check 2026-08-30**: single 3.7 TB RAID (`/dev/md127`) backing `/workspace` + `/mnt/raid0/llm`;
**291 GB free (92% used)**; nothing H3 on disk yet. 165 GB fits but leaves ~126 GB (~95.5% full) —
verify headroom again immediately before download.

**10Eros-Max specifics**: transformer-only drop-in for `Ref2VA/transformer/`; beta4 (released
2026-08-29) fixed the beta3 turbo corruption in i2v/reference starts; runs t2v + i2v + reference modes;
euler/simple 6–8 steps; no cache/spectrum in reference mode; INT8 convrot variant covers the whole
transformer; carries grafted character from Wan 2.2/LTX 2.3/Krea 2 (their community licenses apply to
the grafted portions per the author).

## Open questions / next steps

- [ ] **Scope decision (operator)**: is video generation a product need at all? If not, close this
      handoff — the download is 165 GB on a 92%-full volume, so "interesting model" alone is not a reason.
- [ ] If scope approved: re-check disk headroom, then download `model_index.json` + `Ref2VA/*` + the
      beta4 INT8 transformer (~165 GB total)
- [ ] Serve on the MI210 stack via SGLang or ComfyUI (reference deployment is 4×GPU ulysses-degree 4 —
      confirm single-MI210 feasibility with the INT8 transformer before committing; ~2.4 GB/K GPU not
      transferable from the SGLang cookbook without measurement)
- [ ] 768p quality smoke on a small prompt set (T2VA + FL2VA + Ref2VA cases from the model card's
      reproducible scripts); record wall-clock, VRAM, failures
- [ ] Content-filter audit of local output (hosted moderation does NOT apply locally)
- [ ] File the research-intake row when adoption is decided (none exists yet — created directly at
      intake, mirroring intake-937 for ERNIE; verdict will be `new_opportunity` or `already_integrated`)
- [ ] License compliance note for any production use: US/EU/UK/KR are Excluded Territories — use there
      requires the MiniMax application; guardrail-bypass via uncensored LoRAs is an AUP #5 breach
      (governance note only; does not gate the capability evaluation)

## Files

- Upstream: https://huggingface.co/MiniMaxAI/MiniMax-H3 (model card, README, LICENSE, scripts/)
- NSFW-capable finetune: https://huggingface.co/TenStrip/10Eros-Max (+ `h3_graft_methodology.md`)
- Graft INT8: `cicalooo/10Eros-Max-h3-int8-convrot` (community, separate repo)
- SGLang cookbook: https://docs.sglang.io/cookbook/diffusion/MiniMax/MiniMax-H3
- ComfyUI templates: `Comfy-Org/workflow_templates` `video_minimax_h3_r2v.json` / `_t2v.json`

## Reporting Instructions

After any work in this handoff:
1. Update the **Status of Prep**-style evidence above with dates and artifacts.
2. If the scope decision lands, update this handoff and the EVL-32 row's Next action.
3. If adopted into a serving role, file the intake row and move integration rows to
   pipeline-integration-index (PIP) — the ERNIE precedent owns image; H3 would be video.
4. Run `python3 scripts/handoffs/index_state.py` and `--check` after any index edit.
