CAFE-4 token-witness HIP build qualification (R6)
================================================

Row `df2-cafe4-modes-hip-build-r6-20261119` binds the token-witness
candidate produced by root commit `989397117d14267f3596598991428c62104a7f28`:
SHA-256 `f11d4e31bbdebf1533d42136d900076124acd8a3b59ec572c7ad3ed5bb28fbdc`.
Header SHA-256:
`e4c7b544a72f21014d9d3999be4d8072f03c1aa779c936416b870e6978d33e70`.

The separate scratch root is
`/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r6-20261119`.
The existing detached v10 diagnostic source tree is reused. `inputs.json`
binds the candidate, header, bridge, supervisor and driver. No production
source or earlier build artifact is modified.

Both the smoke object and full executable must contain `CAFE4_BOUNDARY`,
`CAFE4_PROPOSAL` and `CAFE4_VERIFY_TOKEN`, alongside all eight R5 markers.
R5 contracts remain: exact defined IQK/HIP exports, hash-bound artifacts,
six local library mappings, Clang IQK compatibility configuration and
compiled gfx90a content. Full scheduled build qualification is required
before a fresh native row. The original R5 UNKNOWN and fixed native error
gate **0.743863867** remain unchanged and unevaluated here.

Validation: **17/17 model-free ELF-fixture tests PASS**, including individual
rejection of each token marker in both smoke and full-build modes. Shell
syntax and pinned input checks PASS. Stop on source mismatch, build/linkage
failure, STOP or deadline; stop on answer at a validated full build receipt.
No model is loaded by this row.

Publication: four-CPU smoke **PASS**, cores 116–119, clean STOP rc75
at 22:37:14Z. First progress validated the compiled object.
Receipt `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe4-modes-hip-build-r6-20261119/PASS.json`,
SHA-256 `70171301ff0d1b09062de82dc6876cc3ed1759ccef4246134dbf77a199ed688e`. Full build and native controls remain pending.
[no-belief: compiled-object qualification and publication only]

Scheduled full-build verdict (2026-11-19)
----------------------------------------

Filed `df2-cafe4-modes-hip-build-r6-20261119` **PASS**, scheduled rc0 at
23:07:32Z. The full receipt is validated before atomic publication by
`driver.write`: exact source/patch/input and artifact bindings, all eleven
compiled markers (including boundary/proposal/target-token witnesses),
Clang IQK compatibility configuration, exact defined IQK/HIP exports,
HIP ON/gfx90a configuration and compiled image, and six local libraries.
No repeat build or native execution was needed to file this result.

Evidence retained in place:

- `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r6-20261119/RESULT.json`
  SHA-256 `6579bdac406a13b5942bd8bcba8cbad8dfcee5f00a8a07545aaaa0fc277b4840`.
- `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r6-20261119/runs/build-ci7c93lw/build/bin/cafe4-mtp-rollback`
  SHA-256 `d346b6fe24397f057a367699f77b2ed0a0319f1b34f11f6682f656ab31191b77` (bound by the full receipt).

Parent CAFE-4 remains open. Next: prepare a native R6 token-witness diagnostic
using this qualified executable and six bound libraries, preserving the
widths 2/3 normal and explicit rc1 fault controls, live residency checks and
fixed **0.743863867** error gate. Original native R5 UNKNOWN is unchanged.
Existing CAFE-4 source registration and VB-SERVING-DF2 wiring task apply.
[no-belief: full build qualification only; no native rollback verdict]
