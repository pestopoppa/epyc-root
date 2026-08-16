# P3-4 — Swap the fleet-gate predicate for the ephemeral pool

**Handoff**: `handoffs/active/loop-owned-fleet-implementation.md` § Phase 3 / P3-4
**Plan of record**: `docs/design/loop-owned-fleet.html`
**Status**: staged as patches, awaiting the D9 ack that lets them land.
**Date**: 2026-08-16

---

## Deliverables in this directory

| File | Applies to | `git apply --check` |
|---|---|---|
| `p3-4-fleet-predicate.patch` | `scripts/coordination/session_bus_coordinator.py` | clean |
| `p3-4-tests.patch` | `scripts/coordination/tests/test_fleet_gate.py` | clean |
| `p3-4-config-comment.patch` | `coordination/session-bus/config.yaml` (comment only) | clean |

All three were verified together in one `git apply --check` run against the
current working tree. Verbatim:

```
$ git apply --check --verbose artifacts/operator/staged/p3-4-fleet-predicate.patch \
                              artifacts/operator/staged/p3-4-tests.patch \
                              artifacts/operator/staged/p3-4-config-comment.patch
Checking patch scripts/coordination/session_bus_coordinator.py...
Checking patch scripts/coordination/tests/test_fleet_gate.py...
Checking patch coordination/session-bus/config.yaml...
```

### Why patches and not commits — the D9 apply path

`scripts/hooks/check_d9_loop_plane.py` gates the loop plane at **commit** time:
`scripts/coordination/**` and `scripts/hooks/**` by prefix, plus
`coordination/session-bus/config.yaml`, `BUS_PROTOCOL.md`,
`session_bus.schema.json` and `compute_policy.yaml` by exact path. A commit
touching any of them is refused unless the message carries a `D9-ack:` line (or
the run exports `EPYC_D9_ACK`). Two of the three patches here are guarded —
the test patch is **exempt** (`/tests/`, `/test_`), deliberately, so that the
safe half of a change is never harder to land than the dangerous half.

That is why this arrives as patches: an agent may prepare the change, only the
operator may ack the merge. The intended apply path is **one commit**, because
landing the predicate without its tests leaves the suite red:

```bash
git apply artifacts/operator/staged/p3-4-fleet-predicate.patch \
          artifacts/operator/staged/p3-4-tests.patch \
          artifacts/operator/staged/p3-4-config-comment.patch

python3 -m pytest -q scripts/coordination/tests/test_fleet_gate.py    # expect 49 passed

git commit -m "P3-4: replace the fleet-existence halt with runner-liveness + starvation

<why>

D9-ack: <who authorised this, and why>" \
  -- scripts/coordination/session_bus_coordinator.py \
     scripts/coordination/tests/test_fleet_gate.py \
     coordination/session-bus/config.yaml
```

The pathspec-limited form is not optional in this tree: the shared clone means a
bare `git commit -a` sweeps whatever hunks other sessions have left uncommitted
in the same files.

---

## 1. What was there, and why it had to go

P0-2 shipped `_fleet_presence()` and wired it as the first statement of
`apply_assignment`:

> zero live roster mains ⇒ **halt assignment** + one critical `fleet-absent` alarm.

Its own comment declared it TRANSITIONAL and named P3-4 as the swap. The
reasoning was sound for the fleet it was written against: a "main" was a
persistent tmux session, and a session that is gone never comes back to read its
inbox, so zero live mains genuinely was an emergency.

Phase 2/3 changed what a main is. `workerpool` is an `exec:` endpoint — a
program the daemon runs fresh per assignment, holding no session, no window and
no heartbeat that can go stale. **Zero live workers is now the normal idle
state.** Left in place, `_fleet_presence` would have done two harmful things on
every quiet hour of every well-run night:

1. **halted assignment** — the fleet stops itself because nothing is running,
   which is circular and self-latching; and
2. **paged CRITICAL** — the alarm that fires when everything is fine.

The plan's own metric is *"Alarm fidelity: every drill alarm arrives; **zero**
alarms on well-run nights."* A predicate that cannot meet that metric trains the
operator to mute the channel, and a muted channel is precisely how 2026-08-14 ran
for eleven hours with every internal light blinking correctly.

### The protection did not live in the halt

Worth stating plainly, because it is the reason retiring the halt is safe. Rows
were destroyed on 08-14 by **assignment to dead recipients**, and the thing that
stops that is the per-recipient `dead_agents` filter (P0-2b) inside
`compute_advice` — the gate that reproduced and blocked the bug live on 08-16,
minutes after the ghost sweep. It is untouched by this change, still checked
before the busy test, and still mutation-guarded. The fleet-wide halt only ever
added an alarm on top of it. **This change retires the halt and re-points the
alarm; it removes no protection.**

---

## 2. What replaces it

Not "the same question, tuned" — two different questions, because "is anybody
home" no longer has an answer worth having about a mechanism that is *supposed*
to be absent most of the time.

### 2a. Runner liveness — three-valued

`_runner_liveness(config, roster, lane_state) -> functional | broken | unknown`

| Reading | When | Alarm |
|---|---|---|
| `unknown` | roster declares no `exec:` endpoint | none, ever |
| `unknown` | `worker_pool.enabled: false` (flagged `policy_disabled`) | none, ever |
| `broken` | the named runner program is missing/unreadable | `fleet-runner-broken`, critical |
| `broken` | the pool root is gone, or holds no `lane*` worktree | `fleet-runner-broken`, critical |
| `unknown` | the pool root exists but cannot be read | none, ever |
| `functional` | program present, pool enabled, lanes on disk | clears the key |

The order of those questions is the design. Each one moves a different failure
into a different bucket, and two distinctions carry most of the weight:

* **`enabled: false` is UNKNOWN, not BROKEN.** The pool ships disabled. It is an
  operator decision, not a fault, and paging critical because the operator
  switched the pool off is the well-run-night alarm wearing a different hat.
  `_exec_endpoint_ready` folds the policy switch and the missing program into
  one string, so it is called here with `config=None` — the policy branch is
  answered separately, above it, precisely to keep the two apart.
* **Missing ≠ unreadable.** A pool root that is absent is a deploy defect and
  determinate: no probe can be unsure whether a directory exists. A pool root
  that raises `OSError` is a blind instrument and reads UNKNOWN. This is the C14
  polarity rule that `_looks_dead` and `_live_window_names` already enforce,
  applied one level up.

### 2b. Starvation — the loop-is-inert condition

Evaluated **only** when the runner reads `functional`. Five conjuncts, each
load-bearing:

```
runner == functional          ∧
runner is IDLE                ∧   (no held lane lock, no in-flight row owned by an exec identity)
capacity is FREE              ∧   (a pool lane is takeable now)
dispatchable rows > 0         ∧   (_eligible ∧ dispatch_gate — NEVER raw READY)
no spawn attempt THIS tick
```

…held for **N consecutive ticks** (`worker_pool.starvation_ticks`, default 3).
Raised as `fleet-pool-starved`, **warning** — the pool being idle with work is a
throughput defect, not an outage.

**"Dispatchable" is a fold, and that is the whole ballgame.** `status == "READY"`
is not dispatchable work. A row `dispatch_gate` refuses — unscreened, or with no
occupancy estimate — *stays READY forever*; refusing it is what the gate does to
it, and nothing ever transitions it out. A starvation predicate reading raw
READY would therefore be TRUE every night from the moment the first ungated row
was seeded, with the loop behaving perfectly. So a row counts only if **both**
admission tests the write path applies would admit it — `_eligible` (status,
deps, operator gates, anchor resolution, lane, load, co-residency) **and**
`dispatch_gate` (`screened_by`, `expected_occupancy`) — and only if its lane is
one the pool can actually serve. A `gpu` row the pool may never take is not the
pool starving; it is a row for somebody else.

**"Runner is idle" is the conjunct that stops the back door.** `compute_advice`
skips an agent that already owns an `ASSIGNED`/`CLAIMED`/`RUNNING` row, and the
pool is a single identity (`workerpool`). So a healthy 40-minute worker means no
spawn attempt for 40 minutes. Without this conjunct, every successful long batch
would read as starvation — the nightly alarm re-entering through a side door.

**Consecutive condition-ticks, not ticks-since-last-spawn.** These differ in
exactly the case that matters. After a genuinely quiet night, "ticks since last
spawn" is in the thousands; the first row seeded at 06:00 would trip the alarm on
the tick it *arrived*, before the daemon had any chance to dispatch it. Counting
consecutive condition-ticks means the clock runs only while work is actually
sitting there un-dispatched. The two formulations agree on what P3-4 asked for:
N consecutive condition-ticks implies no spawn attempt in those N ticks, because
"no spawn this tick" is one of the conjuncts. (Mutation-tested: swapping the
counter for ticks-since-spawn fails
`test_a_quiet_night_followed_by_morning_work_does_not_page`.)

### 2c. UNKNOWN never alarms — on either branch

`_sync_alarm(bus_root, raised, key, want, ...)` takes a **three-valued** want:

* `True` → raise. Called on every tick the condition holds; `alarm_channel` is
  the authoritative deduper (it notifies only on inactive→active), so
  re-asserting is silent and self-heals if the two state files disagree.
* `False` → clear, but only on the true→false **edge**, tracked in the gate's own
  state. `clear_alarm` on an inactive key is already a silent no-op, so an
  unconditional clear would be correct *and* a subprocess spawned for nothing on
  every tick forever.
* `None` → **touch nothing.** Not a raise (paging on a blind instrument), and not
  a clear. Clearing a live critical alarm because the instrument went dark is
  strictly worse than the noise: it manufactures the belief that the fault is
  gone. So a runner that goes from `broken` to `unknown` (e.g. the operator
  disables the pool in response to the page) leaves `fleet-runner-broken`
  **active** until it reads `functional` again. That is intended.

### 2d. Retiring `fleet-absent`

`_retire_fleet_absent_alarm` clears the key **exactly once, ever**, guarded by a
durable marker in `fleet_gate_state.json`. This matters because the key can be
ACTIVE at the moment the predicate lands — the pool ships `enabled: false`, which
the old gate read as "no live main" — and the code that would have cleared it is
deleted in the same commit. A retired alarm that never clears is
indistinguishable from an ignored one. If the key was not active, the channel
notifies nobody and the call is invisible; that is the correct outcome, not a
reason to skip it.

### 2e. It reports; it does not halt

`fleet_health_pass` has no way to halt: it appends advisory rows and drives two
alarm keys. `evaluate_fleet_health` returns an explicit `halt_assignment: False`
field so a future edit that reintroduces a halt has to change a stated value
rather than slip past a comment. The health pass runs at the **end** of
`apply_assignment`, after the writes, and the ordering carries meaning — see §3.

---

## 3. The quiet-night walkthrough — to zero

The scenario the gate metric names: 22:00Z to 06:00Z, nobody at the console, the
pool enabled and healthy, both lanes free, no dispatchable work. 480 ticks.

**Per tick, the old predicate.** `_fleet_presence` folds `_looks_dead` over
roles `main` + `reviewer`. Live roster today: `inference` (tmux, window closed
overnight), `workerpool` (`exec:`, read via `_exec_endpoint_ready`, NOT READY
because the pool ships `enabled: false`), and five `retired`/`service` rows that
are not candidates. Result: **zero live mains** ⇒ `present: False` ⇒ **assignment
halted for the whole night** and one critical `fleet-absent` page at 22:01Z. One
alarm — but the wrong one, unactionable, and self-latching: the halt guarantees
the condition it alarms on persists until a human intervenes.

**Per tick, the new predicate.** Trace the tick:

| Step | Reading | Effect |
|---|---|---|
| tick counter | `tick = n` in `fleet_gate_state.json` | bookkeeping only |
| `fleet-absent` retirement | marker already set (tick 1 of the daemon's life) | no-op, no subprocess |
| `_pool_lane_state` | root exists, 4 lanes, 0 locks held | `state: free`, `live: 0` |
| `_runner_liveness` | exec row present; pool enabled; `worker_runner.py` readable; lanes present | **`functional`** |
| `_dispatchable_for_runner` | queue holds only DONE/terminal rows and rows a gate refuses | **0** |
| `runner idle` | no lane lock, no in-flight row owned by `workerpool` | True |
| `capacity_free` | `state == free` | True |
| starvation conjunction | `dispatchable > 0` is **False** | condition False |
| `starvation_ticks` | resets to **0** every tick | never reaches N |
| `want_broken` | runner is `functional` → `False` | clear-on-edge only |
| `_sync_alarm(fleet-runner-broken, False)` | `raised` dict is **empty** | **returns immediately — no subprocess, no notification** |
| `want_starved` | runner is `functional`, `starved` is False → `False` | clear-on-edge only |
| `_sync_alarm(fleet-pool-starved, False)` | `raised` dict is **empty** | **returns immediately** |
| advisory | one compact `kind: fleet-health` row | local record only; `advisory.jsonl` is delivered to no one by design |

**Total over 480 ticks: 0 raises, 0 clears, 0 invocations of `alarm_channel.py`,
and assignment never halted.** The `raised` map is the mechanism: on a healthy
night `want` is `False` and the map is empty, so the clear branch is a
dictionary lookup that returns an empty list. Zero is reached not by suppression
but because there is nothing to suppress.

Two adjacent quiet scenarios, because "quiet" has more than one shape:

* **Quiet night → morning work.** 480 silent ticks, then a fully-gated row is
  seeded. Tick 481: dispatchable = 1, capacity free, runner idle,
  `starvation_ticks` = **1**, threshold 3 ⇒ silent. The daemon dispatches it on
  that same tick, so by the end-of-tick evaluation it is no longer dispatchable
  and the counter resets to 0. Never a page. (This is the case that a
  ticks-since-last-spawn formulation gets wrong, and the case the end-of-tick
  placement gets right: evaluated at the *top* of the tick, the single row
  `inference` is about to take would read as work the pool is starving on.)
* **Busy healthy night.** One worker running a 40-minute batch, one lane held,
  three free, 18 rows queued behind it. `runner idle` is False ⇒ condition
  False ⇒ silent. 120 ticks, zero alarms.

All three are tests, not assertions:
`QuietNightTests.test_quiet_healthy_night_touches_no_alarm_at_all`,
`test_a_quiet_night_followed_by_morning_work_does_not_page`,
`test_a_healthy_working_pool_is_silent`.

### What still pages, and it is what should

* Runner program deleted, or the pool worktrees vanished ⇒ `fleet-runner-broken`,
  critical, once. Assignment does **not** halt: rows queue and stay visible
  rather than burning, which is what P0-2 was protecting and what P0-2b actually
  delivers.
* Work + free capacity + an idle functional runner + no spawn, three ticks
  running ⇒ `fleet-pool-starved`, warning, once. That is the pick loop failing to
  reach the runner — a real, silent, previously-undetectable inertness.

---

## 4. Verification performed

* `git apply --check` on all three patches, individually and together — clean
  (output in §Deliverables).
* `pytest -q scripts/coordination/tests/test_fleet_gate.py` → **49 passed,
  7 subtests passed** (run against a mirror tree with the patch applied).
* `ruff check` clean on both patched files (baseline: the unpatched coordinator
  has one pre-existing `F841`, untouched).
* Neighbouring suites, patched vs unpatched, same environment:
  `test_advisory_archive` 14 passed · `test_scheduling_recommendation` 34 passed ·
  `test_worker_runner` 61 passed · `test_bus_root_resolution` 8 passed ·
  `test_session_bus_m4` **identical failure set before and after** (13
  pre-existing failures in this sandbox, byte-identical lists — no regression).
* **Mutation-tested, six mutations, all caught** — because a check that cannot
  fail is not a check:

  | Mutation | Caught by |
  |---|---|
  | fold replaced by raw `status == "READY"` | `test_unscreened_ready_row_is_not_dispatchable` (+5 more) |
  | drop the `runner idle` conjunct | `test_a_live_worker_is_not_a_starving_pool` (+2) |
  | UNKNOWN clears the alarm instead of no-op | `test_unknown_neither_raises_nor_clears_an_active_alarm` |
  | retirement clear runs every tick | `test_fleet_absent_is_cleared_exactly_once_ever` (+1) |
  | count ticks-since-spawn, not condition-ticks | `test_a_quiet_night_followed_by_morning_work_does_not_page` |
  | drop the pool-lane filter on dispatchable rows | `test_row_on_a_lane_the_pool_cannot_take_is_not_dispatchable` |

---

## 5. Test changes — enumeration

`scripts/coordination/tests/test_fleet_gate.py` goes from **9 tests to 49**.

### Survive verbatim — 4

The `_looks_dead` calibration is the one predicate both gates fold over; if it
drifts, everything drifts. And the P0-2b guard is the permanent half.

1. `LooksDeadContractTests.test_live_window_beats_stale_heartbeat`
2. `LooksDeadContractTests.test_no_window_and_stale_heartbeat_is_dead`
3. `LooksDeadContractTests.test_fresh_heartbeat_without_window_is_alive`
4. `MutationGuardTests.test_dead_agent_filter_is_present_in_the_pick_loop`

### Rewritten — 1

5. `MutationGuardTests.test_fleet_gate_runs_before_any_write` →
   **`test_the_fleet_gate_no_longer_halts_assignment`**. The old test pinned the
   gate as a pre-write guard. The new gate is not a guard at all, so the
   assertion inverts: no `def _fleet_presence`, no call to it, no
   `"assignment-halted"` kind in `apply_assignment`. (The bare name survives in
   exactly one place — the historical note explaining what was retired — which
   is why the assertion is on the definition and the call, not the string.)

### Deleted — 4

The whole `FleetPresenceTests` class. It tested a predicate that no longer
exists; its two genuinely portable lessons (UNKNOWN must not halt; an empty
roster is not an emergency) are re-expressed against the new predicate as
`test_unreadable_pool_root_is_unknown_not_broken` and
`test_no_exec_endpoint_declared_is_unknown_not_broken`.

6. `test_absent_fleet_is_detected`
7. `test_unreadable_tmux_never_halts`
8. `test_fresh_heartbeat_alone_keeps_fleet_present`
9. `test_no_mains_in_roster_is_not_an_emergency`

### New — 44

**`RunnerLivenessTests` (9)** — the three-valued mechanism read.
`test_healthy_pool_reads_functional` ·
`test_no_exec_endpoint_declared_is_unknown_not_broken` ·
`test_pool_disabled_by_policy_is_unknown_not_broken` ·
`test_missing_runner_program_is_broken` · `test_missing_pool_root_is_broken` ·
`test_pool_root_with_no_lanes_is_broken` ·
`test_unreadable_pool_root_is_unknown_not_broken` (skipped as root) ·
`test_lane_state_probe_and_free_pool_lane_agree` ·
`test_concurrency_cap_closes_capacity_even_with_a_free_lane`

**`DispatchableFoldTests` (7)** — the fold, one refusal class per test.
`test_a_fully_gated_ready_row_is_dispatchable` ·
`test_unscreened_ready_row_is_not_dispatchable` (**the nightly-alarm test**) ·
`test_row_without_occupancy_estimate_is_not_dispatchable` ·
`test_row_on_a_lane_the_pool_cannot_take_is_not_dispatchable` ·
`test_non_assignable_status_is_not_dispatchable` (4 subtests) ·
`test_stale_requeued_is_dispatchable` ·
`test_ungranted_operator_gate_is_not_dispatchable`

**`StarvationTests` (11)** — one conjunct per test, plus the persistence rule.
`test_work_capacity_and_an_idle_runner_starve_after_n_ticks` ·
`test_a_single_condition_tick_never_starves` ·
`test_no_dispatchable_work_never_starves` ·
`test_a_live_worker_is_not_a_starving_pool` ·
`test_a_held_lane_lock_is_not_a_starving_pool` ·
`test_full_capacity_never_starves` ·
`test_a_spawn_attempt_this_tick_resets_the_counter` ·
`test_starvation_is_not_evaluated_when_the_runner_is_unknown` ·
`test_starvation_is_not_evaluated_when_the_runner_is_broken` ·
`test_the_threshold_is_data` · `test_the_verdict_never_halts_assignment`
(3 subtests)

**`QuietNightTests` (3)** — the gate metric, executable.
`test_quiet_healthy_night_touches_no_alarm_at_all` (480 ticks) ·
`test_a_quiet_night_followed_by_morning_work_does_not_page` ·
`test_a_healthy_working_pool_is_silent`

**`AlarmTransitionTests` (7)** — emit once on state change, both directions.
`test_broken_runner_raises_critical_once` ·
`test_recovery_clears_the_broken_alarm_exactly_once` ·
`test_unknown_neither_raises_nor_clears_an_active_alarm` ·
`test_starvation_raises_a_warning_not_a_critical` ·
`test_starvation_clears_when_the_work_is_taken` ·
`test_a_broken_runner_does_not_also_report_starvation` ·
`test_health_row_is_emitted_every_tick`

**`RetiredFleetAbsentAlarmTests` (2)** —
`test_fleet_absent_is_cleared_exactly_once_ever` ·
`test_the_retirement_marker_is_durable`

**`GateStateTests` (2)** —
`test_an_unreadable_state_file_reads_as_empty_and_silent` (a gate that cannot
remember must go quiet, not page) ·
`test_the_tick_counter_is_not_the_epoch` (`epoch` counts daemon *generations*;
reading it as ticks would make "no spawn in 3 ticks" true forever on a daemon
that never restarts)

**`MutationGuardTests`, new members (4)** —
`test_the_fleet_gate_no_longer_halts_assignment` (listed above as the rewrite) ·
`test_the_health_pass_runs_after_the_assignment_writes` ·
`test_a_spawn_attempt_is_marked_before_the_lane_check` ·
`test_unknown_is_a_no_touch_branch`

### One fixture change worth flagging

The old suite wrote into `scripts/coordination/tests/_tmp_fleetgate/` — a fixed
directory inside a **tracked** tree — and left it behind. The new `_GateFixture`
uses `tempfile.mkdtemp()` and `shutil.rmtree`s it in `tearDown`. Untracked
litter in a tracked directory is what turns a parallel session's
`git clean -ffdx` from a no-op into an event; this session's own first attempt
at P3-4 was destroyed exactly that way.

---

## 6. Surfaced, not fixed — one finding for the operator

While tracing the starvation conjunction: **the pool serializes at one row at a
time, regardless of `max_concurrent_workers`.** `compute_advice` skips any agent
already owning an `ASSIGNED`/`CLAIMED`/`RUNNING` row, and the whole pool is a
single roster identity (`workerpool`). So with four free lanes and twenty
dispatchable rows, the daemon still assigns exactly one row per tick and then
skips the pool until that row completes. D1's concurrency-≤4 and the four
pre-created lanes therefore cannot be reached through the automatic path as
written. (The 08-16 pilot's "three concurrent" is consistent with P2-6 static
batching — up to 3 rows inside one invocation — rather than with three
independent assignments.)

This is deliberately **not** alarmed. It is true continuously, so alarming on it
would produce a warning that is permanently on — the exact failure P3-4 exists
to end. It is visible in the data instead: every tick's `fleet-health` advisory
row carries `capacity_free`, `runner_idle`, `in_flight` and `dispatchable`, so
"three lanes idle, eighteen rows queued" is readable off the record without a
page. Fixing it is a dispatch-concurrency change (per-lane identities, or a
per-agent concurrency budget), out of scope for this predicate and worth its own
row.
