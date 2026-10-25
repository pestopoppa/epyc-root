# 2026-10-25 Codex NI major-boundary checkpoint

**Evidence cutoff:** 2026-10-25 10:04:55Z. **Root base:** refreshed `origin/main` at
`2d934313eff5390973afe5beb445c1583d40d942`. The prior published tally remains 17 tracked
closures (9 original, 6 scoped, 2 wiring). NIB2-103 is on research main; the latest owner reply
only says the parent tick is in progress. This checkpoint does not claim an 18th closure or
revise the 2026-10-24 cutoff.

## Evidence and current state

- **AK startup diagnostic:** the official off/on diagnostic completed at 09:39:52Z. JUnit
  records 2 cases, 0 failures/errors/skips, 4.710 s. Workspace-58 marked `NO_REPRO` at
  09:44:48Z. This closes only the diagnostic; the original startup-flake root-cause task stays
  open. Evidence:
  `/mnt/raid0/llm/tmp/codex-ni-20261024-ak-startup/packet-v2/runs/20261025T093946Z-2209481-nMACp2KN/{junit.xml,classification.txt}`.
- **EG2 job 14:** the granted r3 runner ended rc=1 at 09:50:07Z because its expected count was
  wrong. Independent reconciliation established 37 explicit roots -> 42 exact JUnit identities
  (35 singletons + 3 role values + 4 Q combinations); identity diff is empty, the roots have no
  defects, and all 53 source hashes verified. The 44-case assertion double-counted parameterized
  roots. Workspace-58 reconciled the canonical job COMPLETE at 09:58:52Z, retaining the original
  rc=1, `FAILED`, `status.json` and logs. This is not a fresh passing run. Kuzu remains explicitly
  unvalidated; do not alter r3 or rerun job 14. The approved v4 identity gate is for the next EG
  run only. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261025-eg2-reconcile/REPORT.md` and
  `/mnt/raid0/llm/tmp/codex-ni-20261025-eg2-recovery/eg2-side-calls-r3/`.
- **NIB2-103:** commit `9eee9121d215f911363f0cee29808bf49cea3d1a` was pushed to
  `codex/nib103-template-durability-20261025`; publication log confirms all six pinned diffs and
  the two-file commit. At 10:01:27Z workspace-58 confirmed review and said it was merging to
  research main and ticking the parent. Fresh research `origin/main` contains this SHA; the
  latest owner reply does not confirm the parent tick, so the root parent checkbox and aggregate
  tally are not claimed here. Evidence:
  `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/nib2-103-publish/{publication.txt,job.log}`.
- **INF66-AFF-1:** granted q2 regression completed 09:48:27Z (CPUs 48–71, 24 threads), with
  64 passed in 1.88 s and both edited-file hashes rechecked. Normal hooks passed; commit
  `cb86b6cfd9687c4e3b16008b7643c447b65bed68` was pushed to `codex/inf66-aff-1-20261024`.
  Workspace-58 confirmed re-pin to that SHA and re-armed inf66 for its 19:30Z whole-host window.
  No inference outcome is claimed. Evidence:
  `/mnt/raid0/llm/tmp/codex-ni-20261025-inf66-aff/{COMPLETE,run.log,poller.log}`.
- **G1:** the first poller PID 2249672 exited before its grant and ran no test. The corrected
  runner then completed rc=0 at 10:04:50Z. Synthetic cases verified that rc=134 and 7 propagate,
  a later PASS does not clear the prior failure, and ANSI/plain/empty OK counts work; proposal
  `bash -n` checks passed and all four pinned inputs were unchanged. Main accepted the result and
  notified the owner. This validates only the proposed synthetic regression; no real gate/fold
  call occurred. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261025-g1-verdict/{validation.log,status.txt}`
  and `PROPOSED.md`.
- **HPR-B-SIM-FIX-2:** the owner verified 98 functional tests passed. The recorded CPU affinity
  was 192 CPUs rather than the granted q3 CPUs 72–95 plus SMT 168–191; Filler8's region lock
  does not pin the job. Grant CPU pinning therefore failed, so make no execution-isolation or
  performance claim. The native contract remains **UNVERIFIED**, and the historical INVALID
  result is unchanged. The proposal was pushed at `c4c2a3638` to
  `codex/hpr-b-sim-fix-2-20261025`, but no parent closure is claimed. At 10:01:27Z the owner
  registered a new row; next is a predeclaration, source-enrollment draft and golden-parity row
  with a pre-run affinity readback assertion, due 10-26 12:00Z. Owner will merge the proposal
  only with golden-parity PASS.
- **V11-086-SLOW-1:** diagnosis remains that candidate B's `tg32@d32768` was terminated by the
  driver's 3,000 s timeout, leaving the declared A/B result incomplete/hold. Workspace-58 chose
  a bounded one-quarter B-vs-C probe with thread/`wchan` observation and no 8 h booking. The
  owner is handling that probe on q1; it is owner-scheduled, and no result is included in this
  cutoff. Report:
  `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/tasks-from-ws58/V11-086-SLOW-1-REPORT.md`.
- **AKX-LB32-OVERHEAD-1:** updated control-v2 proposal specifies same-source fresh profiler
  OFF/ON builds, GM/MG order at both thread counts, run identity/resume guards, build/compiler
  attestations, and prospective same-family writer/adapter schema-v2 capture. The owner asked
  for a FILEPATH-filter correction and stale-B0 resume guard; those are represented in the new
  patch set. It remains untested and awaits main/owner review before integration or any grant.
  Target is before 10-26 12:00Z; existing ±5% gate and historical INVALIDs stay unchanged.
  Packet: `/mnt/raid0/llm/tmp/codex-ni-20261025-akx-lb32-control-finish/REVIEW-AND-GRANT-PLAN.md`.
- **VB-FOLDGATE-WRITE:** assigned parent task remains open. Optional AKX writer/adapter fixes
  and their test-row preparation are not parent completion. No second source family or grading
  ladder is proposed.

## Delivery, misses, and remaining queue

The boundary receipts `BOUNDARY-2-RECEIPT.json` and `BOUNDARY-3.receipt.json` record
`socket_sent` with recipient confirmation pending; they do not prove delivery. Actual owner
acknowledgments are the later 09:58:52Z EG2 reconciliation and 10:04:55Z G1/HPR update, plus the
earlier AK diagnostic and EG2-r2 replies.

EG2 and AK startup missed original 03:00Z deadlines; AK diagnostic is now complete and EG2 has
been reconciled with its failed-run provenance intact. INF66 missed 05:30Z but its corrected
source/test publication is complete and re-armed for the owner window. HPR-B-SIM-FIX-2 and
KPF18-R4-FORK-CODEREAD-1 missed 08:00Z; HPR has a new queued task, while the latest owner reply
does not acknowledge KPF18 completion.

| Task | Deadline / state | Next action and dependency |
|---|---|---|
| G1 | 10-25 14:00Z; synthetic regression complete | Main accepted rc=0 regression result; no real gate/fold call. |
| V11-086-SLOW-1 | 10-25 12:00Z; owner probe on q1 | Owner completes bounded B-vs-C probe; no 8 h booking. |
| AKX-LB32-OVERHEAD-1 | target before 10-26 12:00Z | Main/owner review of v2 patch and amendment before integration/grant. |
| HPR-B-SIM-FIX-2 | 10-26 12:00Z; new row queued | Prepare predeclaration, source-enrollment draft, golden-parity row, and granted-affinity readback. |
| AKX-ALL-31 | 10-26 12:00Z | Proposed non-finite/fp32 accumulator gates, planted controls and test. |
| LOOP-SAFETY C1 / C2 | 10-26 12:00Z / 18:00Z | Reader pin, then fail-closed changes, in assigned order. |
| VB-FOLDGATE-WRITE | 10-26 18:00Z | Structured records, strict adapter, CLI ingest; highest-priority T1 item. |
| T1 blockers | 10-26 18:00Z: RTG-57, EVL-50, UFH-01, INF-67, RTG-58, INF-26; 10-27 18:00Z: INF-50, INF-64, INF-62, INF-73, EVL-37, INF-78, INF-81; 10-28 18:00Z: INF-74, UFH-12, UFH-08 | Continue from `tasks-from-ws58/T1-BLOCKERS-BATCH-20261025.md`; INF-67 remains model-scoped to qwen4exp/v10. |
| BATCH-2 canary defects / calendar briefs | 10-26 18:00Z | Continue from `tasks-from-ws58/BATCH-2-20261025.md`. |
| META-ASSERT-1 | 10-27 18:00Z | Read-only diagnosis and proposed champion-line fix; GPU test requires owner grant. |
| KPF18-R4-FORK-CODEREAD-1 | 10-25 08:00Z missed; no completion acknowledgment | Main checks current report state; do not infer completion. |
| NIB2-103 publication | pushed; owner says merge/tick in progress | Await owner confirmation before root checkbox/closure tally changes. |
| INF66-AFF-1 | passed/pushed; owner re-pinned/re-armed | Owner's 19:30Z whole-host window owns the next inference result. |

No handoff checkbox, canonical index row, index-state artifact, source table, queue/grant/writer,
shared checkout, kernel tree or kernel store was edited by this checkpoint. These are evidence
and coordination updates only; no new ClaimTuple class or grading rule is proposed.
