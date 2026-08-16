# Loop-Owned Fleet — operator package, 2026-08-16

Everything below is work that is **built, tested, and deliberately stopped at a gate**.
None of it is blocked on more engineering. Each item names the gate, why the gate exists,
and the exact command.

The rule these all obey: a gate I built is not a gate I may sign. Where the implementation
hit a trust boundary or a self-repair control, it stopped and recorded rather than routing
around — which is the behaviour the whole plan exists to produce.

---

## 1. Doctrine collapse (P1-1 … P1-4, P1-6) — human-only write paths

**Gate:** `agents/shared/*.md`, `CLAUDE.md` and `agents/AGENT_INSTRUCTIONS.md` are hash-pinned
in `coordination/session-bus/human_only_paths.yaml`. The PreToolUse hook refused the edits.
That is invariants 4 and 10 working exactly as designed, not an obstacle.

**What is staged:** `INVARIANTS.md` (new, 35 lines, the 15 invariants verbatim),
`OPERATING_CONSTRAINTS.md` 261→298, `SESSION_LIFECYCLE.md` 105→127, `CLAUDE.md` 227→220,
`agents/coordinator-agent.md` 187→134.

The five must land together: `coordinator-agent.md` cites `INVARIANTS.md`, and both the
reference guard and `validate_agents_references.py` refuse a dangling reference.

```bash
bash tmp/p1-doctrine/apply_p1_doctrine_collapse.sh              # dry run, default
bash tmp/p1-doctrine/apply_p1_doctrine_collapse.sh --apply
```

Every target is sha256-pinned; the script ABORTS on drift, SKIPS if already applied, and was
mutation-tested in four directions. A post-apply simulation passes both agent validators.

**Five merges you should know about** — content that existed in only ONE copy and would have
been destroyed by a naive dedup: the subagent index-modification prohibition (nowhere else in
the corpus); "never tick another agent's checkbox" (absent from the canonical checkbox axiom);
the heartbeat refresh command and its vocabulary (canon forward-referenced CLAUDE.md); the
stale-heartbeat causal chain; and "read the heartbeat AND the outbox, never infer".

**One thing deliberately not done:** `coordinator-agent.md` came to 134 lines, not the ~50 the
plan asked for. Going further meant deleting contracts rather than citing them, which is the
failure the phase exists to prevent. Flagged rather than forced.

Also staged separately: `tmp/p1-5-agent-instructions.patch` (read-order item 6 still describes
the archived persona layer — stale text, no dangling link).

---

## 2. D9 loop-plane merge — pilot-02's regression test

**Gate:** D9 as you ratified it: merging anything under `scripts/coordination/**` requires
operator ack. `promote_lane.py` exited **5** and named the path.

A pool worker wrote a regression test for the FETCH_HEAD worktree bug (below). It is in
`pool/lane1`, not on main.

```bash
python3 scripts/coordination/promote_lane.py promote \
  --agent coordinator-agent --task-id pilot-02-fetchhead-worktree-regression-test \
  --lane-worktree /mnt/raid0/llm/worktrees/pool/lane1 \
  --range "$(git -C /mnt/raid0/llm/worktrees/pool/lane1 rev-parse HEAD)~1..$(git -C /mnt/raid0/llm/worktrees/pool/lane1 rev-parse HEAD)" \
  --operator-ack "<your ack>" --apply
```

I did not sign this. Bypassing a control I had just built, on my own authority, would have
taught the fleet exactly the wrong lesson.

---

## 3. Turn the alarm channel live — ONE line

**Why it matters now:** the channel is built, drill-tested and inert behind a `REPLACE-ME`
sentinel. Until it points somewhere real, every alarm records locally and logs
`skipped_not_live`. The gate metric "zero alarms on a well-run night" is **unfalsifiable**
while no alarm can arrive at all.

Edit `coordination/session-bus/alarm_config.yaml`:

```yaml
  url: https://ntfy.sh/epyc-fleet-<10-random-chars>-alarms
```

(An ntfy topic name IS its password — use random characters, or self-host, which needs no code
change.) Then:

```bash
python3 scripts/coordination/alarm_channel.py test        # must print DELIVERED
bash scripts/coordination/tests/alarm_drill.sh            # must print RESULT: PASS
```

---

## 4. Enable the worker pool — ONE flag

The pool is proven end-to-end (4 workers, 3 of 3 completed rows passed, salvage verified
byte-for-byte). It ships **disabled** because the roster row makes it *schedulable* while the
flag makes it *executable*, and a schedulable-but-not-executable pool is the 2026-08-14 shape
exactly: assign, nothing runs, lease expires, row dies.

In `coordination/session-bus/config.yaml`:

```yaml
worker_pool:
  enabled: true        # currently false
```

Recommended before flipping: item 3 above (so a wedged pool can reach you), and one more
supervised run with `--pilot-override` if you want to watch a pane yourself first.

---

## 5. P3-4 — the fleet-gate predicate swap (proposal, not applied)

`session_bus_coordinator.py` is untouched. The proposal is a patch that `git apply --check`
accepts cleanly:

- `tmp/p3-4-fleet-predicate.patch` (5 hunks)
- `tmp/p3-4-design.md` (237 lines, incl. a quiet-night walkthrough to zero alarms)

It replaces the transitional Phase-0 predicate with runner-liveness + "dispatchable work ∧
capacity free ∧ no spawn attempt in ~30 min", so that zero live workers — the NORMAL idle
state of an ephemeral pool — stops reading as an emergency. Per-recipient P0-2b stays.

Applying it needs your D9 ack (it is loop-plane), and it wants its `test_fleet_gate.py`
changes landed in the same commit (7 tests survive, 4 rewritten, 12 new).

---

## 6. One-line follow-ups, low risk, D9-gated

- `session_bus.py::_OCCUPANCY_MARKERS` still lists `IDLE-CANDIDATE`, and `BUS_PROTOCOL.md:274`
  still names it. Harmless — the marker simply never matches now, and `COMPUTE-IDLE` carries
  the line — but both want a one-word edit.
- `scripts/dashboard/hub_supervisor.sh` has the same two-state `if health_ok` defect that
  P0-4 fixed in `backfill_supervisor.sh`. Already recorded as OBS-2 with a live owner.

---

## What ran without a gate, for context

17 commits. Phase 0 complete; Phase 2 complete and piloted; Phase 3 complete except the P3-4
proposal above. `PN-1/2/3` deliberately NOT started — they are "pulled by need", and no
measured consumer exists yet. `P4-1` is a 7-day observation whose harness (`fleet_metrics.py`)
is built and running.

Current measured state: self-repair share **11.1%** (107/966 commits, D9's commit-path
definition, target <10%); queue **0 INFRA_BLOCKED** (was 14) and 27 READY; 12 dead-owner claims
released under reversible receipts; mainA–D retired as tombstones with receipts and archived
cursors.
