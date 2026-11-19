CAFE-4 token-witness HIP R6 native controls
==========================================

Row `df2-cafe4-modes-native-hip-r6-20261119` binds the qualified R6
executable and all six local libraries from the existing full-build receipt.
It retains pre-rollback boundary, MTP proposal and target prediction token
messages in case diagnostics, including failed strict-partial-acceptance trials.
These messages explain failures and do not qualify UNKNOWN as PASS.

Executable SHA-256: `d346b6fe24397f057a367699f77b2ed0a0319f1b34f11f6682f656ab31191b77`.
Build receipt: `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r6-20261119/RESULT.json`,
SHA-256 `6579bdac406a13b5942bd8bcba8cbad8dfcee5f00a8a07545aaaa0fc277b4840`.
Candidate SHA-256: `f11d4e31bbdebf1533d42136d900076124acd8a3b59ec572c7ad3ed5bb28fbdc`.
All six library digests are in inputs.json. Model content verification reuses
its existing receipt only with unchanged full stat; no model hashing or input
preparation runs in the grant. Inputs validated before publication.

Widths 2 and 3 each require normal rc0 and explicit injected-fault rc1,
strict partial acceptance, target modes 1/2 and draft rewind. The numerical
gate stays **0.743863867**, lower is better; fault differences must exceed
10x tolerance. Stop after all four valid cases or the first failed/missing
control, STOP or deadline. No retries or threshold changes.

GPU execution requests -ngl 99 with its own LD_LIBRARY_PATH. Every case
requires the model and all six local libraries mapped without foreign
libraries, two live per-child KFD/nonzero-VRAM samples, and a reaped child.
Scheduled execution binds the official grant. Smoke establishes mapping and
residency only; no rollback, fault-sensitivity or performance verdict.

Validation: **14/14 model-free tests PASS**, shell syntax and pinned input
validation PASS. Added regression proves all three token-witness types survive
failed-trial receipt extraction without producing qualifying controls.
Existing CAFE-4 source registration and VB-SERVING-DF2 task apply; this producer
is not belief-wired. Parent CAFE-4 stays open pending native verdicts.

[no-belief: tested diagnostic runner and inference-row qualification only]

Publication (2026-11-19)
------------------------

Publisher returned **GPU busy: smoke queued** (rc0). No smoke PASS or native
verdict is claimed. Consume the delivered smoke verdict before proceeding;
do not republish while queued or in flight. Result path:
`/mnt/raid0/llm/tmp/df2/cafe4-modes-native-hip-r6-20261119/RESULT.json`.
