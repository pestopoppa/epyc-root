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
- [ ] Pass `-fno-offload-lto` explicitly and prove the device `cc1`/`lld` lines show no offload LTO.
  LLVM 23 / TheRock 10.1 default host+device HIP compiles to full device LTO (llvm #201457), which spilled
  register-bound kernels in ROCm/llvm-project#4434 (intake-1407/1413); ROCm 6.2 defaults to off.
- [ ] Do not test ROCm 7.2.0 or TheRock 7.x nightlies before ~2026-02-13 (7.11 included): they carry the
  llvm #147700 unroll cost-model bug (reverted 7.2.1+/7.12; intake-1414/1424).
- [ ] On any LLVM ≥23 upstream-based compiler, keep AMDGPU runtime unrolling off (llvm #194924 turns it on;
  ROCm afcb2456 gates it off only on therock-10.1/amd-staging; intake-1422/1423), and never combine a
  profile-use (device PGO) build with MMVQ decode without re-checking unrolling (intake-1417).

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
- [ ] Before any unpin is proposed, run the zero-GPU static audit on IQ2_XXS/IQ3_XXS/IQ4_XS/Q4_K/Q8_0
  MMVQ kernels vs the ROCm 6.2 build (VGPR, spill, scratch bytes/ops, drains) across
  {offload-lto default, `-fno-offload-lto`} × {default unroll, `--amdgpu-unroll-threshold-local=600`}, then an
  MI210 decode/prefill same-window ABA with correctness. Unpin only if a cell beats 6.2 on decode without
  losing prefill; expect a plain upgrade to regress. Method: `artifacts/gpu-aux-baselines/a10_iq2_vgpr_compiler_ab_20260915.md`.

## Known failure signature

The historical regression presents as a large prefill loss (decode flat) on ROCm 7.2.0 and early TheRock
7.x nightlies: an AMDGPU unroll cost-model bug (llvm #147700) over-unrolled loops touching `__shared__`
memory, causing VGPR spills (AMD bisect: gfx1100 1416.90 → 4378.87 t/s after revert). The widely quoted
3.7–5× (llama.cpp #19984) is confounded and should not be cited. The local-unroll threshold above is the
mitigation. The host runs ROCm 6.2, so this is an upgrade guard, not a flag to retrofit into frozen v9.

Primary upstream discussion: [llama.cpp ROCm performance discussion #15021](https://github.com/ggml-org/llama.cpp/discussions/15021).
