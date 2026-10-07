#!/usr/bin/env python3
"""Bind tracked source, documentation, and config blobs read by EVL-38."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from pathlib import PurePosixPath

_SOURCE_SUFFIXES = {".py", ".pyi", ".sh", ".toml", ".lock", ".yaml", ".yml",
                    ".ini", ".cfg", ".md", ".rst", ".mdx"}
_SOURCE_JSON_NAMES = {"package.json", "tsconfig.json", "pyrightconfig.json",
                      ".eslintrc.json", "settings.json"}
_SOURCE_BASENAMES = {"Makefile", "Dockerfile", ".clang-format",
                     ".pre-commit-config.yaml", "CMakeLists.txt"}


def _git(repo: str, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", repo, *args])


def _include(path: str) -> bool:
    p = PurePosixPath(path)
    if (p.suffix.lower() in _SOURCE_SUFFIXES or p.name in _SOURCE_BASENAMES
            or p.name.startswith("README")):
        return True
    if p.suffix.lower() == ".json":
        parts = set(p.parts)
        return (p.name in _SOURCE_JSON_NAMES or ".claude" in parts
                or "orchestration" in parts or "config" in parts
                or (p.parts[:3] == ("docs", "reference", "agent-config")))
    return False


def _physical_bytes(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise SystemExit(f"physical source is not a regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            return handle.read()
    finally:
        os.close(fd)


def repository_context(label: str, path: str) -> dict:
    repository = Path(path)
    commit = _git(path, "rev-parse", "HEAD").decode().strip()
    status = _git(path, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise SystemExit(f"tracked or untracked changes in {label} repository")
    ignored = _git(path, "ls-files", "-o", "-i", "--exclude-standard", "-z")
    ignored_sources = [os.fsdecode(item) for item in ignored.split(b"\0")
                       if item and _include(os.fsdecode(item))]
    if ignored_sources:
        raise SystemExit(f"ignored source/config inputs exist in {label}: {ignored_sources[:20]}")
    raw = _git(path, "ls-tree", "-rz", "--full-tree", commit)
    files = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        header, name = item.split(b"\t", 1)
        mode, kind, oid = header.decode("ascii").split()
        relative = os.fsdecode(name)
        if kind != "blob" or mode not in {"100644", "100755", "120000"} or not _include(relative):
            continue
        content = _git(path, "cat-file", "blob", oid)
        worktree_path = repository / relative
        try:
            info = worktree_path.lstat()
        except OSError as exc:
            raise SystemExit(f"missing physical source input in {label}: {relative}: {exc}") from exc
        try:
            if mode == "120000":
                if not stat.S_ISLNK(info.st_mode):
                    raise SystemExit(f"tracked symlink is not a physical symlink in {label}: {relative}")
                physical = os.fsencode(os.readlink(worktree_path))
            else:
                if not stat.S_ISREG(info.st_mode):
                    raise SystemExit(f"nonregular or symlinked source input in {label}: {relative}")
                physical = _physical_bytes(worktree_path)
        except OSError as exc:
            raise SystemExit(f"cannot read physical source input in {label}: {relative}: {exc}") from exc
        if physical != content:
            raise SystemExit(f"physical source bytes differ from pinned Git blob in {label}: {relative}")
        files.append({"path": relative, "git_blob": oid,
                      "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)})
    files.sort(key=lambda row: row["path"])
    return {"label": label, "commit": commit, "files": files}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", action="append", required=True, metavar="LABEL=PATH")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    repos = {}
    for item in args.repo:
        label, path = item.split("=", 1)
        if not label or label in repos:
            raise SystemExit("repository labels must be nonempty and unique")
        repos[label] = repository_context(label, path)
    result = {"schema": "epyc.evl38.source_context/v1", "repositories": repos}
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    with open(args.output, "xb") as handle:
        handle.write(encoded)
    print(hashlib.sha256(encoded).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
