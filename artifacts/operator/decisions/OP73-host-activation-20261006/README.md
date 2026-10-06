# Approved OP-73 host activation package

Operator chose 2A on 2026-10-06: preview and install the host supervision cron. **Executed by the operator on the host; LR-6a accepted with first heartbeat 16:56:01 UTC.** [Independent acceptance and limits](acceptance/README.md). This container session prepared/reviewed the package and inspected retained records; it did not perform the host installation. The separate 1B scanner choice is resolved: both credential fixture files remain scanned.

## Host execution record

Installation is complete; do not repeat `--apply` against the changed registry baseline. The operator ran the following reviewed command as the host account that owns the supervision crontab, outside the container:

```bash
bash /mnt/raid0/llm/tmp/ni07-29-ci-recipe-20261006/dashboard-report/host-activation-20261006/run_host_activation.sh --apply
```

This repeats all preflights and prints the normal installer preview before mutation. To preview alone, use `--preview`. Afterwards, check the actual fresh hygiene heartbeat with:

```bash
bash /mnt/raid0/llm/tmp/ni07-29-ci-recipe-20261006/dashboard-report/host-activation-20261006/run_host_activation.sh --verify-activation
```

Verification exits four while a fresh heartbeat has not yet been observed. It does not force a tick, restart a daemon or wait for the next cron interval. The normal hygiene interval is 600 seconds; actual installation and heartbeat are distinct events. LR-6a was closed after the actual 2026-10-06 heartbeat; NIB2-88 separately requires genuinely observed post-restart reaper recovery.

The retained private launcher/helper are byte-identical to the copies in this directory. Source pin is ROOT `00e1820bcd957e905797b3a1b9e4d9dc53a550b0`; the launcher imports missing commit objects from the retained MAIN private worktree without checkout, ref reset or staging. Default preview may create private plan/log files and Git objects, but does not mutate canonical registry or crontab. The normal installer uses a fixed pin and backs up the existing crontab.

## Required registry dependency

The live canonical root is an older dirty checkout; its registry path itself was independently verified tracked, unstaged and clean. The read-only hub view supplies the current hygiene tick, but that tick reads registry/census/alarm/reaper state from the canonical root. Re-pinning the supervisor alone would therefore omit the approved reaper keeper and hygiene observer.

The package deploys only the already-published `opencode_event_reaper.runtime.relaunch_if_down` and explanatory note, plus the exact `host_hygiene_tick` scheduled observer row. Every other existing row/top-level field is preserved; the unrelated Codex retention row is deliberately not copied. The registry helper runs as its node owner through the explicit host-parent launcher, refuses dirty/staged or changed baseline content and symlinks, takes a backup and preserves mode/ownership. It performs repeated baseline/inode checks followed by an atomic file replacement, not an atomic compare-and-swap guarantee. No other shared file, branch or index is updated.

If preflight refuses source drift or a different owner, retain the refusal and have the owning session reconcile that exact dependency; do not bypass guards or reset the shared clone. A failed or interrupted installer after the registry deployment may leave the recorded registry update and backups in place; report that partial state, do not claim activation or rerun past a baseline refusal. Recovery must be reviewed against the saved backups and current host state.

## Review and evidence limits

[MAIN review](review.json) records source/byte binding and independent registry projection. Launcher SHA-256 `49ed734f89527f93a5afe569caf702ae95dd6de68eddc271663c6b077f092491`; helper SHA-256 `9a794584c497556f1ce0b75a465097621d73792ed456648f55ce1d156b1b9767`. Registry baseline `44ca416c2c802b871e6ed9b999aef1ff8f6bac09116845899b06dedef339e028`; exact projected result `8dfdabfc383585eb840cf2b6212cf15c739cd3cdf8553763ec123c5e78f1c35b`.

The first preparation draft was rejected for premature application, malformed state assignment, permissions and insufficient source/verification binding, then corrected under MAIN review. Static shell syntax, Python AST and independent pinned-JSON projection passed. No local tests, candidate/helper execution, host crontab command or process mutation was used for preparation. At preparation these files had no installed caller; the operator subsequently installed the pinned supervisor. Manual blast-radius review is MEDIUM and limited to the one registry projection and marker-owned supervision cron entries already required for approved option 2A. GitNexus remains untrusted under NI76.

Bootstrap runtime reports are ungraded operational receipts. Prospective belief-kernel wiring is surfaced in `VB-HOST-SUPERVISION-ACTIVATION`; no tuple, new grading ladder or read-side reconstruction is asserted by this package. No inference, kernel/server/reload, harness cleanup or bus-supervisor launch is authorized. The bus remains DOWN.
