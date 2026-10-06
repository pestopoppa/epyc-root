# CTX-2 / CTX-KSHIFT verdicts (2026-10-06)

Base: production-consolidated-v10 `ffc1bac82` (untouched). Experimental branch `llama.cpp-experimental-kshift-probe-20261006`, worktree `/mnt/raid0/llm/worktrees/llama-kshift-probe-20261006`.
Test: `tests/test-kshift-probe.cpp` (standalone ggml, CPU backend, builds the K-shift ops as `build_rope_shift`/`build_graph_shift` do; H2 uses the live `llama_kv_cells`). Fixture: head 256, n_rot 64, NEOX, base 1e7, 2 heads x 8 cells, normal(0,1) seed 1234, orig ctx 262144, YaRN fs 0.5 ext 1 attn 1, plus no-YaRN control. All cells checked. Log: `<wt>/build-probe-run.log` (stock source) and `build-probe-run-fixed.log` (fixes in lib).
Runs under region-lock q1, taskset 24-47.

## Verdicts: all three CONFIRMED. K-shift is NOT safe to adopt as the re-rope primitive at ffc1bac82 (safe only with the three branch fixes below; the fixes are unit-verified, not model-verified).

### H1 CONFIRMED: K-shift re-applies YaRN mscale each shift
Site (ffc1bac82): `src/llama-kv-cache.cpp:1992` `const auto & yarn_attn_factor = cparams.yarn_attn_factor;` passed to `ggml_rope_ext` at :2012/:2022 with `yarn_ext_factor`. ggml applies `mscale *= 1.0f + 0.1f * logf(1.0f / freq_scale)` when ext_factor != 0 (`ggml/src/ggml-cpu/ops.cpp:6181`), and the forward K already carries it.
Measured (norm of rotated dims, shifted vs fresh at final position, d=37 per shift):
- no-YaRN: 1.00000 for n=1..4 (f16 and f32).
- YaRN: n=1 1.06931, n=2 1.14342, n=3 1.22270, n=4 1.30747 (= 1.0693^n; f16 and f32 identical). Whole-head norm 1.0191 .. 1.0914; max-abs error vs fresh up to 1.2.
Fix (branch): shift uses attn_factor = 1/(1+0.1 ln(1/freq_scale)) when ext_factor != 0 else 1.0 (pure rotation). Fix-formula check: ratio 1.00000 for n=1..4, max-abs 1.1e-5..2.0e-5 (f32 noise).
Also hits server context-shift under YaRN.

### H2 CONFIRMED: pos_div records the shift with the wrong sign
Site: `src/llama-kv-cells.h:478` `shift[i] += p_old - pos[i];` vs pos_add `shift[i] += d` (:447). `set_input_k_shift` passes `get_shift` straight to rope (`llama-kv-cache.cpp:1549`), so the delta must be new - old = floor(p/G) - p (negative).
Measured (G=2, 8 cells at positions 10,13,...,31, no-YaRN, f32): get_shift = +5,+7,+8,+10,+11,+13,+14,+16 vs expected -5,-7,-8,-10,-11,-13,-14,-16. Max-abs vs fresh K at floor(p/G): 4.711 as shipped; 1.699e-6 with the expected delta (and with the negated get_shift). pos_add(-5) control: 1.445e-6.
Note: the plan's 1e-6 threshold is below the fp32 floor of the control itself (1.4e-6); the defect (4.7) is 6 orders above it and the fixed value equals the control floor.
Fix (branch): `shift[i] += pos[i] - p_old;`. Post-fix error 1.699e-6 (= control floor). Other `get_shift` consumer (`llama-kv-cache.cpp:515`, seq_cp-style copy) just copies the value; unaffected.

### H3 CONFIRMED: Hadamard nrot comes from the full head dim, applied to the n_rot-wide view
Sites: `llama-kv-cache.cpp:1454-1461` build_input_k_rot derives nrot from `n_embd_head_k_all` (256 -> nrot 256); `:2086-2092` build_graph_shift views only `n_rot` (64) dims of each head (`n_rot, n_head_kv, ...`); `:2006-2018` build_rope_shift does cast -> `llama_mul_mat_hadamard(rot 256)` -> rope -> hadamard -> `ggml_cpy(tmp, cur)`. The cache holds H256(rope(k)) over the whole head, so Hadamard on a 64-wide slice regroups 4 unrelated (head,cell) rows into one 256 vector.
Measured (q8_0, no-YaRN, d=37, error vs float truth in the Hadamard domain, plain q8_0 roundtrip rms 5.318e-3 / max 1.603e-2):
- shipped (n_rot view, host-emulated store): rms 0.4502 (84.7x), max-abs 1.936 (120.8x). Threshold 2x.
- candidate full-head view: rms 7.57e-3 (1.42x), max-abs 3.34e-2 (2.08x; double quantization, marginal at the 2x line).
- f16 control (non-quantized path): max-abs 1.8e-3 vs f16 roundtrip 9.8e-4.
Second defect found on the way: the shipped graph's `ggml_cpy(tmp, cur)` writes a NON-CONTIGUOUS q8_0 destination; CPU backend aborts: `ggml/src/ggml-cpu/ops.cpp:323` GGML_ABORT("not implemented") (`dup_to_q` requires `ggml_is_contiguous(dst)`, :294). So a quantized-K shift with n_rot < head dim aborts the process on CPU. The full-head view is contiguous and runs.
Fix (branch): when `k_rot && n_embd_nope == 0 && quantized K`, view the full head (rope still rotates only n_rot dims). MLA layout (n_embd_nope > 0) with k_rot is NOT handled (rope dims offset inside the Hadamard span); out of scope, still defective.

## Branch commits (parent ffc1bac82)
- db306f54a tests: probe (+ f9cb7cd32 test follow-up, tip)
- 4c9f61d96 kv-cells: pos_div sign (H2)
- 800aee1da kv-cache: pure-rotation attn_factor (H1)
- 64cd14912 kv-cache: full-head view for Hadamard K (H3)
libllama compiles with all fixes. Not done: end-to-end model run of a shift (no inference per brief); real graph path for H1/H3 is mirrored by the test, not executed through `llama_kv_cache`.

## Outcome rule
Gate G2: K-shift primitive may be adopted only from this branch (all three fixed, unit-verified) after a model-level shift test; stock v10 K-shift must not be used under YaRN or quantized K.
