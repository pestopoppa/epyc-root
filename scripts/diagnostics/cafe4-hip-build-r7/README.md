CAFE-4 rollback-isolation HIP build qualification (R7)
====================================================

Row `df2-cafe4-modes-hip-build-r7-20261119` binds generated source
SHA-256 `af8bdd0e8261e200701ae9ad8fe5ed7a00070b0a0ab46d1a18d30737173bd1d4`
from `scripts/diagnostics/cafe4_port.py` at root commit
`8f57045d1673ad1b5f4771c0110dd4215e774ad9`.
The candidate keeps snapshot mode zero through proposal and verification,
then selects the requested mode at rollback. R6 native UNKNOWN remains unchanged.

The scratch root is `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r7-20261119`.
It reuses the existing detached v10 diagnostic source tree without changing it.
`inputs.json` binds the candidate, header, bridge, driver and supervisor.
The small runner inputs live in scratch; no source checkout or old build is copied.
Both smoke object and full executable must contain `rollback-configure`,
in addition to the eleven R6 control/token markers. Full qualification retains
exact defined IQK/HIP exports, artifact hashes, six local libraries,
Clang IQK compatibility checks and gfx90a configuration/content proof.

Validation: **17/17 model-free ELF-fixture tests PASS**, including individual
marker rejection in smoke and full-build modes. Shell syntax and pinned input
checks PASS. Publication returned **queued for smoke**. This is neither a smoke
PASS nor a qualified full executable. No model was loaded and no native rollback,
fault sensitivity or speed verdict is available. Do not republish while queued.
Stop on validated full receipt; futility on source mismatch, build/linkage
failure, STOP or deadline. Native error gate **0.743863867** is unchanged
and unevaluated by this build-only row. Parent CAFE-4 remains open.

Once smoke passes, the keeper can schedule the full build. File that receipt
before preparing a native row; preserve independent trials, matched controls,
widths 2/3 normal rc0 and explicit fault rc1, and overlapping live residency.
Existing CAFE-4 source registration and VB-SERVING-DF2 wiring task apply.

Input hashes (original files; no evidence copies):

- `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r7-20261119/candidate.cpp`: `af8bdd0e8261e200701ae9ad8fe5ed7a00070b0a0ab46d1a18d30737173bd1d4`
- `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r7-20261119/driver.py`: `615cece13691348ea362d7f8dbd33ff17ff23a88f89ec118b1f382b9085552e4`
- `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r7-20261119/cafe4_modes.hpp`: `e4c7b544a72f21014d9d3999be4d8072f03c1aa779c936416b870e6978d33e70`
- `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r7-20261119/mtp_draft_bridge.hpp`: `9688a97c3ad30e5aa008650d29a7b4d463109220b7dc48a136f9324aa2cf3919`
- `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r7-20261119/supervise.py`: `ab378fc8bd635da299c0dbe7371cfc8d42842c864473755d905fbaa9931871c2`

[no-belief: tested build-row publication only; smoke queued]

Scheduled full-build verdict (2026-11-20)
---------------------------------------

Filed `df2-cafe4-modes-hip-build-r7-20261119` **PASS**, scheduled rc0,
complete at 09:41:28Z (started 09:40:09Z). The producer validates before
writing RESULT and the row completion command validates the full receipt.
The receipt binds pinned v10 plus the diagnostic patch, exact inputs,
compiled rollback/verify-batch/fault/token/rollback-configure markers,
Clang IQK compatibility, exact defined IQK/HIP exports, HIP/gfx90a and
all six local llama/ggml libraries. No additional benchmark was run to file it.

Original evidence (paths outside the repository; no evidence copies):

- `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r7-20261119/RESULT.json`:
  SHA-256 `1e86d12f6685f05928e152e60676931a5beec31175006eb01e3dc8d8d4ecf708`.
- Executable `runs/build-jc7fsfpo/build/bin/cafe4-mtp-rollback` beneath that scratch root:
  SHA-256 `f866bc5c5f4c293e8099211c644422727b56342ed417dea406106ba85e5ac1e8`.
- HIP library `runs/build-jc7fsfpo/build/bin/libggml-hip.so.0.16.0`:
  SHA-256 `0c3c245092a22452ee1dabd6eecee9f6580e9911ca6af2edd3aef165811c2fc8`.
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe4-modes-hip-build-r7-20261119/PASS.json`:
  SHA-256 `dae805b03763ba2b75cd19653e89fddbd93ed60549634132157ce2abc93642f2`.
  Four-CPU smoke on 116–119 passed at 2026-11-19T23:46:39Z, STOP rc75;
  its validator requires the unsuppressed IQK error and identical-source fixed check.

`file_result.py` wrote the verdict and FILED receipt; the delivered completion
alert was acknowledged. The parent box stays open: this build does not establish
native model execution, rollback, fault sensitivity, residency or performance.
R6 native UNKNOWN and the fixed **0.743863867** gate remain unchanged.
Next: prepare and publish the R7 native diagnostic with these hash-bound artifacts,
widths 2/3 normal rc0 and explicit fault rc1 controls, independent trials,
matched proposal/prefix controls and overlapping live residency proof.
Existing source registration and VB-SERVING-DF2 wiring task still apply.

[no-belief: full build qualification only; no native measurement]
