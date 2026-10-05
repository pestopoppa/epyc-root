"""Tests for worktree_manager.py — git worktree isolation for PromptForge.

These tests use a temporary git repo to avoid touching the real project.
"""

import subprocess

import pytest

from scripts.autopilot.worktree_manager import WorktreeManager


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repo with an initial commit."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Initialize repo
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo, capture_output=True, check=True,
    )

    # Create initial file and commit
    prompts_dir = repo / "orchestration" / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "frontdoor.md").write_text("original frontdoor content")
    (repo / "src" / "escalation.py").parent.mkdir(parents=True)
    (repo / "src" / "escalation.py").write_text("# original escalation\ndef escalate(): pass\n")

    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=repo, capture_output=True, check=True,
    )

    # Create worktrees base dir
    (repo / "tmp" / "worktrees").mkdir(parents=True)

    return repo


def test_experiment_create_and_cleanup(temp_git_repo, monkeypatch):
    """Worktree is created and cleaned up."""
    import scripts.autopilot.worktree_manager as wm
    monkeypatch.setattr(wm, "WORKTREE_BASE", temp_git_repo / "tmp" / "worktrees")

    mgr = WorktreeManager(temp_git_repo)
    wt_path = temp_git_repo / "tmp" / "worktrees" / "test_trial"

    with mgr.experiment("test_trial") as ctx:
        assert ctx.worktree_path == wt_path
        assert wt_path.exists()
        assert (wt_path / "orchestration" / "prompts" / "frontdoor.md").exists()

    # Cleaned up after exit
    assert not wt_path.exists()


def test_apply_file_writes_to_both(temp_git_repo, monkeypatch):
    """apply_file writes to worktree and main repo."""
    import scripts.autopilot.worktree_manager as wm
    monkeypatch.setattr(wm, "WORKTREE_BASE", temp_git_repo / "tmp" / "worktrees")

    mgr = WorktreeManager(temp_git_repo)

    with mgr.experiment("test_apply") as ctx:
        ctx.apply_file(
            "orchestration/prompts/frontdoor.md",
            "mutated frontdoor content",
        )
        # Main repo has mutated content
        main_content = (temp_git_repo / "orchestration" / "prompts" / "frontdoor.md").read_text()
        assert main_content == "mutated frontdoor content"

        # Worktree also has mutated content
        wt_content = (ctx.worktree_path / "orchestration" / "prompts" / "frontdoor.md").read_text()
        assert wt_content == "mutated frontdoor content"

        # Reject
        ctx.reject()

    # After rejection, original is restored
    restored = (temp_git_repo / "orchestration" / "prompts" / "frontdoor.md").read_text()
    assert restored == "original frontdoor content"


def test_accept_commits_to_main(temp_git_repo, monkeypatch):
    """accept() commits the mutation in the main repo."""
    import scripts.autopilot.worktree_manager as wm
    monkeypatch.setattr(wm, "WORKTREE_BASE", temp_git_repo / "tmp" / "worktrees")

    mgr = WorktreeManager(temp_git_repo)

    with mgr.experiment("test_accept") as ctx:
        ctx.apply_file(
            "orchestration/prompts/frontdoor.md",
            "improved frontdoor",
        )
        ctx.accept("autopilot: improved frontdoor prompt")

    # Main repo has the mutation persisted
    content = (temp_git_repo / "orchestration" / "prompts" / "frontdoor.md").read_text()
    assert content == "improved frontdoor"

    # And it's committed
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=temp_git_repo, capture_output=True, text=True,
    )
    assert "improved frontdoor" in result.stdout


def test_auto_reject_on_no_decision(temp_git_repo, monkeypatch):
    """If neither accept nor reject is called, auto-reject."""
    import scripts.autopilot.worktree_manager as wm
    monkeypatch.setattr(wm, "WORKTREE_BASE", temp_git_repo / "tmp" / "worktrees")

    mgr = WorktreeManager(temp_git_repo)

    with mgr.experiment("test_auto_reject") as ctx:
        ctx.apply_file(
            "orchestration/prompts/frontdoor.md",
            "possibly bad mutation",
        )
        # Deliberately don't call accept() or reject()

    # Original restored
    content = (temp_git_repo / "orchestration" / "prompts" / "frontdoor.md").read_text()
    assert content == "original frontdoor content"


def test_multiple_files(temp_git_repo, monkeypatch):
    """Can apply mutations to multiple files in one experiment."""
    import scripts.autopilot.worktree_manager as wm
    monkeypatch.setattr(wm, "WORKTREE_BASE", temp_git_repo / "tmp" / "worktrees")

    mgr = WorktreeManager(temp_git_repo)

    with mgr.experiment("test_multi") as ctx:
        ctx.apply_file("orchestration/prompts/frontdoor.md", "new frontdoor")
        ctx.apply_file("src/escalation.py", "# new escalation\ndef escalate(): return True\n")
        ctx.reject()

    assert (temp_git_repo / "orchestration" / "prompts" / "frontdoor.md").read_text() == "original frontdoor content"
    assert "original escalation" in (temp_git_repo / "src" / "escalation.py").read_text()


def test_reject_restores_exact_uncommitted_main_worktree_preimage(temp_git_repo, monkeypatch):
    """Rollback preserves the bytes present at apply time, not the HEAD version."""
    import scripts.autopilot.worktree_manager as wm
    monkeypatch.setattr(wm, "WORKTREE_BASE", temp_git_repo / "tmp" / "worktrees")

    target = temp_git_repo / "orchestration" / "prompts" / "frontdoor.md"
    dirty_preimage = b"operator edit not committed\nwith a second line\n"
    target.write_bytes(dirty_preimage)

    with WorktreeManager(temp_git_repo).experiment("test_dirty_preimage") as ctx:
        ctx.apply_file("orchestration/prompts/frontdoor.md", "candidate mutation")
        ctx.reject()

    assert target.read_bytes() == dirty_preimage
    assert "operator edit" in subprocess.run(
        ["git", "diff", "--", "orchestration/prompts/frontdoor.md"],
        cwd=temp_git_repo, capture_output=True, text=True, check=True,
    ).stdout


def test_reject_distinguishes_empty_file_from_absent_file(temp_git_repo, monkeypatch):
    import scripts.autopilot.worktree_manager as wm
    monkeypatch.setattr(wm, "WORKTREE_BASE", temp_git_repo / "tmp" / "worktrees")

    empty = temp_git_repo / "empty.txt"
    empty.write_bytes(b"")
    absent = temp_git_repo / "new.txt"

    with WorktreeManager(temp_git_repo).experiment("test_empty_absent") as ctx:
        ctx.apply_file("empty.txt", "candidate")
        ctx.apply_file("new.txt", "candidate")
        ctx.reject()

    assert empty.exists() and empty.read_bytes() == b""
    assert not absent.exists()
