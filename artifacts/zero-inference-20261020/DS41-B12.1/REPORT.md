# DS41-B12.1 (2026-10-20) - read-only source anchors
Revs: OFF = /mnt/raid0/llm/models/deepseek-ai/DeepSeek-V4.1-Flash/inference/model.py (1309 lines, sha256 prefix 4e9ae23620ed; the Sept official copy the task's line numbers refer to).
OFF17 = /mnt/raid0/llm/tmp/dive-deepinfer-1017/inference/model.py (1312 lines, sha e5decd76fe70; the 1017 copy, +3 lines so head collapse is 1271 there).
DI = /mnt/raid0/llm/tmp/dive-deepinfer-main/src/deepinfer/model_executor/models/deepseek.py.
OURS = llama.cpp champion dd3d9721c (= ak/champion/llama-cpp-ffc1bac82eec tip). v10 ffc1bac82 has NO src/models/deepseek41.cpp (git show -> absent), so anchors are champion-only.
All verified by reading the files/`git show dd3d9721c:<path>`.

## DS41-B12 (a) head collapse (no output_hc_*)
Head collapse = hc_pre of the LAST layer's FFN pre-mix, then norm+head.
- OFF model.py:1268 `h = layer.hc_pre(h, pre_mix)` (then :1269 `logits = self.head(self.norm(h))`); OFF17 :1271.
- DI deepseek.py:229-232 (`if self.hc_shifted: mhc_pre_apply_mix(hidden_states, residual.pre_layer_mix) else flatten`).
- OURS src/models/deepseek41.cpp:1372-1374 @ dd3d9721c (comment cites model.py:1268; `build_hc_pre(inpL, pre_mix, -1)`; pre_mix carried and row-selected at :1369).
MATCH.
## (b) layer-20 compressor gate absent
- OFF model.py:461-462 `if ratio == 1: return self.norm(self.wkv(x))` (wgate only created for ratio>1, :446-447). Single-token softmax = 1, so ungated projection is exact.
- OURS deepseek41.cpp:314-315 (wgate TENSOR_NOT_REQUIRED, "layer 20 has no compressor gate"), :938 `GGML_ASSERT((ratio == 1) == (layer.attn_comp_wgate == nullptr))`.
MATCH.
## (c) ratio 1/2 geometry
- OFF model.py:473-475 (unflatten (-1, ratio), softmax over group dim, sum): non-overlapping, no ape term (:464-465 adds nothing to score). compress_ratios default (0,2,2,1,1,0) at :81.
- OURS deepseek41.cpp:310 `coff = ratio == 4 ? 2 : 1`, :316-317 (no attn_compressor_ape), :653-655 non-overlapping `ratio*n_blocks` rows, :942-943 no absolute-position term.
MATCH.
=> Proposed completion line: `- [x] DS41-B12 - closed 2026-10-20 by DS41-B12.1: (a) model.py:1268 / deepseek.py:229-232 / deepseek41.cpp:1372 @ dd3d9721c; (b) model.py:461-462 / deepseek41.cpp:314-315,938; (c) model.py:473-475 / deepseek41.cpp:310,653-655,942.` and tick DS41-B12.1.

## DS41-B11 anchors (RoPE and norm deltas)
- Interleaved adjacent pairs: OFF model.py:392-404 (`unflatten(-1,(-1,2))` view_as_complex). OURS: DEEPSEEK41 returns LLAMA_ROPE_TYPE_NORM (src/llama-model.cpp:2624..2643 group @ dd3d9721c; adjacent-pair, not NEOX). MATCH.
- Inverse rotation on attention output: OFF model.py:781 `apply_rotary_emb(o[..., -rd:], freqs_cis, True)`; OURS deepseek41.cpp:1213 `ggml_rope_ext_back`. MATCH.
- Last 64 of 512 dims: OFF rope_head_dim (:74 is the demo default 32; released value from config) - not re-verified from config here.
- YaRN only on compressed layers at compress_rope_theta, pure SWA theta 10000 YaRN off: OFF model.py:680-687; OURS deepseek41.cpp:1133-1138. MATCH.
- rms_norm_eps 1e-20: OFF :75 (norm_eps default 1e-20), RMSNorm :346; ours reads LLM_KV_ATTENTION_LAYERNORM_RMS_EPS (deepseek41.cpp:86) - value comes from the GGUF, not source-verified here.
- DIVERGENCE (the only open piece): top-k renorm epsilon. OFF model.py:825 `weights.sum() + 1e-20  # not norm_eps, matches training`; OURS uses the shared build_moe_ffn clamp `weights_sum = ggml_clamp(..., 6.103515625e-5, INFINITY)` at src/llama-graph.cpp:2260 @ dd3d9721c (additive 1e-20 vs clamp-at-F16-min; differs only when the sum of selected weights < 6.1e-5, otherwise identical). 
Verdict: DS41-B11 stays open ONLY for this epsilon (dormant trigger per task). Pairs with RoPE/norm bullets citable as above.
