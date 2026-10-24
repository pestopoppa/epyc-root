# 2026-10-24 — Campaign reconciliation checkpoint

This checkpoint reconciles the bounded S4/DS41 source work and the queued correctness jobs in
`/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/`. It does not claim inference or a live serving
measurement. No API, model, server, reload, kernel, build, compile, or live queue/calendar mutation
was performed. The canonical calendar and grants remain owned by workspace-58.

## Accepted source work

- **S4 source suite:** the valid granted job ran 13:07:58–13:08:13Z on the clean private
  orchestrator worktree at
  `/mnt/raid0/llm/worktrees/codex-ni-20261024-s4-orch`, HEAD
  `7c0f2929ebef839fdf87edf6c20adc47a564035c`. The job completed `rc=0` at 13:08:13Z; its pytest
  summary records 22 passed, 1 OpenTelemetry deprecation warning, in 1.85 s. The preceding
  22-passed/1-warning result from the wrong checkout remains retracted and is not evidence. The
  accepted run is a separate source-test warrant.
- **DS41-1017 native sidecar:** preflight, append, and second dry-run/idempotency records in
  `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/wave1/ds41-{preflight,ingest,idempotency}.json`
  show the exact five native rows
  projected to 15 frames, then zero new frames on replay (15 skipped), with no missing, refused,
  or declined records. The producer source class is already enrolled in
  `scripts/vidya/adapters/README.md`; no new source class or task was derived here.
- **M-26 native escalation counter:** the focused source run completed at 13:11:14Z with 3 tests
  passed in 2.62 seconds on source `96dc99c978a00c27d9ab130318048c4f3e44adf2`. That source is
  published on epyc-orchestrator `main` at `f279d2debddd978a2a97d42dcad4e37662bbdc09`; its root
  closeout landed at root `de6c27611` (an ancestor of this candidate base). The orchestrator
  integration commit is verified as an ancestor of current orchestrator `main` `17db`; the detailed
  owner-authored closeout is already in
  `progress/2026-10/2026-10-24-codex-ni-m26-fix.md`; it is not duplicated here. No live-store or
  teacher invocation is part of this source task.

## Failed originals and queued retries

**Scheduler snapshot: 2026-10-24 13:55:51Z.** The first request-usage run (pin `df8e89fa`) failed 6 tests, Omega (pin `c9073a20`) failed one
fixture, and output accounting (pin `b6bf5e05`) failed 8 tests. Their original logs and failures
are retained. Corrected retries are armed, not passed: request-usage at
`6e6d85ade9c29f86a58ca5bfaeff4132a2dd39b0` (poller/watcher 1213192/1213193), Omega at
`737773b4e0f89f378c5c68b620597fba41eec666` (1213198/1213199), and output at
`fbc9ed329b5f5b01e3957294639457adad7e3514` (1302326/1302327). Their respective result
directories had no completion artifact at the snapshot. The original output failure's three
stale-provenance assertions were corrected; no result is inferred from that correction. At the
same snapshot, all five poller/watcher pairs were alive; their only grant `.ended` files were the
three retained original `rc=1` failures. No corrected `.grant`, completion marker, or new test log
was present for any of the five jobs.

Two more source-only jobs are registered/queued without observed grants or results: M-26 pool
capture/reader (`codex-ni-m26-wire-20261024`, poller/watcher 958083/958084; orchestrator pin
`cf60ae80bb312b98d5a88120d079f0542f9d4ce0`, root pin
`7b7f03468ea6d26324ef4b4ed3c3c88e488addaf`) remains PROPOSED; learned-routing extraction
(`codex-ni-lrc-extract-20261024`, 1219545/1219546; pin
`d350a8478d629d006975725c05157a22f9a1a4e8`) has a passing fake-grant preflight only. All five
corrected/queued poller and watcher pairs were alive on the latest process check. Their old `.ended`
files are the preserved failures; no corrected `.grant`, completion, or test result was present.

**Scheduler update: 2026-10-24 14:02Z (main's verified read).** No new grant or result was observed
for these five jobs. workspace-58 says quarter-queue grants stop when
`HOLD_GPU_FOR_QUIET_20261024` is set for the whole-host C4 → C5 → INF66 quiet block; the queued
correctness jobs may wait until after the planned v11 CPU slot around 22:05Z. Treat this as a
possible wait boundary, not a confirmed start time; the earlier ~14:19 placement estimate was not
confirmed.

**Result update: 2026-10-24 14:12Z (owner-reviewed scheduling records).** Existing grants produced
these results; no rerun or new grant was started for this checkpoint:

- Request-usage retry at `6e6d85ade9c29f86a58ca5bfaeff4132a2dd39b0` completed 24 passed, 2 warnings
  (`request-usage-v2/COMPLETE`, `test.log`).
- Omega retry at `737773b4e0f89f378c5c68b620597fba41eec666` completed 9 passed, 1 warning, and the
  synthetic dry-run (`omega-v2/COMPLETE`). This records the validator retry only; the Omega root
  adapter remains unimplemented while its producer is unstable.
- Output accounting R2 failed 1 test and passed 30 on the classification fixture; corrected R3 is
  armed, not passed (`request-output-v2/FAILED`; `request-output-v3` has no accepted result).
- LRC extraction failed 1 test and passed 3 on label order (`lrc-extract/FAILED`).
- M-26 pool-wire failed 2 root tests and passed 3 on the boolean and numeric observation carrier;
  the orchestrator phase did not run (`m26-wire/FAILED`). It remains a source-task finding under
  owner review, not closure of a parent implementation task.

The original failures remain retained. These five source-unit outcomes do not close implementation
parents; each owner/main review boundary remains in force. No additional job or live scheduler poll
was performed here.

## Open boundaries

- **S4 live proof:** workspace-58 reports the registered serving stack is down and its S4-T1 row is
  BACKLOG. The serving owner must name the stack bring-up window before the proof can be scheduled.
- **NIB2-98:** the source audit found the proposed 100 GiB residual-memory rule in
  `artifacts/operator/host-memory-rules-20261021.patch`, SHA-256
  `97072d8a3b04672024646d66d5f3ddbaccbe2c2d0868332147ee6c32de423741`; the required ratification
  receipt is absent from fresh `origin/main` (`23db24709`), which still labels the bundle
  prepared/not applied. The 13:55 claim snapshot showed this held only for the existing OP-HOSTMEM
  operator-only application; main released the claim at the later ownership refresh because no
  source implementation is active. The operator task remains open. No helper or live admission
  behavior was changed; do not describe the 100 GiB rule as applied or ratified.
- The Omega root adapter implementation remains paused in its clean implementation worktree until
  its producer is stable. The corrected Omega source-test retry is independently queued above.
- M-26 pool capture/reader remains a separate proposed source task; at the 13:55 scheduler/claim
  snapshot no M26-wire claim or validation result was listed. Main later added and claimed the
  exact `VB-M26-DISTILL-POOL-WRITE` task before releasing the completed original M-26 claim after
  root closeout was verified. No pool capture/reader validation result is claimed here.
- The existing DS41-1017 source/adapter enrollment already covers the five-row append. RTG-50
  DB-1 and DB-2 source findings were recorded in separate commits `25645248f` and `f212297db`;
  the main-reviewed RTG-50 next action now points to archival during an operator-invoked wrap-up.
  The index row remains present until that operator cadence; this checkpoint does not prune or
  archive it.
- Claim audit at 13:55:09Z listed DB-1, DB-2, VB-DS41-1017-AKSCOPE, S4-T2, LRC-RI-EXTRACT-SOURCE,
  NIB2-98, and original M-26 as claimed by `codex-ni-01a16d6b`; no bulk release was performed.
- Claim refresh at 14:03:30Z showed DB-1, DB-2, VB-DS41-1017-AKSCOPE, S4-T2,
  LRC-RI-EXTRACT-SOURCE, and the new `VB-M26-DISTILL-POOL-WRITE` claim. NIB2-98 and original M-26
  were no longer claimed. No claim mutation was performed by this checkpoint.
- Coordination refresh files `coord-refresh/workspace-58.json`, `workspace-f8.json`, and
  `bark-intake-stage3-plan.json` confirm no scope overlap: workspace-f8/workspace-7b are handing
  inference/calendar ownership to workspace-58; session `3c4ca599` retains champion/kernel work.
  Keep all paths named by those replies protected; no cleanup or cross-session message was sent.
  workspace-58 inherits the approved API-only reload after `nib2-gnx1-reindex-2` fast-forwards;
  this checkpoint did not execute it. Kernel learnings route to `3c4ca599`; production kernels
  remain untouched.
- Coordination audit: older service-scoped agent-log invocations overwrote the main session marker.
  Main recorded the correction in its own session `ses_20261024_134913_1409539`; historical log
  events remain untouched. No runtime or process state changed.

## Review and validation notes

This candidate is based on fetched root `origin/main` at `023a75f7d962f0287b76c3e3d7663c5f8e00a516`.
Root GitNexus remained stale (indexed 10/23 at `bfb43f9`); no re-analysis was attempted without
CPU admission. A targeted impact query for the existing orchestrator symbol
`get_role_max_concurrency` reported LOW/exact with zero upstream callers; it is navigation only,
not a claim about changed source, and no root graph blast-radius assertion is made. No code or
symbol refactor was performed. The README freshness check exited 0 with no warnings.
`python3 scripts/vidya/cli.py sync --check` reported `ledger FRESH` at intake-2510 (2,491 entries;
zero lag; last sync 2026-10-22T21:34:42Z). The operator-cadence wiki compilation sweep, index
pruning, archival, and compaction were deliberately not run.

**Preparation audit correction (2026-10-24).** The first reported DB-1 `git apply --check` failure
was run from the source worktree where those hunks were already present; its self-application errors
were incorrectly reported as fresh-target conflicts. No target conflict or peer edit was involved.
With the explicit target path and a captured clean `23db24709` target, the reviewed two-path DB-1
patch checked and applied cleanly. In the final publication candidate based on `023a75f7d`, the
DB-1 and DB-2 docs were committed separately; DB-2's patch was replayed as its approved handoff
append after an intentional progress sentence cleanup changed the old patch context. No semantic
or peer-file conflict occurred. The RTG-50 next-action cell was copied exactly from main's reviewed
change; the row remains until operator-cadence archival.
