from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/system/autokernel_dirty_preserve.py"
SPEC = importlib.util.spec_from_file_location("autokernel_dirty_preserve", SCRIPT)
assert SPEC and SPEC.loader
preserve = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preserve
SPEC.loader.exec_module(preserve)


def run(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if check and proc.returncode:
        raise AssertionError(f"command failed: {args}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return proc


def git(repo: Path, *args: str) -> str:
    return run("git", "-C", str(repo), *args).stdout.strip()


def make_world(tmp_path: Path, *, pushed: bool = True) -> dict:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "dirty"
    run("git", "init", "--bare", str(remote))
    run("git", "init", str(repo))
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.bin").write_bytes(b"base\x00data\n")
    git(repo, "add", "tracked.bin")
    git(repo, "commit", "-m", "base")
    git(repo, "remote", "add", "origin", f"https://example.invalid/{remote.name}")
    if pushed:
        # Populate a network-named remote-tracking ref without making a network request.
        git(repo, "update-ref", "refs/remotes/origin/main", git(repo, "rev-parse", "HEAD"))
    (repo / "tracked.bin").write_bytes(b"changed\x00binary\n")
    (repo / "staged.txt").write_text("staged\n")
    git(repo, "add", "staged.txt")
    (repo / "staged.txt").write_text("staged plus worktree\n")
    (repo / "new.txt").write_bytes(b"untracked\n")
    os.symlink("new.txt", repo / "link")
    return {"repo": repo, "remote": remote}


def source_state(repo: Path) -> dict:
    files = {}
    for p in sorted(repo.rglob("*")):
        rel = str(p.relative_to(repo))
        st = p.lstat()
        if stat.S_ISREG(st.st_mode):
            files[rel] = ("file", stat.S_IMODE(st.st_mode), hashlib.sha256(p.read_bytes()).hexdigest())
        elif stat.S_ISLNK(st.st_mode):
            files[rel] = ("symlink", stat.S_IMODE(st.st_mode), os.readlink(p))
        else:
            files[rel] = ("dir", stat.S_IMODE(st.st_mode))
    return {"head": git(repo, "rev-parse", "HEAD"), "status": git(repo, "status", "--porcelain=v2", "--untracked-files=all"), "files": files}


def make_manifest(tmp_path: Path, repo: Path, verdict: str = "KEEP-dirty") -> tuple[Path, str]:
    row = {
        "path": str(repo), "repo": str(repo), "kind": "git-worktree", "family": "worktree-root",
        "verdict": verdict, "size_bytes": 1, "reason": "fixture", "reasons": {verdict: ["fixture"]},
    }
    data = json.dumps({"schema": preserve.SWEEP_SCHEMA, "rows": [row]}, sort_keys=True).encode()
    path = tmp_path / "sweep.json"
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def invoke(*args: str) -> subprocess.CompletedProcess:
    return run(sys.executable, str(SCRIPT), *args, check=False)


def tar_names(path: Path) -> list[str]:
    with tarfile.open(path, "r:") as tf:
        return tf.getnames()


def test_default_dry_run_writes_no_archive_and_does_not_mutate_source(tmp_path):
    world = make_world(tmp_path)
    manifest, sha = make_manifest(tmp_path, world["repo"])
    archive = tmp_path / "archives"
    before = source_state(world["repo"])
    proc = invoke("--manifest", str(manifest), "--manifest-sha", sha, "--archive-root", str(archive))
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["mode"] == "dry-run"
    assert report["results"][0]["action"] == "dry-run"
    assert not archive.exists()
    assert source_state(world["repo"]) == before


def test_write_archives_exact_status_diff_untracked_and_verifies(tmp_path):
    world = make_world(tmp_path)
    manifest, sha = make_manifest(tmp_path, world["repo"])
    archive_root = tmp_path / "archives"
    before = source_state(world["repo"])
    proc = invoke("--manifest", str(manifest), "--manifest-sha", sha,
                  "--archive-root", str(archive_root), "--write")
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)["results"][0]
    assert result["action"] == "archived"
    archive = Path(result["archive"])
    assert archive.name == result["archive_sha256"] + ".tar"
    assert set(tar_names(archive)) >= {
        "metadata.json", "git-status-v2-z.bin", "git-diff-binary-head.patch",
        "git-diff-binary-staged.patch", "git-diff-binary-worktree.patch",
        "untracked/new.txt", "untracked/link", "ARCHIVE-MANIFEST.json",
    }
    verified = preserve.verify_archive(archive, world["repo"])
    assert verified["archive_sha256"] == result["archive_sha256"]
    with tarfile.open(archive, "r:") as tf:
        archived_status = tf.extractfile("git-status-v2-z.bin").read()
        archived_head_diff = tf.extractfile("git-diff-binary-head.patch").read()
        archived_staged_diff = tf.extractfile("git-diff-binary-staged.patch").read()
        archived_worktree_diff = tf.extractfile("git-diff-binary-worktree.patch").read()
        assert tf.extractfile("untracked/new.txt").read() == b"untracked\n"
        assert tf.getmember("untracked/link").issym()
        assert tf.getmember("untracked/link").linkname == "new.txt"
        assert archived_status == preserve.git(
            world["repo"], "status", "--porcelain=v2", "-z", "--untracked-files=all"
        )
        assert archived_head_diff == preserve.git(world["repo"], "diff", "--binary", "HEAD", "--")
        assert archived_staged_diff == preserve.git(
            world["repo"], "diff", "--cached", "--binary", "HEAD", "--"
        )
        assert archived_worktree_diff == preserve.git(world["repo"], "diff", "--binary", "--")
        assert b"GIT binary patch" in archived_head_diff
        assert b"staged.txt" in archived_staged_diff
        assert b"staged.txt" in archived_worktree_diff
    assert source_state(world["repo"]) == before


def test_identical_rerun_deduplicates_by_archive_hash(tmp_path):
    world = make_world(tmp_path)
    manifest, sha = make_manifest(tmp_path, world["repo"])
    root = tmp_path / "archives"
    args = ("--manifest", str(manifest), "--manifest-sha", sha, "--archive-root", str(root), "--write")
    first = json.loads(invoke(*args).stdout)["results"][0]
    second_proc = invoke(*args)
    assert second_proc.returncode == 0, second_proc.stderr
    second = json.loads(second_proc.stdout)["results"][0]
    assert second["action"] == "deduplicated"
    assert first["archive_sha256"] == second["archive_sha256"]
    assert len(list((root / "objects").rglob("*.tar"))) == 1
    assert len(list((root / "records").rglob("*.json"))) == 1


def test_unpushed_head_gets_standalone_verified_bundle(tmp_path):
    world = make_world(tmp_path, pushed=False)
    manifest, sha = make_manifest(tmp_path, world["repo"])
    root = tmp_path / "archives"
    proc = invoke("--manifest", str(manifest), "--manifest-sha", sha,
                  "--archive-root", str(root), "--write")
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)["results"][0]
    assert result["unpushed_bundle"] is True
    archive = Path(result["archive"])
    assert "unpushed-head.bundle" in tar_names(archive)
    verified = preserve.verify_archive(archive, world["repo"])
    assert verified["metadata"]["head_unpushed_to_network_remote"] is True
    bundle = tmp_path / "saved.bundle"
    with tarfile.open(archive, "r:") as tf:
        bundle.write_bytes(tf.extractfile("unpushed-head.bundle").read())
    restored = tmp_path / "restored"
    run("git", "clone", str(bundle), str(restored))
    assert git(restored, "rev-parse", "HEAD") == git(world["repo"], "rev-parse", "HEAD")


def test_pushed_head_omits_bundle(tmp_path):
    world = make_world(tmp_path, pushed=True)
    manifest, sha = make_manifest(tmp_path, world["repo"])
    proc = invoke("--manifest", str(manifest), "--manifest-sha", sha)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["results"][0]["unpushed_bundle"] is False


def test_wrong_manifest_sha_refuses_without_creating_archive_root(tmp_path):
    world = make_world(tmp_path)
    manifest, _ = make_manifest(tmp_path, world["repo"])
    root = tmp_path / "archives"
    proc = invoke("--manifest", str(manifest), "--manifest-sha", "0" * 64,
                  "--archive-root", str(root), "--write")
    assert proc.returncode == 2
    assert "REFUSED" in proc.stderr
    assert not root.exists()


def test_requested_path_must_be_keep_dirty_in_reviewed_manifest(tmp_path):
    world = make_world(tmp_path)
    manifest, sha = make_manifest(tmp_path, world["repo"], verdict="REMOVE")
    proc = invoke("--manifest", str(manifest), "--manifest-sha", sha, "--path", str(world["repo"]))
    assert proc.returncode == 2
    assert "not KEEP-dirty" in proc.stderr


def test_cleaned_tree_fails_closed(tmp_path):
    world = make_world(tmp_path)
    manifest, sha = make_manifest(tmp_path, world["repo"])
    git(world["repo"], "reset", "--hard", "HEAD")
    (world["repo"] / "new.txt").unlink()
    (world["repo"] / "link").unlink()
    proc = invoke("--manifest", str(manifest), "--manifest-sha", sha)
    assert proc.returncode == 1
    assert "now clean" in json.loads(proc.stdout)["errors"][0]["error"]


def test_verify_archive_detects_tamper(tmp_path):
    world = make_world(tmp_path)
    manifest, sha = make_manifest(tmp_path, world["repo"])
    root = tmp_path / "archives"
    result = json.loads(invoke("--manifest", str(manifest), "--manifest-sha", sha,
                               "--archive-root", str(root), "--write").stdout)["results"][0]
    original = Path(result["archive"])
    tampered = tmp_path / "tampered.tar"
    data = bytearray(original.read_bytes())
    data[600] ^= 1
    tampered.write_bytes(data)
    with pytest.raises((preserve.PreserveError, tarfile.TarError, UnicodeError, json.JSONDecodeError)):
        preserve.verify_archive(tampered)


def test_verify_archive_checks_content_address_filename(tmp_path):
    world = make_world(tmp_path)
    manifest, sha = make_manifest(tmp_path, world["repo"])
    root = tmp_path / "archives"
    result = json.loads(invoke("--manifest", str(manifest), "--manifest-sha", sha,
                               "--archive-root", str(root), "--write").stdout)["results"][0]
    wrong = tmp_path / (("0" * 64) + ".tar")
    wrong.write_bytes(Path(result["archive"]).read_bytes())
    with pytest.raises(preserve.PreserveError, match="content-address filename"):
        preserve.verify_archive(wrong)


def test_stability_guard_refuses_changed_source(monkeypatch, tmp_path):
    world = make_world(tmp_path)
    manifest, sha = make_manifest(tmp_path, world["repo"])
    row = json.loads(manifest.read_bytes())["rows"][0]
    original = preserve.capture
    calls = 0

    def changing_capture(*args, **kwargs):
        nonlocal calls
        calls += 1
        snap = original(*args, **kwargs)
        if calls == 2:
            snap.diff += b"changed-during-capture"
        return snap

    monkeypatch.setattr(preserve, "capture", changing_capture)
    root = tmp_path / "archives"
    with pytest.raises(preserve.PreserveError, match="changed during capture"):
        preserve.preserve_one(row, sha, root, True)
    assert not list(root.rglob("*.tar"))


def test_verify_cli_is_independent_of_manifest(tmp_path):
    world = make_world(tmp_path)
    manifest, sha = make_manifest(tmp_path, world["repo"])
    root = tmp_path / "archives"
    result = json.loads(invoke("--manifest", str(manifest), "--manifest-sha", sha,
                               "--archive-root", str(root), "--write").stdout)["results"][0]
    proc = invoke("--verify-archive", result["archive"])
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["verified"][0]["archive_sha256"] == result["archive_sha256"]
