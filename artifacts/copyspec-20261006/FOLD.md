# COPYSPEC-WIDTH champion fold (candidate)

Candidate branch: llama.cpp-experimental-champion-specwidth-20261006
Candidate SHA:    bb5d982395f8584dd3d6948903f8733c1f8745cf  (llama-server --version: 10341 (bb5d98239))
Worktree:         /mnt/raid0/llm/worktrees/llama-champ-specwidth-20261006
Base (champion tip at worktree creation, ak/champion/llama-cpp-ffc1bac82eec): 4348de400191c0b4c5127047037bf9ad83da19b6
Candidate = base + exactly 1 commit (cherry-pick of defa269af, branch llama.cpp-experimental-specwidth-20261006). Champion branch NOT touched.

## Ancestry: git log --oneline b0ba1d427..4348de400
4348de400 akm-cpu-mmid-flat-activation-blocks: +2.048% on serving:q38fn-802bf9ac6-cpu-t48-mtp-d4 over 5 pairs
a331665d4 akm-cpu-float-narrow-m-column-jobs: +3.357% on serving:q38fn-802bf9ac6-cpu-t48-mtp-d4 over 5 pairs
253e50c32 akm-ds41-verify-bounded-flat-expert-slabs: +0.120% on serving:ds41-00d118d44-cpu-t48-dspark-b2 over 5 pairs
96870b11c akm-ds41-small-sumrows-solo: +0.350% on serving:ds41-00d118d44-cpu-t48-dspark-b2 over 5 pairs
0d270f99b akm-cpu-q8-verify-five-single-pass: +3.932% on serving:q38fn-802bf9ac6-cpu-t48-mtp-d4 over 5 pairs
8b8d28711 akm-ds41-small-concat-solo-runs: +1.112% on serving:ds41-00d118d44-cpu-t48-dspark-b2 over 5 pairs
86fd98e25 akm-cpu-q8-proportional-stream-placement: +0.627% on serving:q38fn-b0ba1d427-cpu-t48-mtp-d4 over 5 pairs
ce2943a03 akm-ds41-solo-small-three-row-runs: +2.673% on serving:ds41-00d118d44-cpu-t48-dspark-b2 over 5 pairs

## Conflicts
None. git cherry-pick auto-merged common/arg.cpp, common/common.h, common/speculative.cpp, tools/server/server-context.cpp (5 files, +42/-5). Default-off property rests on the original commit (per-impl width only when --spec-ngram-mod-n-max is explicit); not re-run here (no inference permitted). DFlash2/DSpark/KVU-19 paths were auto-merged without textual overlap; the champion owner regression gate should confirm.

## Builds (Release, gcc-15, GGML_NATIVE, OPENMP, LLAMA_CURL=OFF, targets llama-server llama-bench, -j 24, region-lock q1 / cpus 24-47)
- CPU: /mnt/raid0/llm/tmp/copy-spec-eval-20261006/width/champ-build/cpu   rc=0  bin/llama-server
- HIP: /mnt/raid0/llm/tmp/copy-spec-eval-20261006/width/champ-build/gpu   rc=0  bin/llama-server
  flags: GGML_HIP=ON, AMDGPU_TARGETS/GPU_TARGETS=gfx90a, HIP_GRAPHS=ON, HIP_NO_VMM=ON, HIP_MMQ_MFMA=ON, HIP_ROCWMMA_FATTN=ON (copied from gpu-20261004-b0ba1d427 CMakeCache; CPU flags from cpu-20261004-b0ba1d427)
- Both: --version 10341 (bb5d98239); verify_ggml_linkage.sh <bin> <build>/bin = PASS (note: 2nd arg is the build bin dir, not the source tree). Script: champ-build/build.sh, logs champ-build/*.log
- Not run: any server/inference/GPU. HIP backend residency must be proven at serving time.

## Evidence
- /mnt/raid0/llm/tmp/copy-spec-eval-20261006/width/results/summary.md  (+20.5% code-edit decode at ngram cap 16, CPU frontdoor, 65/65 greedy identity)
- /mnt/raid0/llm/tmp/copy-spec-eval-20261006/width/../results/summary.md

## Champion owner actions
1. After your regression gates (speed + quality vs 4348de400, CPU and GPU), fast-forward ak/champion/llama-cpp-ffc1bac82eec to bb5d982395f8584dd3d6948903f8733c1f8745cf. If the champion has advanced past 4348de400, rebase/cherry-pick bb5d98239 onto the new tip (it touches only speculative/server arg plumbing) and rebuild.
2. Enable by setting --spec-ngram-mod-n-max 16 explicitly on the CPU frontdoor launch; default-off otherwise.
