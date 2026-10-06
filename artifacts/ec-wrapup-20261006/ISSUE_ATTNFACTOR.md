> **DRAFT. Operator files; nothing has been posted.** Base: production-consolidated-v10 `ffc1bac82` (fetch not permitted from this session). **Verify on master before filing.**
> Source of findings: `/mnt/raid0/llm/tmp/yarn-inert-design-20261006/CTX2_KSHIFT.md`; probe `tests/test-kshift-probe.cpp` on branch `llama.cpp-experimental-kshift-probe-20261006` (db306f54a, f9cb7cd32).

# context: user --yarn-attn-factor is silently discarded when yarn_ext_factor != 0

## Affected code (ffc1bac82)
- `src/llama-context.cpp:113` honours `params.yarn_attn_factor >= 0`, but the block at `:194` (`if (cparams.yarn_ext_factor != 0)`) then unconditionally overwrites `cparams.yarn_attn_factor` (:215 / :220, scaled at :228), so the CLI value (`common/arg.cpp` `--yarn-attn-factor`, default -1 = unset, `common/common.h`) never takes effect under YaRN (ext_factor defaults to 1 for YARN rope scaling).
- Hence there is no way to override the derived mscale; the flag is inert exactly when YaRN is active.

## Minimal repro
Run any YaRN-scaled model (`--rope-scaling yarn --rope-scale 2 --yarn-orig-ctx N`) with `--yarn-attn-factor 1.0` and with `--yarn-attn-factor 2.0`: the effective `cparams.yarn_attn_factor` is identical (the derived value), and so are the logits. (Read from code; no synthetic test or measured numbers exist for this one yet. Add a logits comparison before filing.)

## Expected vs actual
- Expected: an explicit value (>= 0) is used verbatim; the kernel still multiplies in `1 + 0.1*ln(1/freq_scale)`.
- Actual: the value is discarded whenever `ext_factor != 0`.
- Default path (flag not passed, value -1) is unchanged by the fix: the guard `params.yarn_attn_factor < 0.0f` is true, so the derived computation runs as before. Note `0.0` now means an explicit zero rather than being overwritten.

## Proposed fix (commit 720a98e2a on experimental branch)

```diff
diff --git a/src/llama-context.cpp b/src/llama-context.cpp
index c566e71fc..b599164ed 100644
--- a/src/llama-context.cpp
+++ b/src/llama-context.cpp
@@ -191,7 +191,8 @@ llama_context::llama_context(
         cparams.yarn_ext_factor = rope_scaling_type == LLAMA_ROPE_SCALING_TYPE_YARN ? 1.0f : 0.0f;
     }
 
-    if (cparams.yarn_ext_factor != 0) {
+    // a user-supplied --yarn-attn-factor (>= 0) is taken verbatim: do not overwrite it with the derived value below
+    if (cparams.yarn_ext_factor != 0 && params.yarn_attn_factor < 0.0f) {
         static auto get_mscale = [](float scale, float mscale) {
             return scale <= 1.0f ? 1.0f : (0.1f * mscale * logf(scale) + 1.0f);
         };
```
