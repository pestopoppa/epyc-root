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
