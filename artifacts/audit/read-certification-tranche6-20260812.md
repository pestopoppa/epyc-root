# Read-Certification Tranche 6 — 2026-08-12 (overnight)

**Certifier**: auditor (2 subagent passes over 8 files; every DEAD + headline claim adjudicated
on the main thread — one certifier verdict REFUTED and amended, three of my own briefing
context clues corrected against git by the certifiers). **Adjudicated totals (post-amendment)**:

**48 rows: 20 LIVE (42%) · 19 GATED (40%) · 8 DEAD (17%) · 1 REWRITE.**
Cumulative T4+T5+T6: **376 rows, ~41% of the ~918 backlog; blended dead-rate 25%.**

| File | rows | LIVE | DEAD | GATED | RW |
|---|---|---|---|---|---|
| vidya-belief-substrate-program.md | 12 | 9 | 0 | 3 | 0 |
| unified-trace-memory-service.md | 10 | 8 | 1 | 1 | 0 |
| tri-role-coordinator-architecture.md | 7 | 0 | 0 | 7 | 0 |
| within-role-placement-state-machine.md | 6 | 0 | **5**† | 0 | 1† |
| triattention-kv-selection.md | 4 | 1 | 0 | 3 | 0 |
| tool-output-compression.md | 4 | 2 | 0 | 2 | 0 |
| attention-matching-kv-compaction.md | 4 | 0 | 1 | 3 | 0 |
| laguna-s21-cpu-port.md | 1 | 0 | 1 | 0 | 0 |

† WP-8 amended REWRITE→DEAD on main-thread adjudication: the certifier claimed the
`compute_max_disjoint_live_concurrency` helper has "zero callers anywhere"; refuted by one
grep — `eval_tower.py:1694` calls it in production (the same generic-concurrency mechanism T4
independently certified at numa-L324, `6be6a28e`). Substance landed; only the quarters framing
was stale. Lesson re-proven: adjudicate, never relay.

## Headline findings

1. **AM Track-2 is claimed-deployed-but-DROPPED** (`attention-matching-kv-compaction.md`):
   "Decision Gate 3 PASSED / merged to production" — verified false on three axes: commits
   `81c9ad1ec`/`7784b3d9c` NOT ancestors of v9; zero `set_beta` symbols; explicit removal
   comment at `server-context.cpp:5384` ("not ported to v6"). The live compact endpoint is the
   SIBLING kernel (triattention S4 — verified live, normal hash rot properly discriminated).
   Any implementer trusting the file builds on a missing foundation; P2's "native extraction"
   shortcut does not exist. **The re-port-to-v9-or-formally-decline decision is tracked
   NOWHERE — needs an owner** (coordinator assignment; file owner corrects the status prose).
2. **SC12's window was MISSED**: the v9 final-freeze receipt carries zero ClaimTuple/
   protocol_id wiring — the exact "wire the write side before the next promotion" ask lapsed
   through the promotion it named. The belief-kernel cost realized a second time
   (benchmarks/results was the first). Task rolls to v10 with a sharper deadline framing.
3. **within-role-placement is 5/6 dead post-cutover**: WP-6/7 superseded by the deployed
   full+2-halves lineup (`burst_prefer_split` live); vision_escalation entry REMOVED 08-01
   (verified `stack_topology.yaml:353`); WP-9's target constants deleted 08-11; WP-14 landed
   with sub-items `[x]` and parent open (in-place variant again). WP-10 is the one live
   REWRITE: worker_math still has NO topology entry — re-derive against halves, not quarters.
4. **Briefing-context corrections owned (certifier caught the auditor)**: SC18 is NOT landed —
   the apparent conflict with T5-rocm's RVP-VIDYA-1 DEAD verdict resolves at levels: the
   *filing* row (add README row + program task) is DEAD-landed; the *wiring work* (SC18) is
   LIVE and the README row still says "candidate — wire BEFORE the layer ships". SC19–21 do
   not exist. SC7's own rationale cites an "EMPTY (0 rows)" inventory that has been populated
   since 07-29 — gate stands (SC6-LIVE), rationale text wrong.
5. Laguna-s21 header claims L-8 open while its own body closed it 07-29 (in-place variant,
   file #5) — also the source of the queue's row-count overestimate for the file.

## DEAD (8, owners flip)

utm:187 (NapMem nav surface landed, sub-items all `[x]` 07-11 — thinner-than-stated caveat
noted, nothing gated on it); wrp:377/380/403/408 (cutover supersessions + WP-14 landed) +
wrp:417 WP-8 (amended: helper landed `6be6a28e` and wired `eval_tower.py:1694`);
am-kv:275 L4c (justification cites a dropped foundation; reopening = the re-port decision,
which needs the owner from headline 1); laguna:124 L-9P (weights deleted 07-28, trigger
cannot fire).

## GATED highlights + rosters

tri-role: all 7 rows behind the DAR freeze — reject-path lens run: the gate is confirmed
still closed (frozen-not-unfrozen `bf900467`; operator decision L489 open — same item my T4
flagged; two tranches now converge on it). vidya SC7/SC299/SC316 (predecessors incl.
AutoPilot-stopped-since-07-27); triattention S8/S9/S3 (Package G NOT STARTED); toc L417/L448
(B42-starved telemetry; inference). LIVE rosters in the certifier transcripts; notable LIVE:
toc L449 (the trajectory-artifact prerequisite, dispatchable non-inference), utm V1-V6 (the
whole verification-memory program, unstarted), vidya SC10-SC18 core.
