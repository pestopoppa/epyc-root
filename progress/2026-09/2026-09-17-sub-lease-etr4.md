# 2026-09-17 — sub lease-etr4: D-f session lease + ETR-4 test

Zero inference, zero process management. `epyc-orchestrator` work landed on origin/main.

## D-f — cross-process session lease with fencing (repl-session-memory-maturity.md)

- **Why a mutex was not enough**: uvicorn runs 6 API worker processes. Two `/chat` requests for one
  `session_id` on different workers both restored the same checkpoint, and the later save erased the
  earlier turn. A `threading.Lock` cannot see the other process.
- **Commit**: `epyc-orchestrator` `0d6d1dd2`.
- **Design**: a `session_leases` table in the existing session SQLite DB. Each row holds the holder,
  host, boot id, PID, `/proc` start ticks, a monotonic per-session fencing token, and heartbeat/expiry
  timestamps. The row is never deleted.
  - Acquire runs under `BEGIN IMMEDIATE`, so exactly one of several simultaneous acquirers wins.
  - Someone else can take over a live lease only after it expires, or when the owner is proven dead:
    its PID is gone, its PID now belongs to another process, or the host has rebooted. An owner on
    another host can only expire.
  - Heartbeat is strict: an expired lease cannot be renewed.
  - Release is idempotent and never frees a successor's lease.
  - Session-row, checkpoint and delete writes check the token inside their own transaction. While a
    lease is live, a write without a token is refused.
  - `_execute_repl` holds the lease for the whole turn and passes the token with its checkpoint save.
  - The sessions API returns 409 when a write is refused.
- **Tests**: `tests/unit/test_session_lease.py` has 15 tests, and `test_repl_executor.py` adds 2
  executor cases. The multi-process cases run in real forked processes:
  - 6 simultaneous acquirers: exactly 1 winner.
  - 6 processes × 8 leased read-modify-writes: 48 of 48 updates kept.
  - Owner crash: another process reclaims the lease immediately.
  - Delayed stale writer: its write is refused, and neither half of the checkpoint lands.
  - **Negative control**: without the lease, the same 6-process workload kept only **8 of 48**
    updates.
- **Follow-ups filed**:
  - D-f1: verify under the live 6-worker API.
  - D-f2: decide whether to fence findings, documents and tags.
  - D-f3: a pre-existing defect. The graph snapshot writers call `save_checkpoint` with a signature it
    never had, and the `TypeError` is swallowed at debug level, so those snapshots are silently
    dropped.

## ETR-4 — rubric_threshold_source guard (eval-tower-loop-robustness-audit-2026-07-20.md)

- **Re-verification**: the `getattr` guard had already landed in `4055dba0` (NIB2-69, 2026-09-15), but
  no test covered it.
- **Commit**: `1097a392` adds 4 tests in `tests/unit/test_etr4_rubric_threshold_source_guard.py`.
  - Behavior: a duck-typed row without the attribute is compacted without error; a row that has the
    attribute is still serialized.
  - Structure: an AST check forbids any bare `r.rubric_threshold_source` read. It flags both reads in
    the pre-fix source.

## Verification

- 133 focused tests passed after the rebase. The set covered the session lease, the ETR-4 guard, the
  REPL executor, the SQLite store, the session protocol, the persister and infra-failed disposition.
- `ruff` is clean on the changed files.

## Belief kernel

This work produced no measurements or verified findings, so there is no source to wire into the
belief kernel.
