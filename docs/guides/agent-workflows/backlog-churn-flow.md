# Churn through the backlog — the one workflow (operator, 2026-11-01; simplified the same evening)

"If I ever ask to churn through the task backlog it should just work." This page is the canonical definition;
skills and goals point here. Operator ruling (2026-11-01): **remove every gate that is not indispensable** — each
extra artifact was a place for a row to get stuck and token-wasting busywork for workers.

## The flowchart (verbatim from the operator)

1. The task backlog consists of prioritized tasks of two types: **inference** and **non-inference**.
2. Non-inference tasks that block inference tasks can be done **regardless of compute usage**.
3. Once an inference task is unblocked, its **launcher is prepared and dry-run in a realistic environment**.
4. Once dry runs pass, it is **passed to the scheduler so it may be armed**.
5. Go back to the next blocking non-inference tasks. Rinse. Repeat. **Do not stop until ALL non-inference tasks are
   exhausted and inference tasks armed.**

## The row flow (`scripts/coordination/rowflow/`)

**The owner writes TWO things**: the launcher script (on the canonical engine `filler_run15.sh`) and a small spec.

```json
{"id": "<row-id>", "owner": "<session>", "launcher": "/mnt/raid0/llm/tmp/<job>/launch.sh", "lane": "cpu|gpu",
 "result_path": "/mnt/raid0/llm/tmp/<job>/out/results.jsonl", "result_format": "jsonl",
 "decision_rule": "<how the result is judged>", "estimate_s": 3600, "handoff_task": "handoffs/active/<h>.md:<ROW-ID>",
 "priority_rank": 10}
```
Optional: `regions` (default `mi210_0,184-191` / `any-cpu-quarter`), `ram_gib` (48), `scratch_root`, `keep`,
`dryrun_timeout_s` (900 cpu / 1500 gpu), `lineage`, `lineage_reset`, `supersedes`.

`python3 scripts/coordination/rowflow/publish_row.py spec.json` derives everything else (engine/min-window/ports from
the launcher, window, scratch_root + keep for the reaper, checksums) into `compute-flags/ready/<id>.json`
(`epyc.row.v3`). Legacy manifests: `rowflow.py publish --migrate compute-flags/ready/<id>.json` (writes a sibling
`launch.v15.sh` repointed at the new engine; the original launcher is untouched).

**The keeper is the qualifier** (`ws58-calendar-keeper-v10.sh` → `rowflow.py`, deterministic, no LLM):

| step | what happens |
|---|---|
| dry run | when the row's lane is free the keeper runs the EXACT launcher through its engine under the real region-lock claim on the REAL lane (GPU rows on the MI210) with a real short `grants/<id>.grant`. One dry run per lane per tick, starved lane first, then `priority_rank`. |
| **PASS** | the first real unit of measured output lands in `result_path` in the filer's format (`result_format`), the job then exits or stops cleanly on the stop file (rc 0/75), and for GPU rows VRAM was in use during the run. Startup alone never counts. Record: `compute-flags/dryrun/<id>/PASS.json` (launcher sha, units, VRAM max, log). |
| **FAIL** | `dryrun/<id>/FAIL-n.json` = the owner's **one fix task** (reason + launcher.out tail), shown in the backlog. Not retried until the launcher file changes. 3 FAILs in a lineage → `parked` + `operator-escalations/<lineage>.md`. |
| arm | a passing row's poller is started and its queue line appended; the grant writers grant it. `grant_ok.sh` v4 admits only a row with a PASS whose launcher sha is unchanged (an edited launcher is `stale` and needs a new dry run — automatic, no ceremony). |
| end | `grants/<id>.ended`; the dispatcher resumes the OWNING handoff session with `result_path` + `decision_rule`; the session files the verdict itself and touches `filing-done/<id>.FILED`; the keeper's reaper reclaims scratch deterministically. |

`rowflow.py status <id>`: `needs-dryrun | dryrun-running | failed | parked | stale | grantable | armed | running | done`.

**Retired** (2026-11-01): `epyc.ready.v2` manifests, `ready/<id>.row.md`, the 18-cell FILLERS row for new rows,
keeper nonces / receipt files / fixtures / cutoff proofs (`qual-v1`, `qual-v2-row`), the owner-wide worker breaker,
the registry-row check, `validate_fillers.py` and `keeper_qual_gate` in `grant_ok`, `ws58_arm-v2.py`, the sonnet filing
subagent for piloted handoffs. The FILLERS table remains the legacy registry of rows armed before 2026-11-01.

## Backlogs (`scripts/coordination/backlog_gen.py`, every 10 min)

Objective: **unblock the maximum number of inference rows as quickly as possible so every lane always has ready work.**
Non-inference tasks are ranked by `score = Σ lane_weight(row)` over the inference rows they unblock (transitively via
`[unblocks: <row-id>|<handoff-row>|<file:line of another task>]`, `unblocks.json`, backlog-priority `unblocks`),
`lane_weight = 1/(1+ready rows in that lane)` host-wide (GPU first while it has the fewest), then effort `[S]<[M]<[L]`.
Zero-unblock tasks sort last. Inference rows: emptiest lane first, then `priority_rank`.

Workers: the ni / refactor / codex3 Codex sessions are **closed**. The single always-open generalist is **codex-gen**
(`compute-flags/BACKLOG-<worker>.md` and `compute-flags/GOAL-<worker>.md` with worker = codex-gen): **small tasks only**
(`[S]`, bounded, ~30 min, no design judgment; a `[too-big: …]` note re-routes the task). Everything else goes to the
owning **per-handoff session** (`compute-flags/BACKLOG-handoff-<slug>.md`), or is listed under "needs a handoff session"
until one is started. The closed sessions' legacy queues (`compute-flags/WORK-<worker>-code.md`) are read and routed the
same way; nothing is lost.

## Session per handoff (`scripts/coordination/handoff_sessions.py`)

Registry `compute-flags/handoff-sessions.json`; the brief `compute-flags/briefs/HANDOFF-<slug>.md` is self-sufficient (a
cold agent of any engine can take over from it + the handoff + the progress file + the backlog). The dispatcher resumes
the owner on `grants/<id>.ended|.complete`, starts suspended sessions with advanceable rows, caps live sessions.

**Auto-start (2026-11-01 evening; origin: all compute idle while dozens of handoffs sat under "needs a handoff session"
and nothing consumed that list).** Every pass, while live sessions (a live pid; a suspended session waiting on a running
row holds no slot) < `max_live`, the dispatcher STARTS a fresh session for the best handoff without one — `start`
semantics: brief written, cwd inside the project, fan-out line, the WRAPPED gate — and logs `AUTO-START <slug>
handoff=… engine=… pid=… score=… rows=… priority=… rank=…`. The ranking is `backlog_gen`'s `needs_session`: handoff
score = Σ lane_weight over the DISTINCT advanceable inference rows the handoff's open tasks unblock (transitive, same
score as the task ranking) plus the rows whose fix task points into it, plus ½ × lane_weight for each of the handoff's
OWN unpublished inference tasks (open boxes that read like a run; at most 8 — the `unblocks:` graph is sparse, so without
this most handoffs score 0); ties — including score 0 — by the
`backlog-priority.json` rank of the handoff's index row (`.index-state.json`), never alphabetically. The same order
drives the "Routed elsewhere" section of `BACKLOG-codex-gen.md`. A session whose handoff has no open `- [ ]` left (or
whose file left `handoffs/active/`) becomes `done` and frees its slot. Registry knobs: `default_engine` (codex),
`auto_start` (true), `max_live` (5). The same ranking covers handoffs WITH sessions (`handoff_sessions.py rank`): a
session whose handoff falls below the top-`max_live` **yields** — it finishes its current task and wraps up, is marked
`yield` and is not resumed for NEW work (its own rows' run-end events still reach it); never killed mid-task.

**tmux window per session (operator, 2026-11-01).** start/resume/transfer run the engine inside window `h-<slug>` of
the tmux session `agent` (created with `new-window -d -t agent: -n h-<slug>`, reused with `respawn-pane -k`; addressed by
NAME `agent:=h-<slug>`, never by index; no `send-keys`, ever; the `codex-gen` and `claude` windows are never touched).
The JSONL is still tee'd to `handoff-sessions/<slug>/<ts>.jsonl` (the dispatcher reads session id / WRAPPED from it as
before), the pane shows `handoff_sessions.py pretty`, `<ts>.jsonl.pid|.rc` carry the engine pid and exit status
(`last_rc` in the registry), the pane stays open after the turn (remain-on-exit) and the window is killed on `done`.
No tmux session → `TMUX-FALLBACK` (detached engine, as before).

**Pause rule (operator, 2026-11-01 21:15Z — binding).** A session may be paused ONLY when everything left in its handoff
waits on an inference row that is queued or running. After a landed wrap-up the dispatcher reads `BACKLOG-handoff-<slug>.md`:
any advanceable row (blocked / needs-launcher / needs-qualification), own inference task to publish, or non-inference
task → resumed at once with `continue: next task` (logged `OPEN <slug>: <why>`); every open item waiting on a
qualified-armed/running row → `PAUSE <slug>: waiting on row(s) …`; nothing open and no rows → `DONE`, slot to the next
ranked handoff. A session that itself replies `IDLE: <reason>` is re-asked after 30 min. Between turns the tmux pane runs
`handoff_sessions.py pane-status <slug>` and shows one line every 30 s: `RUNNING turn …` / `PAUSED — waiting on row <id>
(queued|running) since <t>` / `RESUMING …` / `DONE` — never "Pane is dead".

**Inference first (operator, 2026-11-01)** — every brief and every `BACKLOG-handoff-<slug>.md` opens with it: the
session's first job is to turn the handoff's measurement/inference tasks into published rows (`publish_row.py`), fastest
blockers first, so every lane always has runnable rows; non-inference tasks come after, or while rows wait. The backlog
lists the handoff's rank and its own inference tasks that read like runs.

**`running` (BACKLOG state) means: `grants/<id>.grant` open, NO `grants/<id>.ended|.complete`, and the recorded
launcher/poller pid (armed record or queue line) alive.** A grant with an `.ended` is `done`; a grant whose pid is dead
is `blocked` ("stale grant", keeper/writer must end it). Origin: an HSF row showed `running` while its `.ended` said rc=1.

**Every launched session (any engine; spawn, resume, transfer)**: starts with its cwd INSIDE the project — `/workspace` or
one of its git worktrees — so it loads AGENTS.md and CLAUDE.md like any project agent (`handoff_sessions.py` validates
`project_cwd()` and logs `REFUSED-CWD` instead of spawning anywhere else); and carries the **subagent fan-out policy**
explicitly in its brief and prompts (own thread = review/integration/boundaries; execution = 3–5 concurrent subagents on
the cheapest capable model/effort; exceptions in `agents/shared/OPERATING_CONSTRAINTS.md` → *When NOT to fan out*).

**Portability (binding)**: a session wraps up at EVERY task boundary (progress file, ticks, pathspec commit, push via
`serialized_push.py`, `git cherry origin/main` empty) and prints `WRAPPED <sha>`; the dispatcher refuses to resume a
session for new work while its last task is unwrapped (`UNWRAPPED <slug>` in the log). Ownership can move at any time:
`handoff_sessions.py transfer <slug> --engine claude|opencode|codex` starts a fresh session from the files alone and
records `transferred_from` in the registry.

## Roles

- **Handoff sessions / codex-gen**: run the flow against their backlog file, forever. Never arm rows, write grants,
  hold or kill compute; the keeper and writers own the calendar.
- **ws58 (calendar owner)**: keeps the keeper, generator, dispatcher and writers healthy; starts handoff sessions;
  puts new work into the backlog. No ad-hoc orders to panes: change the backlog or the goal file.
- **Operator**: trust-boundary ratifications, destructive host actions, un-parking a lineage.

## Operator rulings of 2026-11-01 (binding; each is implemented where the pointer says)

| ruling | where it lives |
|---|---|
| **Remove every gate that is not indispensable.** The dry run on the real lane is the only proof a row needs. | `rowflow.py`, `grant_ok.sh` v4, keeper v10 step 5 ("Retired" list above) |
| **The owner writes only a launcher and a spec**; publishing derives everything else. | `publish_row.py`, "The row flow" above |
| **The dry run is robust**: a disk floor below `dryrun_disk_policy.json` is a WAIT, never a FAIL; a job that ignores the stop file after 600 s grace is truncated by signal and PASSES with a warning (the engine hard-end is production's own truncation path); directory results count as units; a FAIL is retried only when launcher, spec or rowflow change (sha-keyed). | `rowflow.py` (`dryrun-run`), `bin/rowflow/dryrun_disk_policy.json` |
| **The owner files its own results** (`filing-done/<id>.FILED`) when the dispatcher resumes it with `result_path` + `decision_rule`; the sonnet filing subagent is retired. | "end" row above, `handoff_sessions.py`, `filing_watch.sh` (writes `filing-due.jsonl`, raises the takeover alarm) |
| **Session per handoff, at most 5 live, auto-started in rank order (rows unblocked), inference first.** | "Session per handoff" above, `handoff-sessions.json` knobs `max_live`/`auto_start` |
| **codex-gen takes small tasks only.** | `GOAL-codex-gen.md` (git: `scripts/coordination/churn/GOAL-codex-gen.md`) |
| **Per-task wrap-up and transfer portability** (`WRAPPED <sha>`, `transfer`). | "Portability" above |
| **Fan-out in every launched session.** | brief section + prompts in `handoff_sessions.py` |
| **Sessions launch inside `/workspace`** (or one of its worktrees). | `project_cwd()` in `handoff_sessions.py`, `REFUSED-CWD` |
| **tmux windows are addressed by NAME, never by index; every handoff session has its own window `h-<slug>` in session `agent`; `renumber-windows` is off** on that session (window numbers must not shift when a window closes). Operator windows: `claude` (ws58) and `codex-gen`. Nobody sends keys to an agent pane. | `handoff_sessions.py` (tmux section), `churn_up.sh` (`ensure_tmux`, `--status` warns when renumber-windows is not off) |

## Reboot / cold start (one command; nothing depends on any session's memory)

Everything the pipeline executes is in git — `scripts/coordination/churn/` (keeper watchdog, grant-writer templates,
`GOAL-codex-gen.md`, the zero-token watchers, `ram_admit.sh`, the legacy `grant_ok_launcher.py` the GPU writer imports),
`scripts/coordination/rowflow/` (keeper v10, rowflow, engine, `grant_ok_v4.sh`, disk policy) and `scripts/coordination/`
(`backlog_gen.py`, `handoff_sessions.py`, `flow_scoreboard.py`, `filing_watch.sh`, `filing_takeover_alarm.py`,
`validate_fillers.py`). `compute-flags/` holds only installed copies plus state. The installed copy of every file must equal
the git copy (`--status` prints `ok`/`DIFFERS` per file); a hot-fix in `compute-flags/` that is not committed is a defect, not a
state.

**Order after a reboot** (`/mnt/raid0/llm` mounted, orchestrator venv present; the compute stack itself is the inference
main's business, not this page's):

```bash
cd /workspace && git pull --ff-only                       # the pipeline code is whatever origin/main says
scripts/coordination/churn/churn_up.sh --dry-run          # read what it would do
scripts/coordination/churn/churn_up.sh                    # the one command
scripts/coordination/churn/churn_up.sh --status           # every loop UP, no DIFFERS, no DEAD grant, renumber-windows off
```

`churn_up.sh` is idempotent: (1) installs the git copies into `compute-flags/` (temp file + `mv`, never an in-place edit of a
running script; a running copy that differs is reported, never restarted); (2) clears reboot residue — open `grants/*.grant`
whose poller/dry-run pid is gone are moved (never deleted) to `grants/stale-reboot-<ts>/` with their `.wsq/.wsg` stamps so
the row is re-armed, and `handoff-sessions.json` entries whose pid is gone become `suspended` (wrap-up landed) or `unpushed`
(only while the dispatcher is not running; region-lock claims clear themselves — the library drops dead-pid records on
read); (3) starts, only if its pidfile pid is not alive with the expected argv (never `pgrep`): the keeper **watchdog**
(which starts `ws58-calendar-keeper.current` = v10 within 120 s), `ws58-backlog-gen-v1.sh`, `ws58-flow-scoreboard-v1.sh`,
the dispatcher (`handoff_sessions.py dispatch --loop --interval 60`), `ws58-disk-trend.sh`, `filing_watch.sh`; (4)
fast-forwards the grant writers with the keeper's own sed recipes — today's `grant-ws58-quarters-<day>.sh` (day rolls at
05:52Z) and the next `grant-gpu-<MMDD>-v<n+1>.sh` (cap = next 06:00Z ≥ 3 h away, predecessor = the dead pid with birth 0)
— and starts them when no writer is live, after which the keeper owns succession again; (5) recreates tmux session `agent`
with windows `claude` and `codex-gen` by name and sets `renumber-windows off`; (6) prints the two things it never does.

**By hand, in the two windows** (never via `send-keys`): `claude` → `cd /workspace && claude`, first message *"You are ws58,
owner of the EPYC compute calendar. Run `scripts/coordination/churn/churn_up.sh --status`, then follow
`docs/guides/agent-workflows/backlog-churn-flow.md` (Roles → ws58)…"*; `codex-gen` → `cd /workspace && codex`, first message
*"Read `/mnt/raid0/llm/tmp/compute-flags/GOAL-codex-gen.md` and follow it exactly. Your backlog is
`/mnt/raid0/llm/tmp/compute-flags/BACKLOG-codex-gen.md`."* Per-handoff sessions need nothing by hand: the dispatcher
auto-starts them in `h-<slug>` windows.

**Expected `--status`** (healthy):

```
== install state (installed sha16 vs git sha16)
  ws58-calendar-keeper-v10.sh          ok 865cbde56b81185d
  …                                    ok …                       (every line ok; DIFFERS = install not applied or uncommitted hot-fix)
== loops (pidfile -> pid, alive+argv, started)
  watchdog         <pid>    UP   since <lstart>
  backlog-gen      <pid>    UP   …      flow-scoreboard … UP      dispatcher … UP      disk-trend … UP      filing-watch … UP
  keeper           <pid>    UP   since <lstart> (ws58-calendar-keeper-v10.sh)
  quarter-writer   <pid>    UP   grant-ws58-quarters-<today>.sh
  gpu-writer       <pid>    UP   grant-gpu-<MMDD>-v<n>.sh cap <next 06:00Z>
== tmux
  window 1 claude: claude …   window 2 codex-gen: node …   window N h-<slug>: … (one per live handoff session)
  renumber-windows (effective): off
== lanes / grants / handoff sessions / backlog freshness / disk      (BACKLOG-codex-gen.md and FLOW-SCOREBOARD.md < 15 min old)
churn_up status: OK                                                 (exit 0; any DOWN/DIFFERS/DEAD/WARN line -> exit 1)
```

Pidfiles the status reads: `ws58-keeper-watchdog.pid`, `ws58-calendar-keeper.pid`, `ws58-backlog-gen.pid`,
`ws58-flow-scoreboard.pid`, `handoff-sessions.dispatcher.pid`, `ws58-disk-trend.pid`, `ws58-filing-watch.pid`,
`grant-ws58-quarters-<day>.pid`, `grant-gpu-<MMDD>-v<n>.pid` — all under `compute-flags/`. A loop started by hand must write its
pidfile or `--status` reports it DOWN and a later `churn_up.sh` would start a second copy.
