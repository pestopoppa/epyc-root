#!/usr/bin/env python3
"""Prospective CH-18 conflict inventory in a lane-local disposable Git clone.

Never operates on production or an external clone. Caller supplies explicit full
commit IDs; no fetch, build, reconciliation, deployment, or historical conversion.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters import ch18_merge_trial as reader

LANE = Path(__file__).resolve().parents[3]


def publish_record(output: Path, rec: dict) -> None:
    """Durably publish complete JSON without replacing an existing record."""
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, pending = tempfile.mkstemp(prefix=".ch18-record-", dir=output.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(rec, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(pending, output)  # Atomic no-replace publication on the same filesystem.
        os.unlink(pending)
        directory = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(pending):
            os.unlink(pending)


def capture(repo: Path, base: str, upstream: str, output: Path) -> dict:
    repo, output = repo.resolve(), output.resolve()
    if not repo.is_relative_to(LANE) or not output.is_relative_to(LANE):
        raise ValueError("repo and output must be inside this lane")
    if not (repo / ".git").is_dir() or not (repo / ".git").resolve().is_relative_to(LANE):
        raise ValueError("repo must be an independent disposable clone, not a linked worktree")
    if output.exists():
        raise ValueError("refusing to replace an existing record")
    if output.is_relative_to(repo):
        raise ValueError("output must be outside the disposable clone")
    env = {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_TERMINAL_PROMPT": "0", "GIT_MERGE_AUTOEDIT": "no"}

    def git(*args: str, cwd: Path = repo):
        return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "rerere.enabled=false",
                               "-c", "user.name=CH18 trial", "-c", "user.email=ch18@invalid", *args],
                              cwd=cwd, env=env, capture_output=True)

    common = git("rev-parse", "--path-format=absolute", "--git-common-dir")
    if common.returncode or not Path(os.fsdecode(common.stdout).strip()).resolve().is_relative_to(LANE):
        raise ValueError("Git common directory must be inside this lane")
    top = git("rev-parse", "--show-toplevel")
    if top.returncode or Path(os.fsdecode(top.stdout).strip()).resolve() != repo:
        raise ValueError("Git top-level must resolve exactly to supplied lane repo")
    for commit in (base, upstream):
        if not reader.SHA40.fullmatch(commit):
            raise ValueError("commit IDs must be full lowercase 40-hex IDs")
        resolved = git("rev-parse", "--verify", commit + "^{commit}")
        if resolved.returncode or resolved.stdout.decode().strip() != commit:
            raise ValueError("commit object missing or differs")
    status = git("status", "--porcelain")
    if status.returncode or status.stdout:
        raise ValueError("disposable clone must be clean")
    work = Path(tempfile.mkdtemp(prefix="ch18-trial-", dir=repo.parent))
    work.rmdir()
    rec = {"schema": reader.SCHEMA, "kind": "experimental_merge_trial",
           "production_base": base, "upstream_tip": upstream,
           "merge_strategy": "git merge -s ort --no-commit --no-ff",
           "tool": {"name": "git", "version": git("--version").stdout.decode().strip()},
           "completed_at": "", "state": "incomplete", "conflict_count": 0,
           "conflicting_paths": [], "conflicts_by_root": {},
           "cleanup": {"worktree_removed": False, "merge_aborted": False},
           "limitation": "Conflict inventory only; contents not reconciled, built, tested, promoted or deployed.",
           "content_sha256": ""}
    active = False
    work_verified = False
    try:
        add = git("worktree", "add", "--detach", str(work), base)
        if add.returncode:
            raise RuntimeError(add.stderr.decode(errors="replace"))
        top = git("rev-parse", "--show-toplevel", cwd=work)
        if top.returncode or Path(os.fsdecode(top.stdout).strip()).resolve() != work.resolve():
            raise ValueError("trial Git top-level must resolve exactly to created lane worktree")
        work_verified = True
        merge = git("merge", "-s", "ort", "--no-commit", "--no-ff", upstream, cwd=work)
        inventory = git("diff", "--name-only", "--diff-filter=U", "-z", cwd=work)
        active = git("rev-parse", "--verify", "MERGE_HEAD", cwd=work).returncode == 0
        paths = sorted(set(os.fsdecode(p) for p in inventory.stdout.split(b"\0") if p))
        rec["conflicting_paths"] = paths
        rec["conflict_count"] = len(paths)
        for path in paths:
            root = path.split("/", 1)[0]
            rec["conflicts_by_root"][root] = rec["conflicts_by_root"].get(root, 0) + 1
        rec["state"] = ("complete" if inventory.returncode == 0 and
                        (merge.returncode == 0 or (merge.returncode == 1 and active and paths)) else "failed")
    finally:
        if work.exists() and work_verified:
            active = git("rev-parse", "--verify", "MERGE_HEAD", cwd=work).returncode == 0
            if active:
                rec["cleanup"]["merge_aborted"] = git("merge", "--abort", cwd=work).returncode == 0
            remove = git("worktree", "remove", str(work))
            rec["cleanup"]["worktree_removed"] = remove.returncode == 0 and not work.exists()
        elif not work.exists():
            rec["cleanup"]["worktree_removed"] = True
        if not rec["cleanup"]["worktree_removed"] or (active and not rec["cleanup"]["merge_aborted"]):
            rec["state"] = "incomplete"
        rec["completed_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rec["content_sha256"] = reader.seal(rec)
        reader._validate(rec, str(output))
        publish_record(output, rec)
    return rec


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--production-base", required=True)
    p.add_argument("--upstream-tip", required=True)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    result = capture(a.repo, a.production_base, a.upstream_tip, a.output)
    print(json.dumps({"state": result["state"], "record": str(a.output)}))
    return 0 if result["state"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
