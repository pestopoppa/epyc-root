# Compute-owner takeover — results filing + scheduler liveness

**Why this exists (operator, 2026-10-28):** "results/verdicts/insights/followups need to be filed IMMEDIATELY after the
inference task/measurement ends", and "fold it into the coordinator-agent skillset so that I can have a separate session
pick it up immediately if your session dies". On 10-28 a session crash killed the writers and keeper (~20 min of idle
compute), and 10 rc0 results sat unfiled for days because filing depended on one session remembering.

Everything here is **files + zero-token daemons**. Any session can take over by running the checks below; nothing lives in
a session's memory. All paths are under `/mnt/raid0/llm/tmp/compute-flags/` (`F`).

## The pieces

| Piece | Path | Role | Liveness check |
|---|---|---|---|
| Calendar keeper | `F/ws58-calendar-keeper-v*.sh` (newest pinned in `scripts/hooks/destructive_scratch_pins.json`) | arms `ready/*.json`, carries rows over writer caps, re-arms rc75, reap-after-filing | `grep 'keeper v. start' F/ws58-calendar-keeper.log \| tail -1` → pid → `ps -o pid,lstart,args -p <pid>` |
| Quarter writer | `F/grant-ws58-quarters-YYYYMMDD.sh` (+ `.pid`) | grants CPU quarter rows from the ACTIVE day's queue | `ps -p $(cat F/grant-ws58-quarters-<day>.pid)` |
| GPU writer | `F/grant-gpu-*-v*.sh` | grants `ws58-gpu.queue` rows | `ps -eo pid,args \| grep -F grant-gpu-` is a NAME pattern — use the pid in its `.log` start line instead |
| **Filing watcher** | `F/ws58-filing-watch.sh` | appends every new `grants/*.ended\|.complete` to `F/filing-due.jsonl` | `tail -1 F/filing-watch.log` → pid → `ps -p` |
| Filing receipts | `F/filing-done/<id>.FILED` | one line: verdict or failure class + commit SHA | — |
| Rulings / contract | `F/LOOP-CONTRACT.md`, `F/OWNER-RULINGS-YYYYMMDD.md`, `F/CODEX-GOAL-*.md` | the binding loop rules | — |
| Codex channels | refactor: `tmp/refactor-01a16fc3/compute-coordination-20261026/owner-reply.md`; NI: `tmp/codex-ni-20261024-scheduling/OWNER-REPLY.json` (`updates[]`) | owner → worker messages | — |

## Takeover checklist (run at every cold start, resume, or when the owner session is dead)

1. **Daemons alive?** For keeper, both writers and the filing watcher: read the pid from the log/`.pid`, prove it with
   `ps -o pid,lstart,args -p <pid>` (never `kill -0`, never `pgrep`/`pkill` by name). Dead → restart with
   `setsid bash <script> </dev/null >/dev/null 2>&1 &` (a keeper needs its pin; a writer must be the ACTIVE day's —
   `date -u -d '-5 hours -52 minutes' +%Y%m%d`).
2. **Stale state after a crash.** For every `grants/*.grant` whose launcher pid (FILLERS row `pid=` / queue line) is
   dead: move the grant aside (not delete), move its `.wsq-granted-<id>`/`.wsg-granted-<id>` marker aside, drop the
   dead-pid queue line, and return the manifest from `ready/armed/` to `ready/` so the keeper re-arms it.
3. **Filing gap — the duty that must never lapse.** Every id in `filing-due.jsonl` without `filing-done/<id>.FILED`
   is an unfiled result. Dispatch ONE filing subagent for the whole gap immediately (brief below). Skip ids whose grant
   is still open.
4. **Arm the wake-up**: a `run_in_background` until-loop that exits when `filing-due.jsonl` grows; on each wake,
   dispatch a filer for the new lines and re-arm. (Never `&`; never poll with sleep in the foreground.)
5. **Idle compute.** `region-lock status` + `ls F/grants/*.grant` + the keeper's last `READY-WAIT`/`READY-SKIP`
   lines tell you why a region is idle. Fix scheduler causes yourself; worker causes go to the Codex channel.

## Filing subagent brief (copy verbatim, fill the gap list)

For each `filing-due.jsonl` line without a `.FILED`:
- **Failure** (rc ∉ {0,75}, admission refusals, `owner-retired`, signals): no verdict, no tick. Write `.FILED` with
  `FAILED-RUN rc=… reason=…; class=<harness|admission|disk-floor|owner-retired|unknown>; owner action=…`; group
  identical failure series.
- **Completed** (rc0/75/complete): read `result_path` and the PREDECLARED rule (manifest `decision_rule`, FILLERS row,
  owning handoff); run `.claude/skills/inference-backlog-scheduling/references/post-measurement-analysis.md`; dated
  result sub-bullet with `[belief: cc]` (or `clm_<id>`), follow-up `- [ ]` boxes, tick only when the rule is fully met;
  no predeclared rule ⇒ diagnostic observation, say so; never invent a threshold.
- Fresh root worktree from `origin/main`; pathspec adds; `index_state.py --check` rc 0; push via
  `serialized_push.py --agent <owner-id> --push`; cherry empty; `worktree_gate.py remove`. Index-row edits are
  prepared as a diff for the owning session, never applied by the subagent.
- Report a `run | outcome | meaning | next` table + commit SHA to the operator.

## Reap safety tie-in

Reap-after-filing deletes a filed run's scratch 3 days after `grants/<id>.complete`. A result that was never filed is
therefore on a clock: the filing gap check (step 3) is what keeps raw outputs from being reaped before anyone has
read them. Target state (LOOP task): the keeper refuses to reap a root until `filing-done/<id>.FILED` exists.
