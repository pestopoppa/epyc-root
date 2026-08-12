# Worktree migration — the two-plane model

Companion doc for `scripts/coordination/setup_main_worktrees.sh` (P1/4 of
`guard-universe-and-worktree-isolation`, phase 1). This is the design note;
the script is the mechanism. **Phase 1 (this) builds and verifies the
machinery against a single throwaway agent (`wttest`, removed after
verification). Phase 2, explicitly post-reboot and explicitly not this
task's to do, is running the script for the five real lane names —
`mainA mainB mainC mainD auditor`.**

## Why: what isolation is for

`coordination/session-bus/` had 89 git-tracked runtime files (inbox,
outbox, cursors, heartbeats, `adapter-ledger.jsonl`) all mutated by five
mains committing concurrently in the SAME `/workspace` working tree. That is
the direct mechanism behind a 21-conflict merge, all night: five sessions
racing to `git add`/`git commit` the same tracked bus files, plus ordinary
work-tree contention on everything else they touched in the same repo at
the same time. Untracking the bus churn (item 2 of this task) removes one
source of conflict; it does not touch the other — five agents editing code,
docs and handoffs in one shared working tree still contends on the
non-bus files. Per-main worktrees remove that second source: each main gets
its own working tree, its own index, its own untracked-file state, on its
own branch. They stop stepping on each other's staged changes because they
are not staging into the same index anymore.

## The two planes

**Canonical runtime plane — `/workspace`, one instance, never forked.**
The session bus (`coordination/session-bus/`), `tokens/token-queue.md`,
`logs/agent_audit.log`, and any other live coordination sidecar. This plane
is *state*, not *work* — it describes what agents are doing and what they
are waiting on, right now, and there can only ever be one live copy of
"right now". Item 1 of this task exists because a naive worktree rollout
would have forked exactly this plane: `session_bus.py`'s bus-root
resolution used to be `Path(__file__).resolve().parents[2]`, so five
worktrees would have produced five independently-mutating buses instead of
one. `get_bus_root()` now resolves to the literal canonical
`/workspace/coordination/session-bus` regardless of which worktree's copy
of the module answers the call — verified by `setup_main_worktrees.sh`
itself, per worktree, via `session_bus.py --print-root` with no
`EPYC_BUS_ROOT` set (production code paths never set that override).

**Versioned work plane — one worktree per main, each on its own
`lane/<agent>` branch.** Code, docs, handoffs, progress entries — everything
that is genuinely that main's own work-in-progress and benefits from git's
normal machinery (diff, log, blame, revert) rather than needing to be a
single always-current snapshot. Lives at
`/mnt/raid0/llm/worktrees/mains/<agent>` (not under `/workspace/worktrees/` —
that path already hosts an unrelated, pre-existing worktree scheme for
throwaway task branches; the two are not the same mechanism and this one
does not touch or depend on that one).

The split is exactly "does this file want to be ONE current answer, or a
HISTORY of changes a main is making". The bus wants the former. Everything
else a main writes wants the latter.

## Per-item sync discipline

A worktree without a sync discipline just moves the merge-hell from "every
commit, in one shared tree" to "one giant merge, whenever somebody finally
looks" — isolation with no sync half is not a fix, it is a deferral (see
*The inference gap*, below, for what that deferral costs in practice).  The
discipline:

1. **Commit in the worktree**, on `lane/<agent>`, normally and often — this
   is now a private branch with a private working tree, so there is no
   reason to batch commits the way a shared tree encouraged.
2. **Promote via the `/wrap-up` skill's existing isolated merge pattern**
   (`.claude/commands/wrap-up.md` §7, "Commit, Push, Promote, and Report") —
   already built, already the standing per-repo promotion path for any
   non-`main` branch, reused here rather than inventing a second promotion
   mechanism for lane branches specifically:

   ```bash
   git -C <repo> fetch origin --quiet
   WT=$(mktemp -d)/promote
   git -C <repo> worktree add --detach "$WT" origin/main
   if git -C "$WT" merge --no-ff -m "Merge lane/<agent> into main (...)" "origin/lane/<agent>"; then
     git -C "$WT" push origin HEAD:main
     git -C <repo> branch -f main origin/main
   else
     git -C "$WT" merge --abort
     echo "PROMOTION BLOCKED: <repo>"
   fi
   git -C <repo> worktree remove "$WT" --force
   ```

   Isolated (a throwaway `--detach` worktree, never the live lane worktree
   or its branch), conflict-guarded (abort and leave `main` untouched on
   conflict, never auto-resolve or force), never force-pushes. A blocked
   promotion is reported to the operator, not silently retried or bypassed.
3. **Frequency**: at minimum, every `/wrap-up` (per `SESSION_LIFECYCLE.md`'s
   per-task-not-session-end wrap-up cadence) — a lane branch that only gets
   promoted at session end is exactly the batching this discipline exists to
   avoid.

**What this dissolves**: the shared-file classes that caused conflicts
under the single-tree model were (a) session-bus runtime files — dissolved
by item 2 (untracked) plus item 1 (still one canonical instance regardless
of worktree); (b) code/doc files two mains happened to touch in the same
session — dissolved by (2) above, since each main's edits land on its own
branch and reach `main` through a merge, not through two sessions racing to
`git add`/`git commit` the same working tree; (c) the five-writer progress
file — dissolved by the per-main convention below.

## Per-main progress file convention

`progress/YYYY-MM/YYYY-MM-DD.md` was a single file five mains all wrote to
on a shared branch — the same contention shape as the bus, just for prose
instead of JSONL. Convention going forward:
**`progress/YYYY-MM/YYYY-MM-DD-<agent>.md`**, one file per agent per day,
written only from that agent's own lane worktree. `/wrap-up`'s step 1
(progress report) targets this per-agent file instead of the shared one.
The shared `YYYY-MM-DD.md` is not retroactively split — this convention
applies from the first day mains actually run from worktrees (phase 2)
onward; existing shared-file history stays as-is.

## Orphan hygiene

A worktree that is `git worktree remove`'d cleanly is fine. One whose
directory is deleted out from under git (`rm -rf` instead of `worktree
remove`) leaves stale metadata in `.git/worktrees/<name>/` forever — `git
worktree list` keeps reporting it, and `git worktree add` at the same path
later fails on stale lock/admin files. This is not hypothetical: the
investigation that produced this task found **53 orphaned worktree
directories on the research side** (`epyc-inference-research`) — accumulated
exactly this way, from throwaway task worktrees that were deleted without
`git worktree remove`.

**Rule: `git worktree prune` at every `/wrap-up`**, for every repo a main
touched that session — cheap (a metadata-only sweep, no effect on worktrees
still genuinely in use), and it is the direct fix for the 53-orphan finding.
`setup_main_worktrees.sh` itself validates before creating anything
(`validate_mains_root()`) rather than pruning automatically — a script that
silently prunes on every invocation could remove a worktree an operator
intentionally left registered but temporarily unmounted; refusing and
naming the problem is the same fail-closed posture the rest of this task's
hooks use, not a new one invented here.

## The inference gap

Stated plainly, per this task's initiating investigation (not independently
re-verified against `epyc-inference-research`'s or the autokernel tree's
full branch topology in this session — that is a separate, larger audit;
flagged here so it is not lost, not overclaimed as freshly confirmed):
**the `inference` lane isolates but has not merged to `main` since
2026-07-29 — approximately 302 commits of divergence, zero codex merges in
that window.** Isolation without the sync half — exactly what step "Per-item
sync discipline" above exists to prevent for the five mains — recreates
tonight's merge hell at a larger scale: a lane branch that runs
autonomously and independently for two weeks does not stop accumulating
conflict potential just because nobody looked at it; it *concentrates* it
into one eventual, much larger merge, with two more weeks of unrelated
`main` history for that merge to have diverged against.

This is the concrete argument for why "one lane worktree per main" is only
half the design here. The worktree isolates; it does not, by itself,
guarantee anything gets promoted. The promotion step above — reusing
`/wrap-up`'s existing isolated-merge pattern, run at least every wrap-up —
is the half that closes the gap this finding shows the cost of leaving
open. Whoever owns the `inference` lane's reconciliation should treat that
merge as its own tracked piece of work, not something this document
resolves by naming it.

## Practical usage

```bash
# Phase 2, post-reboot, NOT this task:
scripts/coordination/setup_main_worktrees.sh mainA mainB mainC mainD auditor
```

- Idempotent: re-running for an agent that already has a valid worktree on
  `lane/<agent>` skips creation but always re-verifies (repos symlinks,
  hooks fire, bus root resolves canonical) — safe as a periodic health
  check, not just safe to re-invoke.
- Refuses outright, before touching anything, if
  `/mnt/raid0/llm/worktrees/mains` already contains an entry that is not a
  clean worktree of this repo on its expected `lane/<name>` branch (stray
  file, foreign directory, wrong branch, broken worktree metadata) —
  `validate_mains_root()` in the script. Fix or remove the offending entry
  by hand and re-run; the script does not guess.
- Each per-agent run verifies, inside the new worktree: (a) the shared
  pre-commit hooks actually fire — a secret-shaped scratch blob is staged
  and must block, a clean scratch file is staged and must commit, then the
  scratch commit is `git reset --hard` off the tip (sanctioned only because
  `lane/<agent>` is that worktree's own branch at that point in setup, with
  nothing else based on its tip yet); (b) `session_bus.py --print-root`
  with no `EPYC_BUS_ROOT` resolves to the one canonical
  `/workspace/coordination/session-bus`, never a worktree-relative path.
- `repos/*` symlinks are set up by running the **worktree's own copy** of
  `scripts/clone-repos.sh`, not `/workspace`'s — it resolves its target
  directory from its own invocation path (`$(dirname "$0")/../repos`), so
  no change to that script was needed; it already targets wherever it is
  run from.
