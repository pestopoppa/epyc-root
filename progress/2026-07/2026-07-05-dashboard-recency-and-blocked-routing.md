# Handoff dashboard hub — card recency signal + Blocked-column routing (2026-07-05)

**Session**: operator-directed — "handoff dashboard hasn't updated since first generated; is it stale / was the commit hook not activated?" then "I don't see the outstanding (not active) handoffs… we should have them."
**Surface**: `epyc-root/dashboard/*` (hub :8100) + `scripts/handoffs/*`.
**Repo**: epyc-root. **Deployed**: hub reloaded via `orchestrator_stack.py reload handoff_dashboard` (final live PID 2730527). Committed `043c6288`, merged to `main` as `5c955d00`.

## Problem 1 — board "felt stale"

The operator believed the kanban hadn't updated since first generated and suspected the commit hook was never wired.

**Root cause (not staleness):** the pipeline was healthy — the `post-commit` hook fires (confirmed: timeline artifact regenerated 2 s after HEAD, `last_sha` == HEAD), and the board is a live 30 s-TTL directory scan that the page polls every 45 s. The board *looked* frozen because the Active/Blocked columns sorted by, and stamped cards with, the frontmatter `Updated` field — which **85 of 134 active handoffs don't have**. So an edited handoff kept showing its old `Created` date and never re-sorted to the top; card content updated live but the ordering/date did not. Completed/Archived sort by mtime, so those moved — making the freeze look selective.

## Problem 2 — outstanding (not-active) handoffs not shown

The Blocked column showed 0 even though several handoffs are effectively blocked/parked/waiting. **Root cause:** routing sent a handoff to Blocked only if its `Status:` *started with* the word "BLOCKED"; real handoffs carry the blocking signal mid-status ("…remains blocked on an off-host target", "…pending operator rollout decision", "PROPOSAL — needs operator approval"), so they stayed in Active.

## Changes

| File (epyc-root) | Change |
|---|---|
| `scripts/handoffs/build_handoff_timeline.py` | Emit `file_activity` map (last commit day per `state/stem`, migrated on rename, dropped on delete, `max()` monotonic) into `data/handoff_timeline.json`; docstring notes merge-commit blind spot. |
| `dashboard/server.py` | `_load_file_activity()` (tolerant artifact read → `{}` on any corruption) + `_dirty_handoff_ids()` (`git status --porcelain -- handoffs/`); both passed into `build_board`. |
| `dashboard/handoff_parser.py` | `build_board(*, file_activity, dirty_ids)` keyword-only (back-compat). Per card `activity = max(frontmatter updated, git last-touch, mtime-if-dirty) → created`, labelled by `activity_source ∈ {updated,git,wip,created}`. Active/blocked sort by `activity`; `_neg_date` → `fromisoformat`. New `_is_blocked_status()` widens Blocked routing with negative guards ("does not block", "blocker … resolved"). |
| `dashboard/static/handoffs.html` | Card chip shows the activity date + source label; header shows the live scan time. |
| `scripts/handoffs/install_timeline_hook.sh` | Rewritten to also wire `post-merge` + `post-checkout` (pulled/merged commits refresh the artifact), each with an argument-appropriate change-guard; idempotent, installs all three. |
| `tests/test_handoff_parser.py`, `tests/test_handoff_timeline.py` | +18 cases: activity max-rule, dirty-mtime gating, rename/delete migration, blocked-status precision/traps, artifact-corruption tolerance. |

## Results (live board, verified)

- Active/blocked recency: **133 of 134 active cards now date+sort by real git activity, 1 by uncommitted-edit mtime** (was 57 created / 45 updated / 31 undated). The "Internal Interaction Lifecycle" card that sat frozen at its May `Created` date now reads `2026-07-05`.
- Blocked column: **0 → 5** genuinely-blocked/parked/pending-operator handoffs (Active 134 → 129; outstanding total unchanged at 134). Trap cases ("cherry-pick BLOCKED, but the fresh path is VERIFIED WORKING", "does not block KB-RAG") correctly stayed in Active.
- Tests: 50/50 pass (`python3 -m unittest tests.test_handoff_parser tests.test_handoff_timeline`), including against the merged-into-main worktree.
- Hook guards validated in an isolated throwaway repo (no branch-switch/merge on the shared clone).

## Notes / deferred

- Completed/Archived columns keep their mtime sort (v1); the same `file_activity` map could later fix their re-touch-scrambled order.
- `.git/hooks` is not version-controlled — fresh clones must run `scripts/handoffs/install_timeline_hook.sh`; worth wiring into `clone-repos.sh`/session init.
- Related standing critique: [`loops-and-dashboards-audit-2026-07-05.md`](../../handoffs/active/loops-and-dashboards-audit-2026-07-05.md) §:8100 flags the backlog banner as "a count, not a steering instrument" and kernel-page freshness/Pareto issues — separate from this recency/routing work, still open.
- **Wiki compile deferred**: `compile_sources.py` reports 48 pending sources spanning many concurrent sessions; a dedicated compile pass is warranted rather than folding it into this focused session.
