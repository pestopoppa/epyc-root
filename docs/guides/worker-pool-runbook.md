# Worker Pool — Operator Runbook

**Scope**: operating `scripts/coordination/worker_runner.py` — the ephemeral pool-worker runner.
Every key name and bound in this document was read out of that file, out of
`coordination/session-bus/config.yaml`, or off a real run directory under
`/mnt/raid0/llm/worker-pool/runs/`. Where the code and a comment elsewhere disagree, this
document follows the code and says so.

**Design context** (not repeated here): `docs/design/loop-owned-fleet.html` (plan of record),
`handoffs/active/loop-owned-fleet-implementation.md` (P2-*), `coordination/session-bus/BUS_PROTOCOL.md`
(rule 8, amended 2026-08-16 for pool workers).

---

## 0. The one-paragraph model

A pool worker is **one process, one assignment, one typed report, then exit**. The runner is exec'd
fresh per assignment and lives only as long as it; there is no resident supervisor, so the code that
runs a batch is the code on disk when the batch started (`git pull` *is* the deploy). The machine's
channel to the worker is one-way and typed: **a brief file in, a report file out**. The runner never
types into the worker's pane and never reads pane text to make a decision. The pane exists for *you*.

One mechanical detail that matters when you are reasoning about signals: in the normal `tmux` path
the harness is a child of the **tmux server**, not of the runner. The runner learns the pid from the
wrapper's `harness.pid` file and then *polls* it (`os.kill(pid, 0)`); it never `wait()`s on it. Only
the test-only `--spawn-mode direct` produces a real child process. What makes the kill safe is not
parentage — it is that the pid was **captured by this process from its own wrapper**, never matched
by name.

---

## 1. Enabling the pool

The switch is one key in `coordination/session-bus/config.yaml`:

```yaml
worker_pool:
  enabled: false          # ← the master switch
```

### Why it ships `false`

Two properties are deliberately separate:

| | granted by | meaning |
|---|---|---|
| **schedulable** | the `workerpool` roster row | the daemon may assign rows to the pool endpoint |
| **executable** | `worker_pool.enabled` | a runner may actually spawn a worker |

With the roster row present and the flag off, the daemon treats the endpoint as *not ready* and
leaves rows **READY and visible** rather than assigning into a pool that cannot run them. The
alternative — schedulable but not executable — is the measured 2026-08-14 failure shape: the daemon
assigns, nothing runs, the lease expires, the row dies. The config comment states the flip condition:
turn it on **only after the runner has been proven end-to-end on this host**.

`check_enabled()` refuses the spawn with exit code **2** when the flag is false. Nothing has been
started at that point.

### What the daemon does with the flag

The daemon's half of the gate is `_exec_endpoint_ready()` in `scripts/coordination/session_bus_coordinator.py`.
It answers *is this exec endpoint ready* with `None` (ready) or a reason string. On the two paths
that matter — the assignment loop and fleet-presence — it is called **with** the config and says "not
ready" when the flag is false, when the endpoint names no program, or when the runner program is
missing or unreadable next to the daemon's own checkout. (It is also called without config from
`_looks_dead()`, where only program presence is checked; the flag is invisible on that path.)

A not-ready endpoint produces a `would-skip` advisory — `agent looks dead (worker_pool.enabled is
false — the pool is schedulable but not executable…)` — and the row is **never assigned; it stays
READY**. It is not parked, not blocked, not assigned anyway. `workerpool` also stops counting toward
"is any main alive" while not ready, so a disabled pool cannot prop up the fleet-presence gate.

The pool is schedulable because of one roster row in the same config file:

```yaml
- {id: workerpool, role: main, lanes: [cpu, none], endpoint: "exec:worker_runner", drain: none}
```

`role: main` is load-bearing — the daemon only schedules mains. The daemon additionally only assigns
at all when `authority: assign` (its current setting).

When it does assign, `_exec_worker_runner()` builds the argv itself:

```
<python> scripts/coordination/worker_runner.py --bus-root <bus> run \
    --lane <first free lane> --task-id <tid> --row-text <task_text, truncated to 4000 chars> \
    [--row-ref <spec_ref>] [--screened-by <screened_by>]
```

and launches it **detached** (`start_new_session=True`), never waiting on it and never reading its
exit code. Three consequences worth knowing:

- **The daemon path is one row per exec.** It never passes `--assignment`, `--batch-id`,
  `--harness`, `--source-handoff`, `--spawn-mode` or `--pilot-override`, so static batching
  (`max_rows_per_batch`) is exercised only by hand-dispatched runs.
- **A refusal from a daemon-launched runner lands in a log, not on your terminal**:
  `/workspace/logs/worker_runner/<task_id>.log` (truncated to 60 chars, `/` → `_`). That is the first
  place to look when the daemon reports `exec-launched` and nothing appears to happen.
- **No free lane is not an error.** `_free_pool_lane()` returns `None` and the daemon emits an
  `exec-deferred` advisory (`no free pool lane (all worktrees hold a live worker)`).

The daemon picks the lane by reading the **first whitespace token of `<lane>/.worker.lock` as a pid
and testing `/proc/<pid>`**, over `pool_root` subdirectories whose name starts with `lane`. The
runner **acquires the same file with `flock`**. That is deliberate: a lock you *observe* is TOCTOU
and a pid file outlives its writer, so the flock is the real exclusion and the pid text is the
daemon's read-only hint. One file, two readings that cannot disagree.

### Before you flip it: check that the running daemon is not stale

The runner is exec'd fresh per assignment, so *it* cannot go stale — but the daemon that execs it is
long-lived, and a daemon started before the `exec:` endpoint code existed will never launch anything
no matter what the flag says. Check before flipping, not after:

```bash
cd /mnt/raid0/llm/epyc-root
python3 -c "import json;print(json.load(open('coordination/session-bus/heartbeats/coordinator-daemon.json'))['source_tree'])"
git rev-parse HEAD:scripts/coordination
```

Equal ⇒ the daemon is running current coordination code. Unequal ⇒ **restart the daemon first**
(`bus_supervisor.sh` makes the same comparison).

This is not hypothetical. On 2026-08-16 the live daemon was measured at `source_tree 86015c01` while
HEAD was `0200a67d`, and its `would-skip` advisories for `workerpool` were still citing the *tmux*
liveness predicate — a tmux test applied to an exec endpoint is the signature of exactly this. It was
restarted later the same morning and the advisories switched to the exec-endpoint text. The tell in
the advisory stream is worth remembering: **which predicate the refusal cites tells you which code is
running.**

### Running before the flip: supervised manual runs

The flag says "flip only after the runner is proven end-to-end", and proving it requires running it.
`--pilot-override` breaks that circularity for a **supervised, hand-dispatched** run:

```bash
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python \
  /mnt/raid0/llm/epyc-root/scripts/coordination/worker_runner.py run \
  --lane lane0 \
  --task-id my-task-id \
  --row-text "the full task text — this is the row IDENTITY" \
  --screened-by "operator dispatch 2026-08-16" \
  --source-handoff handoffs/active/some-handoff.md \
  --pilot-override
```

(The file carries a shebang for that interpreter but is **not** mode +x, so invoke the interpreter
explicitly.) A batch of up to three rows goes in a file instead:
`--assignment /path/to/assignment.json`, an object with a `rows` list. Per row the brief builder
consumes `task_id`, `task_text`, `row_ref`, `screened_by`, `source_handoff`, `expected_occupancy` and
`constraints` — the last being a list of `{text, source}`, because a constraint that cites nothing is
prose in disguise. A bare string is accepted but stamped `source: "unsourced"` so the defect is
visible in the brief rather than indistinguishable from a sourced one.

`--pilot-override` prints a warning to stderr, does **not** touch the daemon's gate (the daemon reads
the config, not this flag), and does **not** bypass the rule-8 ack — a runner may not kill without
the amendment, override or no override.

### The other fail-closed gates

All of these refuse **before anything is spawned** (exit 2). Read the refusal text: each one names
its own origin. They are listed in the order `run()` actually applies them, which matters — the first
eight run before anything has been touched, but the last three run *after* the batch's rows have been
O_EXCL-claimed and possibly screened and parked, so "refused" there is not quite "nothing happened".

| # | gate | refuses when |
|---|---|---|
| 1 | `_require_roster_id` | `workerpool` is not a roster id — a runner that cannot record results must not start work |
| 2 | `check_enabled` | `worker_pool.enabled` is false and no `--pilot-override` |
| 3 | `check_bounds` | config asks for **more** than a D1 bound (see §5) |
| 4 | `check_provider_pin` | `provider` is pinned but the environment sets `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `ANTHROPIC_BASE_URL` or `ANTHROPIC_AUTH_TOKEN` |
| 5 | `check_rule8_ack` | `worker_pool.rule8_amendment_ack` is unset |
| 6 | `resolve_harness` | `worker_harness` names a harness that does not exist |
| 7 | `resolve_lane` | lane is outside `pool_root`, matches `*.orphan*`, does not exist, or is not a git worktree |
| 8 | `check_concurrency` | `min(max_concurrent, 4)` lanes are already held |
| 9 | `check_batch` | more than `min(batch_cap, 3)` rows, rows from mixed `source_handoff`, or missing/duplicate `task_id`s |
| 10 | `build_brief` | a row has no `task_text`, or the brief exceeds 4096 bytes |
| 11 | `LaneLock.acquire` | the lane is already held by a live worker (`flock` on `<lane>/.worker.lock`) |

Both caps are applied as `min(config, hard bound)` at the point of use, so lowering
`max_rows_per_batch` to 1 makes a two-row batch a refusal.

`rule8_amendment_ack` is currently set in config to
`"D6 ratified 2026-08-15 (plan of record: docs/design/loop-owned-fleet.html); BUS_PROTOCOL.md rule 8 amendment 2026-08-16"`.
Clearing it disables the whole pool, not just the kill path — the runner enforces a lease, therefore
it may kill, therefore it refuses to spawn at all without the ack.

### The worker's authority is a config block, not code

`worker_pool.permission_profile` is materialised per run into `<run_dir>/permissions.json` and handed
to the harness (for `claude`, as `--settings`). It is injected as **data**, never baked into the
runner, so widening a worker's authority is a config edit that shows up in a diff:

```yaml
worker_pool:
  permission_profile:
    allow: ["Read", "Grep", "Glob", "Edit", "Write", "Task", "Bash(git *)", "Bash(python3 *)", …]
    deny:  ["Bash(pkill *)", "Bash(pgrep *)", "Bash(killall *)"]
```

`Task` is in the allow list deliberately — a worker fanning out its own subagents is the multiplier
the pool tier exists for, and `subagents_spawned` in the report is how it gets measured. The deny
list is the project's absolute no-name-pattern-kills rule, enforced at the permission layer rather
than trusted to prose. A profile with empty `allow`/`deny` constrains nothing beyond the harness's
own defaults; that is what the earliest pilot runs ran under.

Whatever the profile says, **a denied tool call never renders as a pass**: the worker is required to
record every denial in `report.denials`, an attributed denial fails that row, and an *unattributed*
one fails the whole batch.

### Premise screening happens before the spawn

Each row is screened by `premise_screener.screen_premise`. Every failure mode of that call — absent,
broken, throwing, malformed verdict — returns **`unknown`**, and `unknown` parks the row. A screener
that cannot answer must never be indistinguishable from one that said yes.

A parked row is emitted once as a `requeue` (status READY, `parked_reason: premise-<verdict>`) plus a
`task-propose` asking for the premise to be re-verified, de-duplicated on (row identity, verdict) via
`/mnt/raid0/llm/worker-pool/parked/<claim-key>.json`. If **every** row parks, no worker is spawned
and the run directory stays empty — that is what an empty run dir means.

A row whose `screened_by` names a fresh dispatch (`operator dispatch`, `operator pilot dispatch`,
`console dispatch`, `verdict=still-needed`) **inherits** that screen instead of being re-screened;
the brief records `"premise": "still-needed"`. An *empty* `screened_by` is never accepted — that row
goes to the screener, and an `unknown` from there still parks.

---

## 2. Watching a running worker

Every production worker runs in a **visible tmux window** named `wpool-<lane>` in the session named
by `tmux.live_session` (currently `agent`):

```bash
tmux list-windows -t agent -F '#{window_id} #{window_name}' | grep wpool
tmux attach -t agent          # then pick the window
# or, without attaching:
tmux capture-pane -p -S - -t agent:wpool-lane3 | tail -50
```

The runner never creates the tmux session: if `tmux has-session` fails it refuses, full stop. Its
refusal message says the config key `tmux.allow_session_creation` is authoritative, but that is not
true of this code path — `load_pool_config()` reads the key and nothing ever reads it back, so
flipping it to `true` changes nothing here. Create the session yourself before dispatching.

### Steering it by hand is expected and safe

This is the design, not a workaround. **Human authority over the pane is the design; machine
authority over the pane is the defect.** The pane is visible precisely so you can watch a worker and
answer a permission prompt yourself.

It is safe because the machine's decision channel does not include the pane:

- the runner **never types into a pane** and **never reads pane text to decide anything**
  (`test_worker_runner.py::test_no_pane_io_decision_channel` enforces this at the source level);
- the only completion signal is the **report file** — never anything the worker prints;
- `capture_scrollback()` is the single place that touches pane text, and its output is written to
  `pane-scrollback.log`, attached to a failed row, and **read by a person** — never parsed or
  branched on.

So typing into the pane cannot corrupt the runner's state machine. What you type is just input to the
harness, exactly like a keystroke in any other interactive session.

### One thing NOT to do: killing the pane

The runner's salvage is guarded by `handle.alive()` — it runs **only when the runner finds the worker
still alive and kills it itself**. Kill the harness yourself before it has written `report.json` and
you land in the other branch: `watch()` sees the pid gone, returns `exit`, the salvage block is
skipped, **no salvage ref is written**, and the rows come back FAILED with
`failure_reason: report-invalid` and `detail: "report file was never written"`. The work is still
sitting uncommitted in the lane — nothing is destroyed — but nothing has captured it either.

Killing the *window* is murkier still. `watch()` polls the harness pid from `harness.pid`, not the
pane; whether that pid dies with its pane is a signal-propagation question the runner does not
settle. If it survives, the runner keeps waiting and the lease path — kill **and** salvage — is what
eventually takes it. So killing a pane gives you neither outcome reliably.

If you need to stop a worker and keep its work, in preference order:

1. let the lease expire — the runner kills *and* salvages, which is the path with the no-loss proof;
2. commit the lane's work yourself with a pathspec-limited commit;
3. salvage by hand — **after** the worker is dead, never while it is still writing:

```bash
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "/mnt/raid0/llm/epyc-root")
from pathlib import Path
from scripts.coordination.worker_runner import salvage_worktree
print(salvage_worktree(Path("/mnt/raid0/llm/worktrees/pool/lane3"), "manual-<batch_id>"))
PY
```

Note the `Path(...)` — the function takes a `Path`, and a bare string raises `AttributeError`. The
"after it is dead" order is not fussiness: `verify_salvage()` byte-compares the committed blobs
against the **working tree**, so a file that changes between the staging and the verify read raises
`SalvageError`. The runner itself only salvages after proving the pid dead, for exactly this reason.

`salvage_worktree()` is otherwise non-destructive and re-runnable: it builds its tree in a temporary
index (`GIT_INDEX_FILE`), never the lane's own index or HEAD, so the lane is left exactly as found.

---

## 3. Where the run artifacts live

Runtime root is `worker_pool.runtime_root`, defaulting to `/mnt/raid0/llm/worker-pool` (the key is
not set in config today, so the default applies). Per batch:

```
/mnt/raid0/llm/worker-pool/runs/<batch_id>/
```

`batch_id` is `--batch-id` if given, otherwise `<first task_id>-<UTC %Y%m%dT%H%M%SZ>` —
e.g. `pilot-04-worker-pool-operator-runbook-20260816T102313Z`.

| file | written by | when |
|---|---|---|
| `brief.json` | runner | before spawn — the typed dispatch (`worker_brief.v1`) |
| `permissions.json` | runner | before spawn — the D2b allowlist, passed to `claude --settings` |
| `spawn.sh` | runner | before spawn — generated wrapper; **do not edit** |
| `harness.pid` | wrapper | at spawn — the pid the runner captured itself |
| `harness-transcript.log` | wrapper | continuously — `tee` of the harness's own stdout/stderr |
| `progress.jsonl` | **the worker** | per row — `{"task_id":…, "event":"start"\|"complete"}` |
| `report.json` | **the worker** | at completion — `worker_report.v1`; **the only completion signal** |
| `harness.rc` | wrapper | after the harness exits — its exit status |
| `pane-scrollback.log` | runner | only on the kill path — evidence for a human |

An **empty run directory** means the batch was parked before spawn (premise not `still-needed`).
Absent `report.json` means the worker never wrote one. Absent `harness.rc` means the harness has not
exited yet — that plus a live pid is the shape of a worker still running.

**`report.json` must be written last.** `watch()` polls three signals and no fourth: process exit,
report file present, lease expiry. Once the report appears, the worker gets a bounded grace
(`post_report_grace_s`, default 60 s) to exit on its own; a worker still running after that is taken
by the kill path — SIGTERM, salvage, and a `defect` message on the bus — because from the runner's
side "report written, process will not leave" is indistinguishable from a hang. A worker that writes
its report at the halfway mark gets killed at the halfway mark.

Adjacent state: `/mnt/raid0/llm/worker-pool/parked/<claim-key>.json` holds the last park verdict per
row, which is what makes the park emit once instead of every tick.

The runner's own output goes to the bus, not to the run dir — everything lands in
`coordination/session-bus/outbox/workerpool.jsonl`:

- one `task-complete` (or `requeue`, for a row returning to READY) **per row**;
- a `finding` to `auditor` carrying the audit packet — **pointers only**, never the worker's own
  summary, so the reviewer is not anchored on the defendant's statement of the case;
- when something passed *and* produced commits, a `task-propose` merge-gate promotion row;
- when a kill or salvage happened, a `defect` to `coordinator-agent` carrying the kill record and the
  salvage manifest;
- and, on the park path, a `requeue` plus a `task-propose` per parked row asking for its premise to
  be re-verified.

**The runner never writes `queue.jsonl`** — status is proposed, the daemon transcribes (with the
caveats in §8).

---

## 4. A FAILED row with a `salvage_ref`

### What it means

The lease expired, so the runner killed the worker and **salvaged** its state. Kill is allowed; loss
is forbidden (D6).

- **Kill**: SIGTERM → grace (`lease_grace_s`, currently 60 s) → SIGKILL, on **a pid this runner
  captured itself**, signalled to that pid's process group so subagents die with it. Never a name
  pattern (INC-20260731-broad-process-pattern-kills). It refuses to signal its own process group or
  group 1, falling back to the single pid. Death is verified, not assumed.
- **Salvage**: everything `git status --porcelain -uall --no-renames` reports in the lane —
  modified, added, deleted, untracked — is committed to a ref, with `.worker.lock` as the single
  named exclusion. The harness transcript, the captured scrollback and the brief go in the same
  commit under `.salvage-evidence/`. Ignored files (build outputs, venvs, `__pycache__`) are
  excluded by design but **enumerated** in the salvage record's `ignored_excluded`, so "excluded" is
  visible rather than silent.
- **Proof**: `verify_salvage()` re-reads the *committed object* and compares every enumerated path
  byte-for-byte against the working tree. A mismatch raises `SalvageError` and the runner exits **3**
  — the loudest thing it can do. Exit 3 means *a human must look at that lane now*; the lane is
  deliberately left untouched.

### Which rows carry it

At lease expiry **at most one** row is blamed: the row `progress.jsonl` shows in progress, or, if
that file is missing or ambiguous, the first briefed row with no completion record — and **none at
all** if every briefed row already appears in the report, in which case the salvage ref is attached
to nothing. The blamed row goes `FAILED / failure_reason: lease-expired / salvage_ref: …`. Rows that
were never started go back **READY, unmarked** — no attempt increment, no failure reason — because
they were never dispatched in any meaningful sense. That is why writing `progress.jsonl` is in the
worker's prompt: it narrows blame at a timeout, and it is not a completion signal.

The full set of `failure_reason` values, all from `classify_outcomes()`. The lease-expiry branch is
evaluated **first**, so at a timeout the reasons below it do not apply to unreported rows:

| reason | carries `salvage_ref`? | meaning |
|---|---|---|
| `lease-expired` | yes | the blamed row at a timeout |
| `report-invalid` | yes | the report failed its own schema — the **whole** document is set aside and every row falls here. **A missing report file lands here too**, with `detail: "report file was never written"` |
| `row-unreported` | yes | a valid report simply did not mention this row |
| `permission-denied` | no | a denial was recorded; an *attributed* denial fails that row, an **unattributed** one fails the whole batch |
| `token-ceiling-breach` | no | `tokens_used` exceeded the D1 ceiling — checked **after** the run, on the worker's self-report |
| `worker-fail` / `worker-blocked` | no | the worker's own outcome for that row |

(`no-report` exists as a constant in the code but `run()` cannot reach it: `read_report()` always
returns a schema error for a missing file, so the `report-invalid` branch wins. If you see
`no-report`, it came from a test, not from a run.)

A worker-reported `skipped` returns the row to READY unmarked rather than failing it.

### Recovering the work

The ref is `refs/salvage/<batch_id>`. Note the discrepancy: the config comment and the
`salvage_worktree` signature both say `<task_id>`, but `run()` passes the **batch_id** as that
argument, so the ref you will actually find is named after the batch. List them rather than guessing.

The pool lanes are linked worktrees of one clone and therefore **share one ref store**, so a salvage
taken in any lane is listable from `/mnt/raid0/llm/epyc-root` and from every other lane:

```bash
cd /mnt/raid0/llm/epyc-root
git for-each-ref --format='%(refname) %(objectname:short) %(committerdate:iso) %(subject)' refs/salvage/
git show --stat refs/salvage/<batch_id>                      # what was captured
git diff --name-status refs/salvage/<batch_id>^ refs/salvage/<batch_id>   # the delta vs the lane's HEAD
```

The commit's author and committer are `worker_runner <workerpool@epyc.local>`, so a salvage is
identifiable in any log by author alone.

Read the attached evidence without checking anything out:

```bash
git ls-tree --name-only refs/salvage/<batch_id>:.salvage-evidence
git show refs/salvage/<batch_id>:.salvage-evidence/harness-transcript.log
git show refs/salvage/<batch_id>:.salvage-evidence/pane-scrollback.log
git show refs/salvage/<batch_id>:.salvage-evidence/brief.json
```

Recover, in increasing order of commitment. Every form below was exercised against a scratch repo
driven through the real `salvage_worktree()` (this clone has no salvage refs yet — the pool has not
had to kill anything):

```bash
# read one file, touching nothing at all
git show refs/salvage/<batch_id>:path/to/file > /workspace/tmp/file

# restore one file into the tree you are standing in, WITHOUT staging it
git restore --source=refs/salvage/<batch_id> -- path/to/file

# everything, in a fresh worktree — the lane keeps its state
git branch recover-<batch_id> refs/salvage/<batch_id>
git worktree add /mnt/raid0/llm/tmp/recover-<batch_id> recover-<batch_id>

# or replay the salvaged delta onto a branch of your own
git cherry-pick refs/salvage/<batch_id>
```

The salvage commit is parented on the lane's HEAD at kill time, so `<ref>^` is the right baseline, a
deletion in the lane is a real deletion in the salvage tree, and a recovery branch rebases cleanly
onto whatever the lane was tracking. (Note what the no-loss proof does and does not cover: it
compares the committed *paths* against the working tree. It does not check the parent — that comes
from `git rev-parse HEAD` at salvage time.)

Five properties worth internalising, each observed on a real salvage rather than assumed:

- **`git checkout -b recover-<id> refs/salvage/<id>` fails inside the still-dirty lane** — "local
  changes would be overwritten". It aborts safely and leaves the lane intact, but the recovery route
  from within an occupied lane is `git branch` + `git worktree add`, not a checkout in place.
- **`git checkout <ref> -- <path>` STAGES the file; `git restore --source=<ref> -- <path>` does
  not.** Prefer `restore` for surgical recovery, especially in a shared clone where a stray staged
  path rides into the next commit anyone makes.
- **Re-salvaging the same id overwrites the ref, and there is no reflog for `refs/salvage/*`**
  (`core.logAllRefUpdates` covers heads/remotes/notes/HEAD only). The tree is idempotent for
  unchanged state, but if the lane changed in between, the previous salvage commit becomes orphaned
  and prunable with no ordinary way back. If a lane may be salvaged twice, `git branch` the first
  commit before re-running.
- **`refs/salvage/*` is local to this clone.** A default `git push` / `git fetch` / `git clone`
  neither sends nor receives it; moving one takes an explicit refspec
  (`git push <remote> 'refs/salvage/*:refs/salvage/*'`). It *is* a ref, so it anchors its objects
  against `gc` and it *does* show up in `git log --all` — but not in `git branch`. The risk is not
  loss, it is invisibility: nothing surfaces an unrecovered salvage except
  `git for-each-ref refs/salvage/`. Make that part of the sweep, and retire a ref with
  `git update-ref -d refs/salvage/<batch_id>` once its work is recovered or judged worthless.
- Salvage is re-runnable and non-destructive. Running it twice on an unchanged lane produces the same
  tree; it never touches the lane's index, HEAD or working files.

---

## 5. D1 bounds

D1 is *standing spawn authority, bounded* — not a tunable. The bounds are compiled into
`worker_runner.py` and a config asking for **more** is **refused, never clamped**: a silent clamp
reads as compliance to whoever wrote it.

| bound | constant in `worker_runner.py` | config key | current value |
|---|---|---|---|
| concurrent workers | `HARD_MAX_CONCURRENT = 4` | `worker_pool.max_concurrent_workers` | 4 |
| rows per batch | `HARD_BATCH_CAP = 3` | `worker_pool.max_rows_per_batch` | 3 |
| tokens per batch | `HARD_TOKEN_CEILING = 250_000` | `worker_pool.token_ceiling_per_batch` | 250000 |
| provider | — | `worker_pool.provider` (default `anthropic-paid`) | default (unset in config) |

Config **may lower** any of them; raising one is refused at preflight with a message telling you to
take a new operator decision instead.

Additional bounds that are not numbers in a table:

- **Concurrency is measured by *probing*, not counting.** `live_lane_count()` tries the `flock` on
  each `<lane>/.worker.lock`; a lockfile is a birth certificate, the lock is the liveness signal. A
  crashed runner cannot wedge a lane, because the kernel drops its flock.
- **Concurrency is additionally floor-capped by the number of pool worktrees that exist** — four
  today (`/mnt/raid0/llm/worktrees/pool/lane0..lane3`). This one is *not* a runner bound: it falls out
  of the daemon's `_free_pool_lane()`, which enumerates the lanes on disk and returns nothing when
  none is free, combined with one-worker-per-worktree. The runner's own `live_lane_count()` counts
  held locks, not lanes. Either way the runner **will not create a lane** — creating them is a
  deliberate, operator-visible step, and a runner that made its own lane would hide a missing
  precondition. There is no script that creates pool lanes; it is a `git worktree add` you run.
- **The token ceiling doubles as the Phase-2 cost gate**, and it is enforced *after the fact* on the
  worker's self-reported `tokens_used`. It does not stop a run mid-flight. A breach fails every row
  that reaches that check — rows the report never mentioned fail as `row-unreported` instead, and a
  denial on a row shadows the ceiling check for it.
- **The brief is capped at 4096 bytes** (AUD-2) — a dispatch too big to read gets skimmed.
- **Batching is static**: the batch is fixed before the worker starts and never grows, and all rows
  must share one `source_handoff`, so a timeout cannot blame a context the other rows never shared.
- **Provider pinning** is checked against the environment, not asserted (see the gate table in §1).
- The lease itself is `worker_pool.lease_s`, defaulting to **5400 s** (90 min); it is not set in
  config today.

---

## 6. Changing the harness

The harness is a config knob (D2). Adding one is a template-argv dict entry, **not** a code change.

### Fleet-wide

```yaml
worker_pool:
  worker_harness: claude        # built-ins: claude | codex | stub
```

`claude` is the pilot harness (it isolates the structural variable from model quality); `codex exec`
is the intended scale-out default once the pilot has measured tokens/row; `stub` exists so the whole
lifecycle is testable with no LLM, no tokens and no network.

### Per lane

```yaml
worker_pool:
  lane_harness:
    lane0: codex        # flip ONE lane for a scale-out A/B, leaving the other three alone
```

A second, more general spelling overrides *any* key per lane:

```yaml
worker_pool:
  lanes:
    lane0: {worker_harness: codex, token_ceiling_per_batch: 100000}
```

### Precedence

`load_pool_config()` merges in this order, so later wins:

a top-level `worker_harness:` key (defaulting to `"claude"` if absent) < the `worker_pool:` block <
`lane_harness[<lane>]` < `lanes[<lane>]` < `--harness` on the command line.

The CLI flag wins outright and is the right way to try a harness for a single run without editing
config. `DEFAULTS` sits underneath the whole merge for *other* keys — the module's own default must
never outrank a value the operator wrote down — but it carries no `worker_harness` entry, so the
effective fallback for the harness specifically is the literal `"claude"` in `load_pool_config()`.

### Adding a harness

```yaml
worker_pool:
  harnesses:
    myharness: ["mytool", "--cwd", "{worktree}", "--prompt", "{prompt}"]
```

A list of argv parts, or a single string (split with `shlex`). The substitutable fields are exactly:
`{prompt}`, `{brief_path}`, `{report_path}`, `{permissions_path}`, `{worktree}`, `{run_dir}`,
`{python}`, `{stub_cmd}`, `{batch_id}`. An unknown field is a refusal naming the available set — but
note **when**: `build_harness_argv()` runs immediately before the spawn, inside the acquired lane
lock and after the rows have been claimed and the brief written, not at preflight. Typo a field name
and you find out late.

Two constraints on any new harness:

- it must be able to **write files**, because the completion contract is *write `report.json`* and
  the runner reads nothing else. It does not have to take `{prompt}`: the shipped `stub` template
  takes `--brief`/`--report` and no prompt at all. What it must receive, one way or another, is the
  location of the brief and of the report;
- it runs in a visible pane. `--spawn-mode direct` (headless) is **refused for every harness but
  `stub`**, because a production worker the operator cannot watch or steer is the thing D8 forbids.

Config aliases, applied once at load so a bound is never enforced at one value and reported at
another: `max_concurrent_workers` → `max_concurrent`, `max_rows_per_batch` → `batch_cap`,
`lease_grace_s` → `grace_s`.

---

## 7. Exit codes, and what to do about each

| code | meaning | operator action |
|---|---|---|
| **0** | the batch ran (pass **or** fail) and every outcome was recorded on the bus; **or** the batch was parked before spawning; **or** every row was already claimed by someone else, in which case nothing was recorded and no run artifacts exist | read `report.json` and the bus messages — and if there are none, check `claims/` for who holds the rows |
| **2** | a guard said no — usually **before** anything was started | read the refusal text; it names the gate and its origin |
| **3** | **SALVAGE FAILED** — a kill happened and state may be at risk | **look at the lane now.** It was deliberately not cleaned up. Do not let anything else touch it first |
| **4** | internal error | read stderr; the run dir has the brief and whatever transcript exists |

Two qualifications on exit 2, because "refused ⇒ nothing happened" is *almost* but not always true:
a `BusError` also exits 2, and the bus writes happen at the **end** of a completed batch, so a schema
or roster failure there gives you exit 2 after the worker ran to completion. And if the wrapper
launches but never reports a pid within `spawn_timeout_s`, the refusal comes *after* a process
started — the tmux path kills the window, but a `direct`-mode wrapper is left running. Check the run
directory before assuming a clean slate.

Exit 3 is the only code that is an incident.

---

## 8. Sharp edges on the daemon path (verified 2026-08-16)

These are properties of the code as it stands, found while verifying this runbook against it. They
matter only once the pool is daemon-driven; the hand-dispatched pilot path is unaffected. Each one
was read out of the source and cross-checked against live bus data.

- **A pass may transcribe as FAILED.** The runner's `task-complete` payload carries
  `status: "DONE_PASS"`. The daemon's `transcribe()` reads `payload.outcome` and maps
  `pass → DONE_PASS`, `marginal → DONE_MARGINAL_OBS`, **anything else → FAILED** — and `outcome` is
  absent from every message the runner writes (verified against the three real `task-complete` rows
  in `outbox/workerpool.jsonl`, whose payload keys are `status`, `commits`, `artifacts`, … and no
  `outcome`). The same mismatch hits the reason: `transcribe()` reads `payload.reason` while the
  runner writes `payload.failure_reason`, so the transcribed `FAILED` row is also reason-less. Until
  the two agree on one key name, check `report.json` and the outbox rather than trusting a `FAILED`
  queue row from the pool.
- **`requeue` is not transcribed at all.** The literal kind does not appear in the daemon. A parked
  row (premise not `still-needed`) and an untouched-at-timeout row are both emitted as `requeue`,
  which is *relayed as mail* to `coordinator-agent` — it does not move the queue row back to READY on
  its own. Someone has to act on the mail.
- **`task-propose` is relayed AND raises a `relay-handler-reachability` defect**, because the handler
  that turns proposals into queue rows (`intake_proposals`) is reachable only from the manual
  `session_bus_coordinator.py intake` CLI, never from `tick`. Both the promotion proposal and the
  premise-fix proposal take this path. The defect is deduped per message, so it is one per proposal,
  not one per tick — expected noise, not a fault, but it does mean **a promotion proposal sits as
  mail until someone runs `intake`**.
- **Two different leases run at once.** The daemon stamps `lease_expires_ts = now + leases.max_hold_s`
  = **1800 s**, while the runner enforces its own `worker_pool.lease_s` = **5400 s** by default. A
  batch running longer than 30 minutes can be requeued `STALE_REQUEUED` with `attempt+1` by the
  daemon's stall ladder while the worker is still happily working, and `attempt > max_attempts` then
  writes `INFRA_BLOCKED`. Either lower `lease_s` below `max_hold_s` or expect that interaction.
- **The `task-assign` inbox message to `workerpool` is dead mail.** The runner never reads an inbox
  and never emits `ack`, so the assignment sits unread forever. Expect periodic `stuck-unreachable`
  advisories for the pool (unread mail + a non-`tmux:` endpoint is the trigger). You will *not* see
  ack-deadline redeliveries, despite the message carrying `requires_ack: true` — that path needs a
  `corr_id` and the daemon does not put one on this message. All expected: the runner's channel is
  the brief file, by design.

---

## 9. Quick reference

```bash
# what is running right now
tmux list-windows -t agent -F '#{window_name}' | grep wpool
ls -t /mnt/raid0/llm/worker-pool/runs/ | head

# the daemon said exec-launched but nothing happened — the refusal is here
tail -20 /workspace/logs/worker_runner/<task_id>.log

# is lane3 held?
cat /mnt/raid0/llm/worktrees/pool/lane3/.worker.lock     # "<pid> <ts> workerpool"; the flock is the truth

# what did the last batch report
jq . /mnt/raid0/llm/worker-pool/runs/<batch_id>/report.json
tail -f /mnt/raid0/llm/worker-pool/runs/<batch_id>/harness-transcript.log

# what did the runner tell the bus
tail -5 /mnt/raid0/llm/epyc-root/coordination/session-bus/outbox/workerpool.jsonl | jq .

# is anything salvaged and unrecovered
git -C /mnt/raid0/llm/epyc-root for-each-ref refs/salvage/
```
