# Multi-phase programs (the AK-DTREE P1-P6 pattern)

Origin: AK-DTREE, 2026-11-19 — plan P1..P6 filed in `handoffs/active/speculative-decoding.md`
(`d69e53711`, 18:36Z) and driven to P3 by 22:58Z (two kernel branches, e2e gate 80/80, rows
published) with no intermediate operator checkpoints. Earlier: INF-48 close-out (11-17), AKU
wiring batch (11-18/19), intake 2694..2717 Stage 1→4.

## Before the first dispatch
File one table in the OWNING handoff (not a new file):

| Phase | Done-when (checkable) | Dispatch class | Depends |
|---|---|---|---|
| P1 | e.g. op tests pass vs CPU at fork `<sha>` | subagent opus/high, build=claim q0 | — |
| P2 | row `<id>` filed with verdict | row (gpu), owner watcher | P1 |
| … | | | |
| Pn | the deliverable the operator touches (ratify / stack-change) | owner | … |

Rules: every done-when names an artifact (commit, row id, FILED receipt); dispatch class names
model/effort and the build clause; at most ONE operator touchpoint, at the end.

## Driving it
- Each hand-back → hand-back triage (SKILL §7) → file/tick → dispatch the next phase **in the same turn**.
- Independent phases go out in parallel (3–5 ceiling); sequential ones never wait for a status check.
- A blocker becomes a fix task (a new box or a fix commit), never a checkpoint or a question.
- Update the phase table cell (done / row id / sha) as each phase lands; the table is the status.
- Run programs to the deliverable (memory `feedback_run_programs_to_deliverable`).
