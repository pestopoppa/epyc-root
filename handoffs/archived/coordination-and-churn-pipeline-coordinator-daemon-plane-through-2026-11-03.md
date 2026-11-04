# Coordination-and-churn pipeline — coordinator-daemon / tmux delivery plane (historical ledger)

> **Historical ledger only — retired 2026-11-03** (content review `213112e68`; superseded by loop-owned fleet, SendMessage + flag files, compute-calendar grant protocol). Current work lives in `../active/coordination-and-churn-pipeline.md`.
>
> Every block below was moved verbatim out of the active handoff (rows retired by the 2026-11-03 content review `0d0bb7646`, plus the sections that existed only to narrate the plane). Each block is preceded by an HTML comment naming its original active-file line range and enclosing heading. bus_supervisor and the coordinator daemon stay DOWN by operator ruling; the daemon scripts remain on disk, dormant.

<!-- moved from active L23-L45; under: ## Track: coordination-and-churn-pipeline -->
#### Current executor start here — 2026-08-13

The M1–M4 build plan below is historical: the bus is already implemented. The current rollout gate
is **AIR-6** near the end of this handoff. `coordinator-agent`, as the live coordinator-daemon owner,
must deploy commit `d7b83ddf93776a56869aee7326c8770602262bc0`, replay the live bus, and retain these canary
artifacts:

1. One `mainA`–`mainD` completion producing exactly one linked audit request, followed by an
   Auditor-authored linked verdict and no direct Auditor→source-main assignment or message.
2. One CPU lease completing request → Inference grant → `region-lock`-receipted activation → renew
   → drain → close-receipted release, with replay reconstructing the same terminal state and zero
   overlapping/orphan leases.
3. `session_bus.py validate` clean of new authority/lifecycle defects and daemon replay idempotent.

Only `coordinator-agent` may then change selected audit policy from `shadow` to `required` and
resource admission from `observe` to `enforce`, after recording the canary artifacts here. GPU
delegation is a separate AIR-7 prerequisite and is not part of the CPU canary.

This handoff remains large because it still carries 18 open delivery-plane, observation, and rollout
tasks; they are indexed by the unchecked checklist entries below. Completed history was not split
during this wrap-up because doing so without moving those live task contracts out of `active/` would
make the next-executor surface less complete, not more.


<!-- moved from active L72-L79; under: #### Nomenclature (operator, 2026-07-27) — one role, two tiers -->
#### Historical M1 executor start — retired

The following was the original build order and is retained as provenance. Do **not** restart M1.
It required zero inference: build **M1 verbatim from §Skeleton** (files + schema + CLI), run the
M1 manual round-trip acceptance, then M2→M4 in order. Every M5 item is independently
flag/grant-gated — do not build any of them until its gate is granted. The coordinator-daemon NEVER
analyzes, reviews, or edits work products — queue/routing/watchdog only ("the moment it
reviews, it's a second main" — operator).

<!-- moved from active L234-L246; under: #### Failure modes designed out -->
#### Hybrid triage (operator decision Q1 — M5, flag-gated, budget-capped)

One-shot smallest-model subprocess (`claude -p --model haiku` via `claude_via_devc.sh`),
never resident, two duties ONLY:
1. **Dead-agent block drafting**: when an agent dies without authoring its decision block,
   draft one from log tails — output always marked `DRAFT-UNREVIEWED`.
2. **Task→tier routing annotation**: classify inbound task proposals against
   `config/routing-table.yaml` (task-class → main, model-tier, effort) and write an advisory
   `routing_annotation`. The table is **policy-as-data**: seeded manually from
   `feedback_subagent_model_effort_matching`; future: rebuilt from benchmarked episodic
   routing memory (the operator's original claude-tier task-benchmark concept, revived as a
   data artifact). Triage never assigns; the deterministic rule consumes annotations.
Bright line: the triage hook never reads or evaluates work products.

<!-- moved from active L638-L694; under: #### Milestones -->
- **[declined: ws58 2026-11-03 content-review: superseded — the machine delivery plane (coordinator daemon) was retired by the loop-owned fleet (operator 2026-08-15, Phase 3) and bus_supervisor stays DOWN by operator decision]** **M3 — coordinator-daemon, read-only advisory.** *BUILT ✅ 2026-07-27* —
  `scripts/coordination/session_bus_coordinator.py` (flock singleton, tick loop, heartbeat,
  epoch fencing) and `scripts/coordination/bus_supervisor.sh` (userspace watchdog, health =
  heartbeat mtime, SIGTERM-then-SIGKILL, exponential backoff, `loop|once|status`; no systemd).
  Emits non-binding advisory `saturation` / `would-assign` / `would-idle` / `would-skip` records
  to `advisory.jsonl`. C2 relay, ACK redelivery, and C8 durable boundary surfacing may also append
  prescribed transport/notification rows to daemon-owned `inbox/*`; C8 persists its comparison
  snapshot in `boundary_state.json`.
  Verified: **survives kill -9 via supervisor** (recovered in 1s, epoch 1→2, and advisory rows
  carry the epoch so a pre-restart generation is identifiable); eligibility honours priority order,
  lane-busy, ungranted `operator_gates`, and non-terminal `depends_on`;
  `authority: assign` is **refused** because M4 is not built — an unbuilt assign path must never
  be silently approximated by the advisory one.
  **M3 acceptance restatement — no autonomous decision at `authority: manual|advisory`.** The
  retired “exactly two files” count was only a proxy for this property and is no longer evidence:
  legitimate C2/C8 transport now writes inboxes. In either pre-M4 authority, every daemon mutation
  must be one of: (a) its heartbeat, advisory, or C8 comparison state; (b) a schema-valid,
  explicitly addressed outbox relay that preserves the sender-selected recipient, `kind`,
  `task_id`/`corr_id`, and payload verbatim (the daemon adds only its delivery envelope and
  `relayed_src`); (c) the fixed ACK-redelivery transform of a previously delivered, overdue
  `requires_ack` message; or (d) the fixed C8 transform of a recorded non-idle → `idle` heartbeat
  transition into the defined `task-boundary` status notice for `coordinator-agent`. These are
  mechanical derivations, not choices. The daemon must not select work or a work recipient, nor
  set or alter priority, lane, owner, lease, queue status, gating, or a token outcome; it must not
  write `queue.jsonl` or `tokens/token-queue.md`. Advisory records remain observations only.
  **Required evidence for M3 sign-off:** run manual and advisory ticks over fixtures containing an
  explicit relay, an overdue ACK, and an idle transition; account for every mutation; prove
  byte-equivalence of relay-controlled fields, provenance of every generated notice, and no
  queue/token or assignment-state mutation. **This criterion is falsified by** any manual/advisory
  tick that changes `queue.jsonl` or `tokens/token-queue.md`; creates `task-assign` or another
  assignment/lifecycle/priority/lease/gating decision; alters a relayed recipient, kind,
  task/correlation identity, or payload; emits a boundary notice without its prior non-idle → idle
  heartbeat transition (or fields not derived from that heartbeat); or redelivers without a prior,
  overdue `requires_ack` source. File count alone is deliberately non-evidence.
  Two bugs found by its own tests and fixed: `classify_load()` returns `state`, not `class`
  (reading the wrong key fail-safes to permanently-busy, so the daemon would never have advised
  anything), and the same task was being advised to every idle agent (harmless while advisory,
  a double-assignment once M4 has authority).
  **Remaining for M3 sign-off: would-assign matches actual human/agent choices over a working
  day, divergences explainable.** That needs elapsed time and cannot be compressed.
  - [x] **M3a — supervisor running.** ✅ 2026-07-27 — started by the operator's instruction;
    supervisor 2009016 holds the lock, daemon does not. Fixing a self-lockout was required first
    (see M3b).
  - [x] **M3b — supervisor could never start (fd-9 self-lockout).** ✅ 2026-07-27 —
    `exec 9>"$LOCK_FILE"` creates an inheritable descriptor, so the daemon inherited the
    supervisor's own flock and held it for life. Every `loop` logged "another supervisor holds the
    lock" while `status` showed none running. Fixed with `9>&-`; pinned by
    `scripts/coordination/tests/test_bus_supervisor.py` (5/5), which asserts the daemon holds ZERO
    fds on the lock.
  - [x] **M3c — the supervisor test killed the live daemon.** ✅ 2026-07-27 — it scoped
    `LOCK_FILE`/`EPYC_ROOT`/`BUS_ROOT` but the supervisor's `pgrep -f` pattern is global, so a
    stub with the same filename matched production. `DAEMON`/`DAEMON_PATTERN` are now overridable.
    *Isolation is only as strong as its weakest axis.*
  - **[declined: ws58 2026-11-03 content-review: superseded with M3 (daemon soak evidence has no consumer)]** **M3d — the queue must hold real work for the evidence to mean anything.** Seeded
    2026-07-27 (19 tasks); before that the advisory stream held 978 records and ZERO
    `would-assign`. Widen per-handoff with `seed_queue.py --list` as the soak proceeds.
  Rollback: stop the daemon; the bus returns to fully-functional M1 manual mode.

<!-- moved from active L695-L726; under: #### Milestones -->
- **[declined: ws58 2026-11-03 content-review: superseded — daemon assignment authority was never accepted and the delivery plane is retired (loop-owned fleet Phase 3)]** **M4 — assignment authority.** *CODE BUILT ✅ 2026-07-27, acceptance pending.*
  `apply_assignment()` in `session_bus_coordinator.py`, gated entirely on
  `coordinator_daemon.authority == "assign"`. M3's decision-property criterion—not a file
  count—proves that manual/advisory transport cannot become an assignment path, so flipping
  authority is the single switch and setting it back to `advisory` is the whole rollback.
  Implemented: real task-assign (queue row + inbox `task-assign` + lease from `leases.max_hold_s`);
  deterministic transcription of agent reports (ack→CLAIMED, status→RUNNING,
  task-complete→DONE_PASS/DONE_MARGINAL_OBS/FAILED, carrying `failure_reason`); token relay into
  `tokens/token-queue.md` with the pre-validated command verbatim, marking the task
  `HELD_OP_GATE`; and all three stall rungs (soft→`nudge`, hard/lease-expired→`STALE_REQUEUED`
  with owner cleared and attempt+1 plus a defect, give-up→`INFRA_BLOCKED` plus a token-queue alert
  that explicitly leaves the decision to the operator).
  **Ordering is deliberate:** transcribe → relay → stall ladder → assign. Transcribing first means
  decisions are made against current truth, not a stale queue; relaying before assigning means a
  newly-gated task is not assigned in the same tick; the ladder before assignment means a requeued
  task is immediately available.
  **Idempotent by construction, not by bookkeeping.** Transcription compares the latest report per
  task against the queue instead of tracking consumed messages — which would have needed
  daemon-owned cursors on files the daemon does not own. Repeated ticks provably append nothing.
  Also: a `token-request` lacking dry-run evidence is refused and raises a defect rather than being
  relayed, because presenting a command that fails is an agent defect by policy.
  Tests: `scripts/coordination/tests/test_session_bus_m4.py`, **31/31**.
  A documented test seam (`SESSION_BUS_LANE_SNAPSHOT_JSON`) makes lane state deterministic — real
  probing made the suite 66s and host-dependent, and a test whose result depends on whether a role
  happens to be serving is a test that will eventually lie (it already did once today, on the
  drop_caches guard). With the seam: 7s, plus five cases that could not be expressed before
  (lane-busy gating, `exclusive-contiguous` needing a quiet host, `replay_eligible` bypassing a
  busy lane).
  **Remaining for M4 sign-off:** the 48h zero-idle soak, one induced stall, an induced restart
  mid-assignment showing epoch fencing, and operator touching only token-queue checkboxes — plus
  M3's advisory-accuracy evidence, on which M4's go/no-go rests. The switch stays at `manual`
  until then. Rollback: `authority: advisory`.

<!-- moved from active L900-L1363; under: ##### C-series ownership + residuals after the 2026-07-29 gpu-lane re-task (filed at wrap-up) -->
- **[declined: ws58 2026-11-03 content-review: superseded — tmux send-keys/spawn nudging is replaced by SendMessage + flag-file hand-offs (OPERATING_CONSTRAINTS, Token-Efficiency rules)]** **M5 — flag-gated extensions** (each independent). *Send-keys/spawn BUILT ✅ 2026-07-27*
  after the operator granted `OP-SENDKEYS-CODEX` with `max_spawns_per_day: 3`:
  `scripts/coordination/tmux_adapter.py` (probe/nudge/spawn). Fail-closed; refuses to
  guess a pane; spawns only as a **window in `tmux.live_session`**, never its own session; creates
  all four bus files before the pane starts.
  Three defects its test suite found: an unverified target could send keys to the **wrong pane**
  (tmux resolves a miss to the current window with exit 0); the quiet-check was **fail-open**
  (`window_activity` only tracks output while attached); and `--dry-run` created files.
  - [x] **C6 — nudge submission verification.** ✅ 2026-07-28 — commit `8033f039`. Attempt 1
    (fail-open) let an unverified target send keys to the wrong pane; attempt 2 (quiet-check via
    `window_activity`) produced a false-negative on TUI overlays; attempt 3 (`codex-bus-tests`)
    replaced the row-window predicate with a **cursor-anchored** one — the composer is everything
    up to the terminal cursor, a pending message is one the composer *ends with*, matching is
    whitespace-insensitive (both TUIs soft-wrap inside the fragment), and the 240-char cap became
    a 4000-char policy ceiling on measured calibration (Claude blobs at ~805, Codex at 1001 and
    truncates blobs at 1024; 400-char chunks with a load-bearing 0.15s gap are verified to 12,000).
    Independently reviewed by `claude-gpu-lane`, which found attempt 3 had **reopened the
    fail-open through two narrower doors** and fixed both; 21 → 29 tests.
    - `text_absent` post-Enter was read as "submitted". An Enter consumed by a completion overlay
      rewrites or *extends* the typed text instead of submitting, leaving a pane that is
      byte-for-byte a success. Fixed twice over: success now requires the transcript **echo**
      positively (`text_echoed`), and messages containing `@` or starting with `/ ! #` are refused
      up front, because the extend case is undetectable from the pane afterwards. A leading `!` is
      Claude Code's bash mode — such a nudge would have *executed* in the target session.
    - A whitespace-only 60-char tail normalised to `""`, and `endswith("")` matched every pane, so
      the pre-Enter gate passed unconditionally and fired a bare Enter into the pane.
    - Also: post-Enter acceptance now needs 2 consecutive samples (a half-drawn repaint frame was
      believable on one); `send-keys` gained `--` (a chunk starting with `-` parsed as a flag); a
      mid-message chunk failure now reports how many chars it left pending in someone's composer.
    - **Testing rule this produced — a fixture must not hide the predicate under test.** The
      end-to-end fixture cleared the screen on submit (`\033[2J\033[H` after `read`). No real TUI
      does that — both echo the submitted message into the transcript — and it is precisely the
      echo that the post-Enter check must observe. A screen-clearing fixture therefore passes an
      implementation that cannot tell submission from a swallowed Enter: the test models away the
      one signal it exists to verify. When a fixture stands in for a real system, check what it
      *removes*, not just what it reproduces; anything the predicate reads is not optional detail.
  - [x] **C7 — roster-bound writer containment** ✅ 2026-07-28 — heartbeat/outbox appends require
    a roster id; rebuild and daemon audit ignore non-roster artifacts; validation warns without
    deleting them. `tests/test_session_bus.py` proves no task-shaped writer becomes an agent.
  - [x] **Bus protocol test suite** ✅ 2026-07-28 — first-ever automated coverage for the session
    bus (`tests/test_session_bus.py`); grew from 14 passed + 2 xfail to 27 passed, 0 xfail across
    the campaign below. Commit `69c65068`.
  - [x] **C1 — no inbound route for coordinator-agent.** ✅ 2026-07-28 — added
    `session_bus.py provision`. (Fixed by coordinator-agent, same campaign.)
  - [x] **C2 — daemon never relayed agent-authored outbox messages.** ✅ 2026-07-28 — added
    `relay_outbox_messages`, idempotent via `relayed_src`. (Fixed by coordinator-agent, same
    campaign.)
  - [x] **C3 — drain failed open on a missing inbox.** ✅ 2026-07-28 — drain now exits 2 on a
    missing inbox instead of silently succeeding. (Fixed by coordinator-agent, same campaign.)
  - [x] **C4 — ack redelivery and cursor-rewind enforcement.** ✅ 2026-07-28 — one durable tagged
    ack-deadline nudge per unacked `corr_id`, recipient-outbox ACK only; Rule 4 cursor rewind now
    refused (lower `--set` offsets rejected, equal/higher allowed). Commit `d6599a2b`; both prior
    xfails promoted to passing (16 passed).
  - [x] **C8 — durable task-boundary surfacing + endpoint-lint coverage.** ✅ 2026-07-28 —
    `detect_task_boundaries` in the coordinator-daemon delivers a task-boundary status message to
    coordinator-agent's inbox on any main's transition to idle, persisted in daemon-owned
    `boundary_state.json` so a daemon restart does not replay; plus a `validate` WARN for any
    roster row whose endpoint has no working delivery path, and a WARN for a missing
    `config.yaml`. Commits `496363c8`, `fa7ad915`, `7806b6a8` (durable surfacing, fixed by
    coordinator-agent). 27 passed, 0 xfail.
  - [x] **Guard self-idiom regression** ✅ 2026-07-28 — `agents_reference_guard.sh` now resolves
    bare nested session-bus references, and the compliant coordinator-agent role file is
    explicitly tested (a guard must not forbid its own idiom). Commit `667ed96f`, 3 passed.
  - **[declined: ws58 2026-11-03 content-review: superseded with M5]** **M5a — `--min-interval-s` default of 600s is the implementer's guess, not an operator
    decision.** Same class as the `max_spawns_per_day: 4` that the operator corrected to 3.
  - [x] **M5b — operator disposition for preserved roster orphans.** ✅ 2026-08-11 — `mainD`,
    commit `060efa27`, on `coordinator-agent`'s approval of a disposition package. **This row's own
    recommended action, carried out in its own order.** The two task-keyed outboxes were dealt with
    FIRST: their four messages — the E8-launch audit finding and three E8-R2 statuses including the
    sealed-vector scorer fix `c7f6c7fa` — were relayed to `coordinator-agent`
    (`msg-20260811T111438Z-193-mainD`) before anything moved, because they were never relayed and
    the archive would otherwise have been the only copy. Then all 24 files (2 outboxes + 22
    heartbeat snapshots) moved to `archive/non-roster-20260811/` with a provenance README.
    `validate`'s non-roster warning set: 24 → 0.
    **One deviation from the letter of the recommendation, stated rather than glossed:** it says a
    roster writer should "adopt the messages with original ids". That is not achievable — the msg
    `id` pattern encodes its writer, and one agent cannot author another's id without forging
    provenance. So the content was relayed with the original id CITED, and the originals kept
    readable in the archive. Same guarantee (nothing lost, content delivered), honest about
    authorship.
    *Original filing:* C7 prevents recurrence and
    keeps existing task-named heartbeat/outbox files out of roster-derived state, but does not
    delete or move evidence. **Audit 2026-07-29:** archive (never delete) the 22 task-keyed
    heartbeat snapshots after disposition; each is only `{agent,state,task_id,ts}` and carries no
    unique finding or attestation. Retain/re-home first the two task-keyed outboxes: their four
    messages are unique and unrelayed — one E8-launch audit finding and three E8-R2 statuses,
    including the sealed-vector scorer fix `c7f6c7fa`. Recommended action: a roster writer adopts
    the messages with original ids/payloads, then archives both outboxes with the heartbeats. Only
    the operator can authorize this disposition.
  - **[declined: ws58 2026-11-03 content-review: superseded — instruction refresh of running sessions is the Phase 5 nudge of the wrap-up division-of-labor plan (this file), not a coordinator-agent chore]** **M5c — standing instructions do not reach running sessions.** A CLAUDE.md rule added at
    21:43Z left an active agent on its 19:45Z heartbeat. Recorded in `BUS_PROTOCOL.md`; the open
    task is for coordinator-agent to nudge running mains to *re-read* on every such change.
  - [x] **C9 — `cmd_spawn` caps a daily action count, not live concurrency.** ✅ 2026-07-28 —
    `cmd_spawn` now counts LIVE roster-member windows in `tmux.live_session`; closing an idle main
    returns its slot immediately. `live_mains()` maps each roster row to the window that can carry
    it — its id, or the window component of a tmux endpoint where they differ (`codex` lives in
    `codex-inference`) — and intersects that with `tmux list-windows`; a window-INDEX endpoint
    (`tmux:agent:3`) contributes no name — an undercount, which **relaxes** the cap (see C14; this
    line originally said the opposite). **Fail-closed on an unreadable count:**
    tmux unreachable, the live session absent, or a roster with no ids all return `None`, never an
    empty set — "I could not count" is not "nothing is running", which is the exact shape of C3,
    C6 and C8. Spawning a main that is already live is also refused (one identity, one window).
    **Key decision, stated:** `caps.max_spawns_per_day` is **refused, not read as a fallback** —
    its `6` authorised six spawn ACTIONS in a day, and re-reading that as six SIMULTANEOUS mains
    would grant concurrency nobody approved, i.e. a fail-open. The old key alone now exits
    `EX_MISCONFIG` with the one-line config edit spelled out. `caps.max_concurrent_mains: 4` set
    by operator decision 2026-07-28 (one slot above the then-steady state of 3 live mains).
    The daily ledger count survives in `probe` as `spawns_today_history_only` and gates nothing.
    Tests: 10 new cases in `tests/test_tmux_adapter.py` (40 passed) including an end-to-end
    disposable-session proof that closing a window returns the slot, plus 4 new cases in the
    standalone suite, since renamed to `scripts/coordination/tests/test_tmux_adapter_live.py`
    (37/37 — but see C10: that run was flaky-green on one C9 check).
    *Found while doing it:* that standalone suite had been **red at HEAD** since the C6 change —
    it is not pytest-collected, so nobody re-ran it — and for the same reason the C6 review
    flagged: its nudge fixture cleared the screen on submit, deleting the transcript echo the
    post-Enter check must observe. Same fixture bug, second file. Fixed; see the C6 entry's
    testing rule. **Anyone touching this module: run BOTH suites.**
    <details><summary>Original filing (2026-07-28)</summary> `caps.max_spawns_per_day` is enforced by counting `kind == "spawn"` rows in
    `coordination/session-bus/adapter-ledger.jsonl` whose `ts` starts with today's date — a rate
    limit on the spawn action, not a bound on simultaneously-live mains. Killing or closing a main
    never returns its slot. Observed with three spawn rows for the day (`codex-bus-tests`
    15:34:25, `claude-gpu-lane` 16:04:42, `fable-auditor` 19:47:34) while only two mains were
    actually alive — `codex-bus-tests` had already been destroyed — yet further spawns were
    refused at 3/3 despite spare real capacity.
    A concurrency cap should bound the thing that actually costs something: simultaneous mains
    competing for compute, context, and coordinator attention. A daily action cap instead
    penalises churn, turns one operational mistake into a cost for the rest of the day, and —
    worst — makes closing an idle session cost a spawn slot for no reason, directly against the
    session-lifecycle rule in `agents/shared/OPERATING_CONSTRAINTS.md` ("nothing assignable →
    close the session"): a coordinator that correctly closes a finished main is punished for it.
    The operator's expectation was concurrency semantics; the config key name matches the
    implementation, so the key name is not the bug — the design is.
    Fix: count **live roster-member windows** (e.g. `tmux list-windows` against
    `tmux.live_session`, intersected with roster ids from `config.yaml`) instead of ledger rows.
    Rename the cap to reflect concurrency (e.g. `caps.max_concurrent_mains`) — decide and state
    explicitly whether the old key stays readable for one release or the module fails closed when
    only the old key is present; do not leave that ambiguous. Stay fail-closed: if the live-window
    count can't be determined (tmux unreachable, session absent), refuse rather than assume zero —
    this module's whole history (C3, C6, C8) is fail-open defects; do not add another. Needs tests
    in `tests/test_tmux_adapter.py`. `tmux_adapter.py` is grant-gated (`OP-SENDKEYS-CODEX`) and had
    three fix attempts on the unrelated C6 defect on 2026-07-28 alone, so this change wants an
    independent review before it lands, not a same-session self-merge.
    *Context, not part of the fix:* the operator raised the cap 3 → 6 in
    `coordination/session-bus/config.yaml` on 2026-07-28 as interim headroom. That bump is not the
    fix and does not close this item.
    </details>
  - [x] **C10 — the standalone adapter suite is not collected, so it rots unrun.** ✅ 2026-07-28.
    Renamed `scripts/coordination/tests/test_tmux_adapter.py` →
    **`test_tmux_adapter_live.py`** (`git mv`, history preserved) and made its entry points
    assert. It is now collected and green: `pytest tests/test_tmux_adapter.py
    scripts/coordination/tests/test_tmux_adapter_live.py` → **42 passed**.
    Two distinct defects, both worse than "not collected":
    - **The basename collided.** It shared `test_tmux_adapter.py` with `tests/`, and neither
      directory is a package, so pytest derived the module name `test_tmux_adapter` for both and
      raised `import file mismatch` — a collection ERROR that **interrupts the entire run**, not a
      skip. Any attempt to run both suites together aborted, so in practice only the `tests/` one
      was ever run, and this file sat RED at HEAD for a day after the C6 change.
    - **Collected would have been WORSE than uncollected.** `check()` only appended to a
      module-global list that `main()` inspected; `test_unit`/`test_live` returned `None`. Under
      pytest they would have reported **PASS with every check failing** — manufactured green
      evidence. Each entry point now asserts over the checks it recorded (sliced by start index,
      so `test_live` cannot inherit `test_unit`'s failures), and `_skip()` yields a real pytest
      skip when tmux is unreachable instead of a silent pass. Verified by injecting a failing
      check: the assertion fires.
    - **A third defect fell out: the spawn fixture was racy.** Real spawns used `command="true"`,
      which exits at once — measured, tmux reaps the window within ~0.3 s — so every check needing
      the spawned main to *be live* raced the reaper. The C9 duplicate-refusal check failed on the
      very next run after landing; **the "37/37" first quoted for C9 was flaky-green.** Fixture
      now spawns `sleep 300`. This is a fixture defect, not an adapter defect: a window whose
      command exited is genuinely not a live main, and the adapter counting it as dead is correct.
      3 consecutive clean runs after the fix.
    Anyone touching `tmux_adapter.py` still runs **both** suites — the header of each says so.
  - [x] **C16 — a bare repo-wide `pytest` cannot run, which is why C10 could hide.** ✅ 2026-07-28
    — `pytest.ini` + two package markers. Before: `pytest` from `/workspace` collected 2200 tests
    and **aborted with 46 collection errors**, so there was no whole-repo run for anything to be
    red in. After: **576 collected, 0 collection errors, 0.8 s**, and the run completes.
    - 45 of the 46 were `repos/` — the child repos reached by symlink, plus `*.bak-*` backups.
      They own their suites and their dependencies. `norecursedirs` excludes them from
      *recursion* only, so `pytest repos/epyc-orchestrator/tests` still works on purpose.
    - The 46th was `tests/compliance`, and the cause was not the obvious one. Its modules import
      themselves absolutely (`from tests.compliance.agent_file...`), which is required by the
      documented `python -m tests.compliance.agent_file.runner` CLI, so rewriting them to relative
      imports would have broken that CLI. But `tests/` had no `__init__.py`, and **a namespace
      package loses to a regular package anywhere on sys.path regardless of order** — so `tests`
      resolved to `/mnt/raid0/llm/epyc-orchestrator/tests/__init__.py`, reached through this venv.
      `pythonpath = .` alone does not fix that; `tests/__init__.py` +
      `tests/compliance/__init__.py` do. The documented CLI was broken by the same cause and now
      imports.
    - **Nothing is hidden.** No test is suppressed, deselected or xfailed. The 53 collected cases
      in the codex-owned E8 files (`test_e8_quality_baseline_v4_wrapper`,
      `test_e8_quality_source_protocol_amendment`, `test_ratify_pbench4_fg4b_*`) are collected and
      still fail — that is the intended outcome. **The goal was a run that is honestly red, not a
      green one.**
    - **First whole-repo run:** `5 failed, 571 passed, 2 warnings in 189.05s`. The five are exactly
      the pre-existing E8 reds; no new failure introduced, none hidden. Codex owns those; do not
      "fix" them from this lane.
  - [x] **C11 — C9 landed without the independent review its own filing required.** ✅ Paid
    2026-07-29 by `auditor` as part of the C24 review, commit `3d509613` — the two touch the same
    invariant, exactly as the row directed. Re-verified by `mainD` 2026-08-11 against current HEAD
    rather than taken from the earlier claim: the commit exists, carries 145 lines of test, and its
    review attacked C9's central claim — *can `live_mains()` return a set missing a genuinely live
    id?* — and found that **it can**, correcting a safety argument this module had stated wrongly
    twice. The debt is paid; this box was simply never flipped.
    *Original filing:* The C9 entry
    says the change "wants an independent review before it lands, not a same-session self-merge",
    and it was implemented and committed (`8cbe50c0`) by the same session that had just reviewed
    C6 — on direct operator instruction, which supersedes the handoff's own procedure, but the
    review debt is real and unpaid. A second pair of eyes on `live_mains` / `resolve_spawn_cap` /
    `cmd_spawn` is cheap now and expensive after something spawns wrongly. Not urgent: the change
    is fail-closed on every branch it cannot evaluate, and both suites are green.
  - [x] **C12 — the nudge fragment can collide with the transcript.** ✅ 2026-08-11 — `mainD`.
    Closed with an OCCURRENCE COUNT rather than the cursor offset the filing proposed: the capture
    is re-normalised and the pane can scroll between samples, so a byte offset does not survive a
    poll and a count does. The caller records how many times the fragment is on the pane before
    Enter; a genuine submission MOVES our copy from the composer into the transcript so the count
    holds, while an Enter eaten by a completion overlay DELETES it so the count drops and whatever
    remains is provably stale. An unreadable pane yields `None` = no anchor and keeps the pre-C12
    behaviour — the capture-failure path already refuses a moment later, and refusing twice for one
    cause turns a transient tmux hiccup into a nudge failure. 3 tests.
    *Original filing:* Post-Enter success is "the
    60-char tail is on the pane but not at the cursor". If an identical fragment is already in the
    scrollback (the same nudge sent earlier, or an agent echoing the text), an Enter that never
    submitted could still find it and read as success. The 600s rate limit makes a same-text
    repeat unlikely and the failure needs a *second* fault to matter, which is why it is filed
    rather than fixed. Closing it properly means anchoring the echo to a position *below* the
    pre-Enter cursor rather than anywhere on the pane.
  - [x] **C13 — nudge refuses `@` anywhere in the message, which is broader than the hazard.**
    ✅ 2026-08-11 — `mainD`. Narrowed to a token-initial `@` (start of message or after
    whitespace), which is the shape the picker actually binds to. `ops@example.com` and `a@b` now
    pass; `@file.py` and a bare `@` still refuse. **Narrowed, not relaxed** — the filing's own
    condition was "if it proves annoying in practice", and it did, on a message containing an email
    address. 6-case parametrised test covering both directions.
    *Original filing:*
    The trigger is a picker opening on an `@`-prefixed *token*; the guard refuses the character
    anywhere, so an email address or an `@`-mention in otherwise-fine prose is rejected. Chosen
    deliberately — a false refusal costs a rephrase, a false accept fires Enter into a picker —
    but if it proves annoying in practice, narrow it to `@` at a token start and keep the rest.
  - [x] **C14 — a roster row whose window is unmatchable is invisible to the concurrency count,
    and that INVENTS capacity.** ✅ 2026-07-28 — *Polarity corrected 2026-07-28 — this item, the
    `roster_window_names` docstring, and the `8033f039`/`8cbe50c0` commit messages all originally
    claimed the opposite ("an undercount in the direction that refuses spawns, never one that
    invents capacity"). It is backwards.* `cmd_spawn` refuses when `len(ids) >= cap`, so missing a
    live main makes `len(ids)` **smaller**, the comparison passes when it should not, and a slot
    that is actually occupied is handed out. It also weakens the `args.agent in ids` duplicate
    check, so the invisible main can be spawned twice. **Undercount = fail-open**, in the module
    whose entire defect history (C3, C6, C8, C9) is fail-opens — which is exactly how the next one
    gets built when the invariant is documented backwards.
    Three drift triggers, none live in `config.yaml` today (checked), which is why this is a
    documented residual rather than an open hole:
    (a) **an operator renames a window without updating the endpoint** — the real
    `codex` → `codex-inference` rename of 2026-07-28 stayed counted *only* because the endpoint was
    updated with it; (b) **window-INDEX endpoints** (`tmux:agent:3`) — an index is not a name;
    (c) **pane-suffixed components** (`tmux:agent:win.0`) — `.0` is a pane, so the string never
    equals a `#{window_name}`.
    **FIXED ✅ 2026-07-28.** `live_mains` now lists with
    `-F '#{window_index}\t#{window_name}'` and `parse_endpoint_window()` resolves all three shapes:
    an index against `#{window_index}`, a pane suffix by stripping `.<pane>` and resolving the
    remainder, and an endpoint with more `:` parts than `tmux:<session>[:<window>]` as an outright
    **refusal**. Four refusing branches, each tested:
    (i) an endpoint that cannot be READ refuses the whole count — *uninterpretable is not absent*,
    since skipping the row shrinks the count and frees an occupied slot;
    (ii) two roster rows claiming one window refuses (which main is live would be a guess);
    (iii) a `list-windows` row without the tab refuses rather than being read as an empty session;
    (iv) the pre-existing unreadable/absent-session branch is unchanged.
    **Kept usable:** a row that is interpretable but matches no live window is simply NOT LIVE —
    the normal state of a retired or closed main — and costs nothing. Only unreadable endpoints
    refuse.
    **Where there was a choice, it overcounts:** an id is counted live if a window carries its id
    OR its endpoint resolves, and the endpoint match applies even across sessions. Overcounting
    refuses a spawn that might have been allowed; undercounting grants one that must not be. Only
    the first is recoverable by asking again.
    **`pane_dead` is deliberately NOT consulted** (fable-auditor's caution): a dead pane still holds
    a window, and excluding those would shrink the count — flipping the error polarity back toward
    inventing capacity if the `pane_dead` read ever misreported. There is a test asserting
    `live_mains` contains no `pane_dead` filter, so a future "optimisation" trips it.
    Latent, not live: no roster row triggered any of these shapes, and the real config resolves to
    the same 4 mains before and after. 40 → 46 tests in `tests/test_tmux_adapter.py`; 48 across
    both suites.
  - [x] **C19 — the whole-repo test result depends on WHICH PATH you invoke it from.** ✅ CLOSED
    2026-07-29 by owner decision: **codex retains the literal canonical-root guard deliberately**,
    as a trust-boundary property — a production ratifier must not accept a second name for the
    production root. So this is intended strictness, not drift, and the resolution is procedural:
    quote the invocation path with any tally and prefer the canonical root (`pytest.ini` says so at
    the top). *Original measurement below for the record.* *Measured
    2026-07-29, and it is why two sessions reported different truths about the same commit.* Same
    tree, same commit, same interpreter:
    `cd /mnt/raid0/llm/epyc-root && pytest tests/test_ratify_pbench4_fg4b_*` → **28 passed**;
    `cd /workspace && …` → **3 failed, 25 passed**. `/workspace/.git` and
    `/mnt/raid0/llm/epyc-root/.git` are the same inode (96604699), so this is one tree reached two
    ways. The E8 ratifier scripts under `artifacts/operator/` compare the invocation path against
    the literal canonical root as a **trust-boundary guard** ("production ratifier must run from
    the canonical root"). *The guard is correct and must not be relaxed to make a test pass* — it
    is exactly the kind of check that should not accept a second name for the production root.
    Consequence for C16: a pass/fail tally from this repo is only comparable when the invocation
    path is quoted with it. `pytest.ini` now documents the canonical path at the top. Open question
    for the owner of those scripts (codex / measurement, NOT this lane): should the guard compare
    `realpath` so one physical tree gives one answer, or is binding to the literal path the
    intended strictness? Either answer is fine; the current silent divergence is not.
  - [x] **C17 — a live window that NO roster row claims is silently excluded from the count.**
    ✅ CLOSED 2026-07-29 by operator answer on the bus: the `claude` window is **operator-owned and
    out of scope**, and coordinator-covered mains are **always coordinator-spawned**, so an
    unattributed window can never be one. The exclusion is therefore correct, not a fail-open: the
    count is of coordinator-managed mains, and a window outside that set is not a slot the cap
    governs. No `tmux.non_main_windows` key is needed. *Original filing below for the record.*
    ~~Filed as a live fail-open:~~ *Found 2026-07-29 while auditing routed bus messages.* C14 closed the
    **row → window** direction (a roster row whose endpoint could not be read). This is the
    **window → row** direction, and it is live rather than latent: session `agent` holds a window
    named `claude` that no roster row claims (`claude-main` is RETIRED with a `monitor:file`
    endpoint and its historical window was `claude_A`). `live_mains` reports 4 —
    `claude-gpu-lane`, `codex`, `coordinator-agent`, `fable-auditor` — and `claude` is attributed
    to nobody. ~~**If that window is a main, the cap is really 5/4 and a slot has been
    invented**~~ — **RETRACTED 2026-07-29**: that framing is wrong. `max_concurrent_mains`
    governs COORDINATOR-SPAWNED mains, and an operator-owned session outside the roster is a
    different CATEGORY, not a shortfall — the count measures exactly what it should. The one
    genuine signal that survives is narrower and is C14's: a *roster* main whose window was
    renamed away from both its id and its endpoint, which WAS coordinator-spawned and does
    belong under the cap;
    the count resolves the ambiguity in the capacity-inventing direction, which is the one this
    module keeps getting wrong.
    Why it was not simply fixed with C14: an unattributed window is indistinguishable from a tool
    window, and `htop`/`btop`/`fish` are legitimately not mains — refusing on every unattributed
    window would make spawn refuse permanently. The principled fix needs config data that does not
    exist yet: an explicit `tmux.non_main_windows` allowlist, after which any window that is
    neither a roster main nor allowlisted refuses (or at minimum surfaces in `probe`). That is a
    new config key changing spawn behaviour, so it is an operator decision, not an implementer's.
    **Immediate question, independent of the fix:** is `claude` a main needing a roster row, or an
    operator shell? If it is a main, `config.yaml` is stale and the concurrency count is
    understating the fleet today.
  - [x] **C18 — a routed message to a dead session is dropped silently.** ✅ 2026-07-29 —
    detection landed (`528435fc` fan-out + defect advisories; liveness check in `e428bceb`,
    record `92348b68`), activated at daemon **epoch 9** (pid 1795713, 11:19:51Z). The data
    cleanup (a) remains as its own line below. *Original filing:*
    `msg-20260729T092520Z-15-claude-gpu-lane` routed to `[fable-auditor, codex-bus-tests]`;
    `fable-auditor` received it, `codex-bus-tests` no longer exists (no tmux window, heartbeat 16.4h
    stale) and its share vanished with no defect, no bounce, nothing. `append` validates that a
    `needs_routing_to` entry is a roster ID — but a roster row outlives the session, so ID validity
    is not reachability. Audit done here: of 16 outbox rows only 2 carry `needs_routing_to`, and
    `codex-bus-tests` was the only unreachable recipient among them — re-sent to
    `coordinator-agent` as `msg-20260729T100100Z-18-claude-gpu-lane`.
    **Half-closed by `528435fc`, and the remaining half is the case that actually bit.** The relay
    now fans out on `needs_routing_to` and raises a `defect` advisory for an unreachable recipient —
    but only when the id is *not a roster id* or its *role is `retired`*
    (`session_bus_coordinator.py:1288-1291`). `codex-bus-tests` is neither: it is still
    `role: main` in `config.yaml:25`, while its window is gone and its heartbeat is **16.7 h
    stale**. So the exact message that was dropped today would still be dropped silently.
    Two ways to finish it, and they are not exclusive:
    (a) **data** — set `codex-bus-tests` to `role: retired` (coordinator/operator call; the row must
    be kept, not deleted, since its cursors and history are keyed on the identity);
    (b) **code — DONE ✅ 2026-07-29.** `_looks_dead()` + `_live_window_names()` in
    `session_bus_coordinator.py`: reachability is now **observed**, not declared. A live window in
    `tmux.live_session` means alive and SUPPRESSES the warning (a healthy main's heartbeat goes
    stale mid-generation — observed 2026-07-27, so staleness alone would fire on healthy agents and
    train people to ignore it); otherwise a heartbeat silent past 4 h is the evidence. Polarity per
    fable-auditor's caution: **deliver-plus-warn, never refuse** — an inbox row is durable and a
    merely-offline agent drains it on return, so bouncing would convert transient offline into
    message loss. If tmux is unreadable the warning still fires (deduped per (msg, recipient)):
    a false warning costs one visible line, false silence costs the defect. A caller with no
    config never probes the real session, so unit tests cannot read whichever windows happen to be
    up. Four regression tests including the exact 2026-07-29 miss (rostered, non-retired, 17 h
    stale, no window → warned AND delivered). Suites: 48 passed.
    - [x] **ACTIVATION for (b)** ✅ 2026-07-29 — operator restarted the daemon to **epoch 9**
      (pid 1795713, started 11:19:51Z, after `e428bceb`), so the liveness warning is live, not
      inert. Two activation gaps in one day on the same file: **a merged fix and a running fix are
      different states**, and only the process owner can close the second.
    (a) data — still open: `codex-bus-tests` remains `role: main`. Now non-urgent, since (b)
    detects it regardless of whether anyone remembers to set the field.
    - [x] **SECOND HALF: the warning needed a reader too** ✅ 2026-07-29. After (b), a routed
      message to a dead agent was delivered-and-warned — but the warning was an `advisory.jsonl`
      row, and **advisory rows are delivered to no one**; `status` prints the last five on demand.
      So the defect had two layers: a message in an inbox nobody drains, and a notice about it in a
      ledger nobody reads. The notice now also goes to **coordinator-agent's inbox**, a channel
      drained at every task boundary, because coordinator-agent is the party that can retire the
      roster row or re-route the work. Delivery to the dead recipient is UNCHANGED — this adds a
      reader, it does not refuse, bounce or withhold (fable-auditor's polarity note, honoured).
      Idempotency is keyed on **the notice's own durable trace** (a matching row already in
      coordinator-agent's inbox), not on the advisory ledger: the ledger is written by the tick
      loop, so any direct caller — every unit test, and any future one — would have re-notified on
      every pass. Same rule the module applies to liveness: derive it from what the thing itself
      leaves behind. Two regression tests; 96 passed across the affected suites.
    - [x] **ACTIVATION for the second half: the daemon at epoch 9 predates it.** ✅ 2026-08-11 —
      closed by restart. The daemon is at **epoch 16** (pid 942753); the row was written against
      epoch 9, so every restart since carried it. Verified from the live heartbeat, not assumed.
      Its own words — *"third activation gap on this file in one day"* — are the reason **C42**
      exists: a merged fix and a running fix are different states, and this row had to wait for a
      human to notice. The supervisor now detects a daemon predating its own source, so this class
      of gap should not need a row again.
    *Precision + polarity note (fable-auditor, wrap-up 2026-07-29):* post-`528435fc` the rostered
    non-retired case is no longer *dropped* — it is durably DELIVERED to an inbox nothing drains
    (recoverable if the session revives; invisible to the sender either way). For (b), prefer
    deliver-plus-WARN-advisory (`delivered but heartbeat is Nh stale`) over refuse-on-staleness:
    refusal would bounce messages to a merely-offline agent that today drains them on return —
    converting transient offline into message loss, the opposite-polarity error.
    - [x] Relay fan-out + unreachable-recipient defect advisories landed (fable-auditor,
      `528435fc`): delivery to every `needs_routing_to` id IN ADDITION to `to`, per-recipient
      idempotent via `relayed_src`; unreachable = roster row gone OR role `retired`, defect
      advisory deduped once per (msg, recipient) against `advisory.jsonl`; `append` refuses
      retired targets at authoring; regression reproduces the exact 09:50Z miss. NOTE: the commit
      message and two in-code comments originally said "C16"; comments corrected to C18 at
      wrap-up — the pushed commit message is immutable, this line is the record. ✅ 2026-07-29
    - [x] ACTIVATION GAP CLOSED ✅ 2026-07-29 — the operator restarted the daemon (**epoch 8**,
      pid 1659843, started 10:06:18Z, i.e. after `528435fc` at 10:02Z) and verified fan-out live: a
      message addressed to `coordinator-agent` with `needs_routing_to` for `claude-gpu-lane` and
      `fable-auditor` reached both. Routed delivery no longer depends on the triage outbox-scan.
      *The lesson generalises and it applies to this very entry:* a merged fix is inert until the
      long-running process carrying it is restarted, so "landed" and "active" are two states, and
      the second one needs an owner. See the activation note on the code half below.
    - [x] Delete dead `roster_window_names()` in `tmux_adapter.py` ✅ 2026-07-29 — zero callers
      confirmed before deleting. **Its docstring carried the corrected polarity statement and the
      drift-trigger list**, so that text was re-homed onto `live_mains` (the function whose
      arithmetic the invariant is about) BEFORE the deletion — otherwise the cleanup would have
      deleted the correction that `8d865ea2` exists to preserve. 48 passed.
  - [x] **C21 — `check_pytest_safety.sh` matched `-n <num>` anywhere in a compound command.**
    ✅ 2026-07-29 — scoped to the invocation. The match is now segment- and quote-aware
    (`scripts/hooks/pytest_worker_scan.py`, called by the hook): quoted runs are blanked because
    their contents are data, the command is split on shell separators because a later pipeline
    stage is a different program, and **heredoc bodies are blanked too** — found when the guard
    blocked its own test fixture, which listed `-n auto` as example data. That is the third face
    of one bug: it was matching TEXT, not INVOCATIONS. Detection of `pytest` stays deliberately
    generous about position, so `xargs pytest -n 64` and `timeout 900 python -m pytest -n 32`
    are still caught; only the scope narrowed. Fails CLOSED — if python3 is missing or the
    scanner errors, it falls back to the original broad match and refuses rather than guessing.
    14 scanner cases + 18 tests in `tests/hooks/test_pytest_worker_scan.py`; end-to-end the real
    false positive now exits 0 and `pytest -n 40` still exits 2.
    *Original filing:*
    *Observed 2026-07-29.* A command combining pytest with `sed -n 340,360p` was blocked as
    "pytest -n 340 is too many workers" — the guard scans the whole command string rather than the
    pytest segment, so an unrelated `-n` in a later stage trips it. Harmless today (split the
    commands and it passes) and the guard errs toward refusing, which is the right direction for a
    memory-safety check on a 192-thread box — but it will keep surprising people. Scope the match
    to the pytest invocation.
  - **[declined: ws58 2026-11-03 content-review: superseded — tmux spawn is no longer the way mains are started (coordinator-agent skill cold start; SendMessage hand-offs)]** **C20 — after a reboot, `tmux_adapter.py spawn` cannot spawn ANYTHING until someone
    creates the `agent` tmux session by hand. THIS IS ON THE REBOOT CRITICAL PATH.** *Verified
    2026-07-29 by running `live_mains` against an absent session.* With no tmux server or no
    `agent` session, `live_mains` returns `None` ("cannot list windows of the live session"), so
    `cmd_spawn` refuses with `EX_BLOCKED` — correct fail-closed behaviour, and
    `tmux.allow_session_creation: false` means the adapter will **never** create the session
    itself (an operator requirement from 2026-07-27: every main is a WINDOW in the one live
    session, and this module never calls `new-session`).
    So the post-reboot sequence has a mandatory first step that nothing in the code will do for
    you: **`tmux new-session -d -s agent`** (plus restarting the coordinator-daemon, which is a
    process and does not survive either). Until then every spawn attempt refuses with a message
    about being unable to count live mains — which reads like a defect and is not one.
    Decide deliberately, do not paper over it: either the operator/coordinator creates the session
    as a documented reboot step (recommended — it keeps `allow_session_creation: false`, which is
    what stops a stray spawn from inventing its own session), or that flag is flipped with an
    explicit decision recorded. Do NOT "fix" this by making an unreadable tmux count as zero mains:
    that is the C14 polarity error and it hands out occupied slots.
  - [x] **C15 — `caps.max_concurrent_mains: 4` is saturated at 4/4. STILL 4, not 6** — checked ✅ 2026-10-29 (audit: coordination/session-bus/config.yaml:341 max_concurrent_mains now 7 (box was waiting on operator to name a number; was 4)) [no-belief: audit-reconciliation]
    2026-07-29, and the "already raised to 6" recollection is a **key conflation**, which is worth
    recording because it is the exact hazard C9 was about. The 3 → 6 bump (`9b6c4f13`) raised
    `max_spawns_per_day`, the DAILY-ACTION key, and C9 (`8cbe50c0`) **superseded** that key with
    `max_concurrent_mains: 4` — the value chosen by operator decision at the time, against a
    then-steady state of 3 live mains. `git log -L` on the line shows no later change; the working
    tree is clean; `probe` reads **4/4** (`claude-gpu-lane`, `codex`, `coordinator-agent`,
    `fable-auditor`). So the saturation is current, not stale.
    I did not set it to 6, deliberately: re-reading the old 6 as a concurrency figure is precisely
    what `resolve_spawn_cap()` refuses to do in code — six spawn ACTIONS per day is not six
    SIMULTANEOUS mains, and doing it by hand would grant capacity no decision covers. **Operator:
    say a number and it changes in one line.**
  Original list: Claude Stop/SessionStart drain hook
  (clone `*_context.sh`) · send-keys adapter behind `OP-SENDKEYS-CODEX` (OFF; rate-limited;
  idle-pane check) · hybrid triage (dead-agent drafts + routing annotations; budget-capped;
  `DRAFT-UNREVIEWED`) · headless workers via `claude_via_devc.sh` under caps. Accept: per
  feature as specced. Rollback: per-flag disable.

<!-- moved from active L1571-L1576; under: ##### C24–C31 — defects surfaced by the FIRST cold-start coordinator instantiation (2026-07-29) -->
  - **[declined: ws58 2026-11-03 content-review: superseded — relay daemon plane retired; the bus is drained at task boundaries by each agent (CLAUDE.md M1)]** **OPEN — align the schema with the relay contract so `append` refuses at AUTHORING time.**
    Failing at the author is the right place; today a schema-valid gate can be structurally
    unpresentable. **This is a CONTRACT change and is deliberately NOT made here** — it is a
    coordinator/operator call, and tightening it invalidates `mainA`'s existing row, which would
    have to be re-filed. Escalated on the bus with options. **Superseded in part by C34:** the
    schema already requires `validated`; what failed is that authoring never applied the schema.

<!-- moved from active L1689-L1724; under: ##### C24–C31 — defects surfaced by the FIRST cold-start coordinator instantiation (2026-07-29) -->
- **[declined: ws58 2026-11-03 content-review: superseded — backend-per-roster-row served the tmux spawn path, which is retired]** **C30 — the backend a main runs on is invisible to the bus, and spawn reports success for a
  window that died a second later.** Two halves of one gap — **(b) is DONE, (a) is still open:**
  (a) **The launch command is not roster data.** `cmd_spawn --command` defaults to
  `cd /workspace && claude` (`tmux_adapter.py:931`) and no roster row carries a launch command, so
  which backend an identity runs on lives only in the head of whoever types the spawn. That was
  tolerable while ids were named after their backend; it is **not** tolerable now, because the
  2026-07-29 rename made roster ids deliberately **model-agnostic** (`inference`, `mainA`, `mainB`,
  `auditor`) precisely so a main can move between backends — including onto a local model. The thing
  the rename made variable is the thing the bus does not record. It belongs in the roster row as
  data, next to `endpoint` and `lanes`.
  (b) **Spawn confirms `new-window` exit 0, not a surviving window.** A spawned `codex` pane died
  instantly and silently because the codex CLI presented an update prompt on start; the window
  vanished, `cmd_spawn` still reported success, and only a manual `tmux list-windows` revealed it.
  `cmd_spawn` returns on the `new-window` return code (`tmux_adapter.py:899-901`) — which reports
  that tmux accepted the request, not that anything is running in it. Verify the window still exists
  a few seconds after creation before reporting success. Note the polarity: a false success here is
  worse than a false failure, because the four bus files are already written and the identity now
  looks provisioned-and-live to everything downstream, including the C24 heartbeat reset.
  **✅ 2026-07-29 (b) only — `auditor`, commit `dfb775f7`.** `cmd_spawn` re-checks the window list
  after `SPAWN_SETTLE_S` (2s, module-level so tests drive it to 0), records `spawn-died`, returns
  EX_BLOCKED and writes NO `spawn` row, so the ledger never claims a live window that is not there.
  The message states that the four bus files are LEFT IN PLACE and a retry reuses them. One
  deliberate asymmetry, tested: an UNREADABLE window list does NOT manufacture a failure — elsewhere
  in this module an unreadable signal fails closed, but here the window and bus files already exist
  and a transient tmux hiccup must not send an operator to tear down a healthy session, so the check
  fires only on positive evidence of absence. Proven against REAL tmux (`true` is reaped in ~0.3s,
  well inside the settle window) — the only place it can be. 3 unit tests + 3 live checks.
  **Reusable finding: the shared C9 test harness was pinning a false pass.** Its fake tmux answered
  `list-windows` from a fixed string and never showed a window it had just created, so every spawn
  test would have read as "the window died instantly". It now reflects its own `new-window` calls.
  - **[declined: ws58 2026-11-03 content-review: superseded with C30]** **(a) STILL OPEN — the launch command belongs in the roster row as data.** `cmd_spawn
    --command` defaults to `claude` and no roster row carries a launch command, so
    which backend an identity runs on lives only in the head of whoever types the spawn. The
    2026-07-29 rename made roster ids deliberately model-agnostic precisely so a main can move
    between backends — **the thing the rename made variable is the thing the bus does not record.**
    This is a ROSTER SCHEMA change (a contract), so it is escalated rather than taken.

<!-- moved from active L1815-L1815; under: ##### C24–C31 — defects surfaced by the FIRST cold-start coordinator instantiation (2026-07-29) -->
  - **[declined: ws58 2026-11-03 content-review: superseded — a liveness source for the pane-based control surface, which the three-state liveness rule (SESSION_LIFECYCLE) replaced]** **OPEN — the Claude source is an operator/coordinator call.** Escalated: my subagent obtained part of its evidence by decompiling the shipped bundle, which the design doc §7 rules out as a basis. Recommended option is the vendor's documented `claude agents --json` (filtered to `kind == interactive` — it is currently emitting a stale 2026-07-23 background record) with per-pass caching for its ~2s cost. Until answered, Claude mains stay on the heartbeat chain and `probe` reports them as UNAVAILABLE rather than pretending coverage.

<!-- moved from active L1816-L1871; under: ##### C24–C31 — defects surfaced by the FIRST cold-start coordinator instantiation (2026-07-29) -->
- **[declined: ws58 2026-11-03 content-review: superseded — pane-signal liveness ranking; the canonical rule is three states, hardware wins, pane text never clears a main]** **C36 residual (superseded framing kept for history)** *Operator-approved
  Option B, 2026-07-29; assigned to `auditor`. Evidence base:
  [`docs/design/agent-session-control-surface.md`](../../docs/design/agent-session-control-surface.md),
  which ranks 14 candidate signals with measurements and disproves several plausible ones.*
  **The root defect:** the heartbeat is written BY the agent, so an agent that has stopped cannot say
  so — and `probe` refuses every nudge on `state == "working"`. That is the deadlock; C35
  (pane-quiescence override) mitigates the symptom, not the cause. A runtime-reported status has no
  such dependency: it is true even when the agent is wedged, because it is STATE, not a timestamp.
  Scope: `probe`/`cmd_nudge` decide from runtime; the heartbeat is demoted to a CORROBORATOR; when
  the two disagree **the runtime wins and `probe` says so in BOTH directions**, the way C35 reports
  its override even when it did not fire. Signals, in priority order: (1) Codex `thread.status` via
  `codex app-server` JSON-RPC (exact, runtime-reported); (2) the Codex rollout terminal record
  (`task_complete` / `turn_aborted`) — no server needed; (3) `claude agents --json` for Claude mains.
  **Note the direction of the NEW protection:** today a main whose heartbeat wrongly reads `idle`
  while it is mid-generation *will* be nudged. Runtime `active` blocks that — a hazard the current
  guard cannot see at all.
  Constraints carried from the dispatch: every other guard stands (pane exists, `pane_dead` false,
  quiet check, rate limit, auth flag, target resolution); fail closed on anything unreadable; an
  UNAVAILABLE runtime falls back to current behaviour, **never** to `idle`. **CPU delta is INVALID
  for Claude mains** — a main burned 17% CPU sitting at its prompt because its subagents run
  in-process. Option A (running Codex mains as `--remote` clients and injecting turns over JSON-RPC)
  is **not** approved; read-only status queries only.
  - [x] **Signal #2 (rollout terminal record) VERIFIED, with four corrections that change the
    implementation.** ✅ 2026-07-29 — `auditor`. The claim's substance holds and is *stronger* than
    the design doc states, but taking it verbatim would have produced a wrong implementation:
    1. **"64/64 correct on today's rollouts" conflates two claims.** 60 of 64 end terminal; the
       other 4 are live TUIs mid-turn — the signal correctly reporting *busy*. Defensible as
       classification accuracy, false as "64 ended terminal". **The corpus number is much better and
       the doc undersells itself: 400 random files from the full 4,233 → 385 `task_complete` +
       15 `turn_aborted` = 400/400.**
    2. **n is 7, not 64.** 57 of today's rollouts are *subagent* files; the population the signal
       serves — user sessions one might nudge — had n=7 today.
    3. **`thread_source == 'user'` is UNSAFE.** 8 corpus files (older `cli_version`) carry no such
       field at all and an equality test misclassifies them. Use `!= 'subagent'` or fail closed on
       absence.
    4. **THE LOAD-BEARING ONE — the parent holds FINISHED subagent fds open.** Measured 16:38Z on
       live pid 257808 (`mainD`): fd 39 → a subagent rollout reading `task_complete`, fd 45 → its
       own user rollout reading `custom_tool_call`. **Picking the wrong fd reports "idle" for an
       agent that is mid-tool-call, and that unsafe reading is available on a live pid right now.**
       The `thread_source` filter is not hygiene; it is the guard.
    Minor: a session's subagent files can sit in a date directory containing **no** parent user
    file (a 31-file group today), so resolve the parent through the fd, never by scanning a date
    dir; and only the musl `codex` binary holds rollout fds (`node` wrappers and
    `codex-code-mode-host` hold none).
    *Robustness, measured:* `tail -n 1` is size-independent (~10 ms; sub-ms in-process) and 1,800
    reads under live append gave **0** parse failures — but the longest record today is 192 KB, past
    any single-write atomicity guarantee, so a torn tail cannot be *proven* impossible. Retry once,
    then report unknown and fail closed. The property the signal rests on does hold:
    `task_complete` is a **stable resting tail**, only ever followed by `task_started` or
    `thread_settings_applied`, never by the frequent mid-turn `token_count`.
  - **[declined: ws58 2026-11-03 content-review: superseded with C36]** **BLOCKED-ON / dependency: C30(a).** C36 must branch on which backend a roster id runs, and
    C30(a) — still open — is exactly *"the backend a main runs on is invisible to the bus"*. The
    2026-07-29 model-agnostic rename made backend a runtime property that nothing records. Escalated
    with options; the default if unanswered is single-backend scope with an explicit fallback and
    `probe` stating which mains are uncovered, because a wrong backend guess makes C36 return a
    confident WRONG answer — strictly worse than the heartbeat it replaces.

<!-- moved from active L1908-L1919; under: ##### C24–C31 — defects surfaced by the FIRST cold-start coordinator instantiation (2026-07-29) -->
  - **[declined: ws58 2026-11-03 content-review: moot — the daemon is retired and bus_supervisor stays DOWN by operator decision]** **OPERATOR (still open, now a belt-and-braces item rather than the only line of defence) —
    nothing AUTOMATICALLY RESTARTS the daemon.**
    The report was correct-once-asked and pull-only, and **the supervisor was dead too**, so "the
    supervisor will catch it" is not an answer — nothing watched the watcher. `status` now takes
    `--exit-nonzero-if-unhealthy` (default exit stays 0, so no existing reader changes) precisely so
    a scheduler can act on it. **Recommendation:** the cron form already documented for the same
    problem one level up in
    [`handoff-index-and-backlog-graph.md`](coordination-and-churn-pipeline.md#track-handoff-index-and-backlog-graph) — `*/5 * * * *
    session_bus_coordinator.py status --exit-nonzero-if-unhealthy || bus_supervisor.sh once` —
    idempotent, self-exiting when a daemon is already running, no new daemon to supervise.
    Host-level change → operator's call. **Note this is the same unwatched-supervisor defect as the
    open `hub_supervisor.sh` item in that handoff; one decision should cover both.**

<!-- moved from active L1984-L1989; under: ##### C24–C31 — defects surfaced by the FIRST cold-start coordinator instantiation (2026-07-29) -->
  - **[declined: ws58 2026-11-03 content-review: moot — daemon retired]** **DEPLOY — the running daemon is executing the old code.** `pid 496387` started
    2026-08-11 08:48:00, before this landed, and Python loaded the module then. The fix is verified
    by direct invocation but **is not live until the daemon restarts**, which is the coordinator's
    call, not mine — process lifecycle is outside C-OWN's lane. Until then `token-queue.md` keeps
    presenting both gates with no notice. Flagged rather than assumed, because "committed but not
    live" is exactly what **C27** was.

<!-- moved from active L2511-L2516; under: ##### C44–C50 + the 2026-08-12 delivery-plane landings (filed at wrap-up by `coordinator-agent`) -->
  - **[declined: ws58 2026-11-03 content-review: superseded — routing intent is structural (corr_id + target) per the bus protocol; the relay daemon that mis-fired on predicates is retired]** **The fix is a POSITIVE marker, not a tightened negative.** Neither predicate can be repaired
    by exclusion: `action_required` over-fires and the kind-set under-fires, so a sender who needs the
    operator has no way to say so. Add an explicit sender-set field (the `needs_routing_to` /
    structural-intent idiom already in use), make the escalation key on **that alone**, and make an
    item claiming operator attention without it a schema warning — so the marker's absence is
    detectable rather than silent.

<!-- moved from active L2798-L2804; under: #### Delivery-plane repair — C51–C54 landed, four residuals (filed 2026-08-12 at wrap-up) -->
- **[declined: ws58 2026-11-03 content-review: superseded — Claude-pane clear/submit verbs served tmux nudging, replaced by SendMessage + flag files]** **DP-2** (HIGH): **`clear` and `submit` do not work on Claude panes.** The C54 verbs were
  calibrated against a disposable Codex session; against the five Claude mains neither verb takes
  effect. Same backend asymmetry C53 names — faint SGR 2 carries opposite senses on the two TUIs — and
  it means the remedy half of the detector is live for exactly one of the six roster members. Until
  this lands, a Claude pane holding pending input still needs a human at the keyboard, which is the
  condition C51–C54 were opened to remove. Calibrate on an expendable Claude pane and pin it with a
  fixture case; this seat must not send keys to a live main.

<!-- moved from active L2926-L2937; under: #### fleet_watch.sh — productionisation residuals (filed 2026-08-12) -->
- **[declined: ws58 2026-11-03 content-review: superseded — pane-composer heuristics cannot clear or condemn a main under the three-state liveness rule; calibrating them further is dead weight]** **FW-1** (MED): **the Codex EMPTY composer is excluded BY NAME, and that calibration can rot.**
  An empty Codex composer *renders text* — a greyed placeholder (`› Write tests for @filename`).
  Measured 2026-08-12, neither available discriminator separates it from real queued input: the
  placeholder carries the same dim SGR (`ESC[2m`) that Claude uses for genuinely queued text, and
  `cursor_x` is parked at column 2 on every live pane in BOTH the empty and the text-present case,
  so the cursor slice `tmux_adapter.py` relies on cannot separate them either. So `fleet_watch.sh`
  excludes the placeholder with a `PLACEHOLDER_RE` list. If a Codex release ships an unlisted
  placeholder, it reads as pending input and parks a PERMANENT false `STUCK-INPUT` on `inference` —
  the cry-wolf failure the persistence rule exists to prevent. Enumerating the set needs keystrokes
  into a live pane, which this seat must not do. Fix: get an authoritative empty-composer signal for
  Codex (the rollout/TUI state, not the rendered row), or enumerate the placeholder set from an
  expendable pane and pin it with a fixture.

<!-- moved from active L2938-L2951; under: #### fleet_watch.sh — productionisation residuals (filed 2026-08-12) -->
- **[declined: ws58 2026-11-03 content-review: superseded — same rule: pane text is never a liveness signal; the instrument is hardware (process/KFD/CPU), not the composer]** **FW-2** (MED): **five of the six mains have NO runtime liveness signal, so `IDLE-CANDIDATE`
  is a heuristic for them.** `runtime_liveness()` implements the rollout check for Codex only;
  measured across the live roster 2026-08-12, `inference` returns `active`, while `auditor`, `mainA`,
  `mainB`, `mainC` and `mainD` all return `None` with *"backend 'claude': no runtime signal
  implemented yet"*. For those five, `fleet_watch.sh` falls back to tmux's `window_activity` clock
  plus a busy-marker veto — which is why every idle report is a CANDIDATE and says
  *"may be compacting"*. This is the same gap as M5/C36's unwired signal #3
  (`claude agents --json`); landing it upgrades this detector from heuristic to authoritative for
  the whole fleet, and is the single highest-value change available to it.
  - **Annotation (2026-09-07):** the hook-sourced semantic channel added under **OBS-11** above is
    the cheapest available fix for exactly these five `claude`-backend mains — it is backend-agnostic
    and does not wait on `claude agents --json`. It must carry the same six-event set, and it must
    keep `unknown` unpromoted: a channel that reads *compacting* as *idle* would make `IDLE-CANDIDATE`
    confidently wrong rather than honestly heuristic. `intake-1325#record`.

<!-- moved from active L3042-L3059; under: #### Dedicated Auditor and Inference roles (operator-approved 2026-08-13) -->
- **[declined: ws58 2026-11-03 content-review: superseded — compute leases are the compute-calendar grant protocol (inference-backlog-scheduling skill, 2026-10); the dedicated-inference-role daemon deploy has no consumer]** **AIR-6 — deploy and canary live audit plus CPU lease enforcement.** `coordinator-agent`, as
  live daemon owner, deploys `d7b83ddf93776a56869aee7326c8770602262bc0`, replays the live bus,
  and preserves the exact audit and CPU lifecycle artifacts specified in **Current executor start
  here**. It may promote selected audits `shadow` → `required` and resource admission `observe` →
  `enforce` only after replay is idempotent, validation has no new authority/lifecycle defects,
  the audit is exactly-once with no direct source-main route, and the CPU lease traverses request →
  grant → `region-lock` activation → renew → drain → close-receipted release with zero overlap or
  orphan leases. Persistent-idle routing remains `route`; it is transport-only. **Failed live
  canary 2026-08-13:** the daemon assigned ordinary AP-ME-1 backlog work to `auditor` despite the
  role being `schedulable: false` and `accepts_work_types: [audit]`; Auditor declined it and
  coordinator-agent revoked the lease. The tracked guard in `compute_advice` would refuse that row,
  but the running process loaded the shared-main tree at `ff7a5e6f`, where `d7b83ddf9` is not an
  ancestor and the guard is absent. The daemon started at 19:48:03Z after that stale source was
  materialized at 19:47:22Z, so this is a deployment-source failure, not a stale-process inference.
  **Retry gate:** prove the exact running source includes `d7b83ddf9` (or a descendant with the
  equivalent guard), then mutation-canary an untyped ordinary `lane:none` row and require a refusal
  before any `shadow`/`observe` promotion. `compute_advice` has HIGH upstream reach across four
  assignment/coordinator flows; no audit-lane code patch or daemon reload was attempted.

<!-- moved from active L3060-L3064; under: #### Dedicated Auditor and Inference roles (operator-approved 2026-08-13) -->
- **[declined: ws58 2026-11-03 content-review: superseded — GPU grants go through the calendar's grant writers, not delegated bus leases]** **AIR-7 — enable delegated GPU leases only after a general physical-claim provider exists.**
  Select and configure one provider under `resource_claims.gpu`, add provider-qualified open/close
  receipt validation and contention tests, then canary a delegated GPU lease separately. Until all
  three land, `enabled: false` is the required fail-closed state; Inference may still run its own GPU
  work under the existing inference rules.

<!-- moved from active L3072-L3079; under: #### Dedicated Auditor and Inference roles (operator-approved 2026-08-13) -->
- **[declined: ws58 2026-11-03 content-review: superseded — compute-request/grant authority is the calendar grant protocol]** **AIR-9 — fail-close Rule-11 compute-dialogue authority, routing, and payload shape.** Enforce
  `compute-request` routing to `inference`; restrict `compute-grant` and `compute-deny` authorship to
  `inference` and correlate/address the requester; require non-empty grant `boundaries` and deny
  `next`; reject unknown compute payload keys while explicitly retaining intended generic payload
  fields. Add authoring and relay refusal tests for every wrong-role, wrong-target, missing-field,
  and unknown-key forgery. `validate_row` has CRITICAL upstream reach (six dependants across five
  coordinator/append/validation flows), so this needs the focused implementation and mutation
  battery rather than an audit-lane patch.

<!-- moved from active L3188-L3195; under: #### Lost-wake backstop and the wake spike (research-intake 2026-09-07) -->
- **[declined: ws58 2026-11-03 content-review: bus-internal optimization with no measured failure; lost wakes are covered by drain-at-boundary]** **WS-2 — Durable processed watermark.** A monotonic `seq` on bus rows plus a `processed_seq` in
  the **owner-write-only** `cursors/<agent>.json`, advanced **only** by a sequence-naming disposition
  — replacing the O(history) `routed_view` recomputation. **Unlike WS-1, this one creates a standing
  obligation**, so it carries a hard precondition, recorded here so it cannot be skipped: any
  persistent re-presentation must **first** carry C39's spent-receipt lookup and its *"annotate,
  never suppress"* polarity (`:1937-1946`), and must satisfy C49's ruling that *"an escalation that
  fires on a well-run night trains everyone to ignore it"* (`:2463`). The external precedent is safe
  only because its backstop is **one-shot and byte-capped**; ours would not be. `intake-1331#record`.

<!-- moved from active L3196-L3203; under: #### Lost-wake backstop and the wake spike (research-intake 2026-09-07) -->
- **[declined: ws58 2026-11-03 content-review: a design decision for the retired relay daemon's save ordering]** **WS-3 — RAISE AS AN EXPLICIT DECISION, not an implementation detail: store-before-deliver.**
  Store-before-deliver **inverts the deliberate house ordering** at
  `session_bus_coordinator.py:1626` (*"the save happens AFTER the relay pass, so a crash loses at
  most one tick of ledger updates, never a delivery"*) and the fail-safe cursor default at
  `session_bus.py:1790-1815`. Both of ours bias toward **duplicate delivery over loss**; so does the
  external migration path, so the biases **agree** — which is exactly why the flip could happen
  silently. It **must be argued, never silently flipped**. Decision gate on **WS-2**.
  `intake-1331#record`.

<!-- moved from active L6444-L6444; under: #### Newly executable bounded source proposal -->
- **[declined: ws58 2026-11-03 content-review: integrates controls into the retired daemon plane (session_bus_coordinator.py, headless_audit.py)]** **RTG52-D9-SOURCE — integrate reviewed target-selection and exact assignment-stdin source controls after the exact D9 acknowledgement.** Private tip `33df263031234d78272baafd096ef1dee5c946fb`, full six-file footprint: `headless_audit.py`, `session_bus_coordinator.py`, `worker_runner.py`, and coordination tests `test_fleet_gate.py`, `test_headless_audit.py`, `test_worker_runner.py`. Strict supported grammar abstains on ambiguity/negation; task text is sent as bounded exact UTF-8 JSON stdin without clipping. Fake captured-child cleanup is bounded and refuses unconfirmed exit. Native proof is VB-RTG52-D9-CONFORMANCE, not semantic/assignment correctness authority. Protected merge remains operator-gated by D9; no host activation or dispatch. Previously accepted hygiene ancestor is not new RTG52 work.

<!-- moved from active L7074-L7075; under: ##### Phase 5 — migrate standing policy as a protected package -->
- **[declined: ws58 2026-11-03 content-review: moot — the bus daemon is retired and bus_supervisor stays DOWN by operator decision]** Restart the session-bus daemon at its owner's boundary and prove process start time is newer
      than every changed runtime file.
