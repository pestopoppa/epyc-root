"""Real, tiny Git operations exercise prospective capture; no production clone."""
import importlib.util
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ch18_capture", ROOT / "scripts/vidya/producers/ch18_merge_trial.py")
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


@pytest.mark.parametrize("conflict", [True, False])
@pytest.mark.parametrize("cleanup_failure", [True, False])
def test_live_native_boundary_and_cleanup(conflict, cleanup_failure, monkeypatch):
    with tempfile.TemporaryDirectory(prefix=".ch18-test-", dir=ROOT) as temp:
        root = Path(temp)
        repo = root / "disposable"
        repo.mkdir()

        def git(*args):
            return subprocess.check_output(["git", "-c", "user.name=Test", "-c", "user.email=test@invalid",
                                            *args], cwd=repo).decode().strip()

        git("init", "-q")
        (repo / "item").write_text("original\n")
        git("add", "item")
        git("commit", "-qm", "ancestor")
        ancestor = git("rev-parse", "HEAD")
        (repo / "item").write_text("production\n")
        git("commit", "-qam", "production")
        base = git("rev-parse", "HEAD")
        git("checkout", "-q", "--detach", ancestor)
        (repo / ("item" if conflict else "new")).write_text("upstream\n")
        git("add", ".")
        git("commit", "-qm", "upstream")
        upstream = git("rev-parse", "HEAD")
        output = root / "merge_trial.json"
        real_run = capture.subprocess.run

        def run(argv, **kwargs):
            assert "--force" not in argv
            if cleanup_failure and "worktree" in argv and "remove" in argv:
                return subprocess.CompletedProcess(argv, 1, b"", b"simulated cleanup refusal")
            return real_run(argv, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(capture.subprocess, "run", run)
            rec = capture.capture(repo, base, upstream, output)
        assert rec["state"] == ("incomplete" if cleanup_failure else "complete")
        assert rec["conflicting_paths"] == (["item"] if conflict else [])
        assert rec["cleanup"] == {"worktree_removed": not cleanup_failure, "merge_aborted": True}
        assert git("rev-parse", "HEAD") == upstream
        assert not git("status", "--porcelain")
        assert len(capture.reader.native_rows(output)) == (0 if cleanup_failure else 1)
        assert bool(capture.reader.frames_for_path(output, as_of=rec["completed_at"])) is not cleanup_failure
        if cleanup_failure:
            (remaining,) = root.glob("ch18-trial-*")
            git("worktree", "remove", str(remaining))
        assert not list(root.glob("ch18-trial-*"))
        with pytest.raises(ValueError, match="replace"):
            capture.capture(repo, base, upstream, output)


def test_external_clone_refused(tmp_path):
    with pytest.raises(ValueError, match="inside this lane"):
        capture.capture(tmp_path, "a" * 40, "b" * 40, tmp_path / "merge_trial.json")


def test_publication_is_no_replace_and_cleans_pending(tmp_path):
    output = tmp_path / "record.json"
    capture.publish_record(output, {"state": "incomplete"})
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        capture.publish_record(output, {"state": "complete"})
    assert output.read_bytes() == original
    assert not list(tmp_path.glob(".ch18-record-*"))


def test_external_core_worktree_redirect_refused(tmp_path):
    with tempfile.TemporaryDirectory(prefix=".ch18-redirect-test-", dir=ROOT) as temp:
        root = Path(temp)
        repo = root / "disposable"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        marker = tmp_path / "external-marker"
        marker.write_text("untouched\n")
        subprocess.run(["git", "-C", str(repo), "config", "core.worktree", str(tmp_path)], check=True)
        with pytest.raises(ValueError, match="top-level"):
            capture.capture(repo, "a" * 40, "b" * 40, root / "merge_trial.json")
        assert marker.read_text() == "untouched\n"
        assert not (root / "merge_trial.json").exists()
        assert not list(root.glob("ch18-trial-*"))
