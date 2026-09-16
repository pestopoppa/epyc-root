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
