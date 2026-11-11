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
