"""Stage hash-pinned matched Taskflow replay cases and preserve scoped candidate artifacts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess


PYTEST_CACHE_FILES = frozenset({".gitignore", "CACHEDIR.TAG", "README.md", "v/cache/lastfailed",
                               "v/cache/nodeids", "v/cache/stepwise"})


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def read(path):
    return json.loads(path.read_text())


def rel(value):
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts or "\n" in value:
        raise ValueError(f"unsafe case-relative path: {value!r}")
    return Path(*path.parts)


def file_map(root, *, candidate=False):
    files, unsafe = {}, []
    for directory, dirs, entries in os.walk(root, followlinks=False):
        parent = Path(directory)
        # Never read case-writable Git metadata or ordinary runtime caches as source.
        if candidate:
            if parent == root:
                dirs[:] = [n for n in dirs if n not in {".git", ".taskflow-refs"}]
        for name in list(dirs):
            path = parent / name
            if path.is_symlink():
                dirs.remove(name)
                unsafe.append(str(path.relative_to(root)))
        for name in entries:
            path = parent / name
            key = str(path.relative_to(root))
            st = path.lstat()
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                unsafe.append(key)
                continue
            files[key] = {"sha256": digest(path), "bytes": st.st_size, "executable": bool(st.st_mode & 0o111)}
    return files, sorted(unsafe)


def validate_baseline(case_dir, case):
    observed, unsafe = file_map(case_dir / "baseline")
    if unsafe or observed != case["baseline_files"]:
        raise RuntimeError(f"frozen case baseline changed: {case['id']}")
    if digest(case_dir / "oracle.py") != case["oracle_sha256"]:
        raise RuntimeError(f"frozen original acceptance oracle changed: {case['id']}")


def copy_file(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest, follow_symlinks=False)


def git(root, *args):
    cmd = ["git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=Taskflow calibration",
           "-c", "user.email=calibration@local.invalid", "-C", str(root), *args]
    env = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1")
    return subprocess.run(cmd, env=env, check=True, capture_output=True, timeout=45).stdout


def stage(case_dir, work, refs):
    case = read(case_dir / "case.json")
    validate_baseline(case_dir, case)
    refs.mkdir(parents=True, exist_ok=True)
    baseline = case_dir / "baseline"
    for name in case["baseline_files"]:
        p = rel(name)
        source = baseline / p
        if p.parts[0] == ".taskflow-refs":
            target = refs.joinpath(*p.parts[1:])
            copy_file(source, target)
            target.chmod(0o444)
        else:
            copy_file(source, work / p)
    for name in case["editable_paths"]:
        (work / rel(name)).parent.mkdir(parents=True, exist_ok=True)
    git(work, "init", "-q")
    git(work, "add", "--all")
    git(work, "commit", "-qm", "Frozen calibration baseline", "--allow-empty")
    return case


def candidate_state(baseline, observed):
    """Retain raw cache manifests while comparing the candidate's source outputs."""
    runtime = {}
    for name, metadata in observed.items():
        if name in baseline:
            continue
        path = PurePosixPath(name)
        if ".pytest_cache" in path.parts[:-1]:
            suffix = PurePosixPath(*path.parts[path.parts.index(".pytest_cache") + 1:])
            if suffix.as_posix() in PYTEST_CACHE_FILES:
                runtime[name] = metadata
        elif path.parent.name == "__pycache__" and path.suffix == ".pyc":
            runtime[name] = metadata
    return {name: data for name, data in observed.items() if name not in runtime}, runtime


def compare(case, work):
    before = {name: desc for name, desc in case["baseline_files"].items() if not name.startswith(".taskflow-refs/")}
    observed, unsafe = file_map(work, candidate=True)
    after, runtime = candidate_state(before, observed)
    changes = {name: after.get(name) for name in sorted(before.keys() | after.keys())
               if before.get(name) != after.get(name)}
    outside = sorted(set(changes) - set(case["editable_paths"]))
    return changes, outside, unsafe, runtime


def sanitize(case_dir, work, result, staged, refs):
    safety = result["unsafe_paths"]
    if safety or result["outside_scope"]:
        return
    staged.mkdir(parents=True)
    stage(case_dir, staged, refs)
    for name, record in result["changed_files"].items():
        path = rel(name)
        if record is None:
            (staged / path).unlink()
        else:
            copy_file(work / path, staged / path)
            if digest(staged / path) != record["sha256"]:
                raise RuntimeError(f"case output changed while being copied: {name}")
            if name not in result["baseline_files"]:
                git(staged, "add", "-N", "--", name)
    patch = git(staged, "diff", "--no-ext-diff", "--binary", "HEAD", "--")
    if patch:
        result["patch_sha256"] = hashlib.sha256(patch).hexdigest()
        (staged.parent / "candidate.patch").write_bytes(patch)


def write_git_config(box):
    path = box.config / "git/config"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = "[grep]\n\tthreads = 4\n[user]\n\tname = Taskflow calibration\n\temail = calibration@local.invalid\n"
    if path.exists() and path.read_text() != data:
        raise RuntimeError("case Git environment drift")
    if not path.exists():
        path.write_text(data)
        path.chmod(0o444)
