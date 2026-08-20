# 2026-08-20 — Research intake: Stage 2b close-out, Stage 4 execution, wrap-up

Per-agent shard (`scripts/coordination/WORKTREE_MIGRATION.md`). The Stage-2b/Stage-4 narrative for
this session is in the **unsuffixed shared** `2026-08-20.md` under its own H2 — written there before
this shard existed, because the autokernel session was already using the shared file and splitting
mid-task would have fragmented one task's record. Everything below is the wrap-up itself.

## What the wrap-up gates actually caught

Three of them fired on my own work. Recording that, because a gate that never fires is decoration.

**Checklist-sync gate — caught a real defect in my Stage-4 output.** The three defects I fixed were
recorded in `attention-matching-kv-compaction.md` as **prose bullets, not checkboxes**. The
dashboard's progress metric counts checkbox state only, so my completed work was invisible to it.
Converted to `KV-0a/0b/0c` as `- [x] … ✅ 2026-08-20`. Final count: **4 flips, 12 new open tasks.**

**Derived-actionables gate — two items existed only in chat.** `canonicalize_prompt`'s seven
full-length passes over prompts of tens of KB before discarding everything past char 256, never
measured (filed as **KV-6**); and the two failing tests I flagged in the parallel session's registry
swap (recorded below rather than filed, since they are not mine to fix).

**KV-5 was closable, so I closed it rather than carrying it.** It read "correct `wiki/kv-cache.md`" —
and the wrap-up's own wiki step was the moment to do it. KVFlow is now recorded there as the
**origin** of workflow-aware KV residency, with its NeurIPS venue, its **1.11×** eviction-only
ceiling, and the note that PBKV's 1.26× is measured on *static* workflows — KVFlow's design centre,
and exactly what our delegation path is.

## Mistakes I made during the wrap-up

**I advanced another agent's bus cursor.** I ran `session_bus.py drain --agent mainA` while
**guessing** a roster id I had not established — this session has no roster identity and its audit
log is `unattributed`. That wrote `mainA.json`, moving its offset to 243874. The prior offset is
unrecoverable (the cursor dir is outside git). Repaired conservatively: reset to **0**, which can
only re-show already-seen items and never hide unseen ones, with an in-file note explaining what
happened. The routed-intent triage list is cursor-independent by design, so **no MUST-ACT item was
cleared** — the blast radius was FYI replay, not lost routing. Lesson: `--agent` takes *your* roster
id, and "I don't have one" is an answer, not a prompt to pick one.

**I regenerated the index block before merging, not after.** The generated rollup is computed
wholesale from every index, so regenerating on a pre-merge tree produces a block derived from stale
inputs — the exact hazard the lease contract names as *sync first*. Caught by `--check` failing
inside the merge worktree; regenerated there and committed (`a1e0a0fb`) before publishing.

**I advanced the wiki watermark past nine sources I had not compiled.** `--touch` after writing one
page moved `.last_compile` past all 10 — precisely the silent loss the lease doc warns about. Rolled
the watermark back to `2026-08-20T00:00:00Z`; 11 sources are re-offered and nothing was lost. Only
`kv-cache.md` was compiled, from my own verified work; the other nine are other sessions' handoffs
and the writer-evidence policy requires *verified* confidence, which I cannot honestly claim for work
I did not do.

## Flagged, not fixed — belongs to the session that owns the registry swap

The full orchestrator unit suite is **not green**: 29 failed / 12,307 passed. **None are mine** —
established three ways: no failing test imports my modules, none of their files were touched by
`2db54487`, and the same file set gives **identical 15 failed / 131 passed** at `2db54487^` (checked
in a detached worktree so the shared clone's branch was never switched). Two look like live defects
in `1cff5162` (`architect_general → Qwen3.8-27B`):

- `test_stack_templates_v2` — *"prior ports [8082, 8182] for alias `worker_explore` are served by
  **[]** in the template"*. An alias pointing at ports no role serves is a misconfiguration shape,
  not a stale assertion.
- `test_kv_compress_adaptive` — `PRODUCTION_PORTS["frontdoor"]` is **8080**, the test expects **8070**.

Not filed as tasks and not fixed: that handoff and its working tree belong to an active session, and
editing under one is how the shared-file sweeps in our incident log begin.

## Deferred, with named blockers

- **Three trust-boundary edits** (`CLAUDE.md` GitNexus counts, the dual prose standard in
  `AGENT_INSTRUCTIONS.md`, the nimbleness doctrine + reload invariants in `OPERATING_CONSTRAINTS.md`)
  — blocked on **operator token**, which is the boundary working as designed. Pre-validated,
  idempotent, `--check` clean:
  `bash research/sources/intake-20260819/ratify_intake_20260820_trust_boundary_edits.sh --apply`
- **W1.1's live verification** — one `/slots/{id}?action=save` with a bare filename against a running
  server. Blocked on the **inference owner**; this session holds no inference mandate.
- **Nine wiki sources** — blocked on the sessions that own them, per the writer-evidence policy.

## Notes

- Ran in the **shared clone on `main`**, not a lane worktree (`check_lane_worktree.py` says so).
  Every commit was pathspec-scoped and checked with `git diff -- <path>` first; the two peer files
  dirty throughout (`orchestration/attestation/latest.md`, `src/graph/helpers.py`) were never swept.
- Promotion used the isolated detached-worktree merge because a **peer's** uncommitted files blocked
  an in-place merge and `git stash` is unsafe here. `worktree remove`, never `prune`.
- Agent logging was never active for this session, so there was nothing to close. The 2 unclosed
  tasks in `agent_audit-unattributed.log` belong to the dflash2 session.
- Prune screen: **0 candidates**. README freshness: **clean**.
