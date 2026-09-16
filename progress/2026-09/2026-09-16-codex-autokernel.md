# AutoKernel coordination and GLM relaunch — 2026-09-16

The archive-backed disk retirement completed first: 224/224 reviewed dirty
worktrees have `removed` receipts, 224 content-addressed archive records remain,
and host free space rose from 382,977,454,080 to 742,153,621,504 bytes. The
transiently scanner-held row was safely retained and then resumed. See
`2026-09-16-autokernel-dirty-retirement.md` for the exact manifest and guard.
Root `main` published the cleanup and prospective acceptance lifecycle as
`b65138a0`; 61 focused tests and the handoff index check passed. Frozen v9
verification still passed after the cleanup. The old coverage-run 57.5 GiB
growth was a `llama-cli` REPL output-file runaway, not a demonstrated RAM leak;
the valid rerun used single-turn, closed stdin, a timeout and bounded output.

GLM-5.3-Flash CPU AutoKernel resumed from its retained worktree/store as v14 at
`/mnt/raid0/llm/tmp/aku-glm53-continuous-20260916-v14`. The startup dry run
passed. The serial disk guard saw over 680 GiB free and removed no cache. Batch
0 acquired exactly q0+q1 (`cpu_region` and GLOBAL locks) for a half-core screen;
the GPU runner held `mi210_0` separately. The real CPU profile ran. Its author
truthfully abstained from `akm-moe-down-weight-store-fusion`: the required IQK
store change would cross the permitted one-file source boundary. The child
published `status=abstained` after 641.9 seconds, with no measurement or keep.

The serial scheduler then stopped v14 with
`SerialSchedulingRefused: scheduled child outcome is unsupported: abstained`.
This is a scheduler/accounting defect, not a performance null or an actor/provider
failure. The canonical GLM store, accumulator (27 retained keeps), COR and
anchor `34a8b446f9e9283f54e73c96d3143ad411ed4d39` remain intact. v14
completed one batch but is **not running**; do not treat its last status as live.
A narrow scheduler fix with fresh-process recovery tests is in progress in an
isolated research worktree. Relaunch only after that fix is validated and
integrated; keep the same store and a fresh serial state directory.

Historical contention evidence does not establish a q3-only full-core CPU
throughput penalty. In an active GPU-bench overlap, full-core CPU decode fell
about 7%, while the CPU A/A p95 widened from 0.80% to 7.223% (2.151% in an
adjacent subset). The channel included DRAM-bandwidth contention, not merely
the eight q3 SMT siblings. Reduced q0+q1 CPU screens may coexist with GPU work;
full-core confirmation requires a quiet window. The operator will notify this
session when the current GPU work ends. No current GPU-claim holder was stopped.

Read-only intake handover exposed an exact old-champion pin in the separate GPU
discovery factory. A narrow descendant-aware reviewed-instrument fix was tested
in an isolated branch, but the current champion still differs in six of ten
sealed GPU target source files. GPU static discovery needs a newly reviewed
champion-specific source package/template/profile/bundle, not an exception to
the old seal. The GLM CPU serial loop does **not** call that factory, so this is
not its relaunch blocker. The enum-source prior-art pin was separately converted
to ancestry plus enum-block hash verification in an isolated branch.

Per-surface recipe binding was also implemented and tested in an isolated branch
without mutating the live store. A read-only GLM bind replay against an existing
matched-process-v2 COR floor passed with effective
`GGML_NOHUGEPAGE_PROCESS=1`; no re-baseline is needed for that exact frame.
Adopt only at a completed batch boundary, rerun the documented dry-run and bind
once before the next launch. A missing legacy sidecar remains explicitly
`unverified`, never silently verified. U3-SEED's variance-only keep rule remains
under the explicit `OP-AKU-U3` scientific-admission decision; no threshold was
invented during this relaunch.

Operator-invoked wrap-up synchronized NIB2-72 (the closed coverage REPL runaway)
and NIB2-77a (the approved disk retirement), removed the resolved OP-43a/43b
decision queue entries, and kept NIB2-77 open for the untouched 187 frozen-clone
lanes and prospective cleanup observation. The AutoKernel wiki chapter now
compiles nine content-hash-drifted sources, including this GLM abstention
observation. The handoff index check, wiki lint (zero errors), and README
freshness check passed; the shared wiki watermark was advanced after synthesis.

The dashboard's repeated v12 "unexplained stale" banner was traced to the
running hub's inherited `AUTOKERNEL_LOOP_STORE_ROOT` pin, despite v14 publishing
an explicit terminal `failed` report. A producer/reader pair now uses the
canonical `current-serial-run.json` pointer: the serial launcher writes it
atomically at startup/terminal with a run identity guard, and the hub selects
that status per request without redirecting champion or knowledge history.
The legacy env root is only a fallback. A bounded, trusted-root check rejects
invalid pointers. The pointer was initialized to the already-terminal v14
artifact; the new reader reports that exact `failed` notice in a local
integration check. Root dashboard tests passed 75 tests/8 subtests before the
final trusted-root addition, then 25 focused tests passed. Live hub deployment
and a future pointer rollover remain the acceptance checks in AKU-09l.

The dashboard correction was published to research `main` (`8b3b95f6`) and root
`main` (`7ec9f779`). The new watchdog intentionally would not synchronize a
lane-owned served checkout; its old supervisor had exited. The exact published
`dashboard/loop_status.py` blob was applied to the served lane (hash
`780bd03f646f8644eb91dcbdeb3a4a23ef21fba3`, equal to root `main`), and the
owning watchdog performed its normal source-change restart. The hub relaunched
at 10:28:33 UTC as PID 845837. Live `/api/loop` then named v14's
`loop-status.json`, selected by `current-serial-run.json`, with notice
`failed`/`run_state=failed`; the stale v12 notice disappeared. A next-launch
pointer rollover has not yet been exercised and remains open in AKU-09l.

After the live dashboard correctly exposed v14's failure, the narrow serial
abstention settlement fix was integrated and promoted to research `main` as
`fb8a8273`. The exact v14 `complete/{abstained:1}` continuation now maps to
`abstained`; nine focused tests pass. No measurement, keep, floor or retained
store was changed. The loop is still stopped; relaunch and the dashboard's
fresh-pointer rollover check await the operator's notice that shared GPU work
has ended, so full-core confirmation can use a quiet measurement window.

## GLM continuous relaunch and live correction (10:52–12:02 UTC)

At the operator's direction, the half-core q0+q1 GLM campaign was relaunched
without resetting the retained store. v15 reached original-request profiling,
but its CPU history hint timed out on the 4.7 GB journal: an unindexed
`recorded_at` sort exceeded the 200 ms hint deadline. The hint-only query now
uses reverse append order and a payload-size metadata check; the live query
fell from an interrupted read to about 2 ms, and 56 focused tests passed.
The research fix was promoted to `main` as `a7100681`. v15 was intentionally
stopped before a candidate measurement; its zero-measurement batch is not
counted as research progress.

v16 then completed the first full candidate path: profile → planner → critic
→ source patch → build/correctness → five-pair `matched_process_v2` CPU A/B.
`akm-moe-fused-global-slab-balance` measured −0.953% against retained anchor
`34a8b446f9e9283f54e73c96d3143ad411ed4d39` with a 0.708% acceptance
floor. It was not kept; the 27 retained keeps and anchor were unchanged. The
serial supervisor automatically started batch 1. That batch was deliberately
stopped during formation to apply a reporting fix; its `stopped_mid_formation`
outcome is unmeasured, not a performance result. The v16 state and both
continuations are retained at
`/mnt/raid0/llm/tmp/aku-glm53-continuous-20260916-v16`.

The reporting defect was concrete: a decisive negative was labelled
`measured_null` and described as failing to clear the floor. Source outcomes
now use `regression` for decisive negatives while sub-floor negatives remain
nulls; scheduler, memory, status and exact-attempt consumers accept that
status. No keep/accumulator rule changed. The research correction passed 232
focused tests and reached `main` as `be6bbad9`. The root dashboard now counts
regressions as measured candidates (`5a1250ff`); three focused dashboard tests
passed. A separate live dashboard correction surfaces the exact-joined,
fresh child stage in the headline rather than only “serial routing”
(`6e85d3b5`). The hub auto-restarted after the served-lane edit; live
`/api/loop` followed v15→v16→v17 and displayed v17's profiling stage.
The page JavaScript DOM harness rendered that live v17 API response without
an exception and named the current run, target and child evidence; AKU-09l's
fresh-pointer rollover acceptance is complete.

v17 is running continuously from the same GLM store at
`/mnt/raid0/llm/tmp/aku-glm53-continuous-20260916-v17` (`--rounds 0`). Its
first child holds only q0+q1 and is profiling. The requested 20 completed
v17-batch observation is in progress; no claim of 20-loop completion is made.
The production v9 tree was not touched. CPU lifecycle census exceeded its
2,048-process/0.1 s diagnostic bounds during v16's A/B and therefore cannot
support a clean-contention claim; it did not report detected contamination,
and current CPU admission treats the census as diagnostic. The negative
candidate was rejected regardless. Do not reinterpret that incomplete census
as proof of a quiet host.

## Half-screen accumulation restored and v18 continuous run (12:02–13:30 UTC)

v17 completed a valid five-pair half-core matched-process screen for
`akm-moe-private-down-cohorts`: +0.545% against the same retained anchor, below
the 0.708% floor. It was classified `measured_null`, and the screen path failed
to retain it as a provisional positive. This was a real regression from the
original accumulator contract, not evidence that the source change has no
value. The patch archive, binary, native capture and exact receipt remain in
the canonical store. v17 batch 1 was intentionally stopped during profiling to
apply the narrow correction; it produced no measurement.

The live half/quarter CPU screen now retains calibrated, stationary positive
results as provisional `keep_candidate`s even when individually sub-floor.
The original full-target confirmation remains mandatory before a candidate
enters the working accumulator or promotes a full champion; a reduced screen
alone cannot claim either result. The planner-feedback path also no longer
rebinds an accumulated comparison to the old campaign CoR. Research commits
`3c1e9e98`, `0f8bd68c` and `2eab7a48` are on the live lane; the corrected
research main is `e4576171`. The focused combined suite passed 54 tests.

The retained v17 +0.545% patch can be re-evaluated without falsifying its
immutable old receipt. An isolated one-shot recovery implementation is in
research branch `codex/half-screen-accum-20260916` at `e455ad2b`, with 114
focused tests. It verifies the old continuation, patch, source/build identity
and then requires a new full-core oracle and A/B. It is deliberately not
merged into the continuous loop: full-core q3 confirmation must wait until the
other session's MI210 queue releases its claim, and the one-off CLI deserves
review at that boundary. The old candidate is preserved; no store was reset.

v18 launched continuously with the corrected path, `--rounds 0`, in
`/mnt/raid0/llm/tmp/aku-glm53-continuous-20260916-v18`. At 13:29 UTC its
status and the canonical store were fresh, with the child in critic pass 1.
The dashboard followed the new run through the current-run pointer. This GLM
run is CPU-only (`-ngl 0`) on q0+q1 and will not claim the MI210 while
workspace-57's serialized GPU queue is active. One real completed batch
has been observed since the v17 health checkpoint; the requested 20-batch
watch remains in progress. No GPU or full-core q3 measurement was launched,
and production v9 remains frozen.
