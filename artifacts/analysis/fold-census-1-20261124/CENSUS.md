# FOLD-CENSUS-1: conflict census of the next upstream bundle fold (2026-11-24, autokernel)

Zero compute. Read-only `git merge-tree --write-tree --name-only` in `/mnt/raid0/llm/llama.cpp` with a throwaway
`GIT_OBJECT_DIRECTORY` (tree untouched, nothing checked out, built or committed).
Ours = champion C21 `98ff8a42a`. Upstream = `origin/master` `2a487782f` (fetched; contains #32016 `32bdc3a89` and #30846 `660be5506`).
Merge base `a8dc0e326`: upstream is 2332 commits ahead of it, C21 is 683 ahead of it.

## 1. Census numbers

| merge | conflicts | content | add/add | modify/delete |
|---|---|---|---|---|
| C21 vs `32bdc3a89` (#32016 and everything under it) | 141 | 124 | 12 | 5 |
| C21 vs `origin/master` (full bundle) | 144 | 127 | 12 | 5 |

Conflicted files in the speculative / model-class / CPU-kernel / server surface (full-bundle merge):
`common/speculative.{cpp,h}`, `common/arg.cpp`, `common/common.h`, `include/llama.h`, `src/llama-{model,model-loader,model-saver,hparams,context,graph}.*`,
`src/models/{dflash.cpp,models.h,deepseek41.cpp,deepseek4.cpp,qwen35.cpp,qwen35moe.cpp,delta-net-base.cpp,mamba-base.cpp,...}`,
`ggml/src/ggml-cpu/{ggml-cpu.c,ggml-cpu.cpp,ops.cpp,ops.h,repack.cpp,vec.cpp,vec.h}`, `tools/server/server-{context,common,task,schema}.*`,
CUDA/HIP: `fattn*.cu*`, `mmq*`, `mmvf/mmvq`, `top-k.cu`, `topk-moe.cu`, `gated_delta_net.cu`, `ssm-scan.cu`, `vendors/hip.h`, `ggml-cuda.cu`.
Modify/delete: `fattn-wmma-f16.cu`, `ggml-metal.metal` (upstream deleted, we modified) plus 3 others.
Raw conflict lists: `merge-tree-vs-32016.txt`, `merge-tree-vs-master.txt` (this directory).

**Risk: HIGH, not a mechanical merge.** C21 is a long-lived fork (683 commits) against a 2332-commit upstream span; `dflash.cpp` conflicts because #32016
rewrites it (1621 changed lines; new `dflash2.cpp`, `dspark.cpp`, `lilicorr.cpp`, `models.h` +72). A whole-tree merge is rejected;
the plan below re-applies our features onto upstream's structure per head class.

## 2. #32016 versus our DFlash-family fork commits (all are in C21)

| our commit | feature | overlap with #32016 | plan |
|---|---|---|---|
| `0262f0f92` | DFlash2 metadata + loader tensors (arch/hparams/gguf-py) | upstream now has native `dflash2` variant + `dflash2.cpp`; key names and tensor map differ | take upstream loader; add a GGUF-load test on our 27B DFlash2 GGUF; map any key we invented |
| `8f609e10d` | DFlash2 graph execution | superseded by `dflash2.cpp` (224 lines) | take upstream graph, then diff vs ours on the 27B DFlash2 GGUF for numerics |
| `d0f9fab7b` | per-head attention sinks | upstream `dflash.cpp` has sinks (4 refs), `dspark.cpp` 2, `dflash2.cpp` 0 | check which head classes carry sinks; re-apply to dflash2/lilicorr if our GGUFs use them |
| `f7cbe3a35` | NVFP4 per-tensor scales in drafter | upstream dflash 39 scale refs, dspark 29, lilicorr 18, dflash2 0 | re-apply on dflash2 only if a DFlash2 NVFP4 GGUF is in the lineup |
| `affe1097f` | token+embd batches take noise graph with per-token state rows | no upstream equivalent (0 refs in any of the four files) | re-apply per head class on top of the split; own test |
| `c5c61e5ab` | LiLiCorr (port of upstream #30506 C++ parts) | superseded by upstream `lilicorr.cpp` | drop ours, take upstream |
| `990213088` | DS41 DSpark drafter (arch `deepseek41-dspark`, `dflash-dspark41.cpp`, exactness switch, profiler) | **not representable upstream** (section 4) | keep as a separate impl; re-register in the new speculative dispatch |

Plan: fold #32016 whole (with its prerequisites), then re-apply features per head class (dflash / dflash2 / dspark / lilicorr / ds41-dspark),
one feature per commit (forward-port rule V6R-4b), each with its test. The branch is cut from fresh champion per the experimental workflow; this box cuts none.

Gate (greedy; drafted and accepted counts must be IDENTICAL, not just the text): np1 and np4 for (a) 27B DFlash2 and (b) the DS41 GGUF
(DS41 is np1 only: single-slot, `--parallel 1`). Plus the standing GPU+CPU no-regression gate vs C21.

## 3. #30846 (`660be5506`) versus our Q8_0 nrc==2 branch

Confirmed collision. Ours (C21 `ggml-cpu.c` ~1414-1418) special-cases `type == Q8_0 && num_rows_per_vec_dot == 2` in
`ggml_compute_forward_mul_mat_one_chunk`, walking `ir0 += 2` over ADJACENT rows and writing `dst_col[ir0]` directly via `ggml_vec_dot_q8_0_q8_0(..., nrc=2)`.
#30846 rewrites the same loop: rows are split into two streams (`nr0_split`, `blck_0_split`), `vec_dot` is called with row stride `nb01 * nr0_split`
(rows `r` and `r + nr0_split`, not `r` and `r + 1`), and the tmp buffer is de-interleaved by the new `ggml_deinterleave_f32`.
The row pairing differs, so our branch cannot sit inside the new loop unchanged. `merge-tree` reports a content conflict at this site (merged-file hunk ~1453-1476).

Resolution (explicit): take #30846's loop and re-express our Q8_0 nrc==2 special case in its terms (stream-split pairing `ir0` / `ir0 + nr0_split`, output through the de-interleave path), dropping the adjacent-row `ir0 += 2` form.
Required test before the fold branch is accepted: `test-backend-ops` MUL_MAT, Q8_0, n = 2, 4, 8 (odd-m and tail shapes included), candidate vs champion C21, bit-for-bit equal dst (NMSE exactly 0 / byte compare), CPU backend,
plus an unchanged-result check on the iqk Q8_0 prefill route (`GGML_IQK_Q8_0_PREFILL`).

## 4. Launcher audit for `--spec-type` values #32016 refuses

Upstream (`32bdc3a89` `common/speculative.cpp` ~3243-3266): `draft-dflash` runs ANY DFlash-family draft; `draft-dspark` / `draft-dflash2` / `draft-lilicorr`
must equal the model's head or `std::runtime_error("--spec-type X does not match the draft model: use Y")` is thrown; a draft that is not a `llama_model_dflash` throws
`--spec-type X requires a DFlash draft model`. `server-context.cpp` (~1519-1525) CATCHES it, logs `failed to initialize speculative decoding context`, and the server
**keeps running with speculation off** (it returns false only when `has_synth()`). That is the silent disable.

Audit (`epyc-orchestrator`, `epyc-inference-research`; tests excluded):
- Registries and stack (`model_registry.yaml`, `model_descriptors.yaml`, `derived/stack_priors.yaml`, `drafter_selection.py`, `stack_priors.py`): `draft-dflash` only. SAFE under #32016 (the generic type accepts every family head).
- **AT RISK:** `epyc-inference-research/scripts/lib/deepseek_v41_flash_recipe.py` (`DRAFT_SPEC_TYPE = "draft-dspark"`, line 203; SPEC_DEC line 395), the autokernel loop's `resolved_recipe.py:29-38`
  (`SPECULATION_TYPES`, single-slot/external-drafter/exactness sets), `serving.py`, `k35_stack_context_matrix_runner.py`. The DS41 drafter GGUF is arch `deepseek41-dspark`
  (our `LLM_ARCH_DEEPSEEK41_DSPARK`), NOT a `llama_model_dflash`, so upstream `llama_model_dflash_variant()` returns NONE and `--spec-type draft-dspark` throws "requires a DFlash draft model":
  silent no-speculation on DS41 after a naive fold.
- A DFlash2 GGUF launched with `draft-dflash` works; with `draft-dspark` it would be refused (same silent disable). No launcher does the latter today.

Required fold actions: (1) keep a DS41-dspark dispatch path in the new speculative switch (our `is_dspark` / `common_speculative_impl_draft_dspark` for the `deepseek41-dspark` arch) so `draft-dspark` still resolves for DS41;
(2) gate assertion `drafted > 0` on the DS41 and 27B DFlash2 smokes so a spec-off fall-through fails loudly instead of passing on text identity;
(3) optionally move non-DS41 DFlash-family launchers to `draft-dflash`.

## 5. Would we GAIN from adopting each upstream change? (operator question 2026-11-22)

No new measurement was run (zero-compute box); evidence level is stated per row.

**5a. DFlash split into dflash/dflash2/dspark/lilicorr (#32016): NO throughput gain; adopt for maintenance only.**
- It is a refactor (title "refactor DFlash based speculative decoding methods"; `dflash.cpp` -1621 lines redistributed across four files); nothing in the message or diff claims a speed change, and our per-token state rows (`affe1097f`) have no upstream counterpart (0 refs in any of the four files).
- Our DFlash2 path has measured wins upstream lacks, for example DF2-11-BF16-FIX with `GGML_HIP_MMVF_CDNA_MAX_NE11=8`: 27B BF16 drafter 1.125x [1.108, 1.142] at equal acceptance (kernel-champion handoff line 56).
- Gain is structural: upstream-maintained LiLiCorr and DSpark heads, a `dflash2` loader that keeps pace with new DFlash2 GGUFs (#31904), less fork surface. Cost: re-apply 4 features plus DS41. Fold for maintainability when those heads are wanted; it is not a performance lever.

**5b. Fused TOP_K_MASK (#30640 `d454a204e`, #30965 `5c3114268`, #31243 `27b7a8a00`): our H12 fused QSA is faster; the fold must PROTECT it, not adopt the upstream op for Q38FN.**
- Upstream `GGML_OP_TOP_K_MASK` fuses mask construction (top_k plus SET_ROWS scatter into a -inf plane) and still feeds a DENSE masked flash attention (`ggml_top_k_mask(...)` in `qwen4exp.cpp` ~886-890).
- H12 (`ggml-cuda/qsa-sparse.cu`) reads only the selected KV blocks: 3.16x vs C6 dense FA at kv=32k (AK-ASM-H12 RESULT, `ak-asm-h12-gate-20261105` r5; caveats: dispatch gate MIN_KV_RATIO=8 was chosen post hoc, kv=8192 small-batch 0.94x). Upstream's fusion can save at most the mask-build nodes, a strict subset of what H12 already removes.
- **Interaction hazard:** H12's matcher recognises `FA mask = ADD(VIEW(SET_ROWS(FILL(-inf), FILL(0), top_k)), kq_mask)`. Upstream defaults `cparams.fused_top_k_mask = true` (`llama-context.cpp:345`), which replaces that subgraph with a `TOP_K_MASK` node.
  After a naive fold the matcher does not fire, `ggml_cuda_qsa_sparse_try` returns false and Q38FN silently falls back to dense FA (loses the 3.16x at long context).
  Fold action: force `fused_top_k_mask=false` for the qwen4exp/Q38FN graphs or teach the matcher the `TOP_K_MASK` pattern, and make the FOLD-GUARD-H12 fusion test (handoff line 1914) a hard gate.
- Upstream could still help only on models we do not hand-fuse (deepseek4, glm5-next use the op); worth measuring only if those lanes are active. Its CUDA `top-k-mask.cu` sits beside our HIP radix `top-k.cu`, which is conflicted.

**5c. #30846 (mul_mat_one_chunk access pattern), censused though not in the operator question:** possible CPU gain, unmeasured. Adopt only after the section 3 bit-equality test and a CPU A/B; our iqk/repack paths bypass `one_chunk` for most quant types, so the benefit on our lineup is uncertain.

## 6. Done-when check

- merge-tree census recorded (141 / 144 conflicts, by class and by hot file): section 1.
- Plan, gate, #30846 resolution with the MUL_MAT Q8_0 n=2/4/8 bit-equality test, launcher audit (draft-dspark / DS41 finding), per-change GAIN statement with evidence: sections 2-5.
- Compute used: none.

Next: autokernel session; when the fold is scheduled, cut from fresh champion and land first (1) the DS41 dispatch keep, (2) the Q8_0 nrc==2 re-expression with its n=2/4/8 test, (3) the `fused_top_k_mask` / H12 matcher guard.
