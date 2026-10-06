# LR-8 runtime handover decision package (inert)

Prepared against published ROOT source commit `3316e09035e161f229e2de9261d408a75f3e1c08`.
This package is review material only: no live process, cron, registry, database, view, or
source file was changed; no tick or reaper was forced; no test/import/CI was run.

## Recommendation and decision

Recommend **B, an owning-session coordinated handover**, at the current reaper owner's next
session boundary. The source is already published and inactive. B removes the extra daemon and
makes the hygiene tick the only event-reaper scheduler, with a CPU-region gate, one stable alarm
owner, a 30-minute cadence, and an independently visible scheduled log. The current OP-73 choice
2A authorized the earlier host activation only; it does not authorize this new runtime change.

The actual choice is whether to enable the event duty at that owner boundary by (i) stopping the
identified daemon, (ii) deploying the capability-bearing canonical reaper and scheduled registry
row, then (iii) adding `HYGIENE_OPENCODE_EVENTS=1` to the existing pinned host cron command.
Until that choice is made and the current daemon owner can perform the stop, use **A**: leave the
daemon, registry and host cron as they are and keep the new duty inactive. A is safe and reversible;
it preserves the current 1800-second daemon loop, but does not unify its monitoring and alarm path.
There is no process PID or live crontab snapshot in this package; PID `2052506` in OP-73 acceptance
is historical and must never be used as a stop target.

## Source and accepted-state bindings

| Item | SHA-256 / identity | Use |
|---|---|---|
| Published root source | `3316e09035e161f229e2de9261d408a75f3e1c08` | LR-8 source and handover guide |
| Published `host_hygiene_tick.py` | `9d5771245e6ab16ef495a7053321f380dcb403a45b3d38d6930746f05104d6ff` | view source; inactive unless env opt-in and registry contract match |
| Published capability reaper | `533f502b7a022969707f39eaecb3eb3af0050f7e5844259b9572dbce819ee5a4` | canonical-root deployment required for `once-status` |
| Published source registry | `3116dee5c2ba05879d10d045f0a6318a9d822cc9849418bb90bb25e311c89057` | Git source only; not the post-OP-73 runtime bytes |
| Published handover guide | `c0681a50e771cc4f0596d4f7d4a8a98d08df41cdef076f9c197be75e7b33ef03` | owner and failure contract |
| Accepted post-OP-73 registry projection | `8dfdabfc383585eb840cf2b6212cf15c739cd3cdf8553763ec123c5e78f1c35b` | fresh MAIN canonical-registry read matches accepted preimage; still recheck at apply time |
| Reaper bytes from immutable PIN00e | `924fe27ec9a0f1351bdc905938d2da32d3d6d69f9d9dc3b2c2fa16047957639d` | expected old canonical reaper bytes; abort if the live path differs |
| `prune_agent_event_store.py`, PIN00e and reviewed source | `a280648e20c2a35002c0707cf613f43170dc0fe87140a9063e50ff4ab3574e55` | unchanged dependency; no deployment needed |
| `observer_guard.sh`, PIN00e and reviewed source | `a345ed59c3c7b51bc33d146e6b2ff4a1718bfe524da463dccf3b00fc66becd78` | unchanged dependency |
| Accepted root supervisor pin | `00e1820bcd957e905797b3a1b9e4d9dc53a550b0` | keep the existing immutable pin path and four installed blobs unchanged |
| Accepted cron excerpt | `ade94db699bcfc52b3a7c0df8a7ef83d461fdbb11ec9bdb0e41cf50dd5aff9b4` | previous selected lines; actual current crontab was not independently read |
| OP-73 launcher / registry helper | `49ed734f89527f93a5afe569caf702ae95dd6de68eddc271663c6b077f092491` / `9a794584c497556f1ce0b75a465097621d73792ed456648f55ce1d156b1b9767` | immutable reviewed package; do not rerun its apply path against the new baseline |

The prior accepted installer pinned its own source at `00e1820b...`; its event-reaper source
predates `LR8_ONCE_STATUS_V1`. Only the canonical reaper file needs capability deployment. The
published tick is selected from the read-only hub view by the pinned supervisor. Before B, the
owner must confirm that the manifest still selects that view and that its tick bytes equal the
published source. Do not change PIN00e or edit its copied supervisor files.

## Exact proposed handover delta

1. **Canonical reaper capability:** atomically replace only
   `/mnt/raid0/llm/epyc-root/scripts/system/opencode_event_reaper.sh` with the reviewed source bytes
   above. Preconditions: current target is regular, non-symlink, unmodified for this path, and
   hashes to the PIN00e value above. Preserve uid/gid/mode; write and fsync a same-directory temp,
   recheck source/target hashes and inode immediately before atomic replace; retain an exclusive
   preimage backup. If any check differs, abort without overwrite.
2. **Canonical observer registry:** start from exact accepted OP-73 bytes `8dfdab...`; change
   only `opencode_event_reaper.runtime` to the object below. Preserve every other byte-level
   field/row semantically, including `host_hygiene_tick` and unrelated entries. Remove daemon-only
   `pidfile`, `expected_path`, `provenance`, `start_argv`, old tmp log and `_relaunch_note`.
   Build and hash the complete candidate in private scratch first; apply only if the live registry
   still hashes to `8dfdab...`, is regular/non-symlink, and its owner/mode/inode match the
   preflight. Preserve an exclusive exact preimage backup.

   ```json
   "runtime": {
     "mode": "scheduled",
     "scheduler": "host_hygiene_tick",
     "restart_on_stale": false,
     "relaunch_if_down": false,
     "log": "/mnt/raid0/llm/epyc-root/logs/hygiene/opencode_event_reaper.log",
     "max_age_s": 3600
   }
   ```

   This satisfies both `observer_census.check_runtime_well_formed` and the tick's exact runtime
   predicate. Do not retain a hidden daemon restart command on a scheduled row.
3. **Host cron, activation last:** make a fresh private backup of the actual current crontab; verify
   its hub marker line still names the PIN00e supervisor path shown in the accepted excerpt. Add
   only `-e HYGIENE_OPENCODE_EVENTS=1` to that existing `docker exec` command. Preserve its
   `EPYC_ROOT`, `HUB_CANONICAL_ROOT`, `HUB_LAUNCH_MANIFEST`, redirect, cadence, exact PIN00e path,
   fleet-watch entry, and every unrelated line. Do not rerun the old `install_supervision_cron`
   apply helper: it rewrites the selected lines without the opt-in. This cron env is inherited by
   the detached hygiene tick through `run_hygiene_tick`.

The exact before/after selected lines are in `cron-optin.diff`; the exact registry runtime hunk is
in `registry-runtime.patch`. No full raw crontab is included.

## Owner-boundary stop and acceptance sequence (commands are inert)

At the reaper owner's boundary, first capture the then-current PID from
`/mnt/raid0/llm/tmp/opencode-reaper.pid` inside `epyc-root`; validate it is a positive decimal and
that `/proc/<pid>/cmdline` identifies exactly the canonical reaper script with trailing `run`.
Capture `/proc/<pid>/stat` start-time and cmdline before `pidfd_open`; open the pidfd, then
reread start-time and cmdline and require both to match before signaling. The pidfd pins that
process against PID reuse; it does not expose or recheck argv. Send SIGTERM through the pidfd and
verify termination (pidfd readable plus `ps -p <captured PID>` shows no live process). If it remains alive after a bounded SIGTERM wait, the owning session must escalate SIGKILL through that same identity-bound pidfd and verify death; a refusal or remaining live process aborts activation. Never use `pkill`, `pgrep`, name patterns,
shell substring matches, a stale acceptance PID, or a PID not captured and identity-checked by the
owning session. If multiple reaper copies or unreadable `/proc` entries are found, stop the handover.

After stop verification and file preflights, install reaper source, then registry, and change the
existing cron line last. The existing once-status lock excludes overlapping new invocations; it
does **not** atomically exclude the old daemon, which is why the owner stop is first. The event
preflight itself has a scan/start race, only checks the first three argv entries, and wrappers or
changed argv can escape it. The timeout is 900 s and does not prove descendant cancellation; an
inherited lock descriptor may outlive the timed-out child.

Do not force a tick or run `once-status` manually. Let the existing host cadence and CPU gate
produce the first attempt. A hygiene heartbeat alone is not evidence that the event duty ran.
Accept the first duty only from the terminal `LR8_ONCE_STATUS_V1` result plus
`opencode_event_result.json` and a fresh successful `opencode_event_reaper.log`; confirm the
registry census reports `scheduled_current`. `present` or `absent` with prune status 0 are valid;
`failed`/`unobservable` must raise the `opencode-event-duty` alarm. A busy CPU gate defers without
consuming the 1800 s cadence. Once-status retains the existing event-only prune and absent-only
VACUUM behavior; this preparation runs neither and authorizes no DB action now.

The old standalone `observer_guard` breadcrumb, if present at
`logs/observer_alerts/opencode_event_reaper.json`, is separate from the new alarm key. Inspect it
and reconcile it only after a successful first scheduled result; do not erase it as part of source
deployment.

## Rollback to A

Disable the `HYGIENE_OPENCODE_EVENTS=1` cron env first, using a new exact crontab backup and
preserving PIN00e and every unrelated line. Allow any in-flight once-status invocation to finish;
verify its recorded state and do not kill by pattern. Restore the canonical reaper preimage and
accepted registry preimage from the exclusive backups, after verifying backup hashes and current
file identities. The restored registry returns the old keeper contract; the next ordinary tick
may relaunch the reaper under its existing rate limit. Do not launch a second daemon manually.
Keep all backups and acceptance records. Never use the OP-73 original installer package to
overwrite a changed baseline.

## Remaining external gate

This package cannot identify or stop the live daemon owner from historical acceptance evidence.
The named dependency is the owning session reaching a boundary at which it can capture and verify
its own reaper PID. If no owning session can take that boundary, remain in A and route the exact
handover package to that session; this is not a reason to ask the operator to repeat OP-73 choice
2A. No NIB2-88 post-restart claim is made by this package.


MAIN review 2026-10-06: full candidate independently reopens exact native registry preimage and changes only one runtime object. Current tick source includes the accepted optional native-heartbeat callback (81 hosted controls); event-duty conformance is the separate accepted88-case receipt. No extra combined run or operational deployment claim. Current PID/crontab ownership must be acquired at the actual owner boundary; historical IDs are not instructions to stop a process.
