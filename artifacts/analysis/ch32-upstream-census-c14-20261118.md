# CH-32 upstream-delta census redone on champion C14 (2026-11-18)

Operator decision 2026-11-18: upstream llama.cpp fold policy is **port-as-hypothesis** (a change is ported only when a box needs it, gated on that box's own instrument). This census replaces the stale C5 numbers. It is written here and NOT to the v11 manifest (operator HOLD).

## Frame

- Base: champion C14 `eee3da838e3c8306a856f2c72c4b04048fded698` (experimental tree, detached scratch worktree, removed afterwards; production tree untouched, no checkout in the shared clone, nothing pushed).
- Upstream: remote `origin` = ggml-org/llama.cpp, fetched 2026-11-18 (fetch only). Tip `0a76757469ea94ad5f88d14e18cc7370b9931f99` (tag-describe `b12529`). Merge-base with C14 `a8dc0e3269a5378d212e6daea953fbbaa7ac8e4b`; C14 is 2484 commits behind the tip.
- Method 1 (whole tip): `git merge --no-commit --no-ff <tip>`, then `git merge --abort` (worktree verified clean at C14 afterwards).
- Method 2 (per group, whole ancestry): `git merge-tree --write-tree --name-only C14 <group tip commit>`. Raw outputs kept in `/mnt/raid0/llm/tmp/ch32c14/mt-<group>.txt`.
- Method 3 (per group, isolated patch): `git cherry-pick --no-commit <commit>` on C14, count unmerged files, then abort and `reset --hard`. This is the first-patch view: it omits prerequisite upstream commits, so it overstates what a correct minimal chain would conflict on, and says nothing about build or ABI.

## Whole-tip merge, C14 + upstream tip

- 137 conflicted files, 899 conflict hunks (marker count over the files present in the tree). 3559 files differ from C14 in the merged index.
- By area (conflicted files): ggml/src 35 (cuda/hip dominates; also vulkan, metal), src 29, src/models 18, tools/server 10, common 10, tests 7, conversion 6, tools/mtmd 5, gguf-py 4, ggml/include 2, plus include/llama.h, examples/speculative*, docs, tools/cli, tools/completion, tools/llama-bench.
- Conflicts in the predeclared cut-by-hand zones: ggml-cpu 7 (ggml-cpu.c, ggml-cpu.cpp, ops.cpp, ops.h, repack.cpp, vec.cpp, vec.h), speculative 5 (common/speculative.cpp/.h, docs/speculative.md, examples/speculative*), tools/server 10 (server-common, server-context, server-schema, server-task, server-task.h, CMake, README, 3 test files). No `iqk` path conflicts (the iqk files are C14-only and upstream never touches them).
- Heaviest hunk files: common/speculative.cpp 26, src/llama-memory-hybrid-idx.cpp 25, ggml-cuda.cu 18, src/llama-arch.cpp 16, ops.cpp 15, deepseek41.cpp 15, fattn-mma-f16.cuh 14, ggml.c 14.

Conclusion: a bulk merge or rebase onto the tip is not viable; folding is per-feature only, which is exactly the port-as-hypothesis policy.

## ggml generation

- C14 `ggml/CMakeLists.txt`: GGML_VERSION 0.16.0. Upstream tip: **1.0.0** (a generation boundary).
- `ggml/include` differs in 8 headers (ggml-alloc, ggml-backend, ggml-cpu, ggml-kv-mirror, ggml-rpc, ggml-sycl, ggml-zdnn, ggml): +223/-568. `ggml.h` and `ggml-rpc.h` conflict. `ggml-kv-mirror.h` is C14-side.
- Consequence: no group below can be taken as a patch without its ggml prerequisites (see CH-32 notes in the champion handoff: enum ordinal shift `GGML_OP_MUL_MAT` 31 vs 29, batched `ggml_conv_1d`, depthwise F16, `conv_2d_direct`, SSM-conv width 7). Any port needs its own ggml-op instrument gate on the three-ggml-generation hazard.

## Per fold group

`mt` = files conflicted by merge-tree of the whole ancestry of the group tip against C14 (so it includes every upstream change between the merge-base and the commit). `pick` = unmerged files when only that commit is cherry-picked onto C14. `zone` = whole-ancestry conflicts in ggml-cpu/iqk/speculative (S) and tools/server (V).

| Group | Commit | Upstream PR | Diffstat | Ancestry commits | mt files | zone S / V | pick files |
|---|---|---|---|---|---|---|---|
| A | cbe28bb3 | #30408 non-causal ubatch | 5 files +7/-7 | 1532 | 121 | 11 / 6 | **0 (clean)** |
| B1 | b77d646751 | #25994 Nanbeige4.2 | 10 files +265/-1 | 108 | 38 | 2 / 1 | 2 |
| B2 | Ouro #29823 | open PR head | not fetched | n/a | not run | n/a | n/a |
| C1 | a4cb4c61fd | #29818 /v1/systemone | 35 files +2139/-15 | 1316 | 110 | 10 / 5 | 10 |
| C2 | 7e3eeee048 | #30361 H2O-Lightning-4B | 16 files +478/-15 | 1728 | 126 | 11 / 6 | 13 |
| D1 | 2851b3bcbf | #30629 mtmd_audio_stream + Voxtral realtime | 27 files +998/-20 | 1630 | 123 | 11 / 6 | 8 |
| D2 | 1242be66f6 | #30636 realtime transcription API | 9 files +512/-14 | 1735 | 126 | 11 / 6 | 2 |
| D3 | 19cce6919 | #31252 LFM3 arch | 23 files +1070/-5 | 1893 | 128 | 11 / 6 | 11 |
| D4 | 19ff817fb | #31257 LFM3 audio+omni | 31 files +2721/-160 | 1896 | 128 | 11 / 6 | 25 |
| D5 | 8ca4060b7 | #31269 /v1/realtime | 10 files +1423/-14 | 1901 | 129 | 11 / 7 | 5 |
| D6 | d1eb0deba | #31287 realtime tool calls | 7 files +359/-85 | 1913 | 129 | 11 / 7 | 5 |
| D7 | 889f2ec96 | #31386 codec quant | 2 files +2/-5 | 1968 | 130 | 11 / 7 | 2 |
| D8 | d4f1b18b3 | #31283 video | 11 files +561/-47 | 1914 | 129 | 11 / 7 | 9 |

Whole-ancestry merge-tree conflicts are ~121-130 files for every group because each commit drags in ~1300-2000 upstream commits; that figure measures the distance, not the feature. Pick files per group:

- B1: src/llama-arch.h, src/llama-context.cpp.
- C1: conversion/base.py, conversion/qwen.py, conversion/qwen3vl.py, convert_hf_to_gguf_update.py, gguf-py/gguf/gguf_writer.py, src/llama-hparams.h, src/llama-vocab.h, src/models/modern-bert.cpp, tools/server/README.md, tools/server/server-context.cpp.
- C2: common/common.cpp, common/common.h, conversion/__init__.py, gguf-py constants.py + gguf_writer.py, src/llama-arch.cpp/.h, src/llama-ext.h, tools/server/{README.md, server-common.cpp, server-context.cpp, server-decision.cpp, server-decision.h}.
- D1: gguf-py constants.py + tensor_mapping.py, src/llama-arch.h, src/llama-ext.h, src/llama-model.cpp, tools/mtmd/{clip.cpp, clip.h, mtmd.h}.
- D2: tools/server/server-context.cpp, tools/server/server-models.h.
- D3: src/llama-arch.cpp, src/llama-quant.cpp, tests/fusion/MTL.csv, tests/test-llama-archs.cpp, tools/mtmd/{CMakeLists.txt, clip-impl.h, clip.cpp, models/models.h, mtmd-image.cpp/.h, mtmd.cpp}.
- D4 (25): common/{chat.cpp, chat.h, common.h}, conversion/{__init__.py, lfm3.py}, gguf-py {constants, gguf_writer, tensor_mapping}, src/llama-quant.cpp, tools/mtmd/{CMakeLists.txt, clip-impl.h, clip-model.h, clip.cpp, models/models.h, mtmd-audio.cpp/.h, mtmd-cli.cpp, mtmd-helper-gen.cpp, mtmd-helper.cpp/.h, mtmd.cpp/.h}, tools/server/{README.md, server-context.cpp}, tools/tts/tts.cpp.
- D5: tools/server/{CMakeLists.txt, README.md, server-context.cpp, server-task.cpp, server-task.h}.
- D6: examples/realtime_client.py, tools/server/{README.md, server-realtime.cpp/.h, server-task.h}.
- D7: conversion/lfm3.py, src/llama-quant.cpp.
- D8: conversion/lfm3.py, tools/mtmd/{models/lfm3vl.cpp, mtmd-helper.cpp/.h, mtmd-image.cpp/.h, mtmd.cpp, mtmd.h}, tools/server/server-decision.cpp.

## Reading against the predeclared rule

Rule (CH-32): more than 3 conflicted files in server/, or any conflict in ggml-cpu, iqk or speculative code, means cut by hand on a fresh experimental branch from the current champion rather than cherry-pick in bulk.

- Isolated-patch view: A is clean (a trivial 5-file, +7/-7 patch; it is still absent from C14 and C15 per the CH-33 2026-11-18 audit, and its box is CH-33, not CH-35/36). B1 touches no rule zone. C1 has 2 server files, C2 5 (cut by hand), D2 1, D4 2, D5 5 (cut by hand), D6 4 (cut by hand), D8 1. No group's isolated patch conflicts in ggml-cpu, iqk or speculative.
- Whole-ancestry view: every group is over the rule, by hundreds of files.
- Group C needs C1 before C2; D has D3 before D4/D7/D8 and D5 before D6 (from the 2026-11-01 prerequisite census); group C and D8 also depend on decision-handling context from upstream commits not in C14.
- Group B2 (Ouro) not measured: CH-34 is closed deprecated (operator 2026-11-10) and the PR head is not pinned.

## What this does and does not establish

Established: real conflict counts and files on C14, the ggml generation gap (0.16.0 to 1.0.0), and that bulk adoption is non-viable. Not established (by design, not deferred): minimum prerequisite commit chains, ABI compatibility and buildability. Under port-as-hypothesis those are computed per port, when CH-35 or CH-36 pass their own instrument gate (CS-8.STT8 / CS-8.RT1 for CH-35; TD-23.D1 parity and batch-invariance for CH-36), on a fresh experimental branch from the then-current champion tip.

Controls: base sha frozen, raw merge-tree outputs per group retained under `/mnt/raid0/llm/tmp/ch32c14/`, full group list covered except B2, nothing written to the v11 manifest.
