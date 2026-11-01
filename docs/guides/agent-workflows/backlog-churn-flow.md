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

## Operator rulings (2026-11-01) and the structured loop

1. **Starved lane first.** The next inference row to advance is the highest-priority row in any lane (CPU/GPU) below
   its floor of 2 armed rows; only then global priority. `backlog_gen.py` already orders BACKLOG this way.
2. **3 retries, then park.** After 3 failed keeper qualifications of one logical row, the row is `parked`
   (PARKED NEEDS-OPERATOR) and nobody retries it. **Lineage** = the manifest's `lineage` field; else the lineage of the
   id in its `supersedes` field; else the ID stem (id minus trailing `-YYYYMMDD`, `-vN`, `-rN`, `-rearm`, `-retryN`).
   Each distinct failed id counts once. The generator writes `compute-flags/operator-escalations/<lineage>.md`
   (each refusal, what was tried, options). Re-admission is the operator's call: a fresh manifest with
   `lineage_reset: <n>` counts only failures above n.
3. **Cross-session blocks: the row owner fixes it.** If your row is blocked by another session's code, fix that code
   yourself in an ordinary reviewed commit and name the code owner for review. Never wait on another worker's queue.
4. **Non-blocking work until unblocked.** When none of your inference rows can advance, do non-blocking code tasks
   by priority, re-reading BACKLOG at every task boundary; switch back as soon as a row can advance.

The loop every worker runs (GOAL files carry the same text):

- START: re-read `BACKLOG-<worker>.md`.
- Did any of my rows fail since the last loop? File the verdict, fix the root cause, publish a new id, go to
  qualification. Rule 2 limit applies (parked rows are not retried).
- Pick the next row (rule 1):
  - **blocked** → do its unblocking tasks (rule 3 when the blocking code is another session's);
  - **needs-launcher** → build it on the canonical engine v14 (`filler_run14.sh`);
  - **needs-qualification** → submit the v2 row. Keeper qualification passes → ARMED; the scheduler grants it, the
    worker never holds an armed row or waits for a grant. Fails → the refusal becomes a blocking task.
- No row can advance → rule 4.  Backlog empty → report done and stop.

## The three definitions

| term | means exactly |
|---|---|
| the backlog | `/mnt/raid0/llm/tmp/compute-flags/BACKLOG-<worker>.md` (worker = `ni` / `refactor` / `codex3`), regenerated every 10 min by `scripts/coordination/backlog_gen.py` (`ws58-backlog-gen-v1.sh`). Inference rows first, in priority order, each with its state (`blocked` / `needs-launcher` / `needs-qualification` / `parked` / `qualified-armed` / `running` / `done`) and, under every blocked row, the non-inference tasks that unblock it; then the remaining non-inference tasks. |
| dry run passes | the **keeper's qualification** of the row on the real config: `ws58-calendar-keeper-v8.sh` runs `bin/qual-v1/qualify_launcher.py` through the canonical engine `filler_run14.sh` and logs `READY-QUAL <manifest>: <receipt>`. A worker's own smoke is preparation, not the pass. Contract: `artifacts/coordination/ni-d1d4-hard-gate-20261101/README.md`. |
| armed | an `epyc.ready.v2` manifest in `compute-flags/ready/` that the keeper accepted (receipt on disk, no hold, no `READY-SKIP`); `grant_ok.sh` v3 refuses anything else. The keeper arms it when a bin frees; nobody hand-arms. |

## Linking the two lists: `unblocks:`

A non-inference task that unblocks an inference row declares it, so the generator can nest it under the row:

- in `WORK-<worker>-code.md`, append `[unblocks: <ready-id>[,<row-id>]]` to the task line;
- or add `{"<task text>": ["<ready-id>", ...]}` to `compute-flags/unblocks.json`;
- `backlog-priority.json` rows already carry `unblocks: [<row ids>]`, and `inference_prep` entries join a READY id
  (`filler`) to its handoff row (`row`). Keeper refusal reasons, holds and schema mismatches become `fix:` tasks automatically.

Workers fill `unblocks:` when they file a task. A blocked row with no unblocking task shows a placeholder asking for one.

## Session per handoff (pilot, operator-approved 2026-11-01)

Handoffs with a live inference thread can be owned by **one resumable agent session** instead of a generalist worker.
The handoff file is the durable record; the session is a cache.

- **Registry** `compute-flags/handoff-sessions.json` (`epyc.handoff-sessions.v1`): per handoff its path, engine
  (codex default; claude; opencode), session id, status (`live` / `suspended` / `done`), `waits_on` row ids, last
  resume, last wrap-up, brief path, and the ownership matchers `row_ids` / `row_patterns` / `handoff_rows`.
- **Ownership**: `backlog_gen.py` drops matched READY rows, `inference_prep` entries and code-queue lines on the handoff
  from `BACKLOG-<worker>.md` and writes `BACKLOG-handoff-<slug>.md`. Ownership moves only through the registry, never by
  editing grants, the keeper, gates or READY manifests.
- **Brief** `compute-flags/briefs/HANDOFF-<slug>.md` (`handoff_sessions.py brief <slug>`): this flow, scoped to one handoff.
- **Dispatcher** `scripts/coordination/handoff_sessions.py dispatch --loop` (`hs-dispatcher-v1`, zero-token): on
  `grants/<id>.ended|.complete` for an owned row it resumes the owner headlessly with fetch / re-read / result path,
  rc, end line and decision_rule from the READY manifest / file-the-verdict instructions; starts a suspended handoff
  that has advanceable rows after a 45 min cooldown; at most `max_live` (5) sessions run, extra events queue; a
  usage-limit error pauses the dispatcher 30 min and re-queues the event (logged in `handoff-sessions.log`).
- **Headless resume forms** (verified 2026-11-01): `codex exec resume --json <thread_id> -` (prompt on stdin);
  `claude -p --resume <session_id>`; `opencode run -s <ses_id> --format json` (prompt on stdin, needs its backend).
- **Lifecycle**: a session ALWAYS runs the per-task wrap-up (progress, handoff ticks with evidence, commit, push) before
  it ends a turn, and suspends once its row is armed. At a milestone or when large it wraps up and prints
  `FRESH-SESSION-REQUESTED`; the next dispatch starts a fresh session from the handoff and brief.
- Tiny chores with no inference thread stay with the generalist workers (and their subagents).

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
