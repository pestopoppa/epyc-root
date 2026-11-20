CAFE-4 rollback-isolation HIP R7 native diagnostic
=================================================

Row `df2-cafe4-modes-native-hip-r7-20261120` uses the R6 native runner
with a new scratch root and hash-bound R7 executable and six local libraries.
Snapshot mode remains zero through proposal/verification and changes at rollback.
R6 native UNKNOWN remains unchanged; this row tests the isolated candidate.

Qualified executable SHA-256:
`f866bc5c5f4c293e8099211c644422727b56342ed417dea406106ba85e5ac1e8`.
Original build receipt:
`/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r7-20261119/RESULT.json`,
SHA-256 `1e86d12f6685f05928e152e60676931a5beec31175006eb01e3dc8d8d4ecf708`.
Generated source SHA-256:
`af8bdd0e8261e200701ae9ad8fe5ed7a00070b0a0ab46d1a18d30737173bd1d4`.
`inputs.json` records the exact executable/library and runtime hashes.
Existing content-verified model identity is reused only with unchanged full stat;
no weight hashing, downloading, tokenization or copying runs in the grant.

Widths 2/3 require normal rc0 PASS and explicit injected-fault rc1 witnesses,
strict partial acceptance, target modes1/2, draft rewind and matched native
controls. The original **0.743863867** tolerance stays fixed (lower error is
better); fault differences must exceed 10x tolerance. Reference floor is separate.
Stop on all four valid cases, or first failed/missing control, STOP or deadline;
never retry or relax the threshold. Failed-case diagnostics retain token witnesses,
measurements and individual failure predicates without qualifying UNKNOWN.

The child requests -ngl 99 with its own LD_LIBRARY_PATH. Every case requires
model/all six local libraries mapped without foreign libraries, two overlapping
live per-child KFD/nonzero-VRAM samples, no cutoff and a reaped child.
Scheduled execution binds the official grant. Smoke qualifies mapping/residency
only; no rollback, fault-sensitivity or performance conclusion follows from smoke.
Existing CAFE-4 adapter registration and VB-SERVING-DF2 wiring task apply.

Validation: **14/14 model-free tests PASS**, shell syntax PASS and pinned input
checks PASS before publication. Publisher returned **GPU busy: smoke queued**
(rc0); no smoke PASS, ready status or native verdict is claimed. Do not republish.
Result path:
`/mnt/raid0/llm/tmp/df2/cafe4-modes-native-hip-r7-20261120/RESULT.json`.
Consume the delivered smoke/run event and file the native result when it lands.
Parent CAFE-4 stays open. No source tree, model, binary or log was copied.

[no-belief: tested native diagnostic publication only; smoke queued]
