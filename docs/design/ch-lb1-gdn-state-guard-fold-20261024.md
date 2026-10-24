> Durable copy (2026-10-24, workspace-f8 subagent) of the scratch fold record
> `/mnt/raid0/llm/tmp/f8-launchers-20261024/ch-lb1-1-fold/FOLD.md` (sha256 below). Tracking: CH-LB1 / CH-LB1.1 in
> [`handoffs/active/autokernel-champion-aggregate.md`](../../handoffs/active/autokernel-champion-aggregate.md). Scratch paths
> named below (`/mnt/raid0/llm/tmp/...`) may be reclaimed; the branch on `fork` and the `kernels/builds/` dirs are the
> durable artifacts. Source sha256: `8b7d001eb4f6fe75f4c43314a433570c9f0bf77db34eed81a45dd9b62109545b`. No edits vs the source.

# FOLD.md: CPU gated-delta-net BF16-state guard (CH-LB1, intake-2386#record)

Prepared 2026-10-24 by a workspace-f8 subagent for the champion fold owner (coordinator 3c4ca599). Tracking: CH-LB1 / CH-LB1.1 in
`handoffs/active/autokernel-champion-aggregate.md`. **Nothing was built, gated, CAS'd or moved.** The champion ref
`ak/champion/llama-cpp-ffc1bac82eec` is still `dcc853b55` (C3). **Production v10 (`ffc1bac82`, `production-consolidated-v10`)
stays frozen**: this fold changes only the champion line, and production picks it up only when a later champion is promoted.

## What it is

| | |
|---|---|
| trial-merge branch | `experimental/ch-lb1-fold-20261024` @ `d95ce62678949b1e68f6c4062955922a55eb2686`, pushed to `fork` (never origin). Worktree `/mnt/raid0/llm/worktrees/llama-ch-lb1-fold-20261024`. |
| base | `dcc853b5559bef4e50acf251f4910f7f4e0ba538` = the champion tip (C3, CAS'd 2026-10-24T07:50:06Z) |
| commit 1 | `8e7463856` = cherry-pick -x of `5f1eee195` "ggml-cpu: refuse GATED_DELTA_NET with a BF16 recurrent state (CH-LB1)" |
| commit 2 | `d95ce6267` = cherry-pick -x of `452887155` "tests: test-gdn-state-guard includes <initializer_list> (CH-LB1 build fix)" (clean) |
| source branch | `experimental/locals-kernel-fixes-20261022` (fork), cut from `dd3d9721c`; neither commit is an ancestor of `dcc853b55` |
| diff vs base | 6 files, +128/-5: `ggml/src/ggml-cpu/ggml-cpu.cpp` (+5), `ggml/src/ggml-cpu/ops.cpp` (+9), `src/llama-model.cpp` (+8/-1), `tests/CMakeLists.txt` (+2), `tests/test-backend-ops.cpp` (+45/-4), `tests/test-gdn-state-guard.cpp` (new, 59 lines) |
| libs that change | **libggml-cpu** (supports_op + compute abort) and **libllama** (warning in `gdn_recurrent_state_type()`). Test binaries `test-backend-ops` and the new `test-gdn-state-guard` change. Not touched: libggml-base, libggml, libggml-hip, libllama-common, libllama-server-impl, libmtmd, llama-server's own code. |

### Conflict outcome
`5f1eee195` conflicted in two test files only. Both were resolved by keeping both sides:
- `tests/CMakeLists.txt`: the champion's `llama_build_and_test(test-exl3.cpp)` and CH-LB1's `llama_build_and_test(test-gdn-state-guard.cpp)` are both kept.
- `tests/test-backend-ops.cpp`: the champion's generated `AK-SERVED-SHAPE-BEGIN..END` block is kept. CH-LB1's `test_backend_ops_extra_case_set()` helper goes after `AK-SERVED-SHAPE-END`, outside the generated region, so `served_shape_cases.py` regeneration does not clobber it. This is the same place the re-cut commit `51dfed7af` used.

`ggml/`, `src/` and `test-gdn-state-guard.cpp` applied cleanly. Per commit, the sorted added and removed lines are identical to the originals'.

## Why

- `ggml_gated_delta_net()` accepts a BF16 recurrent state (`[TAG_GDN_STATE_BF16]`).
- `llama-model.cpp` selects that state whenever `GGML_CUDA_GDN_STATE_BF16` is set, whatever the backend.
- The CPU kernel reads and writes the state as float, so a BF16 state on CPU was silently reinterpreted: wrong numbers, no error.
- Found during the Locals intake (`intake-2386#record`, recurrent-state handling).

The fix:
- **(a) supports_op:** the CPU backend's `supports_op` returns false for `GATED_DELTA_NET` unless `src[5]` (the state) and dst are F32.
- **(b) compute abort:** `ggml_compute_forward_gated_delta_net` aborts with a named message if a non-F32 state arrives anyway, for example through a direct graph compute or a forced CPU schedule.
- **(c) warning:** `llama-model.cpp` warns when the env var selects BF16.
- **Tests:** the new `test-gdn-state-guard` checks the supports_op contract for K=1/4 with the scalar and KDA gates. Two BF16-state `test-backend-ops` cases sit behind the opt-in set `TEST_BACKEND_OPS_EXTRA_CASES=gdn_bf16_state`, so the default corpus and every case name are unchanged and AK case counts do not move.

**Launcher env audit (done 2026-10-22):**
- No CPU launcher sets `GGML_CUDA_GDN_STATE_BF16`: 0 hits in epyc-orchestrator, none in `/etc/environment`, none in any readable live `llama-server` environment.
- In research it is set only by the ROCm replay arms of `run_autokernel_historical_replay.py` (HIP binary).

**Behaviour change on the F32 path: none.** supports_op returns true exactly as before, and the abort branch is one type compare per op call.

## Gates for the coordinator's CAS (on the full trial-merged candidate)

1. **CH-LB1 tests (1)-(4) on the trial-merged build.** Prepared, not run: `/mnt/raid0/llm/tmp/f8-launchers-20261024/ch-lb1-1-fold/` (`launch.sh`, `job.sh`, `PREDECLARATION.md` sha256 `192b7e20556327ca52019d90000e99bf9d9dab3dd5cdba1aca3d787ea5d9b6a7`). It runs as a CPU build role, about 30 min.
   - (1) `test-gdn-state-guard`: 4x `F32 state supported=1`, 4x `BF16 state supported=0`, then `OK`, rc 0.
   - (2) `test-backend-ops -b CPU -o GATED_DELTA_NET`: all OK, with the same case count as the C3 image (38 on the 10-22 line).
   - (3) With `TEST_BACKEND_OPS_EXTRA_CASES=gdn_bf16_state`: exactly +2 `not supported [CPU]`, the rest OK.
   - (4) `strings libggml-cpu.so` contains `CPU backend supports an F32 recurrent state only`, which is absent from `cpu-20261023-dcc853b55-c3` (negative control). `libllama.so` carries the warning text.
   - Alternatively, run the same four on the store images' `bin/` (the C3 `gate_c3.sh` (a) pattern) and skip the launcher.
2. **Store images.**
   - `kernels/builds/{cpu,gpu}-2026102x-d95ce6267-<tag>` via the CH-28d `build_store.sh` (prefix maps plus the pinned UI dist).
   - This is the first fold after C3, so the hip compare should be `mode=exact`. That closes CH-28d's "run twice / mode=exact" condition if the coordinator builds twice.
3. **`fold_gate.py` (v4) against the C3 images** `{cpu,gpu}-20261023-dcc853b55-c3`, with `--expected-changed libggml-cpu.so --expected-changed libllama.so`, on both the CPU and the GPU image (the HIP build also builds the CPU backend). Every other lib must be IDENTICAL; `libggml-hip.so` in particular must be identical.
4. **Version and linkage:** `llama-server --version` names `d95ce6267`, and `verify_ggml_linkage.sh` passes on both images.
5. **Q38FN greedy identity, C3 vs the candidate.** Required because libggml-cpu changes (C3 precedent G-e, `bundle_gate_c3.sh --items c` pattern, about 5 min, CPU correctness, needs no quiet host). Q38FN is a GDN hybrid, so this exercises the F32 path through the changed supports_op and compute entry. Expect IDENTICAL on p1-p3.
6. **Optional and not CAS-blocking:**
   - CPU test-backend-ops on the scorer ops as in C2.
   - A GPU `test-backend-ops -b ROCm0 -o GATED_DELTA_NET` slice. The GPU kernel is untouched; on ROCm0 the opt-in BF16 cases are skipped because the CPU reference refuses them.
   - **No timing gate.** The change is not on any decode hot path beyond one type compare, so no speed claim is made.

After the CAS: tick CH-LB1.1, write the fold-ledger entry, and set the manifest row (new V11 id, PEND -> IN) in `docs/reference/kernel-manifests/`.

## Interaction with other folds

- **C4 (`experimental/champion-c4-20261024` @ `cdb4d8c77`, CH-30 GPU-LEAK-1c + CH-20.2, coordinator 3c4ca599, in progress).**
  - C4 touches only `ggml/src/ggml-cuda/common.cuh`, `ggml/src/ggml-cuda/ggml-cuda.cu` and `tests/test-llama-archs.cpp`, so there is **zero file overlap** with this fold.
  - `git merge-tree` of `cdb4d8c77` and `d95ce6267` is clean.
  - Recommendation: **follow C4, do not ride it.** C4's gates are GPU-side (libggml-hip only). Adding CH-LB1 would add libggml-cpu and libllama to its expected-changed set and require the Q38FN CPU identity item, which re-opens a fold already in progress.
  - After C4 CAS: re-cut this branch on the C4 tip (`git cherry-pick 8e7463856 d95ce6267`, expected clean) and run the gates against the C4 images.
  - If the coordinator would rather batch, it can ride C4 before C4's store build. The cost is adding gates 1, 3 (two extra expected libs) and 5 to C4.
- **UFH14-LB1.1 (`0daa3ca8d`, `%llguidance` abort -> request error).**
  - Its files (`common/sampling.cpp`, `tools/server/tests/unit/test_chat_completion.py`) are disjoint from this fold's. `git merge-tree` of `0daa3ca8d` onto `d95ce6267` is clean.
  - Its box says "with `452887155`". That commit belongs to CH-LB1: it only fixes the `test-gdn-state-guard.cpp` include. The UFH14-LB1 build used the shared branch tip, which happened to be `452887155`. It is not a dependency of `0daa3ca8d`.
  - Recommendation: **one fold of three commits**, `8e7463856` + `d95ce6267` + `0daa3ca8d`, cherry-picked on the same tip. `452887155` appears once, here. Add `libllama-common.so` to `--expected-changed`, and add UFH14-LB1's server pytest (`unit/test_chat_completion.py -k "llguidance or invalid_grammar"`, 3 PASSED) plus its strings check to the gates.
  - That is UFH14-LB1.1's own work and is not done here.
- **V11-102 iqk FA line (`experimental/locals-kernel-fixes-20261023`).** It carries `51dfed7af`, a verbatim copy of `test_backend_ops_extra_case_set()`. Whichever of the two folds lands second must drop the duplicate helper, or the test file has two definitions and fails to compile.
