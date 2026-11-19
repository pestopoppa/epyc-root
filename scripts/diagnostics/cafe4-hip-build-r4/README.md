CAFE-4 corrected-reference HIP build qualification
==================================================

Row `df2-cafe4-modes-hip-build-r4-20261119` is a CPU-scheduled full HIP/gfx90a
build qualification for corrected generator output SHA-256
`41fc473a908b7c385d79d1941b6576cc993b985e691682d6598d6122e968fe1c`.
The correction is committed in epyc-root `d3cc84653989faa3e0257d985e8db0d2a34989db`;
see [decode-boundary rationale](../CAFE4.md#cold-reference-decode-boundary-correction-2026-11-19).
Native error gate **0.743863867** remains fixed (lower error is better).
This build neither evaluates that gate nor establishes native GPU residency.

R4 retains the [R3 qualification predicates](../cafe4-hip-build/README.md),
including exact defined CPU IQK exports `iqk_mul_mat` / `ggml_iqk_try_mul_mat`
and HIP export `ggml_backend_cuda_reg`, artifact hashes, gfx90a image markers,
CMake configuration and all llama/ggml linkages local to the run directory.
No validator logic changes; the new driver uses a separate scratch root:
`/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r4-20261119`.
All small inputs are prepared before publication and hash-bound by `inputs.json`.
The detached experimental source is v10
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115` plus diagnostic patch SHA-256
`351a431702613a5cad8d165c6959dbcde12a928963b8833bfa4668abb743e4dd`.
Production and R3 outputs remain unchanged; R3 covers the original source only.

Smoke must reproduce the original Clang IQK enum error, pass the identical
translation unit with the compatibility flag, and validate the corrected
compiled candidate object with six load/rollback/rewind/mode/fault markers.
The scheduled build requires the full executable and backend receipt.
Stop on source mismatch, build/linkage failure, STOP or deadline; stop on
answer when the complete build receipt validates. No model is loaded.

Next: file corrected CPU R2 and HIP R4 build receipts when they end, then
publish native width2/3 normal and explicit rc1 fault controls under the
fixed numerical gate. Native results and parent CAFE-4 remain open.
[no-belief: compiled-object qualification only; no native measurement]

Publication (2026-11-19)
------------------------

Publisher smoke **PASS**, cores 116–119, STOP rc75 at 06:51:32Z.
Receipt: `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe4-modes-hip-build-r4-20261119/PASS.json`; SHA-256 `40a818b60975569389975a44053fd7cb055aa49abe63967b69cb1f498fbc01df`.
Full scheduled build and native controls remain pending.

Scheduled build verdict (2026-11-19)
------------------------------------

Row `df2-cafe4-modes-hip-build-r4-20261119` **PASS**, scheduled rc0,
07:13:49–07:15:10Z. Existing `driver.validate` accepted the complete corrected
source receipt: pinned v10/patch and input hashes, all artifact hashes, six
compiled markers, six local llama/ggml library links, Clang IQK compatibility,
exact defined IQK/HIP exports and gfx90a configuration/content.

Evidence remains at its original paths:

- Result: `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r4-20261119/RESULT.json`, SHA-256 `3ac17b5fea20eaab2f6d0daa884883098ea0da4f077cf2fe978fe7b63a82ba7d`.
- Executable: `runs/build-n5x64h2y/build/bin/cafe4-mtp-rollback` under that scratch root, SHA-256 `1623d9e2455116944e330a8c28200a84270f0dd0833563171f48344e22dfb63a`.
- Filing verdict: `/mnt/raid0/llm/tmp/compute-flags/filing-done/df2-cafe4-modes-hip-build-r4-20261119.verdict.json`; `file_result.py` wrote FILED.
- Validator: epyc-root commit `7ff64d37e3d75170fdb112687857593124fdfe74`, `scripts/diagnostics/cafe4-hip-build-r4/driver.py`.

Build qualification only; native GPU residency, rollback and explicit fault
controls remain untested. Gate **0.743863867** stays fixed and unevaluated.
Next publish corrected-source native CPU width2/3 normal and explicit-fault
controls using qualified CPU R2 executable SHA-256
`b3776b70ee6a6736ed08aac9cb379de427b0574f3373ab9c304dd5e80d3cc764`,
then the qualified HIP R4 native GPU controls. Parent CAFE-4 remains open.
[no-belief: build qualification only; no native measurement]
