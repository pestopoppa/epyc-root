> **DRAFT. Operator files; nothing has been posted.** Base: production-consolidated-v10 `ffc1bac82` (fetch not permitted from this session). **Verify on master before filing.**
> Source of findings: `/mnt/raid0/llm/tmp/yarn-inert-design-20261006/CTX2_KSHIFT.md`; probe `tests/test-kshift-probe.cpp` on branch `llama.cpp-experimental-kshift-probe-20261006` (db306f54a, f9cb7cd32).

# kv-cells: pos_div records the K-shift with the wrong sign

## Affected code (ffc1bac82)
- `src/llama-kv-cells.h:478` (`pos_div`): `shift[i] += p_old - pos[i];` while `pos_add` does `shift[i] += d` (:447), i.e. new - old.
- `set_input_k_shift` hands `get_shift()` straight to rope (`src/llama-kv-cache.cpp:1549`) as a delta to add, so the delta must be new - old = floor(p/G) - p (negative). The other `get_shift` consumer (`llama-kv-cache.cpp:515`) just copies the value and is unaffected.

## Minimal repro

Standalone ggml test `tests/test-kshift-probe.cpp` (CPU backend; builds the K-shift ops as `build_rope_shift`/`build_graph_shift` do). Fixture: head 256, n_rot 64, NEOX, base 1e7, 2 heads x 8 cells, normal(0,1) seed 1234, orig ctx 262144, YaRN freq_scale 0.5 ext_factor 1 attn_factor 1, plus a no-YaRN control. Compare shifted K against K freshly roped at the final position.

H2 variant: uses the live `llama_kv_cells`, G=2, 8 cells at positions 10,13,...,31, no-YaRN, f32.

## Expected vs actual
- get_shift actual: +5,+7,+8,+10,+11,+13,+14,+16; expected: -5,-7,-8,-10,-11,-13,-14,-16.
- Max-abs error vs fresh K at floor(p/G): 4.711 as shipped; 1.699e-6 with fix (equals the pos_add(-5) control floor 1.445e-6, the fp32 floor).

## Proposed fix (commit 4c9f61d96 on experimental branch)

```diff
diff --git a/src/llama-kv-cells.h b/src/llama-kv-cells.h
index 5167c037d..19d36dcb3 100644
--- a/src/llama-kv-cells.h
+++ b/src/llama-kv-cells.h
@@ -475,7 +475,7 @@ public:
         seq_pos_rm(i);
 
         pos[i]   /= d;
-        shift[i] += p_old - pos[i];
+        shift[i] += pos[i] - p_old; // delta to ADD to the cached position (new - old), same sign convention as pos_add
 
         seq_pos_add(i);
 
```
