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

## The one rule no gate may break (operator, repeated for months; codified 2026-11-02)

**Sessions NEVER stop unblocking inference tasks and making them ready while any un-readied inference task exists.**
No inventory target, park, stuck rule, cooldown, yield, token-saving or disk gate may stop work on a handoff that still
has un-readied inference tasks (needs launcher / qualification / publish, or blocked). Such gates apply only to
handoffs with none left. Admission test for ANY new dispatcher/backlog_gen/rowflow gate: *can it leave a slot empty, or
a handoff with un-readied inference tasks unresumed?* If yes, it is refused. Origin: on 2026-11-02, from 08:22Z to
09:18Z, every session was parked (await_event + stuck rule) and the whole host sat idle while 69 handoffs held 268
unpublished inference tasks.

## The row flow (`scripts/coordination/rowflow/`)

**The owner writes TWO things**: the launcher script (on the canonical engine `filler_run15.sh`) and a small spec.

```json
{"id": "<row-id>", "owner": "<session>", "launcher": "/mnt/raid0/llm/tmp/<job>/launch.sh", "lane": "cpu|gpu",
 "result_path": "/mnt/raid0/llm/tmp/<job>/out/results.jsonl", "result_format": "jsonl",
 "decision_rule": "<how the result is judged>", "estimate_s": 3600, "handoff_task": "handoffs/active/<h>.md:<ROW-ID>",
 "priority_rank": 10}
```
**Fetch/prepare inputs yourself before `publish_row`** (operator, 2026-11-01): a row whose launcher only downloads or
copies inputs (`kind: fetch|prepare|inputs`) is refused — "prepare inputs before publishing: fetching/copying data is
session preparation, not a compute row". `kind` defaults to `compute`.

Optional: `regions` (default `mi210_0,184-191` / `any-cpu-quarter`), `ram_gib` (48), `scratch_root`, `keep`,
`dryrun_timeout_s` (900 cpu / 1500 gpu), `lineage`, `lineage_reset`, `supersedes`.

`python3 scripts/coordination/rowflow/publish_row.py spec.json` derives everything else (engine/min-window/ports from
the launcher, window, scratch_root + keep for the reaper, checksums) into `compute-flags/ready/<id>.json`
(`epyc.row.v3`). Legacy manifests: `rowflow.py publish --migrate compute-flags/ready/<id>.json` (writes a sibling
`launch.v15.sh` repointed at the new engine; the original launcher is untouched).

**The keeper is the qualifier** (`ws58-calendar-keeper-v10.sh` → `rowflow.py`, deterministic, no LLM):

| step | what happens |
|---|---|
| dry run | the allocator assigns the dry run a free region from its tick snapshot and runs the EXACT launcher through its engine under the real region-lock claim on the REAL lane (GPU rows on the MI210) with a real short `grants/<id>.grant`. A row booking several quarters (`0-95`) is dry-run on ONE quarter (`FILLER_DRYRUN_ONE_QUARTER=1`: the engine claims only the grant's cpus) unless the spec says `dryrun_whole_host: true`; a dry run never holds more than it needs. |
| **PASS** | the first real unit of measured output lands in `result_path` in the filer's format (`result_format`), the job then exits or stops cleanly on the stop file (rc 0/75), and for GPU rows VRAM was in use during the run. Startup alone never counts. Record: `compute-flags/dryrun/<id>/PASS.json` (launcher sha, units, VRAM max, log). |
| **FAIL** | `dryrun/<id>/FAIL-n.json` = the owner's **one fix task** (reason + launcher.out tail), shown in the backlog. Not retried until the launcher file changes. 3 FAILs in a lineage → `parked` + `operator-escalations/<lineage>.md`. |
| arm + grant | the allocator starts a passing row's poller and WRITES its grant from the same snapshot (`regions=… start=… end=… holds=…`; `any-cpu-quarter` is resolved only here, never at arm time), after admission through the one parser `grant_ok_launcher.py` (live argv: window ≥ min+300, regions cover the claim, `--precond-cmd`) and the 64 GiB RAM margin. Only a row with a PASS whose launcher sha is unchanged is grantable (an edited launcher is `stale` and needs a new dry run — automatic, no ceremony). |
| end | `grants/<id>.ended`; the dispatcher resumes the OWNING handoff session with `result_path` + `decision_rule`; the session files the verdict itself and touches `filing-done/<id>.FILED`; the keeper's reaper reclaims scratch deterministically. |

`rowflow.py status <id>`: `needs-dryrun | dryrun-running | failed | parked | stale | grantable | armed | running | done`.

**Rows are independent of lanes (snapshot rule, 2026-11-01).** Lane worktrees (`worktrees/mains/h-<slug>`) merge
`origin/main` before every resume and vanish when the session ends; `/workspace`, `/mnt/raid0/llm/epyc-root` and the repos
`/workspace/repos/*` resolve to move with every pull. A row whose launcher, engine or job file lives there would flip its
sha (`stale` churn) or run code the dry run never saw. So `publish_row.py` SNAPSHOTS such a row: the launcher's directory,
the engine's directory and the directory of every other absolute path on the engine line (`--cmd`, `--complete-cmd`,
`--workdir`) are copied into `<scratch_root>/snapshot/` (`launcher/`, `ext/<path>/`) — `git archive HEAD` of that directory
when the worktree is clean (commit recorded), else a working-tree copy with `snapshot.dirty: true`, `source_commit: null`.
Lane paths inside the copied text files are rewritten to the snapshot, files are made read-only, every file's sha256 is
recorded, and the row's `launcher.path`, `engine.path`, `result_path`, `stop_file`, `workdir` point INTO the snapshot: dry
run and real run execute the same bytes by construction; editing or removing the lane afterwards changes nothing the keeper
sees. `scratch_root` defaults to `tmp/<id>`; `"snapshot": true` forces it for a stable launcher; an impossible snapshot
(>256 MiB directory, repo top level, launcher inside its own scratch_root) is a refusal. `tmp/<job>/` launchers are untouched.


**Retired** (2026-11-01): `epyc.ready.v2` manifests, `ready/<id>.row.md`, the 18-cell FILLERS row for new rows,
keeper nonces / receipt files / fixtures / cutoff proofs (`qual-v1`, `qual-v2-row`), the owner-wide worker breaker,
the registry-row check, `validate_fillers.py` and `keeper_qual_gate` in `grant_ok`, `ws58_arm-v2.py`, the sonnet filing
subagent for piloted handoffs. The FILLERS table remains the legacy registry of rows armed before 2026-11-01.
**Retired the same evening (allocator)**: both grant writers (`grant-ws58-quarters-<day>.sh`, `grant-gpu-<MMDD>-v<n>.sh`),
`grant_ok.sh`/`grant_ok_v4.sh`, `ram_admit.sh`, the legacy `grant_ok_launcher.py` copy, keeper v10's carry-over / writer
succession / idle alarm, arm-time region resolution, `dryrun-pick`/`arm-tick`, the daily `ws58-quarters-<day>.queue` and
`ws58-gpu.queue` (history only; rowflow appends `ws58-armed.queue` `id|pid|window_s|gib|regions` for the backlog generator).

## The allocator (`rowflow.py allocate`, keeper v11, 2026-11-01 evening)

Origin: 21:50Z the keeper armed `handoff-df2-11-inputs` pinned to q0 and in the same tick started a dry run on q0; DF2 waited
while q2 sat idle — three actors (keeper, quarter writer, GPU writer) each deciding from its own snapshot. Now ONE actor:
every 120 s tick the keeper runs `rowflow.py allocate`, which reads region-lock, the open grants (their `holds=` token)
and the live dry runs ONCE, then assigns dry runs and grants together from that snapshot — starved lane (fewest live
rows) first, then `priority_rank`, then a grantable row before a dry run; a region is never handed twice; as long as a
pending row fits the remaining free regions and RAM it is placed. It arms the poller, admits, writes the grant and
spawns the dry runs itself. Invariants it enforces every tick (keeper log lines):

| line | meaning |
|---|---|
| `SNAPSHOT free=… busy=q:id,…` | the tick's one snapshot |
| `GRANT <id> regions=… holds=…` / `DRYRUN-START <id> regions=…` | assignments |
| `IDLE-WHY <region>: <reason>` | a region stayed free: no fitting row, or which row needs what that is busy / RAM short |
| `HEAL stale-grant <id>` | grant whose poller pid is dead with no `.ended`: moved to `grants/stale-<ts>/`, row re-granted |
| `HEAL conflict <id>` | granted onto a region another job holds, before START: grant withdrawn, re-assigned next tick |
| `CONFLICT <id>` | same, but the job already started (queued in region-lock): logged, never killed |
| `UNDERUSED <region> <id>` | < 5 % of a held quarter's CPUs busy for 10 min: owner fix task `dryrun/<id>/UNDERUSED.json`; never killed |
| `IDLE-VIOLATION <id>` | a fitting grantable row was not placed (allocator bug; should never appear) |
| `ALERT <condition> repeated 3 ticks` | any HEAL/CONFLICT/UNDERUSED/violation seen 3 ticks running → `ws58-keeper-alerts.jsonl` |

**Row shapes and the drain (operator, 2026-11-01 evening; binding).** Every row has a shape, recorded by `publish` as
`shape`: `quarter` | `multi-quarter(n)` | `host` | `quiet-host` | `gpu` — the spec's `shape` wins, else derived from the
launcher's `--claim-cpus`, `ram_gib` (> 256 GiB per quarter widens it), `--gpu-quiet exclusive` (→ quiet-host: every
quarter plus the GPU idle, timing baselines) and class. Dry runs by shape: quarter → one quarter; multi-quarter/host →
one quarter only when the launcher is constrainable (installed engine) and the model fits a quarter's RAM, else the real
shape with the reservation capped to first unit + `dryrun_timeout_s`; quiet-host → correctness only, on one quarter, no
gpu-quiet claim (the dry run proves plumbing, not timing). Quiet-host and aged (≥ 1 h) host/multi-quarter rows are
scheduled by **drain, never preempt**: `DRAIN <id> (<shape>) until T` (T = latest end among the running grants), only
rows that end before T are backfilled (`IDLE-WHY <q>: … draining for quiet-host <id> until T`), at T the whole shape is
granted first. Knob, off by default: `compute-flags/allocator.json {"quiet_windows": ["22:00-06:00"]}` (UTC).

Proof: `scripts/coordination/tests/test_allocator.py` (property test over random states: no double booking, no idle region
while a fitting row waits, starved lane first; today's incidents as regression cases) and
`scripts/coordination/tests/test_grant_ok_launcher_flags.py` (every engine flag parses); drain tests: a host row is never starved
by a stream of quarter rows, backfill never delays T, no double booking during a drain. `rowflow.py allocate --plan` is the
read-only preview (`ws58-calendar-keeper-v11.sh --dry-run` prints it).

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
drives the "Routed elsewhere" section of `/mnt/raid0/llm/tmp/compute-flags/BACKLOG-codex-gen.md`. A session whose handoff has no open `- [ ]` left (or
whose file left `handoffs/active/`) becomes `done` and frees its slot. Registry knobs: `default_engine` (codex),
`auto_start` (true), `max_live` (5). The same ranking covers handoffs WITH sessions (`handoff_sessions.py rank`): a
session whose handoff falls below the top-`max_live` **yields** — it finishes its current task and wraps up, is marked
`yield` and is not resumed for NEW work (its own rows' run-end events still reach it); never killed mid-task.

**Lane worktree per session (ws58, 2026-11-01; INC 2026-08-21 class — four sessions committed in the shared `/workspace`
clone within one minute and swept up each other's staged files).** Every session works and commits ONLY in
`/mnt/raid0/llm/worktrees/mains/h-<slug>` on branch `lane/h-<slug>` (created from origin/main by `git worktree add`; a
worktree of `/workspace`, so the project-cwd rule holds). The dispatcher fast-forwards or merges origin/main into the
lane before every resume (a conflict becomes the session's first task); the brief and every prompt say **never commit in
`/workspace`**; wrap-up pushes the lane to main through `serialized_push.py --repo <lane>` and proves
`git -C <lane> cherry origin/main` empty. Live sessions migrate at their next resume (`LANE <slug>: cwd … -> …` in the
log). On `done` the lane goes to `scripts/system/worktree_gate.py remove` (never prune/gc).

**tmux window per session (operator, 2026-11-01).** start/resume/transfer run the engine inside window `h-<slug>` of
the tmux session `agent` (created with `new-window -d -t agent: -n h-<slug>`, reused with `respawn-pane -k`; addressed by
NAME `agent:=h-<slug>`, never by index; no `send-keys`, ever; the `codex-gen` and `claude` windows are never touched).
The JSONL is still tee'd to `handoff-sessions/<slug>/<ts>.jsonl` (the dispatcher reads session id / WRAPPED from it as
before), the pane shows `handoff_sessions.py pretty`, `<ts>.jsonl.pid|.rc` carry the engine pid and exit status
(`last_rc` in the registry), the pane stays open after the turn (remain-on-exit) and the window is killed on `done`.
No tmux session → `TMUX-FALLBACK` (detached engine, as before). **No clutter (operator, later the same evening):** the
window is killed when the session pauses (waiting on a row), yields or is done, and created again by name on the next
resume; the turn's output stays in `handoff-sessions/<slug>/<ts>.jsonl` and `handoff-sessions.log` carries the state line
(`STATE <slug>: paused - waiting on row(s) … ; tmux window h-<slug> killed`).

**Governing objective (operator, 2026-11-01 23:30Z — binding): compute capacity must be the ONLY bottleneck.** Ready rows per
lane target ≥ 2 × capacity (cpu ≥ 8 quarter-rows, gpu ≥ 2; FLOW-SCOREBOARD headline `inventory vs target`). The target is a
PRIORITY ORDER — a deficit lane's blockers (stuck rows with fix tasks first, then own unpublished inference tasks) rank first —
**never a stop condition**: "just because some inference tasks have been submitted and others are running is no reason to stop
processing blockers". A session whose rows are queued or running is not idle; `max_live` slots are never left empty while any
handoff has an open non-inference blocker or an unpublished inference task (auto-start fills continuously; codex-gen takes every
orphaned row fix). Waiting for rows to become available is a pipeline FAILURE: a lane free for >2 keeper ticks with zero
candidates logs `INVENTORY-STARVED <lane>` with the 3 nearest-to-ready rows and their blockers. A push lock whose holder pid is
dead is logged `PUSH-LOCK-DEAD` and never auto-released.

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
is `blocked` ("stale grant"; the allocator heals it next tick). Origin: an HSF row showed `running` while its `.ended` said rc=1.

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

### Token guards (operator 2026-11-06; `scripts/coordination/token_guards.py`)

Implements recs 1-5 of `docs/reports/coordination/token-efficiency-audit-20261106.md`. Knobs live in the registry
under `token_guards` (defaults in `token_guards.DEFAULTS`); top-level `max_live` is the configured cap.

- **G1 model + effort per spawn.** `launch()` resolves `model`/`effort` (row manifest > handoff header
  `model:`/`effort:` lines > registry entry > cheap default `gpt-6-luna`/`medium`; claude `sonnet`/`medium`; opencode
  has none), validates them against `~/.codex/models_cache.json` (the installed CLI's catalog), and passes
  `-m <model> -c model_reasoning_effort=… -c plan_mode_reasoning_effort=…` to both `codex exec` and `codex exec resume`.
  Unresolved or invalid → `REFUSED-SPAWN`, no launch. Every launch logs `SPAWN-CFG` with the values and their source.
- **G2 budget, resumes, quota.** A live turn over `session_token_ceiling` (thread `total_tokens`, default 15 M) or
  `lease_s` (5400 s) is SIGTERMed (SIGKILL next pass) and hard-parked (`PARK-KILL`). A continue-resume needs progress
  evidence (last turn not a NOOP) and stays under `max_resumes` (12 / rolling 24 h), else `PARK`. Parked sessions get
  no resumes and hold their events queued until `handoff_sessions.py unpark <slug>`. A usage-limit hit with no
  parseable reset waits for `budget.json` `resets_at`; the last-resort backoff is 6 h → 12 h → 24 h, never 30 min.
- **G3 budget meter.** `codex_budget_meter.py` (run by every dispatcher pass; standalone `--loop`, `--claude`,
  `--dry-run`) sums rollout `token_count` usage incrementally into `<flags>/budget.json`: weekly fraction (provider
  meter), `resets_at`, burn rate, token totals; alarms at 50 % / 80 % / exhausted through `rowflow/notify.py`; sets
  `paused_until = resets_at` when exhausted, which the dispatcher turns into a codex engine pause (`BUDGET-PAUSE`).
- **G4 rotation.** Last-call input above `context_rotate_tokens` (60 k) → `ROTATE`: the session's report.json
  (`next`, `next_step`, `box`, `wrapped_sha`) becomes the checkpoint and the next start is a fresh thread carrying it.
- **G5 width.** `max_live = min(cap [2], floor(remaining fraction / hours to reset / per-session burn))`; 0 when the
  budget is exhausted. Sessions are told to fan out to at most 2 subagents.
- **Dry run:** `handoff_sessions.py dispatch --dry-run` prints, per session, the pinned command it would spawn or the
  refusal/park/kill/rotate verdict, plus budget and width; it writes and signals nothing.
- Tests: `scripts/coordination/tests/test_token_guards.py` (each guard with a negative control).

## Roles

- **Handoff sessions / codex-gen**: run the flow against their backlog file, forever. Never arm rows, write grants,
  hold or kill compute; the keeper (allocator) owns the calendar.
- **ws58 (calendar owner)**: keeps the keeper (the allocator), generator and dispatcher healthy; starts handoff sessions;
  puts new work into the backlog. No ad-hoc orders to panes: change the backlog or the goal file.
- **Operator**: trust-boundary ratifications, destructive host actions, un-parking a lineage.

## Operator rulings of 2026-11-01 (binding; each is implemented where the pointer says)

| ruling | where it lives |
|---|---|
| **Remove every gate that is not indispensable.** The dry run on the real lane is the only proof a row needs. | `rowflow.py`, keeper v11 step 5 ("Retired" lists above) |
| **One allocator, one snapshot per tick** (2026-11-01 evening: "compute keeps idling because of scheduling races"): dry runs and grants compete fairly from one snapshot, a region is never handed twice, invariants self-heal and alert on the 3rd repeat. | `rowflow.py allocate`, keeper v11, "The allocator" above, `test_allocator.py` |
| **The owner writes only a launcher and a spec**; publishing derives everything else. | `publish_row.py`, "The row flow" above |
| **The dry run is robust**: free disk below the engine floor (`FILLER_DISK_FLOOR_GIB`, 150 GiB; 20 GiB in a smoke) is a WAIT, never a FAIL; a job that ignores the stop file after 600 s grace is truncated by signal and PASSES with a warning (the engine hard-end is production's own truncation path); directory results count as units; a FAIL is retried only when launcher, spec or rowflow change (sha-keyed). | `rowflow.py` (`dryrun-run`), `filler_run15.sh` (`FILLER_DISK_FLOOR_GIB`) |
| **The owner files its own results** (`filing-done/<id>.FILED`) when the dispatcher resumes it with `result_path` + `decision_rule`; the sonnet filing subagent is retired. | "end" row above, `handoff_sessions.py`, `filing_watch.sh` (writes `filing-due.jsonl`, raises the takeover alarm) |
| **Session per handoff, at most 5 live, auto-started in rank order (rows unblocked), inference first.** | "Session per handoff" above, `handoff-sessions.json` knobs `max_live`/`auto_start` |
| **codex-gen takes small tasks only.** | `/mnt/raid0/llm/tmp/compute-flags/GOAL-codex-gen.md` (git: `scripts/coordination/churn/GOAL-codex-gen.md`) |
| **Per-task wrap-up and transfer portability** (`WRAPPED <sha>`, `transfer`). | "Portability" above |
| **Fan-out in every launched session.** | brief section + prompts in `handoff_sessions.py` |
| **Sessions launch inside `/workspace`** (or one of its worktrees). | `project_cwd()` in `handoff_sessions.py`, `REFUSED-CWD` |
| **tmux windows are addressed by NAME, never by index; every handoff session has its own window `h-<slug>` in session `agent`; `renumber-windows` is off** on that session (window numbers must not shift when a window closes). Operator windows: `claude` (ws58) and `codex-gen`. Nobody sends keys to an agent pane. | `handoff_sessions.py` (tmux section), `churn_up.sh` (`ensure_tmux`, `--status` warns when renumber-windows is not off) |

## Reboot / cold start, stop, audit

Moved to the runbook: [`backlog-churn-runbook.md`](backlog-churn-runbook.md) (component inventory, preconditions,
`churn_up.sh` spin-up / `--dry-run` / `--status` / `--stop`, measured verification, audit checklist, open defects).

## AI-free mechanization (CAF, 2026-11-01; `handoffs/active/coordination-and-churn-pipeline.md`)

**Mechanized wrap-up (CAF-2, 2026-11-01).** A session ends a task by writing the turn record (`{slug, state, task_text,
ticks: [text], progress_md, paths, belief, message, question, rows_published, trailers?}`) and running
`python3 scripts/coordination/churn/wrapup.py --json <rec.json>` (lane defaults to `worktrees/mains/h-<slug>`); the six
manual steps are gone. The tool merges origin/main into the lane, resolves every tick by TEXT (exactly one open `- [ ]`
across `handoffs/active|blocked`, else refuses before writing), appends `progress_md` under `## <HH:MMZ> — <task_text>` in
`progress/YYYY-MM/YYYY-MM-DD-handoff-<slug>.md`, flips the boxes as `- [x] … ✅ <date> [belief: …]`, runs
`index_state.py --check` when a handoffs/ file is touched, commits ONLY the pathspec (`paths` + progress + ticked files,
with `trailers`), pushes via `serialized_push.py --repo <lane>` (5 retries on a held lock), proves `cherry origin/main`
empty, writes `handoff-sessions/<slug>/report.json` with `wrapped_sha`/`wrapped_at`, and prints `WRAPPED <sha>` as the
last line (`--dry-run` = plan only, nothing written). Any failure stops with rc 1 and a one-line `[wrapup] FAIL: …`.

**CAF-5 `scripts/coordination/churn/file_result.py`** — files a row's run result without an agent turn when its `decision_rule` is machine-checkable. `python3 scripts/coordination/churn/file_result.py <row-id> [--flags DIR] [--verdict-json FILE] [--lane DIR] [--dry-run]` loads the epyc.row.v3 manifest (`ready/<id>.json` or `ready/*/<id>.json`), the end record `grants/<id>.ended|.complete` (`rc=N` on line 1; `.complete` without rc = 0) and the result at `result_path` (json: top-level keys, dotted paths; jsonl: LAST record + `units` = record count; `rc` always present).
A rule is machine-checkable when it parses as `<metric> <op> <number>[%]` comparisons (`< <= > >= == !=`) joined by `and`/`or` with optional parentheses, e.g. `tps_delta >= +2% and ppl_delta <= 0.1%`; `%` and the sign are notation, the metric is compared to the bare number (no `eval()`, tiny tokenizer + recursive-descent evaluator). Verdict is `pass|fail|inconclusive`; a metric missing from the result (or a missing result file) is `inconclusive` with the name in `reason`, never a pass.
It writes `<flags>/filing-done/<id>.verdict.json` — a record valid against the existing `scripts/coordination/filed_verdict.schema.json` (`epyc.filed.verdict.v1`: `outcome_class` SCIENCE-VERDICT for pass/fail, PARTIAL-VERDICT for inconclusive, `phase: filing`, `verdict.native_result_sha256`) extended with `{row, row_verdict, rule, values, rc, result_path, filed_by, at, reason}` — prints one `FILED …` summary line plus the suggested tick line (`<ROW-ID> … ✅ <date> rc=<rc> <verdict> <values> [no-belief: row verdict filed by file_result.py]`) for the wrapup.py step, then touches `<flags>/filing-done/<id>.FILED` (the DSH-2 receipt the dispatcher and reaper key on). `--dry-run` prints the same and writes nothing.
Non-numeric rules exit 4 with `NEEDS-AGENT-VERDICT <id>: <rule>`; the agent then writes `{verdict: pass|fail|inconclusive, rationale[, tick_text]}` and re-runs with `--verdict-json FILE`, which files it with `filed_by: agent`; when `tick_text` is present the handoff box named by `handoff_task` (`handoffs/active/<h>.md:<ROW-ID>`, resolved under `--lane`) is ticked via `flip_checkbox.flip` by token (exit 5 if the anchor is missing/ambiguous — verdict written, FILED not touched). Exit 2 = manifest or end record missing / bad `--verdict-json`.
Dispatcher wiring: on `grants/<id>.ended|.complete` run `file_result.py <id> --flags <flags>` first; exit 0 → skip the agent filing turn and hand only the printed TICK line to wrapup.py; exit 4 → send the existing `end_prompt` with the `--verdict-json` instruction instead of "YOU file the verdict". Tests: `python3 -W ignore -m unittest scripts.coordination.tests.test_churn_file_result` (12 tests, temp flags dir only).

**Spec lint and `--repair` (CAF-4).** `publish_row.py <spec.json>` now lints before `rowflow.publish`: a `result_path` that is a completion marker (`.complete`/`.ended`/`.done`/`.FILED`, a `grants/` path, `COMPLETE*`/`TERMINAL*`) is rewritten to the declared results file in the same run dir (`result_format: json` → `RESULT.json`, `jsonl` → `results.jsonl`; no declared format → one-line refusal), and missing `lane` (launcher `--class`), `scratch_root` (the launcher's job dir), `keep` (result_path relative to scratch_root) and `kind: compute` are filled; every rewrite prints one `LINT` line. Nothing else moved: `rowflow.publish` still derives regions, window and the launcher sha.
After a dry-run FAIL, `publish_row.py --repair <row-id>` reads the latest `dryrun/<id>/FAIL-*.json` and `ready/<id>.json`; when the reason is "no unit in <p>" / "before writing a unit to <p>" and <p> is a marker or a `RESULT.json`/`results.jsonl` was written in its run dir during the run (or a publish refusal names a lint-derivable field), it rebuilds the spec from the row, lints it and republishes under the SAME id (the FAIL record pins the old row sha, so a changed row is `needs-dryrun` again); output `REPAIRED <id> -> <id>: result_path ... -> ...`. Snapshot rows keep their `snapshot` record.
Any other reason exits 3 with `UNKNOWN-FAILURE-CLASS <reason>` and changes nothing — that one is still the agent's fix task. `--repair` never starts a dry run; the keeper picks the republished row up itself.
Tests: `scripts/coordination/tests/test_rowflow_repair.py` (lint rewrite + fills, class-(1) repair with launcher sha recorded, unknown class exit 3).

# JEV-3 shadow typed judgment (ws58, 2026-11-02) — scratch
- Call path: `sys.path += [/mnt/raid0/llm/epyc-orchestrator]`; `LLMPrimitives(mock_mode=False, server_urls=get_config().server_urls.as_dict(), num_slots=cfg.server.num_slots)`; `src.typed_decisions.run_typed_decisions_native(prim, state=..., questions=[Question(kind=choice, options=<enum>, option_descriptions=...)], role="worker_fast")` -> `DecisionResult.decisions[0].value|probabilities|confidence`; failures -> `ParseFailure(reason, detail)`. Native = local llama-server HTTP (/tokenize probe + one constrained read), no orchestrator API.
- Interpreter split: rowflow.py needs py>=3.12 (nested f-string), typed_decisions needs the 3.11 venv -> typed read runs in a `.venv/bin/python3 -I typed_shadow.py _typed-worker` subprocess (JSON over pipes); tests mock the seam.
- Files: scripts/coordination/churn/typed_shadow.py, scripts/coordination/tests/test_churn_typed_shadow.py (13 tests OK, hermetic, 0.02s).
- Replay 2026-11-02 over /mnt/raid0/llm/tmp/compute-flags: 46 FAIL records; heuristic = 42 unknown / 3 marker_result_path / 1 result_dir_path; typed = 46 unavailable (every stack server :8070-:8180/:8102 down -> `native_tokenizer_unavailable`, fail-closed, zero model calls, zero guessed labels). agree=0 disagree=0 -> re-run `python3 scripts/coordination/churn/typed_shadow.py replay` once worker_fast (:8102) is up to get the diff table.
- Expected informative cases once live: the 42 "unknown" are nearly all job-rc (rc=1/3/70/143, no ended record) or stop-file (codex3-cs8-g1b-cascade) by reason text -- classes repair() has no name for; typed FailClass has them.
- Dispatcher shadow line (handoff_sessions.work_state call site, after `state, why = work_state(...)`): `sh = typed_shadow.classify_work_state(b, open_boxes); log(flags, f"TYPED-SHADOW {slug}: heuristic={state} typed={sh['label'] and sh['label'].value} reason={sh['stop_reason'] and sh['stop_reason'].value} source={sh['source']}")`
- **2026-11-02 REPLACE (operator-approved)**: the shadow above is superseded. `churn/typed_classify.py` `decide_fail` (publish_row.repair) and `decide_work_state` (handoff_sessions.work_state) take the typed label as the decision (including `unknown`); the regex classifier answers ONLY when typed is unavailable (worker_fast :8102 not listening, import/transport/parse failure, out-of-enum), recorded as `source=regex-fallback` with the unavailable detail. TYPED-SHADOW log line and the agree/disagree replay diff are deleted; `typed_classify.py replay` now counts typed_answered vs typed_unavailable.
- Shadow only: no caller behaviour depends on the typed label; activation needs its own gate (JEV plan row JEV-3).
