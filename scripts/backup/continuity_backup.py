#!/usr/bin/env python3
"""Utilities for F4 continuity backup validation.

Implements manifest validation and restore verification:
- manifest parse/checks for expected shape and path references
- restore-path proof by copying selected backup files into a temp dir and
  comparing checksums against live source
- parse validation for JSON/YAML and integrity checks for SQLite files

Usage:
  python3 scripts/backup/continuity_backup.py validate --manifest scripts/backup/MANIFEST.yaml
  python3 scripts/backup/continuity_backup.py verify-restore --snapshot-root /path/to/snapshot
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
from collections import defaultdict
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - environment specific
    raise SystemExit("PyYAML is required (python3 -m pip install pyyaml): " + str(exc))


DEFAULT_MANIFEST = Path(__file__).resolve().parent / "MANIFEST.yaml"
VALID_TIERS = {"T0_irreplaceable", "T1_regenerable_expensive", "T2_excluded_or_redownloadable"}
VALID_COPY_MODES = {"file", "sqlite_or_file"}


@dataclass(frozen=True)
class BackupCheckResult:
    errors: list[str]
    warnings: list[str]
    files: list[Path]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="F4 continuity-backup helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate MANIFEST structure and path references")
    validate_parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST,
        help="path to continuity backup manifest",
    )
    validate_parser.add_argument(
        "--warn-on-missing",
        action="store_true",
        help="emit missing path patterns as warnings instead of hard errors",
        default=True,
    )

    verify_parser = subparsers.add_parser(
        "verify-restore",
        help="restore snapshot paths to temp dir and checksum/parse-validate them",
    )
    verify_parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST,
        help="path to continuity backup manifest",
    )
    verify_parser.add_argument(
        "--snapshot-root",
        required=True,
        help="root of the backup snapshot to verify",
    )
    verify_parser.add_argument(
        "--restore-root",
        help="explicit restore destination; if omitted a temp dir is used",
    )
    verify_parser.add_argument(
        "--tiers",
        default="T0_irreplaceable",
        help="comma-separated tier names to verify (default: T0_irreplaceable)",
    )
    verify_parser.add_argument(
        "--max-age-days",
        type=int,
        help="fail if snapshot is older than this many days",
    )
    verify_parser.add_argument(
        "--skip-json-yaml",
        action="store_true",
        help="skip JSON/YAML parsing validation",
    )
    verify_parser.add_argument(
        "--skip-sqlite",
        action="store_true",
        help="skip SQLite integrity checks",
    )
    verify_parser.add_argument(
        "--report-json",
        help="write JSON summary report to this path",
    )
    return parser.parse_args()


def load_manifest(manifest_path: Path) -> dict[str, object]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest missing: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"manifest must map top-level object, got {type(data).__name__}")
    return data


def _is_wildcard(pattern: str) -> bool:
    return any(ch in pattern for ch in ["*", "?", "[", "]"])


def _expand_pattern(repo_root: Path, pattern: str, *, tolerate_missing: bool) -> list[Path]:
    """Expand one manifest path pattern relative to repo_root.

    Literal directory paths expand recursively to all files below that directory.
    Literal files expand to that file only.
    Glob paths are glob-expanded and files + nested dir contents are included.
    """
    if os.path.isabs(pattern):
        base = Path(pattern)
    else:
        base = repo_root / pattern

    expanded: list[Path] = []
    if not _is_wildcard(pattern):
        if not base.exists():
            if not tolerate_missing:
                return []
            return []
        if base.is_file():
            return [base]
        if base.is_dir():
            return [p for p in base.rglob("*") if p.is_file()]
        return [base]

    if os.path.isabs(pattern):
        matches = [Path(p) for p in glob.glob(pattern, recursive=True)]
    else:
        matches = [p for p in repo_root.glob(pattern)]
        matches = [p for match in matches for p in ([match] if match.is_file() else [match])]

    files: list[Path] = []
    for match in matches:
        if match.is_file():
            files.append(match)
        elif match.is_dir():
            files.extend([p for p in match.rglob("*") if p.is_file()])
    return sorted(set(files))


def validate_manifest(manifest_path: Path, *, warn_on_missing: bool = False) -> BackupCheckResult:
    errors: list[str] = []
    warnings: list[str] = []
    matched_files: list[Path] = []

    try:
        data = load_manifest(manifest_path)
    except (TypeError, FileNotFoundError, yaml.YAMLError) as exc:
        return BackupCheckResult([str(exc)], [], [])

    repos = data.get("repos")
    tiers = data.get("tiers")
    if not isinstance(repos, dict):
        errors.append("missing/invalid top-level key: repos")
    if not isinstance(tiers, dict):
        errors.append("missing/invalid top-level key: tiers")

    if not isinstance(data.get("validation"), dict):
        warnings.append("top-level `validation` section is optional; currently absent or invalid")

    if isinstance(repos, dict):
        for name, repo_path in repos.items():
            if not isinstance(name, str) or not isinstance(repo_path, str):
                errors.append(f"repos.{name!r}: name/path must be strings")
                continue
            repo = Path(repo_path)
            if not repo.is_absolute():
                errors.append(f"repos.{name}: path must be absolute, got {repo}")
            if not repo.exists():
                errors.append(f"repos.{name}: path does not exist: {repo}")
            elif not repo.is_dir():
                errors.append(f"repos.{name}: path is not a directory: {repo}")

    if isinstance(tiers, dict):
        for tier_name, entries in tiers.items():
            if not isinstance(tier_name, str):
                errors.append("non-string tier name in tiers section")
                continue
            if tier_name not in VALID_TIERS:
                warnings.append(f"unrecognized tier name: {tier_name}")
            if not isinstance(entries, list):
                errors.append(f"tiers.{tier_name}: expected list, got {type(entries).__name__}")
                continue
            for idx, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    errors.append(f"tiers.{tier_name}[{idx}]: entry is not a mapping")
                    continue
                repo_name = entry.get("repo")
                has_repo = isinstance(repo_name, str) and bool(repo_name)
                if not has_repo:
                    # Legacy/excluded tiers may use absolute path patterns directly.
                    repo_name = ""
                copy_mode = entry.get("copy_mode", "file")
                if copy_mode not in VALID_COPY_MODES:
                    warnings.append(
                        f"tiers.{tier_name}[{idx}] copy_mode={copy_mode!r} not recognized; expected one of {sorted(VALID_COPY_MODES)}"
                    )

                paths = entry.get("paths")
                if not isinstance(paths, list) or not paths:
                    errors.append(f"tiers.{tier_name}[{idx}]: missing/invalid paths list")
                    continue
                for path_pattern in paths:
                    if not isinstance(path_pattern, str):
                        errors.append(f"tiers.{tier_name}[{idx}].path: pattern not string: {path_pattern!r}")
                        continue

                    if has_repo:
                        if not isinstance(repos, dict) or repo_name not in repos:
                            warnings.append(
                                f"tiers.{tier_name}[{idx}] repo '{repo_name}' has no matching entry in repos map"
                            )
                            continue
                        expanded = _expand_pattern(Path(repos[repo_name]), path_pattern, tolerate_missing=True)
                    elif os.path.isabs(path_pattern):
                        expanded = _expand_pattern(Path("/"), path_pattern, tolerate_missing=True)
                    else:
                        if not isinstance(repos, dict) or not repos:
                            errors.append(f"tiers.{tier_name}[{idx}] entry has no repo for relative path: {path_pattern}")
                            continue
                        expanded = []
                        for repo_path in repos.values():
                            if not isinstance(repo_path, str):
                                continue
                            expanded.extend(_expand_pattern(Path(repo_path), path_pattern, tolerate_missing=True))

                    if not expanded:
                        msg = (
                            f"no files matched for {repo_name if repo_name else '[absolute]'}:{path_pattern}"
                        )
                        if warn_on_missing:
                            warnings.append(msg)
                        else:
                            errors.append(msg)
                    matched_files.extend(expanded)

    return BackupCheckResult(errors=errors, warnings=warnings, files=matched_files)


def file_checksum(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_json_yaml(path: Path) -> bool:
    ext = path.suffix.lower()
    try:
        if ext == ".json":
            with path.open("r", encoding="utf-8") as handle:
                json.load(handle)
        else:
            with path.open("r", encoding="utf-8") as handle:
                yaml.safe_load(handle)
        return True
    except (OSError, ValueError, yaml.YAMLError):
        return False


def validate_sqlite(path: Path) -> bool:
    try:
        conn = sqlite3.connect(str(path))
    except (sqlite3.DatabaseError, OSError):
        return False
    try:
        with conn:
            row = conn.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError:
        return False
    finally:
        conn.close()
    return bool(row and row[0] == "ok")


def _copy_file_for_restore(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_symlink():
        target = os.readlink(src)
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        os.symlink(target, dst)
        return
    shutil.copy2(src, dst)


def _snapshot_tier_entries(manifest: dict[str, object], tiers: set[str]) -> dict[str, list[dict[str, object]]]:
    tiers_map = manifest.get("tiers")
    if not isinstance(tiers_map, dict):
        return {}
    return {
        tier_name: [entry for entry in entries if isinstance(entry, dict)]
        for tier_name, entries in tiers_map.items()
        if tier_name in tiers and isinstance(entries, list)
    }


def _collect_selected_files(
    manifest: dict[str, object],
    tiers: set[str],
    *,
    warn_on_missing: bool = True,
) -> dict[tuple[str, Path], list[Path]]:
    repos = manifest.get("repos")
    if not isinstance(repos, dict):
        raise ValueError("manifest missing repos map")

    collected: dict[tuple[str, Path], list[Path]] = {}
    for tier_name, entries in _snapshot_tier_entries(manifest, tiers).items():
        for entry in entries:
            repo_name = entry.get("repo")
            has_repo = isinstance(repo_name, str) and bool(repo_name)
            if not has_repo:
                # Excluded tiers without repos are not restored by the current snapshot contract.
                continue
            repo_path = repos.get(repo_name)
            if not isinstance(repo_path, str):
                continue
            repo_root = Path(repo_path)
            if not repo_root.is_absolute():
                continue
            paths = entry.get("paths")
            if not isinstance(paths, list):
                continue
            for path_pattern in paths:
                if not isinstance(path_pattern, str):
                    continue
                expanded = _expand_pattern(
                    repo_root,
                    path_pattern,
                    tolerate_missing=warn_on_missing,
                )
                if expanded:
                    collected[(repo_name, Path(path_pattern))] = expanded
    return collected


def _snapshot_repo_dir(snapshot_root: Path, repo_name: str) -> Path:
    return snapshot_root / repo_name


def _check_age(snapshot_root: Path, max_age_days: int | None) -> list[str]:
    if max_age_days is None:
        return []
    errors: list[str] = []
    age_seconds = (datetime.now(tz=timezone.utc) - datetime.fromtimestamp(snapshot_root.stat().st_mtime, tz=timezone.utc)).total_seconds()
    if age_seconds > max_age_days * 24 * 3600:
        errors.append(
            f"snapshot exceeds max age: age={age_seconds / 86400:.1f} days, limit={max_age_days} days"
        )
    return errors


def verify_restore(
    manifest_path: Path,
    snapshot_root: Path,
    *,
    restore_root: str | None = None,
    tier_csv: str = "T0_irreplaceable",
    max_age_days: int | None = None,
    skip_json_yaml: bool = False,
    skip_sqlite: bool = False,
    report_json: str | None = None,
) -> tuple[int, list[str]]:
    try:
        manifest = load_manifest(manifest_path)
    except (TypeError, FileNotFoundError, yaml.YAMLError) as exc:
        return 1, [f"manifest error: {exc}"]

    validate = validate_manifest(manifest_path, warn_on_missing=True)
    if validate.errors:
        return 1, ["manifest invalid"] + validate.errors

    errors: list[str] = []
    errors.extend(_check_age(snapshot_root, max_age_days))

    selected_tiers = {tier.strip() for tier in tier_csv.split(",") if tier.strip()}
    if not selected_tiers:
        return 1, ["no tiers selected"]

    if not snapshot_root.exists():
        return 1, [f"snapshot root missing: {snapshot_root}"]

    if not snapshot_root.is_dir():
        return 1, [f"snapshot root is not a directory: {snapshot_root}"]

    repos = manifest.get("repos")
    if not isinstance(repos, dict) or not repos:
        return 1, ["manifest repos map missing/empty"]

    # Prepare restore target.
    cleanup_temp = False
    restore_base = Path(restore_root) if restore_root else None
    if restore_base is None:
        restore_base = Path(tempfile.mkdtemp(prefix="epyc-f4-restore-"))
        cleanup_temp = True
    else:
        restore_base = restore_base.resolve()
        restore_base.mkdir(parents=True, exist_ok=True)

    metrics = defaultdict(int)

    collected = _collect_selected_files(manifest, selected_tiers)
    if not collected:
        if cleanup_temp:
            shutil.rmtree(restore_base, ignore_errors=True)
        return 1, [f"no files selected for tiers {sorted(selected_tiers)}"]

    try:
        for (repo_name, pattern), sources in collected.items():
            del pattern
            repo_root = Path(cast(str, repos[repo_name]))
            snap_repo = _snapshot_repo_dir(snapshot_root, repo_name)
            if not snap_repo.is_dir():
                errors.append(f"snapshot repo dir missing for {repo_name}: {snap_repo}")
                continue

            for source in sources:
                rel_path = source.relative_to(repo_root)
                snapshot_file = snap_repo / rel_path
                restore_file = restore_base / repo_name / rel_path

                if not snapshot_file.is_file():
                    errors.append(f"snapshot miss: {snapshot_file}")
                    continue

                _copy_file_for_restore(snapshot_file, restore_file)
                metrics["files_copied"] += 1

                try:
                    src_hash = file_checksum(source)
                    restore_hash = file_checksum(restore_file)
                except OSError as exc:
                    errors.append(f"checksum_error: {source} -> {exc}")
                    continue
                if src_hash != restore_hash:
                    errors.append(
                        f"checksum_mismatch: {source} (snapshot restored copy differs from source)"
                    )
                    continue

                metrics["files_checked"] += 1

                if source.suffix.lower() in {".json", ".yaml", ".yml"} and not skip_json_yaml:
                    if not validate_json_yaml(restore_file):
                        errors.append(f"parse_failed: {restore_file}")
                        continue
                    metrics["files_parsed"] += 1

                if source.suffix.lower() in {".db", ".sqlite", ".sqlite3"} and not skip_sqlite:
                    if not validate_sqlite(restore_file):
                        errors.append(f"sqlite_check_failed: {restore_file}")
                        continue
                    metrics["sqlite_checked"] += 1

                metrics["files_ok"] += 1
    finally:
        if cleanup_temp:
            shutil.rmtree(restore_base, ignore_errors=True)

    total_files = metrics["files_checked"]
    summary = [
        f"tiers={sorted(selected_tiers)}",
        f"files_copied={metrics['files_copied']}",
        f"files_checked={total_files}",
        f"files_ok={metrics['files_ok']}",
        f"files_parsed={metrics['files_parsed']}",
        f"sqlite_checked={metrics['sqlite_checked']}",
    ]
    if report_json:
        with Path(report_json).open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "manifest": str(manifest_path),
                    "snapshot_root": str(snapshot_root),
                    "restore_root": str(restore_base),
                    "selected_tiers": sorted(selected_tiers),
                    "errors": errors,
                    "summary": dict(metrics),
                },
                handle,
                indent=2,
                sort_keys=True,
            )

    if errors:
        return 1, summary + ["errors:"] + errors
    return 0, summary


def main() -> int:
    args = parse_args()

    if args.command == "validate":
        result = validate_manifest(Path(args.manifest), warn_on_missing=args.warn_on_missing)
        print(f"manifest: {args.manifest}")
        if result.warnings:
            print("warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
        print(f"files_matched={len(result.files)}")
        if result.errors:
            print("errors:")
            for error in result.errors:
                print(f"  - {error}")
            return 1
        print("validation: ok")
        return 0

    if args.command == "verify-restore":
        exit_code, lines = verify_restore(
            manifest_path=Path(args.manifest),
            snapshot_root=Path(args.snapshot_root),
            restore_root=args.restore_root,
            tier_csv=args.tiers,
            max_age_days=args.max_age_days,
            skip_json_yaml=args.skip_json_yaml,
            skip_sqlite=args.skip_sqlite,
            report_json=args.report_json,
        )
        for line in lines:
            print(line)
        return exit_code

    raise AssertionError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
