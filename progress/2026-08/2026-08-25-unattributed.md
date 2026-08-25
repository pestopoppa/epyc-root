# 2026-08-25 — opencode ad-hoc session (backlog churn: Tier-1 batch)

**Agent**: opencode (ad-hoc, no lane; log shard `logs/agent_audit-unattributed.log`, session
`ses_20260824_114932_2699381`). Continuation of the 2026-08-24 tier-1 selection session
(see `2026-08-24-unattributed.md`).

## Mandate

Operator-directed: churn the Tier-1 backlog batch (INF-43 P0-1, RTG-49 FM-1, REV-04 RD-12,
REV-08 TM-8, RTG-46 hygiene), fan out subagents, CPU inference allowed but never concurrent.

## What happened

- **RTG-49 FM-1 — already done at HEAD** (commit `3bdc9a84`, 2026-08-23: `fanout_timing.py` v1,
  14 tests, corpus run 2428 workflows/4727 subagents). **Hazard flagged:** a peer session has a
  STAGED revert of the FM-1 files + doc box (files staged-deleted, box unchecked) plus a ~31k-line
  inventory diff riding in the shared index. I touched none of it; the RTG-49 row was left as-is.
  **The operator should confirm that staged revert is intended before anyone commits.**
- **INF-43 / N25 P0-1 — CLOSED 2026-08-24.** The 30-failures premise had drifted (re-derived
  2026-08-11; PROMOTION_GATE_TARGETS already green). Subagent fixed the 3 remaining fixture-side
  full-suite failures (`test_dispatch_cross_role_placement.py`, `test_inference_mixin.py`,
  `test_model_server_coverage.py`; gate-fixture `waited_s`/`blocking_roles` fields, SS-BENCH-GATE-c
  `ps` subprocess count): full suite 19 failed → 16 failed / 12526 passed. Remaining 16 = E8-era
  frozen-kernel guard (documented operator decision; left untouched). No source code modified.
- **REV-04 RD-12 + REV-08 TM-8 — IMPLEMENTED + REPLAY EXECUTED.** Code (review_service.py
  accounting, trace coverage module, replay harness `scripts/review/review_replay_50.py`, pinned
  50-question set) + 32 new unit tests. **50-question shadow replay run 2026-08-25** on a dedicated
  production-v9 llama-server (Qwen3.5-122B-A10B UD-Q4_K_M + MTP draft, port 8096, torn down after):
  coverage **100.0%** (50/50), phase tags 187/187, executor_model_id **187/187** (first run 80.2% —
  threaded executor into `apply_verifier_precedence`/`apply_warn_only`/`mark_reject_admissibility`/
  `escalate`, rerun 100%), PLAN_REMINDER 50/50, enforcement side-effects 0, parse-failures 1
  (distinct), **mean 8017 ms / median 8014 ms / p95 8959 ms per decision**, 16692 in / 3826 out
  tokens, overhead delta vs reviewer-off ≈ **8.0 s/decision** (H-LB baseline scaffold). Reports:
  `repos/epyc-orchestrator/data/trace/review_replay_report_{shadow,off,delta}.json`.
  Both boxes flipped; **H4 calibration unblocked**.
- **RTG-46 — 5 boxes closed.** New `scripts/handoffs/duplicate_task_scan.py` (recall 1.00 on the
  10 resolvable C2 pairs, precision 0.86; C2 pair list re-homed into the handoff);
  `backlog_row_check.py` mid-text owner fix (27/1528, zero FPs, 71 tests pass);
  **8 Deps edges applied** to index rows (REV-05→UFH-01, REV-01→INF-56, REV-04→REV-06,
  INF-33→INF-48, REV-02→INF-17, EVL-14→EVL-13, REV-07→REV-02, RTG-39→EVL-45);
  timeline hooks now regenerate in the canonical checkout via `git worktree list` (verified from
  lane mainA); inventory regeneration wired into hooks delta-guarded. Hub-cron decision package
  prepared for operator (recommendation: cron `once` form).

## Artifacts / evidence

- `repos/epyc-orchestrator/data/trace/review_replay_50.json` (pinned set; **needs `git add -f`** —
  `data/trace/` is gitignored) · `review_replay_rd12.sqlite` + reports (gitignored)
- `scripts/handoffs/duplicate_task_scan.py` · `scripts/coordination/backlog_row_check.py` (edit) ·
  `scripts/handoffs/install_timeline_hook.sh` (edit) · `scripts/review/review_replay_50.py` ·
  `src/trace/coverage.py` · `tests/unit/test_review_decision_accounting.py` (32 tests)

## Handoff/index state

- Flipped: N25 P0-1, RD-12, TM-8, RTG-46 ×5. Rows updated: REV-04, REV-08, RTG-46 (+8 Deps edges).
  `index_state.py --check` → 0 problems.

## Open (named, not deferred)

- **Commit decision** — none of this is committed (shared clone, peer staged-state hazards; awaiting
  operator go). Three repos carry uncommitted work: epyc-root (doc/index/script edits),
  epyc-orchestrator (review-plane code + 3 test files + harness), all worktree-only, nothing staged
  by me.
- **Peer staged revert of FM-1** (fleet-fanout-measurement + fanout_timing files + 31k-line
  inventory diff) — confirm intended before any commit touches those paths.
- Operator: hub_supervisor cron ruling (package in `handoff-index-and-backlog-graph.md` §Open).
- Operator: E8-era frozen-kernel guard re-pin (documented in N25 P0-1; human-amendment-only).

## Wrap-up (operator-invoked, 2026-08-25)

- **Index pruning (operator cadence)**: archived `reviewer-decision-plane.md` (REV-04, RD-1..12 all closed) and `reviewer-trace-materialization.md` (REV-08, TM-1..9 all closed) to `handoffs/completed/` with banners; rows deleted from the reviewer index; 4 prose links repointed to `../completed/`. Wiki lint also re-checked (remaining errors pre-existing).
- **Wiki compilation sweep (operator cadence)**: 5 new sources (this session's docs) compiled into `wiki/hardware-optimization.md` (NUMA P0-1 gate close), `wiki/benchmark-methodology.md` (TM-8 coverage + H-LB baseline), `wiki/knowledge-management.md` (backlog-graph hygiene); `--touch` applied. README freshness: all pass.
- **Commits (shared-clone, private-index — no peer staged state swept; hunk-selective per the no-lane rule)**:
  - epyc-root `a9b02275` → pushed to origin/main under the serialized push lock (wrap-up commit above).
  - epyc-orchestrator `6919b885` → pushed to origin/main under the push lock (reviewer-plane + NUMA fixture fixes).
  - Both repos verified 0 commits ahead of origin/main.
- **Checklist-sync gate**: 8 checkbox flips this session (P0-1, RD-12, TM-8, RTG-46 ×5); derived-actionables gate: 0 new tasks required (all session findings filed as box flips; hub-cron package + E8-guard remain operator decisions, already queued).

## Staged-rollback resolution (operator-directed ownership, 2026-08-25)

**Investigation**: the shared clone's index+worktree carried an orphaned ~08-21-era rollback of
committed work — staged by the (now-inactive) 08-23/24 opencode session, spanning 115 staged
entries + 52 worktree-reverted/deleted paths in epyc-root and 21 staged entries in
epyc-orchestrator. The index tree matched no recent commit (hand-staged revert, not a checkout).
The only live session (autokernel, tmux agent:1) works via its lane; its shared-clone paths
(`artifacts/operator/op12-op15-ratification-package-20260823/`) were verified clean vs HEAD and
left untouched.

**Resolution** (per operator directive):
- `git reset` (mixed) in both repos — index = HEAD; peer staged set (FM-1 deletions, 08-24
  handoff-content deletions, R100 renames of two completed handoffs back to active, measurement
  Annex-D ratification deletion, relay ledger, progress files, scripts/tests) all unstaged.
- `git restore --source HEAD` for 50 rollback paths in root + 1 in orchestrator — worktree =
  committed truth. Excluded: daemon-owned `coordination/session-bus/{alarm_state,relay_state}.json`
  (bus_supervisor writes them) and all untracked runtime/backup files.
- Fixed the one pre-existing dead index row this exposed (RTG-25, committed `52e0feb3`).
- Verified: `index_state.py --check` 0 problems; wiki lint 0 dangling links (the two
  `2026-08-22-root.md` errors were rollback-caused, now resolved); FM-1 corpus files, replay
  evidence, and all flagged paths restored to HEAD content; both repos 0 commits ahead of
  origin/main; orchestrator fully clean.
