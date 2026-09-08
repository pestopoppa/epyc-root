#!/usr/bin/env python3
"""List source files for wiki compilation.

Scans knowledge streams (handoffs, progress logs, deep-dives, docs) and
outputs a JSON manifest of files that need to be compiled into wiki articles.
Incremental selection is a content-hash diff against the tracked source
manifest (wiki/source_manifest.json — the one shared watermark): a source is
new when its path is absent from the manifest and changed when its content
hash differs. Filesystem mtimes are never used for the watermark, so the
scan answers identically from any worktree of the repo; lane worktrees carry
checkout-time mtimes that made mtime-based scans report the entire repo
(measured 908 vs a true delta of 17, and 942 vs 4). A missing tracked
manifest means nothing is recorded compiled yet: the first incremental run
emits the full source set once. --touch regenerates the tracked manifest
from the current source set after the reported delta has been compiled, so
the next incremental run reports nothing; the manifest is tracked, so a lane
--touch records the same content hashes a shared-clone --touch would.

Adapted for epyc-root's flat directory layout (no per-user nesting).

Usage (run with the orchestrator venv interpreter — PyYAML is required):
    /workspace/repos/epyc-orchestrator/.venv/bin/python compile_sources.py  # incremental (content-hash diff vs tracked manifest)
    /workspace/repos/epyc-orchestrator/.venv/bin/python compile_sources.py --full  # all sources regardless of the baseline
    /workspace/repos/epyc-orchestrator/.venv/bin/python compile_sources.py --touch  # advance the tracked manifest + .last_compile after compiling the delta
    /workspace/repos/epyc-orchestrator/.venv/bin/python compile_sources.py --type research  # filter by source type
    /workspace/repos/epyc-orchestrator/.venv/bin/python compile_sources.py --since 2026-04-01  # explicit mtime since-date override (not the default selection)
    /workspace/repos/epyc-orchestrator/.venv/bin/python compile_sources.py --full --write-manifest
    /workspace/repos/epyc-orchestrator/.venv/bin/python compile_sources.py --check-manifest
    /workspace/repos/epyc-orchestrator/.venv/bin/python compile_sources.py --changed-since-manifest
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def _find_project_root() -> Path:
    """Walk up from this file to find project root (contains wiki.yaml or .git)."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "wiki.yaml").exists() or (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return Path(__file__).resolve().parents[4]


ROOT = _find_project_root()
MANIFEST_SCHEMA_VERSION = 1
MANIFEST_KIND = "project-wiki-source-manifest"
WRITER_EVIDENCE_POLICY_VERSION = 1
WRITER_EVIDENCE_POLICY = {
    "policy_version": WRITER_EVIDENCE_POLICY_VERSION,
    "applies_to": "generated-wiki-article-writes",
    "minimum_confidence": "verified",
    "minimum_source_references": 3,
    "requires_source_reference_section": True,
    "requires_structural_lint": True,
    "requires_human_or_measured_review": True,
}


def load_config() -> dict:
    """Load compile config from wiki.yaml, with sensible defaults."""
    config_path = ROOT / "wiki.yaml"
    defaults = {
        "output_dir": "wiki",
        "last_compile": "wiki/.last_compile",
        "source_manifest": "wiki/source_manifest.json",
        "skip_filenames": ["INDEX.md", "README.md", "master-handoff-index.md"],
        "skip_patterns": ["*-index.md"],
        "source_dirs": [
            {"path": "handoffs/active", "type": "handoff-active", "recurse": False},
            {"path": "handoffs/completed", "type": "handoff-completed", "recurse": False},
            {"path": "handoffs/blocked", "type": "handoff-blocked", "recurse": False},
            {"path": "research/deep-dives", "type": "research", "recurse": False},
            {"path": "progress", "type": "progress", "recurse": True},
            {"path": "docs", "type": "docs", "recurse": True},
        ],
    }
    if not HAS_YAML or not config_path.exists():
        return defaults

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        compile_cfg = data.get("compile", {})
        for key, default_val in defaults.items():
            if key not in compile_cfg:
                compile_cfg[key] = default_val
        return compile_cfg
    except Exception:
        return defaults


CONFIG = load_config()
LAST_COMPILE_PATH = ROOT / CONFIG["last_compile"]
SOURCE_MANIFEST_PATH = ROOT / CONFIG.get("source_manifest", "wiki/source_manifest.json")
SKIP_FILENAMES = set(CONFIG["skip_filenames"])
SKIP_PATTERNS = CONFIG["skip_patterns"]


def should_skip(filename: str) -> bool:
    """Check if a filename should be skipped."""
    if filename in SKIP_FILENAMES:
        return True
    for pattern in SKIP_PATTERNS:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False


def get_last_compile() -> float:
    """Read .last_compile timestamp. Returns 0.0 if missing."""
    if not LAST_COMPILE_PATH.exists():
        return 0.0
    try:
        text = LAST_COMPILE_PATH.read_text().strip()
        if not text:
            return 0.0
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.timestamp()
    except (ValueError, OSError):
        return 0.0


def get_last_compile_iso() -> str | None:
    """Read .last_compile as ISO string, or None if missing."""
    if not LAST_COMPILE_PATH.exists():
        return None
    text = LAST_COMPILE_PATH.read_text().strip()
    return text if text else None


def touch_last_compile() -> None:
    """Write current UTC timestamp to .last_compile."""
    LAST_COMPILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    LAST_COMPILE_PATH.write_text(ts + "\n")


def extract_title(path: Path) -> str:
    """Extract first H1 heading from a markdown file, or return filename."""
    try:
        with open(path, errors="replace") as f:
            for line in f:
                m = re.match(r"^#\s+(.+)", line)
                if m:
                    return m.group(1).strip()
    except OSError:
        pass
    return path.stem


def file_sha256(path: Path) -> str:
    """Return a stable SHA-256 digest for source-file content."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_sources(since: float, type_filter: str | None) -> list[dict]:
    """Walk source directories and collect files newer than `since`."""
    seen: set[Path] = set()
    results: list[dict] = []

    for source_def in CONFIG["source_dirs"]:
        source_path = source_def["path"]
        source_type = source_def["type"]
        recurse = source_def.get("recurse", False)

        if type_filter and source_type != type_filter:
            continue

        base_path = ROOT / source_path
        if not base_path.exists():
            continue

        if recurse:
            md_files = sorted(base_path.rglob("*.md"))
        else:
            md_files = sorted(base_path.glob("*.md"))

        for md_file in md_files:
            if not md_file.is_file():
                continue
            if should_skip(md_file.name):
                continue

            resolved = md_file.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)

            mtime = md_file.stat().st_mtime
            if mtime <= since:
                continue

            results.append({
                "path": str(md_file.relative_to(ROOT)),
                "type": source_type,
                "modified": datetime.fromtimestamp(
                    mtime, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "size": md_file.stat().st_size,
                "content_hash": file_sha256(md_file),
                "title": extract_title(md_file),
            })

    return results


def source_set_hash(sources: list[dict]) -> str:
    """Hash the manifest's source membership and content hashes."""
    payload = [
        {
            "path": source.get("path"),
            "content_hash": source.get("content_hash"),
        }
        for source in sorted(sources, key=lambda item: str(item.get("path", "")))
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def source_index(sources: list[dict]) -> dict[str, dict]:
    """Return sources keyed by repository-relative path."""
    return {
        str(source["path"]): source
        for source in sources
        if isinstance(source, dict) and source.get("path")
    }


def diff_manifest_sources(saved_sources: list[dict], current_sources: list[dict]) -> dict:
    """Compare saved/current source lists using path + content hash."""
    saved_by_path = source_index(saved_sources)
    current_by_path = source_index(current_sources)
    saved_paths = set(saved_by_path)
    current_paths = set(current_by_path)

    added = sorted(current_paths - saved_paths)
    removed = sorted(saved_paths - current_paths)
    changed = sorted(
        path
        for path in saved_paths & current_paths
        if saved_by_path[path].get("content_hash")
        != current_by_path[path].get("content_hash")
    )

    return {
        "added": [current_by_path[path] for path in added],
        "changed": [current_by_path[path] for path in changed],
        "removed": [saved_by_path[path] for path in removed],
        "added_count": len(added),
        "changed_count": len(changed),
        "removed_count": len(removed),
        "has_drift": bool(added or changed or removed),
    }


def build_manifest(sources: list[dict], mode: str) -> dict:
    """Build the output manifest from collected sources."""
    by_type: dict[str, int] = {}
    for s in sources:
        by_type[s["type"]] = by_type.get(s["type"], 0) + 1

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "kind": MANIFEST_KIND,
        "last_compile": get_last_compile_iso(),
        "scan_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "sources": sources,
        "total_new": len(sources),
        "by_type": by_type,
        "source_set_hash": source_set_hash(sources),
        "writer_evidence_policy": dict(WRITER_EVIDENCE_POLICY),
    }


def read_manifest(path: Path) -> dict:
    """Read and validate a saved source manifest."""
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"manifest is not valid JSON: {path}") from exc

    if not isinstance(manifest, dict):
        raise ValueError(f"manifest root must be an object: {path}")
    if manifest.get("kind") != MANIFEST_KIND:
        raise ValueError(
            f"manifest kind must be {MANIFEST_KIND!r}: {manifest.get('kind')!r}"
        )
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            "manifest schema_version must be "
            f"{MANIFEST_SCHEMA_VERSION}: {manifest.get('schema_version')!r}"
        )
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        raise ValueError("manifest sources must be a list")
    return manifest


def validate_writer_evidence_policy(manifest: dict) -> list[str]:
    """Return policy errors that block model-written wiki article adoption."""
    policy = manifest.get("writer_evidence_policy")
    if not isinstance(policy, dict):
        return ["writer_evidence_policy missing"]

    errors: list[str] = []
    for key, expected in WRITER_EVIDENCE_POLICY.items():
        if policy.get(key) != expected:
            errors.append(
                "writer_evidence_policy "
                f"{key} must be {expected!r}, got {policy.get(key)!r}"
            )
    return errors


def write_manifest(path: Path, manifest: dict) -> None:
    """Persist a manifest as stable, reviewable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def full_current_manifest() -> dict:
    """Build a full manifest for drift comparison."""
    return build_manifest(scan_sources(0.0, None), "full")


def build_manifest_drift_report(saved_path: Path) -> dict:
    """Compare a saved source manifest to the current full source set."""
    saved = read_manifest(saved_path)
    current = full_current_manifest()
    drift = diff_manifest_sources(saved["sources"], current["sources"])
    policy_errors = validate_writer_evidence_policy(saved)
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "kind": "project-wiki-source-manifest-drift",
        "manifest_path": str(saved_path.relative_to(ROOT))
        if saved_path.is_relative_to(ROOT)
        else str(saved_path),
        "scan_time": current["scan_time"],
        "saved_source_set_hash": saved.get("source_set_hash"),
        "current_source_set_hash": current.get("source_set_hash"),
        "writer_evidence_policy_ok": not policy_errors,
        "writer_evidence_policy_errors": policy_errors,
        "ok": not drift["has_drift"] and not policy_errors,
        "drift": drift,
    }


def _baseline_display(path: Path) -> str:
    """Render a manifest path for display, repo-relative when possible."""
    if path.is_relative_to(ROOT):
        return str(path.relative_to(ROOT))
    return str(path)


def _drift_manifest(
    saved: dict,
    current: dict,
    type_filter: str | None,
    mode: str,
    baseline: str,
) -> dict:
    """Build the added/changed-source manifest from a saved/current diff.

    Selection is keyed on path + content hash only — never on mtime — so the
    result is identical from any worktree of the repo. Removed sources are
    carried for review but do not count toward ``total_new``.
    """
    drift = diff_manifest_sources(saved["sources"], current["sources"])
    changed_paths = {
        str(source["path"])
        for source in [*drift["added"], *drift["changed"]]
        if source.get("path")
    }
    selected = [
        source for source in current["sources"]
        if source.get("path") in changed_paths
        and (not type_filter or source.get("type") == type_filter)
    ]
    manifest = build_manifest(selected, mode)
    manifest["baseline_manifest"] = baseline
    manifest["baseline_source_set_hash"] = saved.get("source_set_hash")
    manifest["current_source_set_hash"] = current.get("source_set_hash")
    manifest["removed_sources"] = drift["removed"]
    manifest["removed_count"] = drift["removed_count"]
    manifest["drift"] = {
        "added_count": drift["added_count"],
        "changed_count": drift["changed_count"],
        "removed_count": drift["removed_count"],
        "has_drift": drift["has_drift"],
    }
    return manifest


def changed_sources_since_manifest(saved_path: Path) -> dict:
    """Build a manifest containing sources added/changed since saved_path."""
    saved = read_manifest(saved_path)
    return _drift_manifest(
        saved,
        full_current_manifest(),
        None,
        f"changed-since-manifest:{saved_path}",
        _baseline_display(saved_path),
    )


def incremental_since_tracked_manifest(type_filter: str | None = None) -> dict:
    """Diff the current source set against the tracked source manifest.

    This is the default incremental selection. The per-source content hashes
    stored in the manifest make the delta independent of checkout mtimes, so
    any worktree of the repo reports the same sources. Raises ValueError when
    the tracked manifest is missing — the caller falls back to a full
    baseline for that first-run state.
    """
    saved = read_manifest(SOURCE_MANIFEST_PATH)
    return _drift_manifest(
        saved,
        full_current_manifest(),
        type_filter,
        "incremental",
        _baseline_display(SOURCE_MANIFEST_PATH),
    )


def refresh_tracked_manifest() -> dict:
    """Regenerate the tracked manifest from the current source set.

    This is what ``--touch`` does: after the reported delta has been compiled
    into wiki pages, recording the current full set means the next
    incremental scan reports nothing. The manifest is the shared watermark —
    tracked, so it advances only when the change is committed, and identical
    content hashes are recorded whichever worktree the touch runs from.
    Refuses when no baseline manifest exists yet; establish one with
    ``--full --write-manifest`` first.
    """
    if not SOURCE_MANIFEST_PATH.exists():
        raise ValueError(
            f"no tracked baseline manifest at {SOURCE_MANIFEST_PATH}; "
            "run --full --write-manifest first (nothing is recorded compiled)"
        )
    touch_last_compile()
    full = build_manifest(scan_sources(0.0, None), "touch")
    write_manifest(SOURCE_MANIFEST_PATH, full)
    return full


def resolve_manifest_arg(value: str | None) -> Path:
    """Resolve optional manifest CLI arguments against the project root."""
    if not value:
        return SOURCE_MANIFEST_PATH
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List source files for wiki compilation."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Return all sources regardless of the tracked manifest baseline.",
    )
    parser.add_argument(
        "--touch",
        action="store_true",
        help=(
            "After compiling the reported delta, regenerate the tracked "
            "source manifest (and advance .last_compile) so the next "
            "incremental scan reports nothing."
        ),
    )
    parser.add_argument(
        "--type",
        dest="type_filter",
        help="Filter to a specific source type.",
    )
    parser.add_argument(
        "--since",
        help=(
            "Explicit mtime-based since-date (YYYY-MM-DD) override; the "
            "default selection is a content-hash diff, not mtimes."
        ),
    )
    parser.add_argument(
        "--write-manifest",
        nargs="?",
        const="",
        metavar="PATH",
        help=(
            "Write the emitted manifest to PATH, or to compile.source_manifest "
            "when PATH is omitted."
        ),
    )
    parser.add_argument(
        "--check-manifest",
        nargs="?",
        const="",
        metavar="PATH",
        help=(
            "Compare saved manifest at PATH, or compile.source_manifest when "
            "PATH is omitted, to the current full source set."
        ),
    )
    parser.add_argument(
        "--changed-since-manifest",
        nargs="?",
        const="",
        metavar="PATH",
        help=(
            "Emit only sources added/changed since saved manifest at PATH, or "
            "compile.source_manifest when PATH is omitted."
        ),
    )

    args = parser.parse_args()

    if args.check_manifest is not None and args.changed_since_manifest is not None:
        print(
            "ERROR: --check-manifest and --changed-since-manifest are mutually exclusive",
            file=sys.stderr,
        )
        return 1

    if args.check_manifest is not None:
        manifest_path = resolve_manifest_arg(args.check_manifest)
        try:
            report = build_manifest_drift_report(manifest_path)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        print()
        return 0 if report["ok"] else 1

    if args.changed_since_manifest is not None:
        manifest_path = resolve_manifest_arg(args.changed_since_manifest)
        try:
            manifest = changed_sources_since_manifest(manifest_path)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        json.dump(manifest, sys.stdout, indent=2, sort_keys=True)
        print()
        return 0

    if args.full:
        sources = scan_sources(0.0, args.type_filter)
        manifest = build_manifest(sources, "full")
    elif args.since:
        try:
            dt = datetime.strptime(args.since, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            print(f"ERROR: Invalid date format: {args.since} (expected YYYY-MM-DD)",
                  file=sys.stderr)
            return 1
        sources = scan_sources(dt.timestamp(), args.type_filter)
        manifest = build_manifest(sources, f"since:{args.since}")
    elif SOURCE_MANIFEST_PATH.exists():
        try:
            manifest = incremental_since_tracked_manifest(args.type_filter)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    else:
        print(
            f"NOTE: no tracked manifest at {SOURCE_MANIFEST_PATH} — nothing is "
            "recorded compiled yet; emitting the full source set once.",
            file=sys.stderr,
        )
        sources = scan_sources(0.0, args.type_filter)
        manifest = build_manifest(sources, "full")

    json.dump(manifest, sys.stdout, indent=2)
    print()

    if args.write_manifest is not None:
        target = resolve_manifest_arg(args.write_manifest)
        if target.resolve() == SOURCE_MANIFEST_PATH.resolve() and (
            manifest.get("mode") != "full"
        ):
            print(
                f"ERROR: refusing to overwrite the tracked baseline manifest "
                f"{SOURCE_MANIFEST_PATH} with a partial "
                f"({manifest.get('mode')}) scan; pass an explicit PATH or run "
                "--full --write-manifest.",
                file=sys.stderr,
            )
            return 1
        write_manifest(target, manifest)

    if args.touch:
        try:
            refreshed = refresh_tracked_manifest()
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(
            f"touch: regenerated {SOURCE_MANIFEST_PATH} from the current "
            f"source set ({len(refreshed['sources'])} sources) and advanced "
            f"{LAST_COMPILE_PATH}",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
