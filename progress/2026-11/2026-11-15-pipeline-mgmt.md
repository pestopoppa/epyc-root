# 2026-11-15 — pipeline-mgmt

## Wrap-up 5 (work since root 386a71daa)

### Why the host idled on 11-12 and 11-13
- **Thin published supply.** Few rows were ready and grantable, so free quarters had nothing to run.
- **Stale queue_status buckets.** The operator view sorted rows with its own predicates, not the keeper's, so finished or blocked rows looked runnable and runnable rows looked blocked. Fixed in `958eb6556`: queue_status now classifies with rowflow `status()`/`runnable()`.
- **Finished rows.** Several rows had completed but still looked live. IDLE-WHY now lists every blocked row (`f138b95ab`).
- Requests went out over the bus asking the sessions to publish rows. f2, AK and bb each reported that no other operator commands are pending.

### Keeper fixes now live (each has an operator D9 ack)
| Fix | Commit | Ack |
|---|---|---|
| Cap-cut requeue works without the `.grant` file and never requeues a filed or superseded row | `3c4d2c4b5` | "Requeue same id" |
| IDLE-WHY lists every blocked row | `f138b95ab` | — |
| Docker container PIDs are attributed to their row | `add70e4e9` | "Docker attribution" |
| No pocket smoke during a quiet-host drain, and no quiet-host grant while a smoke is live (added after E5 r2/r3 ran zero cells) | `11b28fbb2` | "Land + deploy" |
| publish_row refreshes the hub view before it checks boxes | `69842390a` | "Publish refreshes view" |
| queue_status uses the rowflow predicates, and its fixture builds real v3 rows | `958eb6556`, `17e4067c4` | "Land it" |
| GPU-lane cap regression tests (no code bug found) | — | "Extend to GPU" |

No D9 fix is still staged; every staged change has landed. Recorded as a ticked box in `handoffs/active/coordination-and-churn-pipeline.md` (RTG-34).

### Results
- **R1a:** passed. The bench claim held all four quarters and then released them. Ticked at `48b005c5c`; verified.
- **INF-45 interference:** P1 coefficients are 0.872 at np1 and 0.900 at np4. P2 is 1.015, which is negligible. Box (3) is ticked; verified.
- **judge79:** Qwen3.8-27B-Q8_0 graded 210/237 (88.6%). Ticked at `358fcdcfb`; verified.
- **E5 Stage-B:**
  - r2 and r3 ran zero cells.
  - r4 was partial: 5 decision-grade qwen38 cells, which answer T=2 with C1 beating C1b. The qwen36 cells were voided by the drop_caches timeout.
  - r5 was published with `--repeat` and a pre-clear (`48b6c207d`). It started at 18:28Z on 11-15 and the pre-clear worked (219 s). The harness then refused to run because of the **host-health gate: uptime is over 1 week, and a reboot is required** for decision-grade cells.
  - r5 ended rc=75 with zero cells. It was **filed inconclusive** by pipeline-mgmt.
  - Still open:
    - the host reboot, which the operator owns;
    - a `cpu_bench` era for binary 10303, which needs the operator;
    - a re-run row for the two failed qwen38-p1 cells.

### Filing
- `inf45-e5v2-stageb-r5-20261115`: filed inconclusive with `--no-reclaim`.
- `agg113-l3-cpu-20261114-r2` (owner autopilot-backlog-session) is ended and unfiled. Its result is not recorded by row id in its handoff, so it is left to its owner.

### Operator housekeeping
- gdb is installed in the container, which unblocks AutoKernel's relianceproof r6.
- The opencode read-only copies are removed: the publish_ro calls were deleted from the host script, freeing about 15 GB. This closes OP-OPENCODE-RECLAIM. The index row removal is drafted for the owning session to apply.
- The trash was swept.
- f2's stale ratify worktree was removed.

### Lesson
**Tests must replay the real launcher's behaviour.** The first requeue fix passed its tests but never fired in production. The tests kept the `.grant` file, but filler_run15 deletes `.grant` when the launch ends, so the requeue path keyed on a file that never exists live. A fixture has to reproduce what the real launcher does to the state directory, not an idealized version of it.
