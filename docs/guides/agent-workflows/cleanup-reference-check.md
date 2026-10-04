# Cleanup reference check: "unused" includes environments and launchers

A disk cleanup or reclaim decides that a worktree, checkout, store or model is unused. **"Unused" means
nothing will open it in future, not just that nothing has it open now.** A path can be idle, clean and
fully landed and still be load-bearing, because a launcher, watchdog or cron job names it in an
environment variable or argument and reads it only at its next launch.

This guide adds a reference check to the destructive-operation pre-flight in
`agents/shared/OPERATING_CONSTRAINTS.md` → *Destructive operations*. That pre-flight checks identity and
trash-first; this check covers liveness. Both apply.

## Origin (2026-10-04)

The operator-approved disk cleanup removed `/mnt/raid0/llm/worktrees/root-main-epyc-root-repo` at about
02:25Z. It had passed every check then in use: landed, clean, idle for more than 7 days, no process cwd or
open fd inside it, and cited by no handoff or campaign input. But the DS41 launch and watchdog scripts
(`/mnt/raid0/llm/tmp/ds41-scope-20260926/ds41_watchdog*.sh`, `swap_*.sh`) export
`EPYC_ROOT_REPO=/mnt/raid0/llm/worktrees/root-main-epyc-root-repo` into every `serial_run` they launch (see
[agent-loop-design.md](agent-loop-design.md) → *Launching and stopping a DS41-style serial run*). DS41's next
batch claim failed, and two watchdog relaunches died within their 5-minute window, which uses up the
watchdog's two quick deaths before it falls back to single-lane arguments. The worktree was restored at
02:30 (`git worktree add --detach <path> 117370a8630f`) and DS41 was relaunched at 02:36. Incident entry:
INC-20261004-cleanup-removed-load-bearing-worktree in `docs/reference/agent-config/INCIDENT_LOG.md`.

The check failed because it defined "unused" by cwd and open files. A reference in a launcher's environment
does not show up in either until the next launch.

## Never a candidate: harness state and session transcripts (operator hard rule, 2026-10-04)

Some trees are excluded before the check below even starts. **Claude and Codex backup logs and session transcripts
are never touched:** not deleted, moved, truncated, vacuumed, compacted or "reaped". That holds under disk pressure,
holds when an operator has approved a cleanup, and holds for any retention script. In the operator's words:
*"Claude/codex backup logs should NOT BE TOUCHED UNDER ANY CIRCUMSTANCES. They are historical transcripts used by a
root filesystem project far more senior to anything performed in this project repo."* The rule covers **every
third-party agent harness's own state**, not just Claude and Codex:

| Tree | What it is |
|---|---|
| `/home/node/.claude`, `/home/node/.local/share/claude` | Claude Code transcripts, backups, share state |
| `/mnt/raid0/llm/claude-backups` | the claude-backups job's output |
| `/home/node/.codex`, `/mnt/raid0/llm/tmp/ds41-c95/codex-home` | Codex sessions, logs and history DBs (incl. harness homes) |
| `/home/node/.local/share/opencode`, `/home/node/.config/opencode` | opencode store and config |
| `/home/node/.hermes`, `/mnt/raid0/llm/hermes-agent`, `/mnt/raid0/llm/tmp/ds41-c95/hermes` | hermes state |
| `/mnt/raid0/llm/cloud-llm-vault` | cloud harness vault |

Code enforces it: `scripts/system/scratch_cleanup.py` refuses every path under its `NEVER_TOUCH` list, whatever a
handoff declares (root `722b7196`, `b639dc8e`). `scripts/system/codex_retention_reaper.py` has its `apply` path
permanently disabled (exit 4, report-only). The authoritative list is the `NEVER_TOUCH` constant: a new harness gets added
there first. If a harness store's growth matters, **report it** (the report-only reaper, `host_hygiene_tick.py`'s
grower ranking) and leave the decision to the operator.

One operator-approved exception exists: `scripts/system/opencode_event_reaper.sh`. It prunes only opencode's
`event` streaming table in idle sessions and never sessions, messages or parts. It is not a precedent for any other
reaper. The doctrine half is prepared for ratification into `agents/shared/OPERATING_CONSTRAINTS.md` →
*Destructive operations* (`scripts/operator/ratify_harness_state_never_touch_20261004.sh`).

## The check: run all of it, per path, before removing anything

Run it for each candidate path `P`, using its realpath and any alias that `scripts/safety/path_identity.sh`
reports. A hit on any step means **keep**, unless the owner of the referencing process or script agrees.

1. **Live process environments and argv.** Read-only, with no name-pattern tools:

   ```bash
   for d in /proc/[0-9]*; do
     { tr '\0' '\n' < "$d/environ"; tr '\0' ' ' < "$d/cmdline"; } 2>/dev/null \
       | grep -qF "$P" && echo "${d#/proc/} $(tr '\0' ' ' < "$d/cmdline" | cut -c1-160)"
   done
   ```

   A long-lived watchdog's environment is inherited by every child it starts later.
2. **Launch, watchdog and swap scripts** written or run in the last 30 days:
   `grep -rlF "$P" /mnt/raid0/llm/tmp --include='*.sh'` (add `-newermt`/`find -mtime -30` to bound it).
   Also check `scripts/` in the repos that launch long runs.
3. **Scheduled jobs:** `crontab -l` and any cron file a supervisor installs.
4. **Campaign and state directories:** AutoKernel `inputs/common-args.json`, serial-run continuation
   state, `loop-status.json`, and AutoPilot or stack configs. A path inside a run's frozen inputs is
   pinned for the life of that run.
5. **Explicit markers:** a `KEEP`, `LOAD-BEARING` or `ARCHIVED.txt` note in or beside the path, AutoKernel
   KEEP-dirty retention (`docs/design/autokernel-disk-hygiene-20260915.md` §6.1), and LEAN retention notes.
   Honour them. Do not re-litigate a marker inside a cleanup pass.
6. **Then** run the existing pre-flight: identity check, `git worktree remove` for git-registered trees
   (never `rm`, never `prune`), and `guarded_rm.sh` for data.

A cleanup menu written by an earlier pass is a set of claims to re-verify against the current state, path
by path. It is not a list to execute (`wiki/agent-architecture.md` → *A purge menu is a set of claims to
re-verify per path*).

## While a long run is live

- **Hold its watchdog before a risky infra change** (a cleanup, a reclaim, a checkout refresh, a stack
  change). DS41's watchdogs read a hold file (for example
  `/mnt/raid0/llm/tmp/ds41-scope-20260926/WATCHDOG3_HOLD`). With the hold set, a broken dependency fails
  once and visibly. Without it, two quick relaunch deaths push the run onto fallback arguments. Remove the
  hold after the change and confirm one clean relaunch.
- **A path a live run exports is frozen with the run.** Refresh or replace it only between runs, like the
  run's code root.

## Recovery

If a removed path turns out to be load-bearing, restore it at the exact commit it held:
`git worktree add --detach <path> <sha>`. The sha is in the worktree's last `git worktree list` record, the
launcher's log or the reflog. Then confirm that the dependent run relaunches and makes its next claim before
calling it fixed.
