# intake-2603 — dsh-superagent-prototype vs the backlog churn pipeline

- Source: https://github.com/deepseek-ai/dsh-superagent-prototype @ `6337fc823ce20251c8de8085948165c81aaa701e`
  (2026-10-31), cloned 2026-11-01. MIT. Labeled a research prototype, not a product. Repo created 2026-10-31.
- Read depth: PARTIAL. Read: README, docs/000–005, docs/007 (Persistence, Reload, Review-on-real-data, Open
  questions), prompts/work.md, worker.md, handoff*.md, and `src/app/tools/executor.ts:78`. Not read: the rest of `src/`, `tests/`,
  docs/006 and docs/008. The retry and redelivery behaviour is checked against the documented contract, not against code.
- Compared with our code at origin/main `c4cdeec05`: `scripts/coordination/handoff_sessions.py`, `backlog_gen.py` and
  `docs/guides/agent-workflows/backlog-churn-flow.md`.
- Companion of intake-1186 (deepseek-harness). It is a separate artifact, not a duplicate.
- Waves: 1 Stage-2 dive and 0 Stage-2b waves. The only source the dive surfaced was declined (see below).

## What it is

dsh-superagent is a DeepSeek Harness bundle for one GitHub repository. Sources (GitHub, Feishu) emit Triggers on Threads. A main
"router" session runs Eval, a deterministic gate followed by a model assessment, and turns accepted work into a Ticket with a
Mandate. Each Ticket gets its own Executor Session (`worker-<ticket>`) and its own directory, usually a git worktree. Workers end
every turn with a structured `orchestrator_report` whose state is one of `progress | ready | blocked | failed | dropped`. A worker
asks a person through a structured `human_action` question, which is called an Attention. One SQLite store holds triggers,
dispositions, tickets, an effect queue and an outbox.

## How it maps to our churn pipeline

| dsh-superagent | our pipeline | verdict |
|---|---|---|
| Ticket + Executor Session per ticket, resumable | session per handoff (`handoff_sessions.py`) | already have it |
| Eval gate + Mandate revalidation before resume | keeper dry-run PASS bound to launcher sha (`grant_ok_v4`) | already have it, in a stronger deterministic form |
| Structured Report enum. Free-text inference of "waiting on a person" is a **rejected** design (docs/001-domain.md:60) | the dispatcher regex-parses `WRAPPED <sha>` / `IDLE: <reason>` / `FRESH-SESSION-REQUESTED` from the last 6000 chars of the JSONL (handoff_sessions.py:703-710) | **gap → DSH-1** |
| Inputs a cut-off turn did not take are redelivered on retry or restart. Post-decision work is stored first and done after (003:152,155) | `pending_event` is cleared unconditionally at turn end (handoff_sessions.py:711). Only a usage-limit error re-queues it. `backlog_gen` counts `.ended` as `done` (backlog_gen.py:220) | **bug → DSH-2**: a run-end filing turn that crashes before `filing-done/<id>.FILED` is lost silently |
| Transient provider errors (408/429/5xx/conn reset) are retried 3× with backoff and a "go on" prompt (003:124) | a usage-limit error pauses the whole dispatcher. Any other crash routes to `unpushed` → PUSH_PROMPT, the wrong prompt for a turn that never reached its wrap-up | **gap → DSH-3** |
| One reserved slot above the concurrency limit for a human message (003:59) | `max_live` 5 with no reserved slot, so an operator-directed resume or a filing resume waits behind auto-start | **gap → DSH-4** (run-end filing gets the reserved slot) |
| Restart recovery note: check directory, git history and remote before repeating an outside action (003:146) | `transfer_prompt` already says "transcript UNAVAILABLE … files are your complete starting state" | covered. A one-clause addition to the DSH-2 resume prompt ("check whether you already filed / pushed") is folded into DSH-2 |
| `dropped`: nothing to do, close silently (prompts/work.md:45) | `IDLE: <reason>` plus a 30-min re-ask, and codex-gen `[too-big]` re-routes | covered by DSH-1 (a `dropped`/`idle` state in the structured report) |
| "Review a change against real data": copy the DB, disable sources, pause, read-only CLIs (007) | dispatcher tests use fixtures (`tests/coordination/test_handoff_sessions_*.py`) | the DSH-2 acceptance replays a copied registry plus a state file in a temp flags dir. No new primitive |
| Panel shows only what needs a person | `operator-escalations/`, hub :8100 | context only |

Engine transfer (codex/claude/opencode): dsh has no cross-engine transfer. Its Ticket deliberately "defines its own state instead
of following the Executor's", which is the same principle as our files-only `transfer`. The structured report in DSH-1 makes transfer
safer, because the receiving engine reads the last report from a file instead of from another engine's transcript format.

## Relevance verdict

**Relevant, as an adopt_patterns source. Do not adopt the component.** Adopting dsh-superagent would import a GitHub/Feishu ticket
product built on DeepSeek Harness. Our keeper, grants and inference lanes have no counterpart in it, so it cannot replace any part of
the churn pipeline. What it does contribute is four reliability contracts that our dispatcher lacks. One of them (DSH-2) exposes a
live lost-event bug.

## Derived-actionables ledger (proposed. Owner: `handoffs/active/session-bus-thin-dispatcher.md`, RTG-34)

Merging `scripts/coordination/**` also needs operator acknowledgement under ratified D9 (master index OP-D9 row). Nothing below has
been written to a handoff.

| ID | Proposed task line | Replaces / improves | Posture |
|---|---|---|---|
| DSH-2 | `- [ ] DSH-2 [S] Run-end events are acked by receipt, not by turn end: keep pending_event until filing-done/<id>.FILED exists; re-queue it when a turn ends without the receipt (cap 3, then operator-escalations/); backlog_gen shows ended-unfiled rows as "needs filing", not done. Acceptance: fixture test with a crashed end_prompt turn re-delivers the event once and files once. [unblocks: owner-filed results] [no-belief: dispatcher reliability; no measurement]` | replaces the unconditional clear at handoff_sessions.py:711 and the `.ended`=done rule at backlog_gen.py:220 | immediate. Bug fix. Deterministic, with fixture conformance in place of empirical controls |
| DSH-1 | `- [ ] DSH-1 [M] Structured turn report: each session writes compute-flags/handoff-sessions/<slug>/report.json {state: progress|ready|blocked|failed|idle|dropped, wrapped_sha, question, rows_published} at its wrap-up; the dispatcher reads it first and falls back to the WRAPPED/IDLE regex for one transition week. Acceptance: pause-rule fixtures pass on report.json alone; transfer prompt includes the last report. [no-belief: dispatcher contract; no measurement]` | replaces free-text tail parsing (handoff_sessions.py:703-710) and makes engine transfer engine-neutral | immediate, after DSH-2 |
| DSH-3 | `- [ ] DSH-3 [S] Transient-failure retry: a turn that ends rc!=0 with a 408/5xx/connection-reset error line (not a usage limit) and no WRAPPED is resumed with "go on" up to 3x with backoff 2/4/8 min, then marked failed in the backlog; PUSH_PROMPT only when a WRAPPED sha exists but has not landed. Acceptance: fixture tests for each branch. [no-belief: dispatcher reliability; no measurement]` | fixes the crash → PUSH_PROMPT misroute (handoff_sessions.py:712-716) | immediate, safe in parallel with DSH-1 |
| DSH-4 | `- [ ] DSH-4 [S] Reserve one dispatch slot above max_live for run-end filing resumes, so a finished row's owner is never queued behind auto-start. Acceptance: fixture with max_live live sessions still dispatches a run-end event. [no-belief: dispatcher scheduling; no measurement]` | improves time-to-filing for owner-filed results | immediate, safe in parallel |
| — | Adopt dsh Eval/Mandate/Source model for GitHub/Feishu intake | — | declined: the churn pipeline has no external-request source; our gate is the deterministic keeper |
| — | Adopt the SQLite effect-queue store | — | monitor. Reopen only if the JSON registry and state files show a lost or double write after DSH-2 lands |

Proposed index-row edit (RTG-34 Next action; the row is owned by `routing-and-optimization-index.md`):
`AIR-6 — deploy exact guarded source and require ordinary-work refusal; then DSH-2 run-end ack-by-receipt`.

## Dive-surfaced sources

| Source | Would settle | Bears on | Disposition |
|---|---|---|---|
| Article "Exploring Super-agent Design: Towards a More Autonomous Agent System" (cited in README) | which designs are implemented and which are only intended | intake-2603 | declined. Two bounded searches on 2026-11-01 found no URL. Reopen when DeepSeek links it |

## Second-reader check

All 8 claim anchors were re-found mechanically with `grep -F` at the pinned SHA. Line numbers are in the index entry.

Artifact audit: clean. Scratch is under `/mnt/raid0/llm/tmp/dive-dsh-superagent/` (source clone only, no figures).
