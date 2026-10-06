> **DRAFT. Operator files; nothing has been posted.** Base: production-consolidated-v10 `ffc1bac82` (fetch not permitted from this session). **Verify on master before filing.**
> Source of findings: `/mnt/raid0/llm/tmp/yarn-inert-design-20261006/CTX2_KSHIFT.md`; probe `tests/test-kshift-probe.cpp` on branch `llama.cpp-experimental-kshift-probe-20261006` (db306f54a, f9cb7cd32).

# kv-cache: Hadamard K-shift for quantized K uses full head dim for nrot but the n_rot-wide view; CPU quantized shift aborts

## Affected code (ffc1bac82)
- `src/llama-kv-cache.cpp:1454-1461` `build_input_k_rot` derives nrot from `n_embd_head_k_all` (256 -> nrot 256).
- `:2086-2092` `build_graph_shift` views only `n_rot` (64) dims per head; `:2006-2018` `build_rope_shift` does cast -> `llama_mul_mat_hadamard(rot 256)` -> rope -> hadamard -> `ggml_cpy(tmp, cur)`. The cache holds H256(rope(k)) over the whole head, so a Hadamard on a 64-wide slice regroups 4 unrelated (head, cell) rows into one 256 vector.
- Second defect: `ggml_cpy(tmp, cur)` writes a NON-CONTIGUOUS q8_0 destination; the CPU backend aborts at `ggml/src/ggml-cpu/ops.cpp:323` (`GGML_ABORT("not implemented")`; `dup_to_q` requires `ggml_is_contiguous(dst)`, :294). So a quantized-K shift with n_rot < head dim aborts the process on CPU.

## Minimal repro

Standalone ggml test `tests/test-kshift-probe.cpp` (CPU backend; builds the K-shift ops as `build_rope_shift`/`build_graph_shift` do). Fixture: head 256, n_rot 64, NEOX, base 1e7, 2 heads x 8 cells, normal(0,1) seed 1234, orig ctx 262144, YaRN freq_scale 0.5 ext_factor 1 attn_factor 1, plus a no-YaRN control. Compare shifted K against K freshly roped at the final position.

H3 variant: q8_0 K, no-YaRN, d=37, error vs float truth in the Hadamard domain.

## Expected vs actual
Plain q8_0 roundtrip: rms 5.318e-3, max 1.603e-2 (acceptance threshold 2x).
- Shipped (n_rot view, host-emulated store): rms 0.4502 (84.7x), max-abs 1.936 (120.8x); and the real graph aborts on CPU (above).
- With fix (full-head view, contiguous): rms 7.57e-3 (1.42x), max-abs 3.34e-2 (2.08x, double quantization, marginal at the 2x line).
- f16 control: max-abs 1.8e-3 vs f16 roundtrip 9.8e-4.

Caveat: MLA layout (n_embd_nope > 0) with k_rot is NOT handled by this fix (rope dims sit at an offset inside the Hadamard span) and remains defective. Unit-verified only.

## Proposed fix (commit 64cd14912 on experimental branch)

```diff
diff --git a/src/llama-kv-cache.cpp b/src/llama-kv-cache.cpp
index 781463e7d..fa34c84cb 100644
--- a/src/llama-kv-cache.cpp
+++ b/src/llama-kv-cache.cpp
@@ -2086,9 +2086,14 @@ ggml_cgraph * llama_kv_cache::build_graph_shift(llm_graph_result * res, llama_co
 
         ggml_tensor * rope_factors = model.get_rope_factors(cparams, il);
 
+        // With the attention Hadamard rotation (quantized K) the cache holds H(rope(k)) with H spanning the FULL head, so the
+        // shift must dequantize, un-rotate and re-rotate whole heads; a view of the n_rot dims only mixes unrelated rows
+        // and also makes the quantized ggml_cpy destination non-contiguous (aborts on CPU). rope still rotates only n_rot dims.
+        const bool full_head = inp->k_rot && n_embd_nope == 0 && ggml_is_quantized(layer.k->type);
+
         ggml_tensor * k =
             ggml_view_3d(ctx, layer.k,
-                n_rot, n_head_kv, get_size()*n_stream,
+                full_head ? n_embd_head_k : n_rot, n_head_kv, get_size()*n_stream,
                 ggml_row_size(layer.k->type, n_embd_head_k),
                 ggml_row_size(layer.k->type, n_embd_k_gqa),
                 ggml_row_size(layer.k->type, n_embd_nope));
```
