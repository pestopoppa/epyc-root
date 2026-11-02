# k175 and k228: bounded local-model capture assessment

Inspection only, 2026-11-02. Neither case is ready to publish as a governed GPU capture. This is a bounded candidate search, not proof that no compatible model exists on the host.

## Identified candidates

* `/mnt/raid0/llm/models/deepseek-ai/DeepSeek-V4.1-Flash/config.json` SHA-256 `8be45ce0476004a3f529fd896115a4a2e800a129ad2d3ec05b16050f52e21879`: `text_config` has 384 routed experts, one shared expert, six experts per token and `sqrtsoftplus` routing. Its model's actual `inference/model.py` `Gate.forward` around lines 792–825 and `MoE.forward` around lines 854–903 are useful prospective real-model observation seams, but cannot satisfy k175's **biased sigmoid top-8** contract without changing the workload. Model directory holds the configuration and index but no safetensor shards in its top level; separately `/mnt/raid0/llm/models/deepseek-ai/DeepSeek-V4.1-Flash-1017-DSpark.gguf` exists. The latter is a different format/variant and has not been bound to this Python implementation or hashed; do not imply it provides the missing safetensors.
* `/mnt/raid0/llm/models/turboderp/Qwen3.8-Flash-Next-exl3-3.05bpw/config.json` SHA-256 `92ce0839c71b5a39988299fe38206a32fea50586be54378d424fc0eb035a44c0`: text configuration declares 512 experts and ten experts per token, so it cannot provide k175's exact top-8 surface merely by observation. No scoring or dispatcher equivalence is asserted.

For k228, the V4.1 reference `inference/model.py` `Attention` around lines 613–780 constructs window/compressed KV and calls `sparse_attn(q, kv, attn_sink, topk_idxs, ...)`, while `inference/kernel.py` around lines 392–400 returns only the sparse-attention output. This is not an established capture surface for the requested causal paged MLA inputs `q_nope`, `q_pe`, `ckv_cache`, `kpe_cache` and base-2 fp32 LSE. Do not synthesize the missing surface or assume the V4.1 sparse attention implementation matches it.

## Concrete next steps

1. Search real local model inventories and their exact runtime configs for an actual model whose routing is biased sigmoid top-8 and a model/runtime with the k228 paged MLA surface. Bind complete model file inventories and runtime source commit before adopting either. Config and filename are discovery aids, not weight or execution identity.
2. In a clean experimental source checkout, instrument the chosen real runtime at its actual attention inputs/output or router/dispatch/expert/undispatch boundaries. Implement `capture_real_model_tensors(plan, model_path)` with exact tensor order and selected branch, and the `epyc.autokernel.c3_epyc_real_model_provider.v1` manifest expected by `epyc-inference-research/scripts/kernel_rnd/autokernel/evaluator/c3_epyc_capture_provider.py`. Do not instrument frozen production.
3. Hash-bind hook, source, full model inventory, recipe, request and toolchain; compile using `c3_epyc_tensor_capture.py`, then publish a GPU row only once the keeper-controlled launcher can satisfy its claim and process-window checks. Capture establishes identity only. Apex mapping remains a separate gfx90a/LSE/ordered-graph problem, as specified in research `scripts/kernel_rnd/autokernel/README.md` lines 549–575.

GitNexus reports this lane unindexed; attempted `impact capture_real_model_tensors --direction upstream` refused because repository selection is ambiguous. This new Markdown assessment changes no executable symbol.
