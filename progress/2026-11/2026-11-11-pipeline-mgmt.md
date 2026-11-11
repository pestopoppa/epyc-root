# 2026-11-11 — pipeline-mgmt

## Landed today

| Item | Commit(s) | State |
|---|---|---|
| Diskpause fixes | `bf32c44db`, `9a50a55d0` | deployed |
| Keeper vault prune fix + 282.9 GiB vault prune | `8ef80ba2a` | done |
| ram_admit | `705f7576a` | landed |
| Opencode V2 plugin | `2fd3d327e` | landed |
| DSpark graveyard row | `f7a95d276`, `114c0f77c` | recorded |
| Worktree salvage (18 trees removed) | `19ff1a8a3` | recorded |
| LR-11 bundle | `cb07709f8` | **awaiting operator signature** |
| 13 operator decisions recorded | root `8744c142b`, `09ae74242`; orchestrator `a0062fe0` | recorded |
| C10 floor accept, research half | research `13a0678ee`, `520395b72` | on main; root receipt waits on operator re-run |

## Operator decisions today

- INJPOLICY goes live at relaunch.
- AUD10 hook is kept.
- D9 "Cap backfill at T": drain backfill is capped at the deadline.
- D9 "Requeue same id": a row cut by the cap is requeued under its own id.
  The two D9 items are being implemented by a separate subagent (rowflow.py); not part of this wrap-up.

## Filing audit (UNFILED-ENDED 7 → 1)

`queue_status.py` counts rows with a `ready/<id>.json` manifest and a `grants/<id>.ended|.complete` but no `filing-done/<id>.FILED`.

| Row | Owner | rc | Class | Resolution |
|---|---|---|---|---|
| pip02-r36-english-run-20261107 | operator-adhoc-ops-20261105 | 1 | superseded by `...20261107b` (FILED, PIP02-PHASEC-ENGLISH-RUN ticked) | FILED SUPERSEDED by pipeline-mgmt (`file_result.py --no-reclaim`) |
| vidya-r234-native-sweep-20261104 | operator-adhoc-ops-20261105 | 75 | superseded by `...20261104h` (PASS, recorded in vidya-belief-substrate-program.md:163) | FILED SUPERSEDED by pipeline-mgmt (`--no-reclaim`) |
| ak-c10-q38fn-floor-r3/r4/r5 | autokernel | 0 | complete | FILED by autokernel during the audit; handoff notes for r3–r5 missing on main (forwarded) |
| ak-mmq-h10b-dense-ctxstate-bracket-20261110-r2 | autokernel | 75 | cut | FILED by autokernel during the audit; no handoff note (forwarded) |
| vidya-kvq-v10-sweep-20261107 | operator-adhoc-ops-20261105 | 1 | failure | **still unfiled**: no result or failure note in VB-KVQ-V10-INGEST; forwarded to owner |

Two manifest-less ended rows not counted by the script: `c7-q38-ppl-bisect-20261106-r2` (main-inf22, rc 0, its box AK-ASM-C7-Q38-BISECT already ticked) and `c2-q38fn-aa-floor` (complete, no handoff hit). Both forwarded; they need `file_result.py --no-manifest` from their owner.

No boxes were ticked: none of the rows is owned by pipeline-mgmt. [no-belief: filing audit, not a result]

## Wrap-up 2 (since 956c95b54)

| Item | Pointer |
|---|---|
| `c2-q38fn-aa-floor` filed WITHDRAWN (operator skipped it 10-22) | filing-done |
| `vidya-kvq-v10-sweep-20261107` filed as a failure; VB-KVQ-V10-INGEST stays open | root `dda834b43` |
| Index regen | root `4b852fb82` |
| C10 accept script path-set fix and C10 floor ratification | root `888481bc8`; research `13a0678ee`, `520395b72`, `e3aac480b` |
| LR-11 signed; OP-LR11-LR13 queue row removed | root `c58f8da6c`, `e6111df1a` |
| INF-45 code: W2 era plumbing, P1-8 reader, W6 partial; research parser bug and signed decouple | orch `9ce3f4b3`, `cfa503e5`, `15402376`; research `18d0c3ea` |
| RTG-34 batch: ① REG-ENF-2 `b6b761603`, ② DP-4 `d2aa30025`, REG-ENF-1 drift fix `873095891`; ③ OBS-CHURN-UP and ④⑤ smoke-complete + pick id still being landed by another subagent | root |
| Operator decisions: "Hold smokes", "Cap backfill at T" (`c046a6b4a`), "Requeue same id", P2-3 "Ratify all now" | — |
| P2-3 ratify package, waiting for the operator to run it in a terminal | root `87eb4c431` |
| R1a and judge79 rows published | root `bef92ac82` |
| AutoKernel afc-r3 withdrawal alarm was false: f2 had withdrawn those rows at 14:09 | — |
| New feedback memory: ratify scripts must be apply-tested | memory |

Boxes ticked this wrap-up (pipeline-mgmt-owned): REG-ENF-1, REG-ENF-2, DP-4 (coordination-and-churn-pipeline.md); INF-45 P1-8 and W2 (numa-placement-and-contention.md). W6 has a PARTIAL note and stays open. [no-belief: tooling/plumbing, not results]

Filing re-audit 14:32Z: UNFILED-ENDED 1, `afc-v3b-q38_flash-tools-none-r2-20261111` (f2, just finished). Left to its owner.

## Wrap-up 3 (work since root 21078443f)

### Filing (15:55Z)
| Row | Verdict | Evidence |
|---|---|---|
| `inf45-judge79-q38-27b-20261111` | pass (capture only) | 79/79 captured ok, `/mnt/raid0/llm/tmp/inf45-judge79-q38-27b-20261111/out/result.json`; grade (Claude-as-Judge, per suite) still to run |
| `rtg34-r1a-bench-claim-20261111` | fail | bench rc 1: region-lock TIMEOUT at 600 s on q3, held by f2 filler `afc-v3c-q36_35b-tools-mild`. The grant booked 0-71 while bench_canonical pins 0-95. Booking-shape defect, not a claim/release defect |
| `inf45-e5v2-stageb-r1-20261111` | already filed SUPERSEDED by `-r2` (filing.supersede, 15:26Z) | — |

No other-owner rows completed and unfiled. Verdict JSONs are in `/mnt/raid0/llm/tmp/pm-filing-20261111/`.

### Handoffs
- Ticked in coordination-and-churn-pipeline.md: OBS-CHURN-UP (`1ffdb6d93`), Re-anchor picks on row identity (`9f5b6c5ed`), FM-9 (README `ab1f1d38d`, operator ratify `fd21d6476`; guards rc 0, cite-check rc 0). Ticked in numa-placement-and-contention.md: P2-4 (operator ratify `a0e248d40`). All carry `[belief: cc]` or `[no-belief]`.
- Notes added: R1a FAIL (box open, republish as whole-host); E5 Stage-B now r2 (`421845e63`); interference row queued; capacity fitter `268c9895a`; MI210 eval-lane design `1ca21d7c4`; judge79 capture pass (grading pending).
- Verified only: P2-3 (`70ba71701`), FM-4 (`0ae751280`, unknown rate 53%, open), WS-4 (`740414d8f`), contention-matrix refresh (already noted under TOOLPERM-DENY-DEFAULT, engineering-hygiene-backlog).
- ROWFLOW-SMOKE-COMPLETE-GENERAL left open. The fix `f0b66044a` is on origin/main, but the deployed rowflow is `eea000786` (DEPLOYED.json at 15:27:58Z) and no newer `deploy_rowflow: OK` was found.
- Drain cap-at-T (`407666d71`) and same-id requeue after a cap cut (`eea000786`): no open box in engineering-hygiene-backlog or coordination-and-churn-pipeline names them, so nothing was annotated.

### Coordination
- P2-4 was already ratified (`a0e248d40`).
- The AutoKernel "host idle" reports were explained by three things: the quiet-host inf85 grant, smoke GPU locks, and an unpublished AK backlog. AutoKernel was told to publish it.
- The INF-85 W3 r3 results were relayed to AutoKernel.
- New memory: a ratify script must be apply-tested before it is handed over, and given as one single-line command.

### Follow-ups
- [ ] Republish R1a as a whole-host successor row (pipeline-mgmt). Tracked in the R1a box note.
- [ ] Grade judge79 with run_judge_suite.py report (zero compute, pipeline-mgmt). Tracked in the judge79 box note.
