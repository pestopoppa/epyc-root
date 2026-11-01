# Churn through the backlog — the one workflow (operator, 2026-11-01)

"If I ever ask to churn through the task backlog it should just work." This page is the canonical definition;
skills and goals point here. There is no other backlog workflow for the Codex workers.

## The flowchart (verbatim from the operator)

1. The entire task backlog consists of prioritized tasks of two types: **inference** and **non-inference**.
2. Non-inference tasks that block inference tasks can be built/completed/implemented **regardless of compute usage**.
3. Once an inference task is unblocked, its **launcher is prepared and dry-run in a realistic environment**.
4. Once dry runs pass, it is **passed to the scheduler so it may be armed** in the inference backlog.
5. Go back to completing the next set of blocking non-inference tasks. Rinse. Repeat. **Do not stop until ALL
   non-inference tasks are exhausted and inference tasks armed.**

## The three definitions

| term | means exactly |
|---|---|
| the backlog | `/mnt/raid0/llm/tmp/compute-flags/BACKLOG-<worker>.md` (worker = `ni` / `refactor` / `codex3`), regenerated every 10 min by `scripts/coordination/backlog_gen.py` (`ws58-backlog-gen-v1.sh`). Inference rows first, in priority order, each with its state (`blocked` / `needs-launcher` / `needs-qualification` / `qualified-armed` / `running` / `done`) and, under every blocked row, the non-inference tasks that unblock it; then the remaining non-inference tasks. |
| dry run passes | the **keeper's qualification** of the row on the real config: `ws58-calendar-keeper-v8.sh` runs `bin/qual-v1/qualify_launcher.py` through the canonical engine `filler_run14.sh` and logs `READY-QUAL <manifest>: <receipt>`. A worker's own smoke is preparation, not the pass. Contract: `artifacts/coordination/ni-d1d4-hard-gate-20261101/README.md`. |
| armed | an `epyc.ready.v2` manifest in `compute-flags/ready/` that the keeper accepted (receipt on disk, no hold, no `READY-SKIP`); `grant_ok.sh` v3 refuses anything else. The keeper arms it when a bin frees; nobody hand-arms. |

## Linking the two lists: `unblocks:`

A non-inference task that unblocks an inference row declares it, so the generator can nest it under the row:

- in `WORK-<worker>-code.md`, append `[unblocks: <ready-id>[,<row-id>]]` to the task line;
- or add `{"<task text>": ["<ready-id>", ...]}` to `compute-flags/unblocks.json`;
- `backlog-priority.json` rows already carry `unblocks: [<row ids>]`, and `inference_prep` entries join a READY id
  (`filler`) to its handoff row (`row`). Keeper refusal reasons, holds and schema mismatches become `fix:` tasks automatically.

Workers fill `unblocks:` when they file a task. A blocked row with no unblocking task shows a placeholder asking for one.

## Roles

- **Workers (Codex NI / refactor / codex3)**: run the five steps against their BACKLOG file, forever. Goal text: `compute-flags/GOAL-<worker>.md`.
- **ws58 (calendar owner)**: keep the generator, the flow scoreboard and the keeper healthy; file results; put new work into the
  backlog (handoffs, `backlog-priority.json`, READY rows). **No ad-hoc orders** to the panes: if something must change, change the
  backlog or the goal file.
- **Operator**: trust-boundary ratifications and destructive host actions only.

## Metrics (FLOW-SCOREBOARD.md, `scripts/coordination/flow_scoreboard.py`, every 10 min)

Per worker per day: inference rows armed (keeper-qualified); blocking tasks closed; idle compute-hours with a blocked row as the
cause. The 50-ticks/day code quota and its pane nudges are retired (`compute-flags/retired/`). The science scoreboard v4 stays beside it.

## Retired layers

`OWNER-ORDER-20261029.md`, `LOOP-CONTRACT.md` and `CODEX-GOAL-20261028.md` live in `compute-flags/retired/` with a header pointing
here. Still-binding rules were folded into `GOAL-<worker>.md`; the code-quota rule was dropped.
