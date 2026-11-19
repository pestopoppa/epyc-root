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

Scheduled native verdict (2026-11-19)
-------------------------------------

Filed **INCONCLUSIVE / UNKNOWN**, scheduled rc2 at 23:32:14Z. Width2 normal
mode1 proposed `32,16106` and accepted zero; modes0/2 proposed `248068,271`,
matching the first target prediction and mismatching the second (`198`).
Boundary token was `271` in all modes. Observe lifecycle and matched prefix/draft
controls failed. Controls/measurements are null; other three cases unexecuted.
The fixed **0.743863867** gate remains unevaluated. This localizes the symptom
to the mode1 proposal/control path; it does not establish its root cause.

Model and all six local libraries mapped; two live child KFD samples each
reported **37,525,798,912 VRAM bytes**. No cutoff; child reaped. Original result:
`/mnt/raid0/llm/tmp/df2/cafe4-modes-native-hip-r6-20261119/RESULT.json`,
SHA-256 `197f30cda373d574a1b06a5c395bbb5c366e472d8f39fdaebef025c09fa452a4`.
Native log SHA-256 `4a32d90a1969bf43288f472513c0845511bf4fb0cdcf65aa3bf9c23e1f3fefb9`.
No threshold change or retry published. Diagnose mode1 state/proposal isolation
before another native attempt. Parent CAFE-4 remains open.

[no-belief: inconclusive single-prompt diagnostic; existing producer registration applies]
