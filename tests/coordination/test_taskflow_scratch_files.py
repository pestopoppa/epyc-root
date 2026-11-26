"""Worker scratch cleanup must preserve Git-tracked files, even after local edits."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow.harness.local_llm import install_scratch_command  # noqa: E402


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def worker(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "docs").mkdir()
    (repo / "docs/README.md").write_text("docs\n")
    (repo / "README.md").write_text("root\n")
    git(repo, "add", ".")
    git(repo, "-c", "core.hooksPath=/dev/null", "-c", "user.name=test", "-c", "user.email=test@example.org",
        "commit", "-qm", "base")
    lane = tmp_path / "lane"
    git(repo, "worktree", "add", "-q", "--detach", str(lane), "HEAD")
    command = install_scratch_command(tmp_path / "run", lane) / "taskflow-scratch"

    def invoke(*args, cwd=lane):
        return subprocess.run([str(command), *args], cwd=cwd, text=True, capture_output=True)

    return lane, invoke


def test_tracked_remove_leaves_edits_untouched_from_root_and_subdir(worker):
    lane, invoke = worker
    original = lane / "docs/README.md"
    original.write_text("uncommitted edits\n")
    scratch = lane / "scratch.txt"
    scratch.write_text("scratch\n")
    subdir = invoke("rm", "README.md", cwd=lane / "docs")
    grouped = invoke("rm", "scratch.txt", "docs/README.md")
    assert subdir.returncode == grouped.returncode == 1
    assert "tracked path: 'docs/README.md'" in subdir.stderr == grouped.stderr
    assert original.read_text() == "uncommitted edits\n"
    assert scratch.read_text() == "scratch\n"


def test_move_guards_tracked_source_and_effective_destination(worker):
    lane, invoke = worker
    original = lane / "docs/README.md"
    original.write_text("uncommitted edits\n")
    (lane / "scratch").mkdir()
    source = lane / "scratch/README.md"
    source.write_text("scratch replacement\n")
    for operands in (("docs/README.md", "scratch/replaced.md"), ("scratch/README.md", "docs/README.md"),
                     ("scratch/README.md", "docs")):
        result = invoke("mv", *operands)
        assert result.returncode == 1
        assert "tracked path: 'docs/README.md'" in result.stderr
    assert original.read_text() == "uncommitted edits\n"
    assert source.read_text() == "scratch replacement\n"


def test_git_index_and_head_are_both_protected(worker, monkeypatch):
    lane, invoke = worker
    git(lane, "rm", "-q", "--cached", "README.md")
    (lane / "index only.txt").write_text("staged\n")
    git(lane, "add", "index only.txt")
    monkeypatch.setenv("GIT_INDEX_FILE", str(lane / "other.index"))
    for name in ("README.md", "index only.txt"):
        result = invoke("rm", name)
        assert result.returncode == 1
        assert f"tracked path: {name!r}" in result.stderr
        assert (lane / name).is_file()


def test_untracked_cleanup_and_move_support_literal_file_names(worker):
    lane, invoke = worker
    scratch = lane / "docs/[scratch note].txt"
    scratch.write_text("scratch\n")
    assert invoke("mv", "[scratch note].txt", "renamed.txt", cwd=lane / "docs").returncode == 0
    assert invoke("mv", "docs/renamed.txt", ".").returncode == 0
    assert (lane / "renamed.txt").read_text() == "scratch\n"
    (lane / "second.txt").touch()
    assert invoke("rm", "renamed.txt", "second.txt").returncode == 0
    assert not any(p.exists() for p in (scratch, lane / "docs/renamed.txt", lane / "renamed.txt", lane / "second.txt"))


def test_cleanup_refuses_paths_outside_lane_and_protected_metadata(worker, tmp_path):
    lane, invoke = worker
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("external\n")
    (lane / "link").symlink_to(outside, target_is_directory=True)
    (lane / "local-link").symlink_to(lane / "docs", target_is_directory=True)
    (lane / ".taskflow-refs").mkdir()
    (lane / ".taskflow-refs/ref.txt").write_text("reference\n")
    (lane / "scratch.txt").write_text("scratch\n")
    for path in (str(sentinel), "../outside/sentinel.txt", "link/sentinel.txt", "local-link/README.md", ".git",
                 ".taskflow-refs/ref.txt", "-f"):
        assert invoke("rm", path).returncode == 1
    for dest in (str(sentinel), "../outside/sentinel.txt", "link/sentinel.txt", "link"):
        assert invoke("mv", "scratch.txt", dest).returncode == 1
    assert invoke("rm", "sentinel.txt", cwd=outside).returncode == 1
    assert invoke("rm", "link").returncode == 0  # Unlink the entry itself without following it.
    assert not (lane / "link").is_symlink()
    assert sentinel.read_text() == "external\n"
    assert (lane / "scratch.txt").read_text() == "scratch\n"
    assert (lane / ".taskflow-refs/ref.txt").read_text() == "reference\n"
