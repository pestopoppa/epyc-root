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

The compile timestamp lives ONLY in the tracked manifest's ``last_compile``
field (ISO-8601 UTC, ``YYYY-MM-DDTHH:MM:SSZ``). The former gitignored
``wiki/.last_compile`` watermark file is RETIRED (KB-WM-4, 2026-09-16): it
no longer drove selection, it had two writers with incompatible formats, and
a stale copy leaked verbatim into every emitted manifest. Nothing reads or
writes it; a leftover copy in a checkout is inert and may be deleted.

Adapted for epyc-root's flat directory layout (no per-user nesting).

Usage (run with the orchestrator venv interpreter — PyYAML is required):
    /workspace/repos/epyc-orchestrator/.venv/bin/python compile_sources.py  # incremental (content-hash diff vs tracked manifest)
    /workspace/repos/epyc-orchestrator/.venv/bin/python compile_sources.py --full  # all sources regardless of the baseline
    /workspace/repos/epyc-orchestrator/.venv/bin/python compile_sources.py --touch  # advance the tracked manifest (and its last_compile) after compiling the delta
    /workspace/repos/epyc-orchestrator/.venv/bin/python compile_sources.py --touch research --touch progress/2026-09  # scoped: advance only those entries (OP-34)
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
    if not config_path.exists():
        return defaults
    if not HAS_YAML:
        # OBS-12: silently using the defaults here diverges from wiki.yaml
        # (e.g. its extra skip_filenames), so refuse instead.
        raise RuntimeError(
            f"PyYAML is not installed in {sys.executable}, so {config_path} cannot be read. "
            f"Run with the orchestrator venv: /workspace/repos/epyc-orchestrator/.venv/bin/python .claude/skills/project-wiki/scripts/compile_sources.py"
        )

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
SOURCE_MANIFEST_PATH = ROOT / CONFIG.get("source_manifest", "wiki/source_manifest.json")
SKIP_FILENAMES = set(CONFIG["skip_filenames"])
SKIP_PATTERNS = CONFIG["skip_patterns"]


def in_linked_worktree() -> bool:
    """True when running from a `git worktree add` checkout rather than the canonical clone.

    In a linked worktree `.git` is a FILE containing a gitdir: pointer, not a directory.
    """
    try:
        return (ROOT / ".git").is_file()
    except OSError:
        return False


def warn_if_worktree_mtime_basis() -> None:
    """Incremental scanning compares file mtime against the watermark. `git worktree add`
    stamps EVERY checked-out file with the checkout instant, so from a linked worktree
    every source looks newer than any watermark and `total_new` is meaningless.

    Measured 2026-09-03: a real drift of 52 sources reported as 928 (18x), and 916 of the
    928 carried one identical mtime. Use content-hash comparison (`--check-manifest`)
    from a worktree; the mtime basis is only valid in the canonical clone.
    """
    if in_linked_worktree():
        print(
            "WARNING: running from a linked git worktree — every file carries the checkout "
            "mtime, so the incremental (mtime) basis is INVALID and total_new is inflated. "
            "Use --check-manifest (content-hash) here, or run from the canonical clone.",
            file=sys.stderr,
        )


def should_skip(filename: str) -> bool:
    """Check if a filename should be skipped."""
    if filename in SKIP_FILENAMES:
        return True
    for pattern in SKIP_PATTERNS:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False


def _manifest_last_compile_iso() -> str | None:
    """The tracked manifest's own ``last_compile`` (ISO-8601 UTC), or None.

    This is the only compile timestamp. The retired ``wiki/.last_compile`` file
    (KB-WM-4) is never consulted: it was gitignored, so lane worktrees never had
    it, and its two writers disagreed on format. A value that does not parse as
    ISO-8601 is reported as None rather than copied forward.
    """
    try:
        with open(SOURCE_MANIFEST_PATH) as fh:
            value = (json.load(fh) or {}).get("last_compile")
    except (OSError, ValueError, AttributeError):
        return None
    return _normalize_iso(value)


def _normalize_iso(value: object) -> str | None:
    """Return ``value`` as a canonical ``YYYY-MM-DDTHH:MM:SSZ`` string, or None."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
        "last_compile": _manifest_last_compile_iso(),
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

    This is what an UNSCOPED ``--touch`` does: after the reported delta has
    been compiled into wiki pages, recording the current full set means the
    next incremental scan reports nothing. The manifest is the shared
    watermark — tracked, so it advances only when the change is committed,
    and identical content hashes are recorded whichever worktree the touch
    runs from. Refuses when no baseline manifest exists yet; establish one
    with ``--full --write-manifest`` first. For a partial compile use
    :func:`refresh_tracked_manifest_scoped` instead (OP-34).
    """
    if not SOURCE_MANIFEST_PATH.exists():
        raise ValueError(
            f"no tracked baseline manifest at {SOURCE_MANIFEST_PATH}; "
            "run --full --write-manifest first (nothing is recorded compiled)"
        )
    full = build_manifest(scan_sources(0.0, None), "touch")
    full["last_compile"] = _utc_now_iso()
    write_manifest(SOURCE_MANIFEST_PATH, full)
    return full


def _normalize_scope_path(token: str) -> str:
    """Render a path scope token repository-relative, without trailing slash."""
    path = Path(token).expanduser()
    if path.is_absolute():
        try:
            path = path.resolve().relative_to(ROOT.resolve())
        except ValueError as exc:
            raise ValueError(f"touch scope path is outside the project: {token}") from exc
    text = path.as_posix().rstrip("/")
    if text in ("", "."):
        raise ValueError("touch scope path must name a file or directory, not the root")
    return text


def parse_touch_scope(tokens: list[str]) -> tuple[set[str], set[str]]:
    """Split ``--touch`` scope tokens into (source types, repo-relative paths).

    A token equal to a configured ``source_dirs`` type is a type scope;
    anything else is a path scope (a file, a directory prefix, or an fnmatch
    glob). Comma-separated lists are accepted inside one token.
    """
    known_types = {str(item["type"]) for item in CONFIG["source_dirs"]}
    types: set[str] = set()
    paths: set[str] = set()
    for token in tokens:
        for part in (p.strip() for p in token.split(",")):
            if not part:
                continue
            if part in known_types:
                types.add(part)
            else:
                paths.add(_normalize_scope_path(part))
    if not types and not paths:
        raise ValueError("scoped --touch needs at least one source type or path")
    return types, paths


def _in_touch_scope(source: dict, types: set[str], paths: set[str]) -> bool:
    if source.get("type") in types:
        return True
    path = str(source.get("path", ""))
    for scope in paths:
        if path == scope or path.startswith(scope + "/") or fnmatch.fnmatch(path, scope):
            return True
    return False


def refresh_tracked_manifest_scoped(types: set[str], paths: set[str]) -> dict:
    """Advance the tracked manifest ONLY for the sources a partial compile covered.

    In-scope entries are replaced by the current scan (added, changed, and
    removed sources all land); out-of-scope entries are carried over from the
    saved manifest byte-for-byte, so another lane's uncompiled delta stays
    visible to the next incremental scan. The manifest's ``last_compile`` is
    kept — a partial compile is not a compile of everything. The scope that was
    applied is recorded under ``last_touch`` for review.

    Raises ValueError when no baseline exists or a scope token matches no
    saved or current source (a typo must not silently touch nothing).
    """
    if not SOURCE_MANIFEST_PATH.exists():
        raise ValueError(
            f"no tracked baseline manifest at {SOURCE_MANIFEST_PATH}; "
            "run --full --write-manifest first (nothing is recorded compiled)"
        )
    saved = read_manifest(SOURCE_MANIFEST_PATH)
    current_sources = scan_sources(0.0, None)
    saved_sources = [s for s in saved["sources"] if isinstance(s, dict)]

    all_sources = [*saved_sources, *current_sources]
    unmatched = sorted(
        [t for t in types if not any(s.get("type") == t for s in all_sources)]
        + [p for p in paths if not any(_in_touch_scope(s, set(), {p}) for s in all_sources)]
    )
    if unmatched:
        raise ValueError(
            "touch scope matches no saved or current source: " + ", ".join(unmatched)
        )

    saved_by_path = source_index(saved_sources)
    current_paths = {str(s["path"]) for s in current_sources}
    merged: list[dict] = []
    touched = {"added": 0, "changed": 0, "removed": 0}
    for source in current_sources:
        path = str(source["path"])
        previous = saved_by_path.get(path)
        if _in_touch_scope(source, types, paths):
            if previous is None:
                touched["added"] += 1
            elif previous.get("content_hash") != source.get("content_hash"):
                touched["changed"] += 1
            merged.append(source)
        elif previous is not None:
            merged.append(previous)
    for source in saved_sources:
        path = str(source.get("path", ""))
        if path in current_paths:
            continue
        if _in_touch_scope(source, types, paths):
            touched["removed"] += 1
        else:
            merged.append(source)

    manifest = build_manifest(merged, "touch:scoped")
    manifest["last_compile"] = _normalize_iso(saved.get("last_compile"))
    manifest["last_touch"] = {
        "at": _utc_now_iso(),
        "scope_types": sorted(types),
        "scope_paths": sorted(paths),
        "advanced": touched,
    }
    write_manifest(SOURCE_MANIFEST_PATH, manifest)
    return manifest


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
        nargs="?",
        const="",
        action="append",
        metavar="SCOPE",
        help=(
            "After compiling the reported delta, advance the tracked source "
            "manifest. Bare --touch (without --type) regenerates the whole "
            "manifest and advances its last_compile. --touch SCOPE (repeatable, "
            "or comma-separated; a source type, a path, a directory prefix or "
            "a glob) and --touch --type T advance ONLY the in-scope entries "
            "and keep the manifest's last_compile."
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

    # the mtime basis is invalid from a linked worktree — say so before reporting a count
    warn_if_worktree_mtime_basis()

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

    if args.touch is not None:
        scope_tokens = [t for t in args.touch if t]
        if not scope_tokens and args.type_filter:
            scope_tokens = [args.type_filter]
        try:
            if scope_tokens:
                types, paths = parse_touch_scope(scope_tokens)
                refreshed = refresh_tracked_manifest_scoped(types, paths)
            else:
                refreshed = refresh_tracked_manifest()
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        if scope_tokens:
            adv = refreshed["last_touch"]["advanced"]
            print(
                f"touch (scoped: {', '.join(scope_tokens)}): advanced "
                f"{SOURCE_MANIFEST_PATH} for in-scope sources only "
                f"(+{adv['added']} ~{adv['changed']} -{adv['removed']}); "
                "last_compile left unchanged",
                file=sys.stderr,
            )
        else:
            print(
                f"touch: regenerated {SOURCE_MANIFEST_PATH} from the current "
                f"source set ({len(refreshed['sources'])} sources); "
                f"last_compile={refreshed['last_compile']}",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
