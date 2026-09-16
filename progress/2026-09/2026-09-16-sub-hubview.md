# 2026-09-16 — sub-hubview (dashboard fix A, operator-approved)

## Problem

The :8100 hub reads handoffs, the index graph and "today's activity" from its own checkout
(`dashboard/server.py`: `REPO = parents[1]`). The orchestrator manifest entry `handoff_dashboard`
launched the hub from lane `worktrees/mains/autokernel-unified-20260908`. That lane was 141 commits
behind origin/main, so pushed progress never appeared on the hub.

## What changed

**The view.** `/mnt/raid0/llm/views/epyc-root-main`
- A standalone clone: `git clone --reference /mnt/raid0/llm/epyc-root/.git <github origin>`.
  - Its `.git` is 556K; it borrows objects from the canonical repo.
  - `--git-dir` equals `--git-common-dir`, so it is not a linked worktree.
- It carries the marker `.epyc-view-readonly` and a copy of it, `README.epyc-view`. Both are listed in
  `.git/info/exclude`, so `git status` stays clean.
- It is detached at origin/main.
- Its artifacts were already generated once: the index state/graph and the timeline.

**Root branch `sub/hubview-20260916`:**
- **`scripts/dashboard/refresh_hub_view.sh` (new).**
  - Refuses (exit 3) a tree without the marker, a tree that is not a git top-level, or a linked
    worktree.
  - Holds a flock in the view's git dir.
  - Runs `fetch`, then `update-index --refresh`, then `checkout --detach --force origin/main`.
  - Regenerates the gitignored `handoffs/active/.index-state.json`, `.index-graph.json` and
    `data/handoff_timeline.json` in three cases: HEAD moved, an artifact is missing, or an artifact is
    older than 3600s.
  - Reverts index_state.py's rollup edit to the tracked master index.
  - Writes one log line per run. A real run takes about 12s when it regenerates and about 1s otherwise.
- **`scripts/dashboard/hub_supervisor.sh`.**
  - Adds `is_hub_view` and `refresh_hub_view`. The refresh is rate-limited by
    `HUB_VIEW_REFRESH_INTERVAL_S=180`, tracked in the state file `logs/hub_supervisor.view_refresh`,
    and can be disabled with `HUB_VIEW_REFRESH_ENABLED=0`.
  - Both `loop` and `once` call the refresh before deploy-sync.
  - Deploy-sync is skipped when the hub source is a view.
  - `plan` reports the refresh state.
  - The supervisor always runs its OWN sibling copy of the refresher, never the view's copy, because
    the refresher overwrites the view's files while bash is still reading the running script.
  - The marker `HUB_SUPERVISOR_MANIFEST_LAUNCH_V1` is kept.
- **Restart semantics.** Checkout rewrites only files whose content changed. The index stat info is
  refreshed first, so a `touch` does not count as a change. As a result, dashboard/*.py mtimes move
  only on a dashboard code change, and the stale-source check restarts the hub once per such change,
  never on a handoff-only refresh. The new test covers this: B1–B4.
- **`scripts/dashboard/tests/test_hub_view_refresh.sh` (new, 42 checks).** Runs against a fake bare
  origin.
- **Test results:**

  | Test | Result |
  |---|---|
  | `test_hub_view_refresh.sh` (new) | 42/42 |
  | `test_hub_manifest_launch.sh` | 38/38 |
  | `test_hub_stale_source.sh` | 6/6 |
  | `test_hub_deploy_sync.sh` | PASS |
- **Other root changes.** A note under OP-9 in `handoffs/active/handoff-index-and-backlog-graph.md`.
  `index_state.py --check` reports 0 problems.

**Orchestrator branch `sub/hubview-orch-20260916`:**
- `launch_manifest.yaml` `handoff_dashboard`: cwd/pythonpath now point to `{llm_root}/views/epyc-root-main`.
- The manifest parses. `hub_supervisor.sh plan` against it (orchestrator resolver) resolves the hub
  source to the view and reports deploy-sync SKIP and view-refresh enabled.
- 294 tests pass across these files: `test_aux_service_env`, `test_stack_manifest_imports`,
  `test_orchestrator_stack_reload`, `test_stack_change_guard` and `test_stack_numa_reader_agreement`.

## Store verification (AUTOKERNEL_LOOP_STORE_ROOT)

**Unchanged.** `/mnt/raid0/llm/tmp/aku12a-glm53-five-loop-store` is live:
- `loop-status.json` was written at 14:11:36 today. Its `batch.output_dir` is
  `aku-glm53-continuous-20260916-v18/batches/batch-000000`, pid 2164706.
- The `aku-glm53-continuous-*-vNN` dirs are per-run batch/output dirs. Their loop-status is
  `legacy-serial`, not a loop store.
- The only STOP file is `STOP.consumed-20260909T2314Z`; there is no live STOP.

## Deploy sequence (main session; nothing was restarted here)

1. Push both branches: root `sub/hubview-20260916` and orchestrator `sub/hubview-orch-20260916`. Merge
   them to main.
2. Update the canonical files:
   - `git -C /mnt/raid0/llm/epyc-root` must contain `scripts/dashboard/{hub_supervisor.sh,refresh_hub_view.sh}`
     from the merged main. Check with `grep -c refresh_hub_view /mnt/raid0/llm/epyc-root/scripts/dashboard/hub_supervisor.sh`
     and `test -x .../refresh_hub_view.sh`.
   - `/mnt/raid0/llm/epyc-orchestrator/orchestration/launch_manifest.yaml` must carry the view cwd.
   - Do not edit a running .sh in place. Replace it with a new file (git checkout writes a new inode),
     then restart the supervisor.
3. Restart the supervisor: stop the current `hub_supervisor.sh` loop pid (from `logs/hub_supervisor.pid`,
   verify with `ps -p`), then run
   `nohup setsid -f /mnt/raid0/llm/epyc-root/scripts/dashboard/hub_supervisor.sh > /mnt/raid0/llm/epyc-root/logs/hub_supervisor.out 2>&1 &`
   with `EPYC_ROOT` unset. Then check `hub_supervisor.sh plan`; it should show hub source = view and
   view-refresh enabled.
   - Once the new manifest is live, the healthy-path stale-source check sees the view's files as newer
     than the running hub, so the supervisor may restart the hub itself on its first poll. Step 4 makes
     that explicit.
4. Reload the hub: `orchestrator_stack.py reload handoff_dashboard`. Do not reload the full stack.
5. Verify:
   - `readlink /proc/$(ss -tlnpH 'sport = :8100' | grep -oP 'pid=\K[0-9]+' | head -1)/cwd` → `/mnt/raid0/llm/views/epyc-root-main`
   - `curl -s :8100/api/handoff_graph` shows `generated_at` after 2026-09-16T10:00. Its handoff states
     should match origin/main, for example this handoff's OP-9 fix-A note.
   - `git -C /mnt/raid0/llm/views/epyc-root-main log -1` equals `origin/main`. After a push, it
     advances within about 180s. `grep hub-view logs/hub_supervisor.log` shows `refresh ... rc=0`.
   - The lane `autokernel-unified-20260908` is no longer served. Its uncommitted WIP stays in the lane,
     as the operator accepted.
