import argparse
import json
import subprocess
from pathlib import Path

import pytest

from scripts.system import acceptance_worktree as aw


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True, check=True
    )
    return result.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Acceptance Test")
    git(repo, "config", "user.email", "acceptance@example.invalid")
    (repo / "tracked.txt").write_text("base\n")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-m", "base")
    git(repo, "remote", "add", "origin", "https://example.invalid/epyc-root.git")
    git(repo, "update-ref", "refs/remotes/origin/main", git(repo, "rev-parse", "HEAD"))
    acceptance = tmp_path / "acceptance"
    acceptance.mkdir()
    receipts = tmp_path / "receipts"
    return repo, acceptance, receipts


def create_args(repo: Path, acceptance: Path, receipts: Path, name: str = "case"):
    return argparse.Namespace(
        repo=repo,
        path=acceptance / name,
        branch=f"accept/{name}",
        base="origin/main",
        owner="test-owner",
        task="AKX-test",
        purpose="lifecycle acceptance",
        acceptance_root=acceptance,
        receipt_root=receipts,
    )


def close_args(receipt: Path, outcome: str):
    return argparse.Namespace(
        receipt=receipt, owner="test-owner", outcome=outcome, remote="origin"
    )


def test_create_writes_durable_identity_and_registers_exact_path(repository):
    repo, acceptance, receipts = repository
    receipt_path = aw.create(create_args(repo, acceptance, receipts))
    receipt = json.loads(receipt_path.read_text())

    assert receipt["state"] == "created"
    assert receipt["owner"] == "test-owner"
    assert receipt["worktree"] == str((acceptance / "case").resolve())
    assert Path(receipt["git_common_dir"]) == (repo / ".git").resolve()
    assert (acceptance / "case").resolve() in aw.worktree_records(repo)
    events = receipt_path.with_suffix(".jsonl").read_text().splitlines()
    assert [json.loads(row)["event"] for row in events] == ["planned", "created"]


def test_explicit_clean_discard_removes_without_force_and_deletes_branch(
    repository, monkeypatch
):
    repo, acceptance, receipts = repository
    receipt_path = aw.create(create_args(repo, acceptance, receipts))
    commands = []
    original = aw.run_git

    def recording(repo_path, *args, **kwargs):
        commands.append(args)
        return original(repo_path, *args, **kwargs)

    monkeypatch.setattr(aw, "run_git", recording)
    aw.close(close_args(receipt_path, "discard"))

    assert not (acceptance / "case").exists()
    missing_branch = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "show-ref",
            "--verify",
            "refs/heads/accept/case",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert missing_branch.returncode != 0
    assert json.loads(receipt_path.read_text())["state"] == "removed"
    remove = next(args for args in commands if args[:2] == ("worktree", "remove"))
    assert remove == ("worktree", "remove", str((acceptance / "case").resolve()))
    assert "--force" not in remove


def test_dirty_discard_fail_closes_and_retains_tree(repository):
    repo, acceptance, receipts = repository
    receipt_path = aw.create(create_args(repo, acceptance, receipts))
    (acceptance / "case" / "untracked.txt").write_text("unique evidence\n")

    with pytest.raises(aw.Refusal, match="dirty"):
        aw.close(close_args(receipt_path, "discard"))

    assert (acceptance / "case" / "untracked.txt").read_text() == "unique evidence\n"
    receipt = json.loads(receipt_path.read_text())
    assert receipt["state"] == "retained"
    assert "dirty" in " ".join(receipt["last_refusal"]["reasons"])


def test_unpushed_commit_fail_closes_even_with_commit_push_outcome(repository):
    repo, acceptance, receipts = repository
    receipt_path = aw.create(create_args(repo, acceptance, receipts))
    worktree = acceptance / "case"
    (worktree / "tracked.txt").write_text("candidate\n")
    git(worktree, "add", "tracked.txt")
    git(worktree, "commit", "-m", "candidate")

    with pytest.raises(aw.Refusal, match="does not point exactly at HEAD"):
        aw.close(close_args(receipt_path, "commit-push"))

    assert worktree.exists()
    assert json.loads(receipt_path.read_text())["state"] == "retained"


def test_pushed_commit_removes_tree_and_retains_branch(repository):
    repo, acceptance, receipts = repository
    receipt_path = aw.create(create_args(repo, acceptance, receipts))
    worktree = acceptance / "case"
    (worktree / "tracked.txt").write_text("candidate\n")
    git(worktree, "add", "tracked.txt")
    git(worktree, "commit", "-m", "candidate")
    head = git(worktree, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/origin/accept/case", head)

    aw.close(close_args(receipt_path, "commit-push"))

    receipt = json.loads(receipt_path.read_text())
    assert receipt["state"] == "removed"
    assert receipt["pushed_witness"]["commit"] == head
    assert git(repo, "rev-parse", "refs/heads/accept/case") == head
    assert not worktree.exists()


def test_discard_refuses_local_commits_instead_of_deleting_them(repository):
    repo, acceptance, receipts = repository
    receipt_path = aw.create(create_args(repo, acceptance, receipts))
    worktree = acceptance / "case"
    (worktree / "tracked.txt").write_text("candidate\n")
    git(worktree, "add", "tracked.txt")
    git(worktree, "commit", "-m", "candidate")

    with pytest.raises(aw.Refusal, match="local commits are retained"):
        aw.close(close_args(receipt_path, "discard"))

    assert worktree.exists()
    assert git(repo, "rev-parse", "refs/heads/accept/case")


def test_create_refuses_path_outside_acceptance_root(repository):
    repo, acceptance, receipts = repository
    args = create_args(repo, acceptance, receipts)
    args.path = acceptance.parent / "outside"
    with pytest.raises(aw.Refusal, match="outside acceptance root"):
        aw.create(args)


def test_local_path_remote_is_not_push_evidence(repository):
    assert not aw.network_remote(str(repository[0]))
    assert not aw.network_remote("file:///tmp/repo.git")
    assert aw.network_remote("https://example.invalid/repo.git")
    assert aw.network_remote("git@example.invalid:repo.git")
