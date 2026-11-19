# Real-lane smoke (replaces the T1 fixture preflight, 2026-10-28)

The T1 same-entry preflight stopped *before* the first model load, server start or write, so it
never met the real path: 60 of 88 failed rows on 10-26..28 had a PF/T1 pass, and 27 % of inference
rows died at entry. A row is ready only when the real path ran, briefly, on the real shape.

Since the 2026-11-01 "one allocator" ruling the smoke is run by the publish flow: the owner
publishes with `scripts/coordination/rowflow/publish_row.py`, which writes the `epyc.row.v3`
manifest (`compute-flags/ready/<id>.json`; its field set is that script's and
`scripts/coordination/rowflow/README.md`'s, not restated here), and the keeper smokes the real
launcher once on the real lane (`dryrun/<id>/PASS.json`) before it grants. Flow:
`docs/guides/agent-workflows/backlog-churn-flow.md`. The retired 10-28 `LOOP-CONTRACT.md` manifest
layout is not current.

## The smoke

- At most 60 s of the real job path (300 s when a model load dominates): entry, first real request or
  compute, result writer, clean exit.
- No owner approval step. Valid < 24 h and only for the same launcher sha256.

## Checks the smoke must show (each one killed a row on 10-27)

1. The grant line parses in the keeper's exact format (minute precision `HH:MMZ`; R6 parsed only seconds).
2. Launched from a non-ancestor tree (`setsid`): Yama `ptrace_scope=1` returns EACCES on `/proc`
   of non-descendants (HSF-3, FA4).
3. Normal inherited env, including `NODE_OPTIONS` (ORCH refused silently).
4. Every refusal prints its reason and rc; a silent refusal fails the smoke.
5. `prlimit --pid $$`, `taskset -pc $$`, `cat /proc/self/cgroup` printed from the job's shell and
   matched to the row (KPF18 R13 inherited an 8 GiB RLIMIT). Declare `process_limit_GiB` when
   the address-space ceiling is below the RAM reservation.
6. `timeout --foreground`, or own PGID killed as a group (FA4 child escaped its grant).
7. Disk floor holds after the declared output (`disk-bin.md`); `min_window + 300 <= window` (INF-50).
8. Deps resolve as the job resolves them (offline `uv` lock missing a git dep, 10-26), without
   touching the shared venv.
9. Graceful stop at window end exits rc75 with `partial=true`.
