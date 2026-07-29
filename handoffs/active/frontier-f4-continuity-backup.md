# Frontier F4 — Continuity: Backup the Evidence Base

**Status**: IN PROGRESS — W1 inventory/policy landed 2026-06-12; W2 snapshot job tooling + W3 validation/restore tooling landed 2026-06-14; latest-snapshot age/restore preflight landed 2026-06-21; first real backup remains blocked on a real off-RAID/off-host target
**Created**: 2026-06-12
**Priority**: HIGH — this-month, existential ROI at trivial effort
**Spec**: [fable5-findings-07-strategic-frontiers.md](../completed/fable5-findings-07-strategic-frontiers.md) §F4 — read before claiming
**Related**: MEASUREMENT.md §5 dump-list note (consolidate 1.2GB superseded blobs first); the ATTESTATION artifact in [fable5-findings-04-impl-plan.md](../completed/fable5-findings-04-impl-plan.md) §B (backup-age + unpushed-commit checks)

## Why

The entire evidence base — journals, state, registries, intake index, deep-dives,
episodic/strategy DBs, agent memory — lives on a single raid0 (striping, zero
redundancy) on a single host. GGUFs are re-downloadable; the lab's memory is not.
No backup policy exists anywhere in governance. The total irreplaceable set is
<2GB, so the fix is half-days of work against an existential failure mode.

## Waypoints

- [x] **W1 — inventory + policy** (half day): `scripts/backup/MANIFEST.yaml` with tiered list (T0 irreplaceable / T1 regenerable-expensive / T2 excluded models). Audit git coverage + unpushed branches (`v5 push pending` known); add unpushed-commit alert to ATTESTATION. Acceptance: manifest enumerates every T0 path per spec §F4-W1. Implementation: manifest plus `scripts/backup/audit_git_state.sh` alert hook for future ATTESTATION.
- [x] **W2a — target discovery/report packet**: `continuity_backup.py discover-targets` inspects explicit candidate roots or locally mounted filesystem roots, runs the same failure-domain checks as snapshot creation, writes a machine-readable report, and emits the exact backup + latest-restore-check commands when a usable target exists. ✅ 2026-07-06
- [ ] **W2 — the job** (half day): `scripts/backup/backup_critical.sh` — restic preferred (dedupe+encryption, open-source) or snapshot-copy fallback. Targets: root SSD (different failure domain) + one off-host target (operator picks). Nightly via nightshift scheduler or systemd timer. Acceptance: nightly run produces a verifiable snapshot of all T0 paths. **Tooling landed 2026-06-14, real run still blocked**: `backup_critical.sh` now creates a `verify_restore.sh`-compatible T0 snapshot layout and performs SQLite `.backup` copies, but refuses same-device and overlayfs targets. `/workspace` and `/mnt/raid0/llm` are both `/dev/md127`, no off-host target is configured, and `/tmp`/container overlayfs is explicitly rejected. Do not accept a fake same-array backup.
- [ ] **W3 — restore proof** (half day + quarterly): `scripts/backup/verify_restore.sh` — restore to temp dir, checksum-compare, parse-validate JSON/YAML/SQLite. Add backup-age check to ATTESTATION. Acceptance: one full restore cycle passes; check wired into attestation. **Tooling landed 2026-06-14**: `9eb3f45` adds manifest validation plus restore wrappers; `0a56b81` fixes restore checksum semantics to compare restored bytes against the snapshot, not mutable live sources. **Preflight landed 2026-06-21**: `scripts/backup/check_latest_backup.sh` wraps `continuity_backup.py check-latest` so attestation/nightshift can fail closed when no timestamped snapshot exists, when the newest snapshot exceeds `--max-age-days`, or when restore verification fails. Still unchecked until a real T0 snapshot from an approved backup target passes end-to-end.

## Gates & pitfalls

- Live SQLite (episodic.db is written continuously) must go through the `sqlite3 .backup` API or stop-copy — naive `cp` produces torn copies.
- A backup that has never been restored is a hypothesis, not a backup — W3 is not optional.
- Audit unpushed branches before trusting "it's in git" coverage; pushed history needs no file backup, unpushed does.
- Do NOT back up the 1.2GB superseded embedding blobs flagged in the reconciliation dump-list — consolidate those first.
- Off-host target must be open-source/self-hosted (external HDD / another box / MinIO) — no cloud SaaS.

## Reporting

On completion of each waypoint: tick here, one-line progress entry, update master index row. Move to `completed/` after W3's first quarterly verify passes.

## Checkpoints

- 2026-06-12 W1: created `scripts/backup/MANIFEST.yaml` and `scripts/backup/audit_git_state.sh`. Validation: YAML parse succeeded; scoped `git diff --check` clean; audit hook intentionally exits 1 with current alerts (dirty worktrees plus unpushed/no-upstream branches, including `epyc-root` `main` ahead of `origin/main` by 16 before this commit). Environment probe: `df/findmnt` shows `/workspace` and `/mnt/raid0/llm` are the same `/dev/md127` RAID0; `restic`/`borg`/`rclone` are not installed.
- 2026-06-14 W3 tooling: `9eb3f45` added `scripts/backup/continuity_backup.py`, `scripts/backup/validate_backup_manifest.sh`, and `scripts/backup/verify_restore.sh`; `0a56b81` corrected restore validation to checksum the snapshot file against the restored copy and added `tests/backup/test_continuity_backup.py`. Validation: `python3 -m py_compile scripts/backup/continuity_backup.py tests/backup/test_continuity_backup.py`; `uv run --with pytest --with pyyaml pytest -q tests/backup/test_continuity_backup.py tests/publication/test_generate_public_results.py` -> 7 passed; `uv run --with ruff ruff check ...` passed; `bash -n` wrappers passed; `bash scripts/backup/validate_backup_manifest.sh scripts/backup/MANIFEST.yaml` returned validation ok with expected missing-pattern warnings. W2 remains blocked on a real off-host/off-array target; W3 remains open until a full restore from a real snapshot passes.
- 2026-06-14 W2 guarded snapshot job: added `scripts/backup/backup_critical.sh` and `continuity_backup.py create-snapshot`. The job expands selected manifest tiers into `snapshot_root/<repo-name>/...`, writes `SNAPSHOT.json`, uses SQLite `.backup` for live database suffixes, and refuses targets that share source storage devices, sit inside source repos, or are Docker overlayfs. Validation: `python3 -m py_compile scripts/backup/continuity_backup.py tests/backup/test_continuity_backup.py`; `bash -n scripts/backup/backup_critical.sh scripts/backup/validate_backup_manifest.sh scripts/backup/verify_restore.sh`; `uv run --with pytest --with pyyaml pytest -q tests/backup/test_continuity_backup.py` -> 3 passed; `uv run --with ruff ruff check ...` passed; `bash scripts/backup/validate_backup_manifest.sh scripts/backup/MANIFEST.yaml` returned validation ok with expected missing-pattern warnings; live same-device probe to `/tmp/epyc-f4-same-device-check` refused overlayfs as expected. W2 remains unchecked until the job succeeds against a real off-array/off-host target and can be scheduled.
- 2026-06-21 W3 preflight hook: added `continuity_backup.py check-latest` and `scripts/backup/check_latest_backup.sh`. The command discovers the newest timestamped snapshot under a target root by `SNAPSHOT.json`, runs the normal restore verification on it, enforces `--max-age-days`, and writes an optional JSON report. Validation: `python3 -m py_compile scripts/backup/continuity_backup.py tests/backup/test_continuity_backup.py`; `bash -n scripts/backup/backup_critical.sh scripts/backup/validate_backup_manifest.sh scripts/backup/verify_restore.sh scripts/backup/check_latest_backup.sh`; `uv run --with ruff ruff check scripts/backup/continuity_backup.py tests/backup/test_continuity_backup.py`; `uv run --with pytest --with pyyaml pytest -q tests/backup/test_continuity_backup.py` -> 7 passed; `bash scripts/backup/validate_backup_manifest.sh scripts/backup/MANIFEST.yaml` returned validation ok with expected missing-pattern warnings; no-snapshot CLI smoke failed closed. This does not satisfy W2/W3 by itself because no approved off-array/off-host target has produced a real snapshot.
- 2026-06-27 target recheck: manifest validation still passes
  (`files_matched=170240`, expected missing-pattern warnings only), but no
  acceptable real target is currently writable. `/mnt/raid0/llm` and
  `/workspace` remain `/dev/md127`; `/opt/AMD` is a different ext4 device
  (`/dev/sda2`) but is mounted read-only; `/dev/sdb1` and `/dev/nvme0n1` are
  visible but unmounted with no filesystem shown by `lsblk`. Do not claim W2
  or W3 from a same-array, overlayfs, tmpfs, or read-only target. Next valid
  action is to mount/provide an operator-approved writable off-array/off-host
  target, then run `scripts/backup/backup_critical.sh` followed by
  `scripts/backup/verify_restore.sh`.
- 2026-07-06 preflight/reporting lane: added `continuity_backup.py preflight-target`
  for dry target checks that report `target_exists`, `target_is_dir`,
  `target_writable`, selected tiers/repos, and machine-readable failure reasons
  without creating a snapshot. Validation: `python3 -m py_compile
  scripts/backup/continuity_backup.py tests/backup/test_continuity_backup.py`;
  `uv run --with pytest --with pyyaml pytest -q tests/backup/test_continuity_backup.py`
  -> `10 passed`; `uv run --with ruff ruff check scripts/backup/continuity_backup.py
  tests/backup/test_continuity_backup.py` passed. W2/W3 remain blocked until an
  operator-approved off-array/off-host target is mounted and a real snapshot
  can be created and restored.
- 2026-07-06 target discovery lane: added `continuity_backup.py discover-targets`
  for read-only enumeration of explicit candidates and mounted filesystem roots.
  The command reuses the preflight/failure-domain logic, writes a JSON report
  with per-candidate errors and `usable_count`, and prints the exact
  `backup_critical.sh` / `check_latest_backup.sh` commands once a target passes.
  Validation: `python3 -m py_compile scripts/backup/continuity_backup.py
  tests/backup/test_continuity_backup.py`; `uv run --with pytest --with pyyaml
  pytest -q tests/backup/test_continuity_backup.py` -> `12 passed`; `uv run
  --with ruff ruff check scripts/backup/continuity_backup.py
  tests/backup/test_continuity_backup.py` passed. Live discovery through
  `uv run --with pyyaml python scripts/backup/continuity_backup.py
  discover-targets --include-mounted-roots --max-candidates 16 --report-json
  /tmp/epyc-f4-discover-targets.json` found `9` mounted candidates and
  `usable_count=0`: RAID0-backed paths share `/dev/md127`, `/` is overlayfs and
  not writable, and `/opt/AMD`/`/opt/rocm` are different storage but read-only
  in the container. W2/W3 still require an operator-approved writable off-array
  or off-host target.
