> **DRAFT. Operator files; nothing has been posted.** Base: production-consolidated-v10 `ffc1bac82` (fetch not permitted from this session). **Verify on master before filing.**
> Source of findings: `/mnt/raid0/llm/tmp/yarn-inert-design-20261006/CTX2_KSHIFT.md`; probe `tests/test-kshift-probe.cpp` on branch `llama.cpp-experimental-kshift-probe-20261006` (db306f54a, f9cb7cd32).

# kv-cache: K-shift re-applies the YaRN mscale on every shift

## Affected code (ffc1bac82)
- `src/llama-kv-cache.cpp:1992` `const auto & yarn_attn_factor = cparams.yarn_attn_factor;` passed to `ggml_rope_ext` at :2012 / :2022 together with `yarn_ext_factor`.
- ggml multiplies cos/sin by `1 + 0.1*ln(1/freq_scale)` when `ext_factor != 0` (`ggml/src/ggml-cpu/ops.cpp:6181`). The cached K already carries that factor from the forward pass, so each shift compounds it. Also affects server context-shift under YaRN.

## Minimal repro

Standalone ggml test `tests/test-kshift-probe.cpp` (CPU backend; builds the K-shift ops as `build_rope_shift`/`build_graph_shift` do). Fixture: head 256, n_rot 64, NEOX, base 1e7, 2 heads x 8 cells, normal(0,1) seed 1234, orig ctx 262144, YaRN freq_scale 0.5 ext_factor 1 attn_factor 1, plus a no-YaRN control. Compare shifted K against K freshly roped at the final position.

## Expected vs actual
Norm of rotated dims, shifted vs fresh, after n shifts:
- no-YaRN: expected 1.0, actual 1.00000 for n=1..4 (f16 and f32).
- YaRN: expected 1.0, actual 1.06931 / 1.14342 / 1.22270 / 1.30747 for n=1..4 (= 1.0693^n; f16 and f32 identical). Max-abs error vs fresh up to 1.2.
- With fix: ratio 1.00000 for n=1..4, max-abs 1.1e-5..2.0e-5 (f32 noise).

Unit-verified only; not run end to end through a model.

## Proposed fix (commit 800aee1da on experimental branch)

```diff
diff --git a/src/llama-kv-cache.cpp b/src/llama-kv-cache.cpp
index c0715cb10..781463e7d 100644
--- a/src/llama-kv-cache.cpp
+++ b/src/llama-kv-cache.cpp
@@ -1989,7 +1989,9 @@ ggml_tensor * llama_kv_cache::build_rope_shift(
     const auto & yarn_ext_factor  = cparams.yarn_ext_factor;
     const auto & yarn_beta_fast   = cparams.yarn_beta_fast;
     const auto & yarn_beta_slow   = cparams.yarn_beta_slow;
-    const auto & yarn_attn_factor = cparams.yarn_attn_factor;
+    // The cached K already carries the YaRN magnitude scale (attn_factor * (1 + 0.1*ln(1/freq_scale)) when ext_factor != 0).
+    // A shift must be a pure rotation, so cancel what ggml_rope_ext applies on its own and drop the rest (factor 1.0).
+    const float yarn_attn_factor = yarn_ext_factor != 0.0f ? 1.0f / (1.0f + 0.1f * logf(1.0f / freq_scale)) : 1.0f;
 
     const auto & n_rot     = hparams.n_rot(il);
     const auto & rope_type = hparams.rope_type == LLAMA_ROPE_TYPE_MROPE || hparams.rope_type == LLAMA_ROPE_TYPE_IMROPE
```
