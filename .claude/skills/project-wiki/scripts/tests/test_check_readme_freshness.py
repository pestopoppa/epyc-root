"""Repository discovery must work for nested umbrella worktrees."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "check_readme_freshness.py"
SPEC = importlib.util.spec_from_file_location("check_readme_freshness", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class OwnedReposTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "worktrees" / "mains" / "lane"
        self.init_repo(self.root)

    def init_repo(self, path):
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        return path

    def discovered(self):
        return checker.owned_repos(self.root)[1:]

    def test_nested_lane_finds_ancestor_siblings(self):
        expected = [self.init_repo(self.base / name) for name in checker.CHILD_REPOS]
        self.assertEqual(self.discovered(), expected)

    def test_valid_umbrella_entries_take_precedence(self):
        expected = []
        for name in checker.CHILD_REPOS:
            self.init_repo(self.base / name)
            target = self.init_repo(self.base / "explicit" / name)
            entry = self.root / "repos" / name
            entry.parent.mkdir(exist_ok=True)
            entry.symlink_to(target, target_is_directory=True)
            expected.append(entry)
        self.assertEqual(self.discovered(), expected)

    def test_nearest_valid_sibling_wins(self):
        expected = []
        for name in checker.CHILD_REPOS:
            self.init_repo(self.base / name)
            expected.append(self.init_repo(self.root.parent / name))
        self.assertEqual(self.discovered(), expected)

    def test_invalid_entries_and_nonrepo_siblings_are_skipped(self):
        expected = []
        for index, name in enumerate(checker.CHILD_REPOS):
            entry = self.root / "repos" / name
            entry.parent.mkdir(exist_ok=True)
            if index == 0:
                entry.symlink_to(self.base / "missing", target_is_directory=True)
            else:
                entry.mkdir()  # Inside umbrella git repo, but not a repo root.
            (self.root.parent / name).mkdir()
            expected.append(self.init_repo(self.base / name))
        self.assertEqual(self.discovered(), expected)

    def test_missing_repos_preserve_explicit_warning_paths(self):
        # Isolate the missing case from real sibling clones above the temp directory.
        names = (f"missing-{self.base.name}-one", f"missing-{self.base.name}-two")
        with patch.object(checker, "CHILD_REPOS", names):
            self.assertEqual(self.discovered(),
                             [self.root / "repos" / name for name in names])

    def test_git_worktree_is_valid(self):
        source = self.init_repo(self.base / "source")
        subprocess.run(["git", "-C", str(source), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit",
                        "--allow-empty", "-qm", "initial"], check=True)
        worktree = self.root / "repos" / checker.CHILD_REPOS[0]
        subprocess.run(["git", "-C", str(source), "worktree", "add", "--detach",
                        "-q", str(worktree)], check=True)
        self.assertEqual(self.discovered()[0], worktree)


if __name__ == "__main__":
    unittest.main()
