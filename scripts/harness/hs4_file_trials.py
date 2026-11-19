#!/usr/bin/env python3
"""Offline preparation and custody checks for shared HS-4 file-task trials.

This prepares public task files only. It does not launch a model, isolate a
grader, score answers or create an SC86 measurement. A future execution
adapter must provide those capabilities before this becomes an acceptance run.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _files(root: Path) -> list[tuple[str, bytes]]:
    """Snapshot regular files only; do not follow symlinks out of the fixture."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError("fixture root must be a real directory")
    files = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs:
            if (Path(directory) / name).is_symlink():
                raise ValueError("symlinks are not allowed in a fixture")
        for name in names:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if PurePosixPath(relative).parts[0] == ".git":
                raise ValueError("git metadata is not part of a public fixture")
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode) or path.is_symlink():
                raise ValueError("fixture must contain regular files only")
            files.append((relative, path.read_bytes()))
    if not files:
        raise ValueError("fixture must not be empty")
    return sorted(files)


def fixture_identity(files: list[tuple[str, bytes]]) -> str:
    rows = [{"path": name, "sha256": _digest(data)} for name, data in files]
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return _digest(encoded)


def prepare_attempt(*, fixture: Path, destination: Path, prompt: str,
                    task: str, arm: str, trial: int, catalog: str,
                    identity: dict[str, str], expected_fixture: str) -> dict[str, Any]:
    """Make a fresh task workspace and bind the P6 comparator's identities.

    The fixture is strictly public model-visible material. References and
    scoring code must be kept elsewhere by the host; this helper does not
    provide an OS boundary and cannot prove grader isolation.
    """
    keys = ("model", "server", "plugin", "base_catalog")
    if (not all(isinstance(x, str) and x.strip() for x in (prompt, task, catalog))
            or arm not in ("baseline", "candidate") or type(trial) is not int
            or trial not in (1, 2) or not isinstance(identity, dict)
            or not all(isinstance(identity.get(k), str) and identity[k].strip() for k in keys)):
        raise ValueError("invalid task, trial or frozen identity")
    source = Path(fixture).absolute()
    if source.is_symlink():
        raise ValueError("fixture root must not be a symlink")
    src = source.resolve(strict=True)
    dest = Path(destination).resolve(strict=False)
    if dest == src or src in dest.parents or dest in src.parents:
        raise ValueError("fixture and output must be disjoint")
    files = _files(src)
    fixture_sha = fixture_identity(files)
    if fixture_sha != expected_fixture:
        raise ValueError("public fixture digest does not match frozen task")
    # mkdir without exist_ok ensures an attempt never reuses state.
    dest.mkdir(mode=0o700, parents=False, exist_ok=False)
    workspace = dest / "workspace"
    workspace.mkdir(mode=0o700)
    for name, data in files:
        path = workspace / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as out:
            out.write(data)
    metadata = {
        "schema": "hs4-file-trial-preparation/v1", "task": task, "arm": arm,
        "trial": trial, "fixture": fixture_sha, "catalog": catalog,
        "identity": {key: identity[key] for key in keys},
        "prompt_sha256": _digest(prompt.encode()),
        "isolation": "not_verified", "status": "prepared_only",
    }
    (dest / "prompt.txt").write_text(prompt, encoding="utf-8")
    (dest / "prepared.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata
