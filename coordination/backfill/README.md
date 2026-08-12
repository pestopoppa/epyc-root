# coordination/backfill/ — hardware-backfill queue

Owning code: [`scripts/coordination/hardware_backfill.py`](../../scripts/coordination/hardware_backfill.py)
(full design rationale lives in its module header — read that first).
Supervisor: [`scripts/coordination/backfill_supervisor.sh`](../../scripts/coordination/backfill_supervisor.sh)
(not started by this commit — starting it is the coordinator/operator's boundary).

## Why this exists

2026-08-11/12 overnight failure (history corrected 2026-08-12 per mainB's
pick-validity analysis): the daemon wrote 590 consecutive all-idle records
into `coordination/session-bus/advisory.jsonl` — a file nothing reads — each
claiming 19 tasks READY. That claim was a stale picker view (C50): 811
records resolve to nine distinct rows, four of six sampled picks closed for
fourteen days at emission. A 3h47m window carries no compute receipts at all
(unwitnessed, not measured-idle); receipted utilisation was ~8–9%. This
directory is the bounded, crash-safe mechanism that closes that gap: a queue
of small, `timeout`-bounded jobs that opportunistically claim CPU regions
through the SAME lock (`region-lock run`) the rest of the fleet uses, plus a
detector that watches whether this queue itself is empty while known READY
work exists — and says so on the session bus exactly once per occurrence,
never 590 times.

## Files in this directory

| File | Writer | Purpose |
|---|---|---|
| `queue.jsonl` | whoever enqueues a job (human, agent, script) | append-only list of backfill job specs (see schema below). Never edited in place — the runner never mutates it. |
| `done.jsonl` | `hardware_backfill.py` only | append-only: one row per completed OR refused job, with exit code / reason and timing. |
| `ready_hint.txt` | human/agent-maintained | a cheap pointer: non-empty content means "compute-gated READY work exists — see \<ref\>". Absent or empty means "no known READY work" — the detector stays silent either way until the queue is ALSO sustained-empty. |
| `inflight.json` | `hardware_backfill.py` only | crash-recovery bookkeeping: which job ids the CURRENT runner instance believes are running. Cleared (not trusted) by any fresh runner instance at startup — see `reconcile_orphans` in the runner. |
| `detector_state.json` | `hardware_backfill.py` only | persisted detector streak + last-emitted-finding signature, so a supervisor restart does not lose the streak or re-emit a finding that already went out. |
| `heartbeat.json` | `hardware_backfill.py` only | liveness for `backfill_supervisor.sh` — pid, timestamp, running-job count, queue depth. |
| `logs/<job-id>.log` | `hardware_backfill.py` only | stdout+stderr of each launched job, for post-hoc debugging. |

Only `queue.jsonl` and `ready_hint.txt` are meant to be hand- or agent-authored;
everything else is runner-owned output.

## Enqueueing a job

Append ONE JSON object per line to `queue.jsonl`:

```json
{"id": "backfill-2026-08-12-embed-recompute-1", "regions": ["q2"], "role": "backfill-embed-recompute", "cmd": ["python3", "scripts/some_bounded_job.py", "--shard", "3"], "max_runtime_s": 1800, "enqueued_by": "coordinator-agent", "ts": "2026-08-12T07:00:00Z"}
```

Required fields, ALL enforced by `validate_spec` in the runner — a spec
failing any of these is refused (written to `done.jsonl` with
`status: "refused"` and never retried, not silently dropped):

- `id` — non-empty string, unique.
- `regions` — non-empty list drawn from `{"q0", "q1", "q2", "q3"}` — CPU
  quarters ONLY, there is no GPU region.
- `role` — must match `backfill-<name>`. Never a real serving-role name:
  region-lock attribution must be unmistakably a backfill job.
- `cmd` — non-empty list of argv strings (no shell; runs directly).
- `max_runtime_s` — a number with `0 < max_runtime_s <= 3600`. **This is not
  a convenience default, it is the owner-pressure mitigation.** A queued
  backfill job admits ~50ms after its regions free (region-lock's own
  admission loop). This runner depends on the 2026-07-27 no-concurrent-
  inference amendment — the compute owner holds its region claim for the
  whole campaign, not per individual run — so the only gap a backfill job can
  ever slip into is one the owner voluntarily released between legs. Bounding
  every job's runtime means the worst-case wait THAT imposes on the owner
  reclaiming the region is exactly ONE bounded job, never unbounded and never
  a pile-up. A spec without this bound, or with an unreasonably large one, is
  refused outright.
- `enqueued_by` — attribution (who/what proposed the job).
- `ts` — when it was enqueued.

## What the runner guarantees

- At most `--max-concurrent` (default 2) jobs run at once; everything else
  waits in `queue.jsonl` until a slot frees.
- Every launch is `region-lock run --regions <r> --role <role> --timeout-s 0
  -- timeout <max_runtime_s> <cmd...>` — it NEVER claims a region itself,
  NEVER touches GPU (enforced by the region validation above), and NEVER
  preempts anything; it only waits its turn on the same lock every other
  caller uses.
- Crash-safe: on restart, any entries the runner finds in `inflight.json`
  belong to a previous instance (a fresh process has no live handles by
  construction) and are treated as orphaned — cleared, and their ids become
  eligible for dispatch again. This is safe because region-lock's own
  live-PID pruning already guarantees a dead runner's children free their
  regions.
- A graceful stop (SIGTERM/SIGINT) forwards SIGTERM to in-flight children —
  which region-lock's own child-signal-forwarding propagates down to the
  wrapped `timeout`+command, releasing the region lock on exit — before the
  runner exits.

## The detector

Runs inside the same loop (not a separate poller). Every
`--detector-interval-s` (default 300s) it checks: has `queue.jsonl` had zero
PENDING/in-flight jobs for `--detector-threshold` (default 3) consecutive
checks, AND does `ready_hint.txt` exist and carry non-empty content? If both,
it emits exactly ONE `kind: finding` message (via
`session_bus.py append --agent hardware-backfill --target outbox`,
`needs_routing_to: [coordinator-agent]`, `action_required: true`) naming the
hint content — then HOLDS. It will not emit again for the same unbroken
(empty-streak, hint-content) pair; a new finding requires either the queue
going non-empty again (a fresh episode) or the hint content changing. This is
the direct fix for the 590-unread-advisory-records failure: one row, routed
structurally, not a flood into a file nobody reads.

Every read is fail-closed: an unreadable `queue.jsonl`/`done.jsonl` leaves
depth UNKNOWN (dispatch and the detector streak are both skipped that check,
never inferred as empty); an unreadable `ready_hint.txt` skips emission that
check; a failed `session_bus append` is logged locally
(`logs/hardware_backfill.log` under the repo root) and retried on the next
check — the dedup signature is only advanced on a CONFIRMED successful send.

**Known gap, stated plainly:** as of this commit, `hardware-backfill` is NOT
a roster id in `coordination/session-bus/config.yaml`, so the real
`session_bus.py append --agent hardware-backfill ...` call fails closed
(`'hardware-backfill' is not a roster id`) every time it is attempted — this
was verified directly, not assumed. The runner handles that correctly (logs
locally, retries, never crashes, never fakes success), but the finding will
not actually reach `coordinator-agent`'s inbox until an agent with roster-
authority (coordinator-agent / operator) adds a roster row for it, per
`coordination/session-bus/config.yaml`'s own "Adding a main = 1 roster row +
4 files" convention. That is a bus-roster/governance decision, not something
this implementing task's scope covers — flagging it here so it is not
mistaken for silent, working delivery.

## Starting it

Not started by this commit (hard rule: implementation delivers code, not a
running process). To adopt:

```
nohup /workspace/scripts/coordination/backfill_supervisor.sh \
      > /workspace/logs/backfill_supervisor.out 2>&1 &
```

See the supervisor's own header for `status`/`once`/`loop` and its
restart/backoff shape (modelled on `bus_supervisor.sh`).
