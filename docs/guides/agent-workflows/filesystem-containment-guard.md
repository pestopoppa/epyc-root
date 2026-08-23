# Filesystem Containment Guard

The mechanical enforcement of the operator directive **"do not touch anything
outside `/mnt/raid0/llm/`"** — the guard that did not exist when it was needed
(INC-20260823-filesystem-containment-gap, 2026-08-23): an agent ran
`sudo -n mkdir -p /mnt/bigdisk && sudo -n mount /dev/sdb1 /mnt/bigdisk`,
planned writes to `/mnt/bigdisk/epyc-backup/`, and `sudo apt-get install restic`.
Nothing stopped it — the Claude Bash surface had no guard, and the opencode
surface had no permissions and no plugins.

## The one shared implementation

`scripts/hooks/filesystem_containment_scan.py` is the ONLY place the policy
lives (the repo rule, RTG-52: never a fifth parser). It reuses
`shell_scan.segments()` and exposes a CLI used identically by both surfaces:

| Surface | Wrapper | When it runs |
|---|---|---|
| Claude Code | `scripts/hooks/check_filesystem_containment.sh`, registered in `.claude/settings.json` under PreToolUse → Bash | every Bash tool call |
| opencode | `.opencode/plugins/filesystem-containment.ts` (project, `/workspace`) + `~/.config/opencode/plugins/filesystem-containment.ts` (global — covers lane worktrees, which have no `.opencode/` of their own) | every `bash` tool call |

Both call: `python3 scripts/hooks/filesystem_containment_scan.py --command "<cmd>"`.
Exit `0` = allowed; `2` = refused (message on stderr, JSON verdict on stdout).

## Policy, in one paragraph each

- **CLASS A — privileged host-level operations, operator-only**: `mount`,
  `umount`, `mkfs*`, `fdisk`, `parted`, `mkswap`, `systemctl`, `modprobe`,
  `shutdown`, `reboot`, `apt`/`apt-get`/`dpkg` install/remove/purge, `dd`
  `of=/dev/*` (except `/dev/null`). Refused with or without `sudo`.
- **CLASS B — writes outside the containment root**: `mkdir`, `touch`, `cp`,
  `mv`, `tee`, `dd of=`, `>`/`>>` redirection, `rsync`, `tar -C`/`--directory`,
  `restic backup|init --repo`, `borg create|init`, `rclone` write verbs,
  `chown`/`chmod`, plus same-class siblings `ln`, `install`, `rm`/`rmdir`,
  `git clone|init|worktree add`. Containment set: `/mnt/raid0/llm/**`,
  `/workspace/**`, `/tmp/opencode/**`, `~/.claude/**`, `~/.codex/**`. Bare
  `/tmp/**` writes are tolerated (ephemeral scratch; CLASS A still applies
  everywhere). Everything else — `/mnt/bigdisk`, `/opt`, `/etc`, `/usr`,
  `/var`, `/media`, `/home/*` outside the config dirs — is refused.
- **Unresolvable targets fail closed**: a quoted or `$VAR`-expanded target
  (other than `~`/`$HOME`) is refused with `unresolvable_target`, never
  guessed at. `cd` is tracked across chained commands, so
  `cd /mnt/bigdisk && mkdir -p x` is caught.

## Operator overrides — visible in the record, never silent

1. **One-off (both classes)**: set in the environment of the Bash tool call
   `EPYC_FS_ACK="operator: <who> <date>: <reason>"`. Read from the hook/plugin
   process environment ONLY — a command cannot self-authorize by writing the
   ack into its own text. In the opencode surface the env is the opencode
   server's, which a shell `export` cannot reach; in the Claude surface it
   mirrors the ratified D9 env-ack model.
2. **Permanent (CLASS B paths only)**: an entry in
   `scripts/hooks/filesystem_allowlist.yaml` (schema
   `session_bus.filesystem_allowlist.v1`):

   ```yaml
   entries:
     - path: /mnt/bigdisk/epyc-backup
       reason: operator-approved backup target
       added_by: <operator>
       added_on: 2026-08-23
   ```

   A path entry is a prefix (covers everything beneath it). CLASS A NEVER
   opens via the allowlist. If the allowlist is missing or unparseable the
   guard FAILS CLOSED (`allowlist_unavailable`).

## Known scope limits

The guard sees the command an agent TYPES. Daemons, cron, and scripts that
internally shell out are invisible to it (OS-level enforcement is the layer
for those); the inner command of `bash -c '...'` is quoted data and is not
scanned. Quoted/`$VAR` targets are refused rather than silently allowed.

## Restart requirement

opencode loads config and plugins at start. After changing the plugin,
`opencode.json`, or the global `opencode.jsonc`, **restart opencode** — the
running session will not pick the guard up.
