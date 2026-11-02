# G5 capture plan: group-32 K-channel outliers under attention rotation

**Status:** implementation and measurement predeclaration draft; not authorization to build or run.  
**Question:** On the production Qwen3.6-35B-A3B checkpoint, does the enabled post-RoPE Hadamard transform flatten group-32 key-channel outlier ratios in the model's full-attention layers, relative to the same fixed prompt with attention rotation disabled?

## Scope and interpretation

The target is the Qwen3.6-35B-A3B Q8_0 GGUF at `/mnt/raid0/llm/models/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf`. The handoff identifies this family as a 40-layer GDN hybrid with 10 full-attention layers; only those ten layers produce the K tensors under study. Before capture, enumerate the actual full-attention layer indices from model metadata/runtime graph and record them; do not assume they are contiguous. Required coverage is all 10/10 full-attention layers and every K/V head on each, or the artifact is incomplete. Do not count GDN/linear-attention layers as missing full-attention observations. The result describes these attention K activations for one checkpoint and one prompt. It does not establish behavior for the 30 GDN layers, other models/prompts, final KV quantization error, downstream quality, or whole-model behavior.

The observation point is the activation graph before K is written to the KV cache. In the current Qwen graph, `Kcur_normed` is after per-head QK RMSNorm and `Kcur` is after RoPE. The generic `build_attn` path then applies Hadamard rotation to K when enabled. Therefore the added experimental-only callback label `Kcur_rotated` must identify the output of that K Hadamard operation, immediately after multiplication. For the disabled arm, emit an explicit `rotation_applied=false` metadata field and treat post-rotation K as an alias of the post-RoPE `Kcur` values; do not silently omit the comparison tensor. Capture normalized, post-RoPE, and post-rotation/alias tensors so the transform's placement and input are auditable.

## Experimental-only source preparation

1. Create a fresh isolated experimental worktree/branch from the frozen production source tip `ffc1bac82eeca6f9099e1ccd9ba49703c460a115` (`production-consolidated-v10`). Do not modify, build, or commit in `/mnt/raid0/llm/llama.cpp`; do not reuse or clean `/mnt/raid0/llm/llama.cpp-experimental`, which the prep inspection found stale and dirty.
2. In the candidate only, add the post-Hadamard `Kcur_rotated` graph callback and a narrowly filtered eval callback that accepts only `Kcur_normed`, post-RoPE `Kcur`, and `Kcur_rotated` (plus the disabled-arm alias). It must copy tensor values without modifying graph data, exclude all unrelated tensors, and persist compact raw per-channel summaries and provenance. Existing `common_debug_cb_eval` is not suitable because it asks for every graph tensor and prints values rather than producing this artifact.
3. Keep source changes limited to the diagnostic tap/capture and any minimal build wiring required to compile it. Record the complete source diff and candidate commit. No production-tree change is in scope.
4. Prepare the candidate through the approved experimental workflow. Publish executable measurement work through rowflow; the keeper owns qualification and grants. This plan does not authorize execution by the handoff session.

## Paired capture design

Use one fixed literal prompt, one tokenization path, one model file, one candidate binary, and one invocation configuration per pair. Persist both the literal prompt and exact token IDs (including BOS behavior). Use a single prompt prefill capture with no generated continuation; disable warmup so captured callback events are unambiguous. Hold constant backend/device, context length, batch/microbatch, seed, RoPE/context settings, and all CLI arguments. Use quantized K (`-ctk q8_0`) in both arms so the production rotation gate is eligible; f16 K does not exercise this rotation path.

- **Arm A — rotation enabled (positive mechanism arm):** unset `LLAMA_ATTN_ROT_DISABLE`; verify startup/runtime reports `attn_rot_k=1` and that the callback observes a distinct post-rotation tensor for eligible full-attention layers.
- **Arm B — rotation disabled (paired control):** set `LLAMA_ATTN_ROT_DISABLE=1`; verify `attn_rot_k=0`, log the force-disabled message, and verify the post-rotation label is represented as an alias of `Kcur` with identical captured values.

Run the pair back-to-back with identical inputs/configuration. The only intended difference is the rotation-disable environment variable. Reject the pair if model hash, token IDs, candidate commit/build identity, runtime config, target-layer/head coverage, or expected rotation state differs. Compare pre-transform `Kcur` values between arms as a diagnostic, but do not require equality: quantized cache behavior in earlier layers can change later-layer activations. To isolate the transform, compare the post-RoPE and post-Hadamard tensors within the enabled arm for each matching layer/head/token, and use the disabled arm as a whole-graph control. No independent repeated prompts or statistical significance claim is predeclared: this is a deterministic mechanism/shape diagnostic, not a generalization estimate.

## Predeclared data and metrics

Preserve raw captured values for each arm, tensor stage, layer, KV head, channel, and prompt token in a lossless numeric representation (FP32 after conversion for storage is acceptable if the callback also records the source tensor type and conversion). Let `K[s,l,h,c,t]` be a captured value at stage `s`, full-attention layer `l`, KV head `h`, channel `c`, and prompt token `t`.

1. For each channel, compute `a[l,h,c] = max_t abs(K[s,l,h,c,t])` and `r[l,h,c] = sqrt(mean_t(K[s,l,h,c,t]^2))`, over the complete fixed prompt token sequence. These are respectively token-max absolute magnitude and token RMS; retain both vectors per layer/head/stage.
2. Partition channels into contiguous, non-overlapping groups of 32 within each head, beginning at channel 0. Require each head dimension to be divisible by 32; otherwise report the remainder and do not silently drop it. Do not pool channels across heads or layers.
3. For each group `g`, report `G32_max[l,h,g] = max_{c in g} a[l,h,c]`; report `G32_rms[l,h,g] = sqrt(mean_{c in g} r[l,h,c]^2)`; and report `G32_ratio[l,h,g] = G32_max / G32_rms`. If the denominator is zero or non-finite, emit a null ratio and an explicit reason. This defines “group-32 max/RMS” without ambiguity: max is the largest channel's prompt-token maximum absolute magnitude; RMS is the RMS across channels of their per-channel token RMS. Also provide per-layer/head summaries (group count, median and maximum ratio) strictly as convenience reductions, while keeping every group row as the primary evidence.
4. Compute the above independently for post-RoPE K and post-rotation/alias K. Include `Kcur_normed` as a diagnostic pre-RoPE stage, not as the rotation comparison endpoint. Present paired per-layer/head/group values and `enabled / disabled` ratio, with undefined-denominator handling. Do not average ratios across layers or heads; no single pooled number may replace the per-group results.
5. Predeclare descriptive reading only: compare group ratio distributions by identical layer/head/group across the two arms. “Near-flat” / “outlier survives” must be accompanied by the full per-group rows and explicitly described as descriptive for this one prompt/checkpoint. No numerical threshold for “near-flat” is supplied by the handoff; do not invent a gate after seeing output. The handoff's B1 trigger is surviving outliers after rotation, but B1 remains unopened until the owning operator/session interprets a complete artifact under the handoff wording.

## Artifact identity and acceptance checklist

Write an immutable run directory containing at least:

- `manifest.json`: experiment ID/date; candidate source commit and full diff hash; base production commit; build configuration and binary SHA-256; exact model path, byte size and SHA-256; prompt text, token IDs and tokenizer/BOS metadata; all CLI arguments; backend/device and relevant runtime/environment settings; context/batch settings; requested K type; rotation state and `attn_rot_k` log evidence; capture callback version/hash; and start/end timestamps.
- `raw/`: lossless captured per-token K data keyed by arm/stage/layer/head, or a documented lossless container with equivalent coordinates.
- `metrics.csv` (or Parquet): one row per arm/stage/layer/head/G32 group with channel range, `G32_max`, `G32_rms`, `G32_ratio`, and explicit null/error fields.
- `coverage.json`: expected and observed full-attention layer IDs, expected and observed head counts, head dimensions, group counts, callback tensor counts, token count, and missing/duplicate/unexpected captures. Acceptance requires exact full-attention coverage and no unexplained duplicate or missing events.
- `run.log`: complete startup/runtime log for both arms, including rotation state and relevant CLI/model identity.
- `checksums.sha256`: hashes for all artifact files, excluding itself.

The model byte size observed during preparation was 36,914,690,368 bytes; verify it again at run time and compute SHA-256 rather than treating size/path as identity. The local production source was observed at the stated v10 commit; verify that identity before preparing the isolated worktree. Candidate identity must be established from the actual binary/build manifest, not directory names or mtimes.

## Known limitations and failure conditions

- Ten full-attention layers are 10/40 of this hybrid's layers. Results cannot be generalized to the 30 GDN layers or described as a whole-stack measurement.
- The fixed prompt samples one token sequence and one model checkpoint; no prompt-distribution or cross-checkpoint claim is supported.
- Captures are graph activations before KV-cache quantization. They measure the rotation's channel-shape effect, not quantization reconstruction error, perplexity, retrieval, generation quality, or serving performance.
- The disabled arm is a mechanism control, not an unrotated production recommendation. The enabled arm exercises the path only if quantized K, compatible head dimension, and runtime `attn_rot_k=1` are proven.
- The callback and host copy may affect runtime/memory behavior. Do not use these runs for speed or memory claims; verify that callback reads are observational and do not write tensor contents.
- Any incomplete layer/head/token coverage, unexpected graph labels, missing/incorrect rotation log state, or identity mismatch invalidates the pair rather than supporting a negative finding.
- This is a predeclaration, not a ratified measurement protocol. Under `MEASUREMENT.md`, the resulting values are observations unless an owning protocol and claim tuple authorize a claim. The keeper must qualify and grant any published compute row before execution.

## Local implementation references checked

- Handoff G5 definition and scope caveat: `handoffs/active/tq3-quantization-evaluation.md:301-311`.
- B1 dependency and “surviving outliers after rotation” trigger: `handoffs/active/tq3-quantization-evaluation.md:384-390`.
- Qwen K normalization and post-RoPE callback points: `/mnt/raid0/llm/llama.cpp/src/models/qwen35moe.cpp:302-336`.
- Generic K Hadamard insertion point: `/mnt/raid0/llm/llama.cpp/src/llama-graph.cpp:2764-2795`.
- Rotation enable/disable gate and runtime log: `/mnt/raid0/llm/llama.cpp/src/llama-kv-cache.cpp:316-342`.
- Existing eval callback interface/example: `/mnt/raid0/llm/llama.cpp/examples/eval-callback/eval-callback.cpp`; broad debug capture behavior: `/mnt/raid0/llm/llama.cpp/common/debug.cpp:143-181`.
- Measurement claim boundary and need for protocol/claim fields: `MEASUREMENT.md` sections 1, 3, and 5.
