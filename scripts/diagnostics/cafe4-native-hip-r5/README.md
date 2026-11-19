CAFE-4 failure-attribution HIP R5 native controls
================================================

Row `df2-cafe4-modes-native-hip-r5-20261119` ports the CPU failed-control
receipt retention into the GPU runner. Every completed case retains numeric
measurements, individual failed predicates and native trial/control messages
separately from qualifying controls. Missing, ambiguous, malformed and nonfinite
measurements remain UNKNOWN and JSON safe. Diagnostics never turn failures
into PASS. The first failed native case stops the run without retry.

The error gate stays **0.743863867**, lower is better; even an otherwise passing
record with another tolerance is rejected and diagnosed. Exact normal rc0 and
explicit injected-fault rc1 witnesses, strict partial acceptance, target modes
1/2, draft rewind and fault differences above 10x tolerance remain required.
Widths 2/3, the frozen prompt and diagnostic scope are unchanged.

The runner binds the qualified failure-attribution R5 executable SHA-256
`c4ab059f9bdece22e8dd2f1d008c937bf54851a5201de0dd7b318bed41932ea8`
and all six local libraries in `inputs.json`. Build receipt is retained in place:
`/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r5-20261119/RESULT.json`, SHA-256
`667dc2e6172db65e705f1084bd890e567615bfc97f4ea0aeda343c36d2359d75`.
Candidate SHA-256 `e6546aa7417e40efecdd2bb03de61416bf62ae21b7c1369b7161e443201f835d`.
Existing build qualification was filed before this turn; no rebuild claimed.
Model verification reuses the prior content receipt only with unchanged full
stat. Prepared input validation passed before publication; no model hashing or
input preparation runs in the grant.

GPU safeguards are retained: -ngl 99, explicit local LD_LIBRARY_PATH, all six
expected libraries and model mapped without foreign libraries, and two live
per-child KFD/nonzero-VRAM samples. Scheduled results bind the official grant.
Smoke qualifies mapping/residency only and stops cleanly through engine STOP;
it establishes no numerical, rollback, performance or general CAFE-4 verdict.

Validation: **13/13 model-free tests PASS**, launcher syntax and pinned input
checks PASS. Child-spy regression exercises GPU residency sampling, failed
case receipt persistence, UNKNOWN and immediate stop after one failed case.
Fixed-tolerance mismatch has a dedicated diagnostic/qualification regression.

Publication returned **GPU busy: smoke queued**. No smoke PASS or native verdict
is claimed. Parent CAFE-4 remains open. Result path:
`/mnt/raid0/llm/tmp/df2/cafe4-modes-native-hip-r5-20261119/RESULT.json`.
Existing CAFE-4 source registration applies; this producer is not belief-wired.
[no-belief: tested runner and queued row publication only]

Delivered smoke qualification (2026-11-19)
-----------------------------------------

Publisher smoke **PASS** at 21:47:17Z, one unit, engine STOP rc75 after
11 seconds, placement `mi210_0,184-191`. Row is grantable; do not republish.
The retained native smoke receipt records model and all six expected local
libraries mapped, plus two distinct live child KFD samples, each reporting
**37,525,798,912 VRAM bytes**. This qualifies mapping/residency only; scheduled
widths 2/3 and explicit fault controls remain pending under the unchanged gate.

Evidence retained in place:

- `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe4-modes-native-hip-r5-20261119/PASS.json`
  SHA-256 `43eb991c8fe58f4856ea46a8ffd3a9b62d8a51765d8d681c77febb05ad8ad447`.
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe4-modes-native-hip-r5-20261119/native-attempts/attempt-totzpi9j/native-result.json`
  SHA-256 `b8551e496a86dada7a78fa464896f52c4e292f827d297e4f4395e463a869baeb`.

[no-belief: native smoke qualification only; no rollback verdict]

Scheduled native verdict (2026-11-19)
-------------------------------------

Filed **INCONCLUSIVE / UNKNOWN**, scheduled rc2 at 22:22:01Z. Width-2
normal stopped at the first failed native control. Both target mode1 and
mode2 reported `stage=strict-partial-acceptance draft=2 accepted=0 sampled=-1
selected=0 faulted=0`. Observe/fault lifecycle controls failed; off/observe
and off/fault prefixes and draft tokens differed. Qualifying controls and
diagnostic measurements are null. These messages locate the failure stage;
they do not establish why the trials diverged. The other three cases did not
execute, including both explicit injected-fault exit controls.

The model and all six local libraries were mapped. Two live child KFD samples
each recorded **37,525,798,912 VRAM bytes**; no cutoff, child reaped.
The **0.743863867** error gate (lower is better) is unchanged and unevaluated.
No rollback, fault-sensitivity, performance or full CAFE-4 conclusion follows.
Parent remains open. Diagnose the mode-specific trial/prefix construction and
strict partial-acceptance selection before publishing another native attempt;
do not relax the gate or count internal fault messages as explicit rc1 controls.

Evidence retained in place (no copied native artifacts):

- `/mnt/raid0/llm/tmp/df2/cafe4-modes-native-hip-r5-20261119/RESULT.json`,
  SHA-256 `340863a393b964d58a72038cc584ed5bbcb7eb1e547e0b225a4dde75f4db6144`.
- `/mnt/raid0/llm/tmp/compute-flags/grants/df2-cafe4-modes-native-hip-r5-20261119.ended`,
  SHA-256 `6d9f07ed80ecf816d64ff589eecb232baa4cd19f85c50cc93fa6769ad8a5cd07`.
- Native case log path is recorded in RESULT; log SHA-256
  `11452aad40b7eb269b35bbb5e283b199b94d65eaf560799b46cb57def233fa21`.

Existing CAFE-4 source registration and VB-SERVING-DF2 wiring task apply.
[no-belief: inconclusive single-prompt diagnostic; producer not belief-wired]
