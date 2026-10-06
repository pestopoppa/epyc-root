# Making context extension INERT inside the native window: options

Read-only study, 2026-10-06. Source read via `git show ak/champion/llama-cpp-ffc1bac82eec:<path>`, which resolves to `a331665d4`. Nothing was checked out, built or run. The two small numeric tables below come from a Python calculation of the formulas, not from a measurement.

Not verified: `/workspace/artifacts/yarn-native-window-20261005/summary.md` does not exist on disk (a find found nothing), so the 1.3% / 7.6% / 53%->48% / 13-of-20 figures are taken from the brief as given.

## 1. How the champion applies YaRN

All sites below are on the champion branch.

| Site | What it does |
|---|---|
| `src/llama-context.cpp:134` | `n_ctx_orig_yarn` comes from `--yarn-orig-ctx`, else the GGUF key, else `n_ctx_train`. |
| `llama-context.cpp:181-231` | Resolves `ext_factor` (1.0 if `--rope-scaling yarn`, else 0) and `yarn_attn_factor`. |
| `llama-context.cpp:220-228` | **Overwrites** `yarn_attn_factor`. It is set to `get_mscale(f) = 1+0.1 ln f`, then multiplied by `1/(1+0.1 ln f)`, so it ends at 1.0. The user's `--yarn-attn-factor` (read at line 113) is discarded whenever `ext_factor != 0`. |
| `ggml/src/ggml-cpu/ops.cpp:6582-6596` (`rope_yarn`) | Per dimension pair: `theta = interp*(1-ramp) + extrap*ramp`. When `ext_factor != 0` it **hardcodes** `mscale *= 1 + 0.1 ln(1/freq_scale)`. `cos` and `sin` are both multiplied by `mscale`. The CUDA/HIP `rope.cu` has the same `rope_yarn`. |
| `ggml.c:4468-4477` | Correction dims `[lo, hi]` from `n_dims`, `n_ctx_orig`, `freq_base`, `beta_fast` (32), `beta_slow` (1). |
| `llama-graph.cpp:1576-1584` | Graph rope parameters come from cparams. The same cparams are used in `llama-kv-cache.cpp:1978-2030` (`build_rope_shift`, K-shift), which supports quantized K via a Hadamard round trip. |
| `llama-model.cpp:2082-2090` | Existing mechanism `get_rope_factors`: if `n_ctx_seq > n_ctx_orig_yarn` use `rope_long`, else `rope_short`. This is a per-context switch, fixed when the context is created. It exists for Phi3/LongRoPE-style models. |
| `tools/server/server-context.cpp:1337-1342` | Caps the slot context to `n_ctx_train`. Needs `--override-kv <arch>.context_length=int:N`. |

**Per-request or dynamic mode: none exists.**
- `rope_scaling_type` is only none / linear / yarn (`common/arg.cpp:2170-2172`, `llama-model.cpp:865-868`). There is no "dynamic" type.
- Every rope parameter is a context-wide cparam, fixed when the graph is built.
- `ggml_rope_ext` takes scalar `freq_scale`, `ext_factor` and `attn_factor`. It also takes a per-dimension `freq_factors` tensor (src2, `theta/ff`), which is the only per-dimension runtime input.
- The upstream references in the source are #2268 (YaRN), discussion 7416 and PR 17945 (mscale cancellation). There is no per-request upstream work.

## 2. Why in-window outputs change (quantified for Qwen3.6-35B-A3B)

Assumed parameters, not read from the GGUF: n_rot = 64 (IMROPE, partial rotary), base 1e7, orig 262144, scale 2, beta 32/1.

Two separate effects:

**(a) mscale, applied at every position.** The kernel multiplies cos and sin by `m = 1 + 0.1 ln 2 = 1.0693`, for both Q and K, on the rotated dimensions. The Q.K logit contribution of those dimensions is therefore multiplied by `m^2 = 1.143`, a 14% sharpening of that part of the score. This happens at position 0 too: the stored K itself is scaled by 1.069 and the Q is scaled by 1.069, so there is no depth below which it vanishes. This is a constant attention temperature, and it is **the dominant in-window drift**.
- It acts only on the rotated dimensions (64 of the head dimension).
- It is consistent with the measured MTP acceptance drop (53% to 48%), since a sharper attention shifts both the target and the drafter.
- It is the same on all 10 or so full-attention layers.

**(b) Frequency interpolation, restricted to a band of dimensions.** Frequency-pair index i, 32 pairs. Dimensions below `lo`=14 are untouched (ramp 1). Dimensions at or above `hi`=22 are divided by 2 (ramp 0). Pairs 14 to 22 blend.

| pair i | wavelength (tokens) | freq multiplier | angle error at p = 30000 |
|---|---|---|---|
| 0 to 12 | 6 to 2,650 | 1.0 | 0 |
| 16 | 19,869 | 0.875 | 1.19 rad |
| 20 | 148,998 | 0.625 | 0.47 rad |
| 24 | 1.1 M | 0.5 | 0.08 rad |
| 31 | 38 M | 0.5 | 0.002 rad |

- Pairs with wavelength in the 10^4 to 10^5 range, which are the long-range positional channels, are rotated by an angle that is wrong by about 1 rad at 30k tokens and more at greater depth. That explains why drift grows with depth (the measured 7.6% at 34k versus 1.3% at depth 0).
- Fast pairs are exact. The slow pairs are off by almost nothing at short range.

**Conclusion.** YaRN is not an identity below the native window by construction, because mscale is applied everywhere and the ramp pairs are off by about 1 rad. Bit-identity therefore needs the YaRN branch to be *off* for those tokens. Neutralising only mscale reduces the drift and the temperature effect but does not give bit-identity.

**Depth-0 decode cost (1.3%).** At depth 0 there is no attention work, so the cost is the extra code path: `ext_factor != 0` evaluates `logf`, the ramp and a blend per pair per token, both in the graph rope and, on this build, possibly on the fused decode path (the fused path's rope parameters were only fixed in item 1 of the dca-yarn notes). This is an estimate, not measured here. An identity path with `ext_factor = 0` costs none of it.

## 3. Designs

### Design A: native until a sequence crosses the native length, then switch once (per-sequence mode)

Decide per sequence from the sequence's own length. Sequences at or below N use `ext_factor = 0`, the exact stock rope. A sequence that crosses N gets extended parameters.

The central difficulty is that rotated K is cached, so a sequence cannot switch parameters without re-roping its cache.
- *Switch at admission.* If prompt length + `n_predict` exceeds N, the server starts the slot in extended mode (the whole sequence is roped extended from token 0).
  - This is a **per-slot decision** made when the prompt length is known.
  - It makes in-window requests exact and needs no re-rope.
  - It does not make a request exact if it begins long and the answer is short, but such a request is above native anyway.
- *Switch mid-sequence.* The sequence starts native and crosses N during generation.
  - The cache holds N positions roped natively. Re-rope them once: apply the inverse native rope (`ggml_rope_ext_back`), then the extended rope, using the cell positions.
  - This is the existing K-shift machinery (`build_rope_shift`, `llama-kv-cache.cpp:1978-2095`), with two rope ops instead of a delta rotation. Quantized K goes through the existing dequantize, Hadamard, rope, requantize path.
  - It happens once per sequence, at the moment of crossing, and costs about one pass over the K cache of the 10 full-attention layers.
  - After the switch the sequence is in extended mode with a self-consistent cache.

**The batching problem.** A ubatch mixes tokens from several slots, and `ggml_rope_ext` takes scalar parameters. Options:
1. Use the `freq_factors` tensor, extended to 2-D (`[n_dims/2, n_tokens]`). Native tokens have ff = 1, extended tokens have `ff_i = 1/f_i` with `f_i` the YaRN per-pair multiplier. This reproduces the frequency interpolation exactly (it is how `rope_freqs`/Llama3 rope works) with `ext_factor = 0` in the kernel. Native tokens then get bit-identical results, because `theta/1.0` is exact. This needs a small change in the CPU and HIP rope kernels (read `ff[token][i]`).
2. Put mscale into a per-token Q scale, as DCA does with `dca_qscale`. Set K mscale to 1 everywhere (the extended stored K is then unscaled), and scale only the rotated slice of Q. Easier approximation: scale the whole Q by `m^2` (this differs slightly on unrotated dimensions, which matters only in extended mode).
3. Fallback with no kernel edit: run both ropes and select per token with a 0/1 mask (`ggml_mul` and add). That doubles rope nodes on the attention layers of the graph. Rope is cheap next to the matmuls, but it adds graph nodes in-window, and the "no perf regression in-window" rule would have to be measured.

**Code sites** (champion carry, all outside production):
- a per-sequence flag in `llama_kv_cache` (set/cleared with the sequence);
- a per-token `ff` input (like `inp_pos`) filled in `llm_graph_input_*::set_input`;
- `qwen35moe.cpp:323-331` and the other callers of `ggml_rope_multi`;
- `ops.cpp` and `rope.cu` for the 2-D `freq_factors`;
- the extended re-rope graph;
- server: admission rule and the cap at `server-context.cpp:1337`.

**Other interactions.** The MTP draft context has its own KV and must switch in step with the target. The fused Flash-Next decode path takes rope parameters from cparams (`5bfdcd18c`), so it would also need the per-token `ff`.
- Risk: **medium-high.** Several touch points, plus MTP and the fused path.
- Perf in-window: neutral if option 1 is used (a 2-D read of `ff` instead of a 1-D one).
- Graph reuse: since the graph is the same shape (only input values change), reuse is unaffected.
- **Bit-identity test plan:**
  1. `GGML_CPU` build of the candidate, in-window prompt set (the 20 greedy prompts, plus long ones to depth 200k).
  2. Compare, token for token and logit for logit (`--logits-all` or `llama-perplexity` dumps), the candidate with extension enabled against the stock binary with no YaRN. Expect max-abs logit diff exactly 0 for both prefill and decode, np = 1 and np = 4, MTP on.
  3. A synthetic mixed batch: one native slot + one extended slot. The native slot's logits must still be exactly 0 diff.
  4. Boundary: a sequence crossing N. Positions before crossing identical to stock. After crossing, compare against a fresh extended-from-zero run (up to rounding in the re-rope, which is the expected non-identity and is beyond native).
  5. `strings` check that the knob is compiled in (per the stale-binary rule in CLAUDE.md).

### Design B: dynamic NTK-style scaling that is exactly identity at or below native

Dynamic NTK (HF `dynamic` rope) raises the base only when the current length L exceeds N: `base' = base * ((s*L/N) - (s-1))^(d/(d-2))`. It is exactly identity for L <= N. mscale is not part of it, so there is no temperature drift either.
- **Problem:** the base depends on the *current* length, so it changes every step above N. Cached K were roped under the earlier base, so Q and old K disagree. HF has this flaw with a post-rope KV cache.
- **Fix 1:** freeze the base at crossing (one re-rope, exactly design A with NTK instead of YaRN). That is simply design A with a different interpolation function.
- **Fix 2:** re-rope the cache each time L changes. Prohibitive.
- NTK-aware scaling gives no mscale and no ramp, and quality at 2x is usually a bit below YaRN (an untested assumption here).
- **Verdict:** only worth it as the interpolation function inside design A. It does not remove the need for per-token parameters and the cache re-rope. Test plan is the same as A.

### Design C: DCA (Dual Chunk Attention)

Status: v1 implemented on `experimental/dca-20261004` (champion `90c12df42`, not the current `ffc1bac`, so it needs a rebase), see `/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/DESIGN-DCA.md`.
- **Why it suits the rule:** keys are roped at `p mod c` and only the query varies, so no cached K is ever re-roped; nothing is rewritten when a sequence grows. For contexts up to c it is exactly plain RoPE attention (per the design doc), and the temperature `s = max(1, 0.1 ln(n/orig)+1)` is exactly 1 below `orig`. Equivalence on qwen2/qwen35/qwen35moe is reported bit-exact in the doc's status table.
- **Catch 1:** the identity range is c = chunk_size - local_size, not N. With `chunk 262144, local 8192` it is 253,952, so positions 253,952 to 262,144 are not identical to stock. Set local small or zero to push c to N (a trade-off to decide: smaller local weakens the local window).
- **Catch 2:** v1 uses generic ops, ignores `-fa`, and always takes the DCA graph when `dca_chunk_size > 0`. It would be slower in-window than stock FA (two extra Q ropes, three mul_mat, the selector input). So **for the in-window rule v1 is not acceptable as is**. It needs the graph to fall back to the stock `build_attn` when `max position + n_tokens <= c`. That is a per-ubatch decision and is cheap, but the stock and DCA graphs differ in shape, so it breaks graph reuse at the crossing only.
- **Catch 3:** v2/v3 FA kernels (planned) are needed for long prefill memory (score tensors of 12 GiB each at 262k with ub 512 in v1). The MTP context is refused in v1, and MTP is part of the canonical recipe.
- **Catch 4:** the 1M quality of DCA on these GDN-hybrid Qwen3.6 models is unmeasured (the model was not trained with it; the doc plans an A/B of YaRN vs DCA).
- **Risk:** high (largest code surface, unfinished kernels). The payoff is a mechanism without any K re-rope.
- **Bit-identity test plan:** as in A, with the stock-versus-DCA comparison restricted to n <= c, and explicit tests at n = c, c+1 and N (expected to differ at c+1 unless local is 0).

### Design D: two servers, no kernel change

A native server (the :8070 canonical recipe unchanged) plus a second server with static YaRN for long requests. The orchestrator routes on estimated `prompt tokens + max_tokens` > N (leave margin).
- **In-window bit-identity:** trivially exact, because the native server is untouched, so the rule is satisfied by construction.
- **Cost:**
  - weights page cache is shared by mmap, so the second instance should not duplicate weight memory (see the mmap-shares memory note), but its KV for 1M tokens is extra RAM, and the extended server needs CPU time under a region lock;
  - the second server is idle most of the time;
  - a conversation that grows across the boundary must be re-prefilled on the extended server, which is very expensive on CPU at 262k tokens (the prefill cost of the whole prefix is paid again);
  - the router must estimate output length at admission;
  - MTP, the np-4 slot split and the 65,536-token slots would need their own recipe for the extended server (np 1).
- **Risk:** low technically. It is mostly orchestrator routing and a stack change (3 gates, change-topology, a registry row).
- **Test plan:** diff the native server's greedy outputs before and after the extended server is added (expect 20 of 20 identical, since nothing changed); route tests at N-1 and N+1.

### Design E: other findings

1. **Mscale-neutral YaRN (no kernel change in principle).** Honour `--yarn-attn-factor` instead of overwriting it at `llama-context.cpp:220`, and pass `attn_factor = 1/1.0693` so the hardcoded kernel multiplier cancels. This removes the temperature effect (a) but leaves the interpolation error (b). It is a 2-line cparams change and is **not** bit-identical, so it does not meet the rule by itself, but it measures how much of the 13-of-20 drift and the MTP drop comes from mscale (a). A caution: whether mscale helps quality at 524k and beyond is a separate question that needs its own measurement.
2. **Context-creation switch (already in tree).** `get_rope_factors` selects `rope_long` vs `rope_short` by `n_ctx_seq > n_ctx_orig_yarn`. A per-server switch can set the freq factors to identity whenever the server is started with a context at or below N. It is the one-server cousin of design D, and the base for design A's `ff` tensor.
3. **Order of work if design A is built:** the one-time re-rope, the per-token `ff` tensor and the Q scale are separable and each can be tested alone.
4. A small defect worth a ticket independent of the rest: user `--yarn-attn-factor` is silently ignored when `ext_factor != 0`.

## 4. Comparison

| | In-window bit-identical | Kernel change | Re-rope needed | Risk | Works with MTP and np 4 now |
|---|---|---|---|---|---|
| A, per-sequence switch with 2-D `ff` | yes | CPU + HIP rope, small | once per sequence | medium-high | needs MTP mirroring |
| B, dynamic NTK | yes | same as A | once (frozen base) | medium-high | same as A |
| C, DCA | yes up to c (c = N with local 0) | large (graph, plus FA v2/v3) | never | high | no (MTP refused in v1) |
| D, two servers | yes (native untouched) | none | none | low | yes |
| E1, mscale-neutral YaRN | no | 2-line cparams | n/a | low | yes |

## 5. Recommendation

**Adopt D now and build A as the in-process path.** D is the cheapest, and the only option that guarantees the operator's rule today, because the native server stays byte-for-byte what it is. It costs idle RAM and a re-prefill when a session crosses the boundary. Build A only if crossing sessions turn out to matter.

**Minimal first experiment (no deployment, CPU only, region-locked, on the experimental branch):**
1. Apply the 2-line cparams fix (E1) in an experimental worktree off `ffc1bac`, so `--yarn-attn-factor 0.935` (that is 1/1.0693) takes effect and cancels the kernel's hardcoded mscale.
2. Rerun the existing 20-prompt greedy A/B and the MTP acceptance measurement on :8070's recipe with three arms: no YaRN, static YaRN (as measured), and mscale-neutral YaRN.
3. Read it as follows. If the mscale-neutral arm recovers most of the 13/20 and the 53% acceptance, the drift is mostly (a) and design A needs only a per-token Q scale plus the `ff` tensor. If it does not, the drift is in (b) and only a true off switch (A, C or D) satisfies the rule.

This experiment is cheap, touches no production tree, and fixes which of A's two components is actually needed before any larger build.

## Prior art (2026)

Evidence level: WebSearch and WebFetch summaries (small-model digests of the pages), not full reads. Items marked (recalled) come from my memory of the source, not from a fetch. TGI and current llama.cpp master were not examined beyond the issues cited below. No upstream code for any per-request scheme was read.

### 1. How production stacks treat the native window

| Stack | Behaviour | Evidence |
|---|---|---|
| vLLM (YaRN) | Static YaRN: the scaling factor is constant regardless of input length, so short texts can degrade. No dynamic YaRN. | [Qwen vLLM docs](https://qwen.readthedocs.io/en/latest/deployment/vllm.html), [Qwen3 card](https://huggingface.co/Qwen/Qwen3-30B-A3B) |
| vLLM (LongRoPE / Phi-3) | Switches factor sets on length. (recalled) vLLM's Phi3 rotary keeps a short and a long cos/sin cache and picks per request using a prompt-length offset, so there is no cache re-rope: the choice is made at admission from prompt length. | not fetched, verify in vllm `rotary_embedding` |
| SGLang | Static YaRN. Dynamic YaRN for Qwen3 was requested and closed without implementation. The reporter's hack (recompute cos_sin_cache every ~200 passes) conflicts with CUDA graphs and with concurrent requests, and cost throughput. KV re-rope was not discussed. | [sglang #6030](https://github.com/sgl-project/sglang/issues/6030) |
| TensorRT-LLM | Supports rotary scaling types none, linear, dynamic, longrope, llama3, yarn, mrope. A dynamic-scaling bug report exists. KV-crossing handling not found. | [TRT-LLM functional docs](https://nvidia.github.io/TensorRT-LLM/python-api/tensorrt_llm.functional.html), [TRT-LLM #1610](https://github.com/NVIDIA/TensorRT-LLM/issues/1610) |
| TGI | Not examined. | n/a |
| HF transformers | `longrope`: `Phi3RotaryEmbedding._longrope_frequency_update` uses the long factors only if seq_len > original_max_position_embeddings, else the short factors. This is the only mainstream inert-below-native mechanism. `dynamic` (NTK) is likewise identity at or below native. | [Phi-3 modeling](https://huggingface.co/microsoft/Phi-3.5-mini-instruct/blob/main/modeling_phi3.py), [rope_utils docs](https://huggingface.co/docs/transformers/en/internal/rope_utils) |
| llama.cpp upstream | LongRoPE factor choice is by allocated `n_ctx_seq`, not actual sequence length (same as our `get_rope_factors`), so short prompts silently get long factors if the context is allocated large. The report suggested using the actual length. It was closed as "not planned". The reporter notes that a sequence crossing the threshold mid-generation cannot easily be re-roped in the KV cache. No per-request YaRN upstream. | [llama.cpp #24823](https://github.com/ggml-org/llama.cpp/issues/24823), also the server context cap [#22140](https://github.com/ggml-org/llama.cpp/issues/22140) |

Pattern: nobody re-ropes at the crossing. Where a length-conditional exists (HF longrope/dynamic), it is a pure function of the current length in an uncached or recomputed setting. Production servers either apply static scaling always or choose at admission. This confirms our finding that "per-sequence switch with one-time re-rope" (A) has no prior implementation to reuse, and that llama.cpp upstream explicitly regards the crossing as hard.

### 2. Qwen's own guidance

- Qwen3 card: static YaRN may hurt short texts; add it only when long context is required and set the factor to the typical length (e.g. 2.0 for 65,536). Alibaba's hosted endpoint supports **dynamic YaRN** by default (so Qwen runs it internally, with no open implementation). [Qwen3-30B-A3B card](https://huggingface.co/Qwen/Qwen3-30B-A3B)
- Qwen2.5-1M: DCA plus MInference sparse prefill; YaRN's attention scaling used with DCA does not alter short-sequence behaviour. [Qwen2.5-1M report](https://arxiv.org/pdf/2501.15383), [blog](https://qwenlm.github.io/blog/qwen2.5-1m/). I did not verify the card for the exact Qwen3.6 model; it likely repeats the Qwen3 text.
- Related active llama.cpp bugs for hybrid Qwen3.8/3.5 at long range with YaRN x4 (a crash near 520K tokens, EOS beyond about 130K): [#27090](https://github.com/ggml-org/llama.cpp/issues/27090), [#27756](https://github.com/ggml-org/llama.cpp/issues/27756). Relevant risk to any 1M plan; not read in depth.

### 3. Is YaRN state of the art in 2026?

- **YaRN** (static) remains the default in every serving stack and the Qwen recommendation, but it is not inert in-window. Matches our finding: mscale everywhere plus the ramp.
- **LongRoPE / LongRoPE2** (per-dimension factors found by search, plus mixed-window training that keeps the original RoPE for short sequences, 97-98.5% of short-context accuracy retained). This needs fine-tuning, and the short/long factor switch is on length, which is exact below native. [LongRoPE2](https://huggingface.co/papers/2502.20082). It is not usable for a trained Qwen3.6 without training.
- **NTK-by-parts and dynamic NTK:** exact below native when used dynamically (dynamic scaling, per YaRN paper section on dynamic scaling [arXiv 2309.00071](https://arxiv.org/pdf/2309.00071)); static NTK is not.
- **DCA / ChunkLlama:** training-free, exact up to c, no re-rope. [arXiv 2402.17463](https://arxiv.org/pdf/2402.17463). Used in production by Qwen2.5-1M through vLLM.
- Newer training-free or small-training variants surfaced by search (not evaluated): GALI [2502.02659](https://arxiv.org/pdf/2502.02659), DCIS [2412.18811](https://arxiv.org/pdf/2412.18811), Jet-Long dynamic bifocal RoPE [2607.07740](https://arxiv.org/pdf/2607.07740), AdaRoPE [2607.19363](https://arxiv.org/pdf/2607.19363). None has a llama.cpp implementation that I found. Treat as unvetted; the operator's rule says not to dismiss them, so they are listed for review, not rejected.
- Exact in-window: dynamic NTK, LongRoPE factor switch, DCA (up to c). Not exact: static YaRN, static NTK, linear PI.

### 4. Does this change the recommendation?

The recommendation (D now, A as in-process follow-up) stands, with these changes:

1. **D stays first.** It is also what the evidence implies for production: nobody ships an in-process re-rope, and the vendor itself says to enable YaRN only for deployments that need it.
2. **New option F: admission-time factor choice (the vLLM-longrope and HF pattern).** Choose static-native vs extended per request from prompt length + max_tokens at admission; no re-rope needed because the whole sequence uses one set. This is design A without the mid-sequence switch, so it needs only the per-token `ff` tensor, the Q scale for mscale, and the admission rule. A request that crosses the threshold mid-generation either gets a margin (route extended if prompt + max_tokens > N) or is truncated at N. This removes the hard part of A (re-rope, KV-shift and MTP mirroring of a switch).
3. **Re-ranked order:** D (zero kernel risk, exact) > F (one process, medium-low risk, exact in-window, no re-rope) > E1 as a diagnostic > A with re-rope (no prior art, upstream considers it hard) > C DCA (proven by Qwen2.5-1M, but unfinished, slower, no MTP) > B (subsumed by F or A).
4. **F's open question:** the upstream "allocated length versus actual length" defect in llama.cpp shows the failure mode: per-context selection by allocated size is wrong. F must select per sequence, not per context.
5. **Minimal first experiment unchanged** (E1 three-arm A/B), plus one more cheap read: confirm in vLLM source how the Phi3 long-prompt offset chooses the cache per request, since that is the closest model for F.
