# CTX-JETLONG-PROTO: synthetic tests (T1/T2/T3)

**Code:**
- Test: `tests/test-jetlong-proto.cpp`, committed in `b216a5deb` on `llama.cpp-experimental-jetlong-proto-20261006`.
- It is built against the libllama that contains the implementation (`a2e129fcc`).

**Run** (CPU 0-23 under region-lock q0, 24 threads):
`region-lock run --cpu-list 0-23 --role build --tag jetlong-proto -- bash -c "... taskset -c 0-23 build-cpu/bin/test-jetlong-proto -t 24 --long"`

**Logs:**
- Full output: `test-run.log` in this directory, a copy of `<wt>/test-run3.log`.
- Result: **ALL PASS (0 failures)**.

**Build:**
- CMake flags copied from `llama-yarn-mscale-20261006/build-cpu/CMakeCache.txt` (Release, shared, GGML_NATIVE, OpenMP, llamafile, CPU repack, no GPU), plus `LLAMA_BUILD_TESTS=ON`.

## Harness
**What it mirrors:** `build_attn` (KV path) for one qwen35moe full-attention layer:
- Head 256, 16 Q heads, 2 KV heads.
- IMRoPE with n_rot 64, sections [11,11,10,0], base 1e7.
- For quantized K: K Hadamard 256 and V Hadamard 64.
- Store via `set_rows`.
- Stock `flash_attn_ext` with F32 precision.

**What it drives:** the same libllama functions as the server:
- `llama_jetlong_plan_ubatch`
- `llama_jetlong_cell_state::collect`
- `llama_jetlong_fill_inputs`
- `llama_jetlong_build_attn`

**Data:** q, k and v are a deterministic N(0,1) function of (seq, pos); every row is checked.

**Window:**
- The small cases use w = 256 and w0 = 32, so that L crosses w, 2w, 3w and 4w cheaply. The code path does not depend on w.
- The `--long` cases use the real geometry, w = 262144 and w0 = 2048. The cache is host-filled up to L - 1, then decoded.

**Reference:** Jet-Long Eq. 1 in double, with the semantics of `_reference_jetlong_decode` (`cute_jetlong_backend.py:93`):
- A near base branch and a grouped distant branch, each with its own (max, sum, acc), merged by LSE weights.
- K is taken from the actual cache content: dequantized, with the Hadamard undone. This is the reference's cached base K (M:336).
- Three variants:
  - **exact**: double angles; the grouped Q is computed directly at floor(p/G), not by composition.
  - **fp32-angle**: mirrors ggml's fp32 theta recurrence, with the correction applied to the fp32 base-roped Q.
  - **Q-q8-aware**: attribution only. The two q8_0 dot products see the q8_0-rounded query, as ggml does.

**Metric:** rel = max |out - ref| / max |ref| over all checked rows.

## T1: in-window identity (flag on vs off), rule max-abs exactly 0

| case | config | result |
|---|---|---|
| T1a np 1, prefill 0..191 (3 x 64) + decode to L = 256 = w | q8_0+Hadamard, f16 | max-abs **0** / 256 rows, 0 active ubatches |
| T1b np 4 mixed: interleaved multi-seq prefill (13 ubatches) + 40 four-token decode ubatches | q8_0+Hadamard, f16 | max-abs **0** / 724 rows, 0 active |
| T1c np 4, seq 0 ABOVE native (to 360), seqs 1-3 in-window, co-batched in prefill and decode | q8_0+Hadamard, f16 | max-abs **0** / 626 in-window rows, 26 active ubatches |

T1a and T1b hold by construction: no Jet-Long node is built. T1c is the non-trivial case. The `get_rows` splice keeps the stock
rows bit-identical even though the ubatch runs the Jet-Long graph. Identity at model level on the :8070 checkpoint is gate A of
LONGCTX_PLAN.md.

## T2: above native vs the reference, tolerance 1e-3 relative (f32)

| case | rows | rel max-abs vs exact ref | vs fp32-angle ref | stock path on the same rows vs its ref |
|---|---|---|---|---|
| prefill (64/ub) + decode to L = 1124, G up to 5, K/V f32 | 868 | **1.26e-6** | 1.9e-7 | 3.1e-4 (FA casts K/V to f16) |
| same, K/V f16 | 868 | **7.55e-5** | 7.55e-5 | 3.1e-4 |
| same, K/V q8_0 + Hadamard | 868 | 1.55e-3 | 1.55e-3 | 9.5e-4 |
| same, q8_0, vs Q-q8-aware ref | 868 | **1.82e-4** | | 2.9e-5 |
| real geometry decode L = 300001 (G = 2), f16 | 2 x 16 heads | 1.63e-4 | **4.39e-5** | |
| real geometry L = 300001 (G = 2), q8_0 + Hadamard | 2 | 1.28e-3 | 1.26e-3 | (Q-q8-aware: **1.34e-6**) |
| real geometry L = 600001 (G = 3), f16 | 2 | 6.82e-4 | **5.94e-5** | |

- **Gates:**
  - f32/f16 pass the strict 1e-3.
  - q8_0 is gated at max(1e-3, 2 x the stock path's own error on the same rows) = 1.9e-3. It passes at 1.55e-3.
  - q8_0 is also gated at 1e-3 against the Q-q8-aware reference, where it passes at 1.8e-4 and 1.3e-6.
- **Reading:**
  - The Jet-Long arithmetic matches Eq. 1 to 1e-6 (f32) or 1e-4 (f16 inputs).
  - In q8_0 mode, the excess over 1e-3 against the exact reference is the q8_0 rounding of Q in ggml's q8_0 x q8_0 dot products. Stock has the same error class, 9.5e-4 on the same rows.
- **Depth effect:** the exact-angle error grows with depth (1.6e-4 at 300K, 6.8e-4 at 600K, f16) while the fp32-angle error stays at about 5e-5. This is the fp32 RoPE angle floor of llama.cpp, shared by the stock base RoPE.

## T3: epoch crossing (G changes mid-sequence), cached per G-epoch vs uncached
Schedule:
- Prefill to 500 (G = 2).
- Decode 30 steps across L = 513 (G 2 -> 3).
- A prefill ubatch straddling 768 (G -> 4).
- Decode 20 steps.
- Prefill to 1010, then decode 30 steps across 1025 (G 4 -> 5).

The schedule makes 4 epoch changes in total.

| config | cached vs uncached | rows recomputed (cached) | cached vs exact ref |
|---|---|---|---|
| q8_0 + Hadamard | max-abs **0** | <= 64 per steady ubatch, 1025 at an epoch change | 1.55e-3 (tol 1.9e-3) |
| f16 | max-abs **0** | <= 64 / 1025 | 7.55e-5 |

T2-long also shows the epoch build at the first above-native step: 300000 / 600000 rows, then 1 row on the next step.

## Not covered by these tests
- Model-level identity, MTP acceptance and needle recall: LONGCTX_PLAN.md.
- The `kv_unified = false` multi-stream path and the FA-off (transposed V) path.
- Abort/rollback of a compute.
- The `llama_kv_cache` / `can_reuse` wiring: it is compiled, and the test drives the same functions through a harness, not through `llama_context`.
