#!/usr/bin/env python3
"""Build a deterministic, source-only Git-object digest manifest for the NI08 hosted fixture."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import PurePosixPath


_SOURCE_SUFFIXES = {".py", ".pyi", ".sh", ".toml", ".lock", ".yaml", ".yml", ".ini", ".cfg"}
_SOURCE_JSON_NAMES = {"package.json", "tsconfig.json", "pyrightconfig.json",
                      ".eslintrc.json", "settings.json"}


def _git(repo: str, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", repo, *args])


def _include(path: str) -> bool:
    p = PurePosixPath(path)
    return p.suffix.lower() in _SOURCE_SUFFIXES or p.name in _SOURCE_JSON_NAMES


def repository_context(label: str, path: str) -> dict:
    commit = _git(path, "rev-parse", "HEAD").decode().strip()
    status = _git(path, "status", "--porcelain", "--untracked-files=no")
    if status:
        raise SystemExit(f"tracked changes in {label} repository")
    raw = _git(path, "ls-tree", "-rz", "--full-tree", commit)
    files = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        header, name = item.split(b"\t", 1)
        mode, kind, oid = header.decode("ascii").split()
        relative = os.fsdecode(name)
        if kind != "blob" or mode not in {"100644", "100755"} or not _include(relative):
            continue
        content = _git(path, "cat-file", "blob", oid)
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
    result = {"schema": "epyc.ni08.source_context/v1", "repositories": repos}
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    with open(args.output, "xb") as handle:
        handle.write(encoded)
    print(hashlib.sha256(encoded).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
