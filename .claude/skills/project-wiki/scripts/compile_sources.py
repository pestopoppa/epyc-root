#!/usr/bin/env python3
"""List source files for wiki compilation.

Scans knowledge streams (handoffs, progress logs, deep-dives, docs) and
outputs a JSON manifest of files that need to be compiled into wiki articles.
Compares file modification times against the last compilation timestamp.

Adapted for epyc-root's flat directory layout (no per-user nesting).

Usage:
    python3 compile_sources.py              # incremental (since last compile)
    python3 compile_sources.py --full       # all sources regardless of timestamp
    python3 compile_sources.py --touch      # update .last_compile after output
    python3 compile_sources.py --type research  # filter by source type
    python3 compile_sources.py --since 2026-04-01  # override since-date
"""

from __future__ import annotations

import argparse
import fnmatch
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


def load_config() -> dict:
    """Load compile config from wiki.yaml, with sensible defaults."""
    config_path = ROOT / "wiki.yaml"
    defaults = {
        "output_dir": "wiki",
        "last_compile": "wiki/.last_compile",
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
                "title": extract_title(md_file),
            })

    return results


def build_manifest(sources: list[dict], mode: str) -> dict:
    """Build the output manifest from collected sources."""
    by_type: dict[str, int] = {}
    for s in sources:
        by_type[s["type"]] = by_type.get(s["type"], 0) + 1

    return {
        "last_compile": get_last_compile_iso(),
        "scan_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "sources": sources,
        "total_new": len(sources),
        "by_type": by_type,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List source files for wiki compilation."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Ignore .last_compile, return all sources.",
    )
    parser.add_argument(
        "--touch",
        action="store_true",
        help="Update .last_compile after outputting manifest.",
    )
    parser.add_argument(
        "--type",
        dest="type_filter",
        help="Filter to a specific source type.",
    )
    parser.add_argument(
        "--since",
        help="Override since-date (YYYY-MM-DD). Takes precedence over .last_compile.",
    )

    args = parser.parse_args()

    if args.full:
        since = 0.0
        mode = "full"
    elif args.since:
        try:
            dt = datetime.strptime(args.since, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            since = dt.timestamp()
            mode = f"since:{args.since}"
        except ValueError:
            print(f"ERROR: Invalid date format: {args.since} (expected YYYY-MM-DD)",
                  file=sys.stderr)
            return 1
    else:
        since = get_last_compile()
        mode = "incremental"

    sources = scan_sources(since, args.type_filter)
    manifest = build_manifest(sources, mode)

    json.dump(manifest, sys.stdout, indent=2)
    print()

    if args.touch:
        touch_last_compile()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
