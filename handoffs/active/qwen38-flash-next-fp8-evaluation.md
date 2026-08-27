# Qwen3.8-Flash-Next-FP8 — Future Inference Evaluation

**Status**: ACTIVE — artifact verified; backend compatibility audit is ready to dispatch
**Created**: 2026-08-27
**Owner**: inference research (`INF-63`)
**Priority**: P2 — preserve and qualify a promising large-model research candidate without changing production

## Objective

Determine whether the official Qwen3.8-Flash-Next FP8 checkpoint is a viable inference-research
model on the EPYC + MI210 host. Select a compatible research backend, prove a bounded load and
coherence path, measure it under the measurement constitution, and finish with a `GO`, `WAIT`, or
`KILL` verdict plus an explicit disk-retention decision.

Production llama.cpp support is not a prerequisite. The frozen production kernel and production
registries remain untouched; an experimental llama.cpp branch is only one optional backend alongside
Transformers, vLLM, SGLang, TokenSpeed, or a justified CPU/hybrid path.

## Artifact identity

| Field | Value |
|---|---|
| Model | `Qwen/Qwen3.8-Flash-Next-FP8` |
| Local path | `/mnt/raid0/llm/models/Qwen3.8-Flash-Next-FP8` |
| ModelScope revision | `f88480ebce48d6daed69eac86aab43b4122ad799` |
| Hugging Face weight pin | `bcd9f01ddc9cff2316eb84281bebcd5b058bddce` (checksum-identical weights) |
| Verified payload | 185,563,783,823 bytes; 145 files; 131 safetensors shards |
| Architecture | `qwen4_exp` / `Qwen4ExpForConditionalGeneration`; multimodal; native 262,144-token context |

All ModelScope SHA-256 checks passed and no partial files remained after download. The checkpoint is
block-FP8 and is much larger than one MI210's 64 GiB VRAM. Because gfx90a has no native FP8 MFMA,
the evaluation must distinguish storage format from compute dtype and must not describe the run as
native FP8 compute without direct proof.

## Scope and gates

- DeepSeek V4 Flash is retired, its local checkpoint was deleted, and it is not a local comparator.
  Vendor-published results may be contextual evidence only.
- Start Phase 0 whenever an inference-research lane is free. Inference starts only after the audit
  identifies a credible gfx90a-compatible or CPU/hybrid path and a governed compute window is held.
- A backend must cover `qwen4_exp`, block-FP8 loading/dequantization, the vision path, QSA/Gated
  DeltaNet components, n-gram embeddings, and MTP as applicable. Unsupported optional features must
  be recorded rather than silently disabled.
- Abort a smoke on OOM pressure, persistent incoherence/repetition, or an unverified compute path.

## Tasks

- [x] Verify artifact acquisition and integrity ✅ 2026-08-26 — exact payload and both upstream pins
  recorded above; all advertised ModelScope hashes passed.
- [ ] Select a compatible research backend and run a bounded load/coherence smoke on the downloaded FP8 artifact
  - Audit the installed and readily reproducible Transformers, vLLM, SGLang, TokenSpeed, and optional
    experimental-llama paths before selecting one.
  - Record the exact environment, dependency pins, compute/dequantization dtype, CPU RAM, VRAM, and
    offload/placement policy. A software FP8-to-BF16 path is acceptable when named accurately.
- [ ] Prove residency during the load/generation window — sample RAM and VRAM while the phenomenon is
  active; for ROCm record non-zero VRAM and KFD process evidence and verify the selected runtime's
  actual libraries/backend.
- [ ] Run bounded coherence smokes — five text prompts (greeting, code, reasoning, structured output,
  tool call) plus one vision prompt; pin chat template, `enable_thinking`, `preserve_thinking`,
  `reasoning_effort`, and tool settings.
- [ ] Measure prefill, decode, context-depth behavior, and MTP on/off when the selected backend exposes
  it. Declare whether higher or lower is better for every metric and use only protocol-matched
  baselines; compare with Qwen3.8-27B only where recipes and workload roles match.
- [ ] Run a focused capability ladder for coding, reasoning, and tool use; include vision only if its
  smoke passed. Preserve prompts, outputs, configuration, timing windows, and failure evidence.
- [ ] Publish the `GO` / `WAIT` / `KILL` and disk-retention verdict. Any new measurement or verified
  finding must also add its source-class adapter row to `scripts/vidya/adapters/README.md` and the
  corresponding task to `handoffs/active/vidya-belief-substrate-program.md` in the same session.

## Completion criteria

The handoff completes only when the chosen backend and exact runtime recipe are reproducible, the
bounded smoke and measurement evidence are durable, capability limits are stated without overclaiming
native FP8 execution, and the final verdict says whether to keep the 172.82 GiB checkpoint on RAID.
