# ROCm Upgrade Checklist for llama.cpp / AutoKernel

Use this checklist before testing or promoting any ROCm toolchain newer than the currently frozen
ROCm 6.2 environment. It does not authorize modifying or building a frozen production kernel. Start
from the current production tip in a fresh `llama.cpp-experimental` worktree, then follow the normal
experimental-kernel workflow in the root `AGENTS.md`.

## Preflight

- [ ] Record the exact ROCm, HIP compiler, LLVM, kernel-tree, CMake, and target-GPU identities.
- [ ] Set `AMDGPU_TARGETS=gfx90a`; do not accept host autodetection as the only build record.
- [ ] Check the current status of upstream llama.cpp issue/discussion evidence for the ROCm 7 LLVM
  loop-unroll regression. Absence of a new report is not evidence that the regression is fixed.
- [ ] On Linux, configure the HIP compilation units with
  `-DCMAKE_HIP_FLAGS="-mllvm --amdgpu-unroll-threshold-local=600"`. Putting the option only in
  `CMAKE_CXX_FLAGS` does not reach the generated HIP objects.
- [ ] Preserve any other required HIP flags when setting `CMAKE_HIP_FLAGS`; do not overwrite them.
- [ ] Prove the option reached the HIP compile commands (for example, inspect the generated verbose
  build or `compile_commands.json`) and record that evidence in the build receipt.

## Validation gate

- [ ] Build only in the experimental tree and verify binary/linkage identity before execution.
- [ ] Run the canonical GPU correctness suite and the matched prefill/decode baseline on the exact
  production model/shape surface.
- [ ] For a ROCm 7+ toolchain, run a matched flag-on/flag-off prefill A/B unless the flag-off arm is
  already rejected by a hash-bound receipt for the same compiler and kernel tip.
- [ ] Keep the workaround for promotion unless the exact-toolchain A/B shows no material regression
  without it. Record that result; an upstream claim alone cannot waive the on-box test.
- [ ] Re-run CPU/GPU no-regression, linkage, packaging, and production-freeze gates before proposing a
  new production version. Promote a fresh full candidate; never patch the frozen tree in place.

## Known failure signature

The historical regression presents as a large prefill loss under ROCm 7+ (reported at roughly
3.7–5×). The mitigation is the LLVM local-unroll threshold above. The host currently uses ROCm 6.2,
so this is an upgrade guard, not a flag to retrofit into the frozen v9 build.

Primary upstream discussion: [llama.cpp ROCm performance discussion #15021](https://github.com/ggml-org/llama.cpp/discussions/15021).
