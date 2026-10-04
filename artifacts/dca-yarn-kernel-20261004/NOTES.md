# dca-yarn-kernel-20261004: notes

Operator-approved (2026-10-04) experimental llama.cpp work. Production v10 was not touched, and neither was any server or the GPU.

**Experimental clone:** `/mnt/raid0/llm/llama.cpp-experimental-fa-maskskip-20261003`, with two new worktrees, both on champion `90c12df42`.

## Item 1: Flash-Next fused decode ignored YaRN (FIXED)

**Location:** worktree `/mnt/raid0/llm/llama.cpp-experimental-fused-yarn-20261004`, branch `experimental/fused-yarn-20261004`, pushed to `fork`.

**Commits:**
- `5bfdcd18c` qwen4exp: the fused decode takes the context's rope/YaRN parameters.
  - `fused_decode(..., const llama_cparams &, ...)` builds `FusedRopeParams` from `n_ctx_orig_yarn`, `rope_freq_base`, `rope_freq_scale` and `yarn_*`. Those are the members `llm_graph_context` reads.
  - Before the fix it hardcoded freq_base 1e7, freq_scale 1, ext 0, attn 1 and n_ctx_orig 0. **freq_base was hardcoded too**, so `--rope-freq-base` was also ignored, not only YaRN.
  - The fused MoE now accepts a merged `ffn_gate_up_exps`; the synthetic model has one, and it used to segfault on the null `ffn_up_exps`.
  - `llama_n_fused_decode()` (llama-ext.h) counts the steps the fused path served.
  - Test: `tests/test-qwen4exp-fused-rope.cpp`.
- `6c126e975` gates two per-token debug leftovers behind `GGML_FUSED_DECODE_TRACE`. One printed a stderr hex line on every token; the other wrote `/tmp/qwen4exp-builds/f_res_hc.bin` and `f_embd_tok.bin` on every token.

**Test design.**
- **Observable.** The synthetic model has weights around 1e-2, which makes the attention softmax nearly uniform, so the logits cannot see the rope (graph-vs-graph sensitivity is about 1e-15). The test therefore compares **the roped K rows each decode step wrote to the cache**, fused against graph, along with the indexer rows and the logits.
- **Guards.**
  - Every decode step must have been fused (56/56).
  - The graph's own K under YaRN and under freq_base must differ from native: nmse 0.69 and 1.09.

**Results.** Logs: `fused-test-fixed.log`, `fused-test-champion-params.log`.

| | K nmse (yarn / freq-base) | logits nmse | verdict |
|---|---|---|---|
| fixed | 6e-9 / 8e-9 | 1.7e-11 | OK |
| old hardcoded params | 0.53 / 1.09 | 1.7e-11 | FAIL; native still OK |

Seed 7: all OK.

**Not done.**
- No GPU work: the fused path is CPU-only.
- At larger synthetic weight scales the fused path diverges from the graph regardless of rope (logits nmse 0.02–3.5 at weight std 0.05–0.3, norms around 1). This is a pre-existing fidelity gap of the INF-64 transcription on non-production shapes. It is not caused by this fix and is outside this item's scope. It is worth knowing before anyone turns `GGML_FUSED_DECODE_OFF` off in production.

## Item 2: Dual Chunk Attention

See `DESIGN-DCA.md`.
- Worktree: `/mnt/raid0/llm/llama.cpp-experimental-dca-20261004`, branch `experimental/dca-20261004`.
- Upstream and vLLM research: `upstream-and-vllm-dca-notes.md`, with `ref-sources/`.
- GPU: `gpu_slot_dca.sh` (`prep` = HIP build on CPU, region-locked; `slot` = needs the GPU).
- Real-model CPU check: `real_model_ppl_cpu.sh`.

## Item 3 (coordinator add-on): FA-INT64-OFFSET, the int32 mask offset in WMMA FA (probable llama.cpp #27090)

**Location.** Worktree `/mnt/raid0/llm/llama.cpp-experimental-fa-int64-20261004`, branch `experimental/fa-int64-offset-20261004` (on the champion), pushed to `fork`.

**Commits** (all tagged `[FA-INT64-OFFSET]`):
- **`6152cdf7a`** fixes the WMMA kernel. In `ggml/src/ggml-cuda/fattn-wmma-f16.cu:104`, `maskh = mask + nb33*(sequence % ne33) + nb31*ic0` multiplied int32 by int. The fix applies `int64_t(nb31)*ic0`, and does the same for `nb12*(head/gqa)` (`:102-103`) and `nb02*head + nb01*ic0` (`:101`).
  - The half-accumulator path indexed the mask as `mask2[(j*ne11 + k_VKQ_0)/2 + k]`, using ne11 as the row stride (`:304`). It now uses `nb31`. This is identical whenever the mask row is n_kv wide, which is true of every llama.cpp mask.
- **`4f21c3477`** adds the test-backend-ops cases. `test_flash_attn_ext` gains `mask_ne0`, the mask row length.
  - Cases: D256, 4 KV heads, GQA 6, kv 512, 557056-wide mask rows (nb31 = 1088 KiB), nb ∈ {64, 2048} × prec ∈ {F32, default}. Filter with `-p mask_ne0`.
  - The ~2.1 GiB mask is the minimum, since the rows must exist. K/V/Q are tiny.
- **`0c4801127`** applies the same int64 products in tile, MMA and vec (`nb12*(head/gqa)`, `nb02*head`, `nb01*ic0`, vec `nb31*ic0`). `launch_fattn` now asserts that the int32 stride arguments do not truncate; nb32 is checked only when the mask has more than one plane.

**CPU proof** (`fa-int64/offset_proof.cpp`, `offset_proof.log`) enumerates n_kv in steps of 256 up to 2M, ub 512–4096, ncols 8–64:
- The 64-bit offsets equal the GPU's wrapped int32 offsets in every non-overflowing case; every difference is an overflow.
- First wrapped mask offset: **n_kv 526,592 at ub 2048**, 1,057,024 at ub 1024, 262,912 at ub 4096, none at ub 512.
- Identical at ≤ 524,288 with ub ≤ 2048, so 512K runs are bit-identical.
- K head offset (f16-converted K): first wrap at **1,398,272** (D256, 4 KV heads) and **599,296** (D256, 8 KV heads).

**Upstream master** (`11fe02151`, 2026-10-04) **removed rocWMMA FA**: `fa72aeccb`, "HIP: remove rocWMMA FlashAttention (#26046)", 2026-07-24. That commit is not in the champion's ancestry.
- Tile, vec and MMA on master still have the int32 products; master has not fixed them.
- **The v11 carry is**: `0c4801127` (tile/mma/vec, picks cleanly) + `git revert fa72aeccb` (applies cleanly on master) + `6152cdf7a` (picks cleanly on master+revert) + the test, ported to master's `test_flash_attn_ext` (new kv_view, v_is_view_of_k and n_kv_max params).
- This sequence is pushed as `fork/experimental/fa-int64-offset-master-20261004` (bcb9e0522, f8836bc05, 7195b7de3, a5df78514).
- The revert does not include the champion's local `db18f3937` (gfx90a eight-wave VKQ); the carry must add it.
- The master carry is not compile-verified here. The v11 audit arm builds master.

**GPU validation:** `fa-int64/gpu_slot_fa_int64.sh` (`prep` = HIP build, region-locked; `slot` = GPU).

## Process note

- After the coordinator's 05:0xZ message, every build and test ran through `rl.sh` (region-lock `--cpu-list 0-95`, taskset 160-183).
- From about 06:55Z, per the quadrant instruction, `rl.sh` locks **q2 only** (`--cpu-list 48-71`, `taskset -c 48-71`, nice 19, ionice idle). Nothing runs on 96-191 any more. Before the instruction, the item-1 builds and the early DCA builds were pinned to 160-183.
- My earlier item-1 builds (about 04:35–04:58Z, `-j24` in `build-cpu` and `build-cpu-dbg` of the fused worktree) ran **without** the region lock, at nice 19 on 160-183.
- The 05:00Z `gpu-20261004-338c5f84f` build the coordinator asked about was **not mine**.

## Real-model CPU check (Qwen2.5-0.5B f16, trained ctx 32K, wikitext-2, one window per arm): PARTIAL

- **Run dir:** `ppl-20261004T080609Z/`. Every arm is region-locked `--role bench`, q2 (48-71), 24 threads.
- **Measured:**

| arm | positions scored | PPL |
|---|---|---|
| native32k | 16K–32K, in distribution | 12.11 ± 0.25 |
| plain64k | 32K–64K, raw extrapolation | 13.63 ± 0.21 |
| yarn2 | 32K–64K, YaRN f2 | 12.63 ± 0.19 |
| **dca** (32768/4096) | 32K–64K | **12.46 ± 0.19** (17 min on CPU vs 6.5 for yarn2: v1 non-FA cost) |

- **Not yet run:** the `dca_t` (+ orig 32768) arm. Attempt at 11:32Z ended rc=143 (stopped externally for the v11fa GPU slot); re-run with the same OUT= command after "resume". One window each, so ±0.19 is per-token spread, not run-to-run noise; dca < yarn2 is suggestive, not significant.
  - The coordinator held all CPU lock claims for a GPU headline measurement, and no "resume" arrived by 09:10Z.
  - The coordinator stopped two earlier attempts: one ran during workspace-89's CPU window, and one was in the way of the fold gate's test-backend-ops.
- **To finish:** run `OUT=/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/ppl-20261004T080609Z /mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/real_model_ppl_cpu.sh` after "resume". It skips the finished arms; about 7 min per arm.

## INF-64 fused decode: divergence from the graph at non-production weight scales (triage note for V11 / Flash-Next owners)

**Read this before anyone unsets `GGML_FUSED_DECODE_OFF` in production.** Unrelated to the rope fix (it reproduces with the
native rope config and with the fix applied); found while making the rope test sensitive.

**What.** `qwen4exp` fused single-token decode (`src/models/qwen4exp-fused.cpp`) vs the graph decode of the same model and
cache, synthetic qwen4exp fixture (2 layers: 1 GDN + 1 QSA attention, MoE 2 experts, hc 4), 40-token graph prefill then 56
decode steps, worst per-step logits nmse:

| weights (non-norm std) | norm weights | logits nmse fused vs graph |
|---|---|---|
| 1e-2 (fixture default) | N(0, 1e-2) | 1.7e-11 (OK) |
| 0.1 | N(0, 1e-2) | 6.4e-7 |
| 1e-2 | N(1, 0.1) | 1.6e-2 |
| 1e-2 | N(2, 0.5) | 0.25 |
| 0.05 | N(1, 0.1) | 1.84 |
| 0.3 | N(1, 0.1) | 3.49 |
| 1.0 | N(1, 0.1) | **crash: "double free or corruption (out)"** |
| 1e-2 | attn_q/k_norm only N(1, 0.1) | 1.7e-11 (OK) |
| 1e-2 | all `attn_*` norms N(4, 0.5) | 4.6e-6 |

So the divergence needs realistic (≈1) norm weights on the *non-attention* norms together with larger activations. In the
confirmed repro the attention layer's K and indexer rows diverge too (nmse ~1.07), but the attention layer is layer 1 and its
input comes from layer 0 (GDN + MoE + hyper-connections), so the divergence originates before attention: it points at the
hyper-connection / GDN / MoE transcription (norm or residual mixing), not at attention or rope (with attention-only norms
raised, logits match to 4.6e-6). The `w=1.0` crash is a memory-safety bug in the fused path (heap
corruption), independent of accuracy. Production evidence so far (INF-64 bisection on the real IQ4_NL model) matched to
~1e-4 per layer, i.e. the real weights may sit in the benign regime, but this was never shown across inputs.

**Exact repro** (branch `experimental/fused-yarn-20261004`, worktree `/mnt/raid0/llm/llama.cpp-experimental-fused-yarn-20261004`):
```
# build (region-lock build, q2)
/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/rl.sh cmake --build build-cpu -j 24 --target test-qwen4exp-fused-rope
# run (region-lock bench, q2); knobs: QFR_W_STD = std of every non-norm tensor, QFR_NORM_MEAN/QFR_NORM_STD = norm tensors
cd build-cpu
/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/bench.sh env QFR_NORM_MEAN=1 QFR_NORM_STD=0.1 QFR_W_STD=0.05 ./bin/test-qwen4exp-fused-rope 1234
#  -> logits_nmse ~1.8 on every rope config (test FAILs on logits; K/idx rows still match)
/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/bench.sh env QFR_NORM_MEAN=1 QFR_NORM_STD=0.1 QFR_W_STD=1.0 ./bin/test-qwen4exp-fused-rope 1234
#  -> abort "double free or corruption (out)"
```
**Reconfirmed 11:2xZ with the committed `QFR_*` knobs** (`fused-divergence-repro.log`): unset -> all OK (logits 1.7e-11);
`w=0.05, norm N(1,0.1)` -> logits nmse 1.84, K 1.08, idx 1.06 on all three rope configs (FAIL); `w=1.0` -> abort "double
free or corruption (out)", rc 134. The other table rows are from the earlier identical-semantics variant (`T_*` knobs). Next triage steps: `GGML_FUSED_LAYER_CMP=1 GGML_FUSED_DECODE_TRACE=1` per-layer compare
(already in the fused code), then ASan build for the w=1.0 heap corruption.
