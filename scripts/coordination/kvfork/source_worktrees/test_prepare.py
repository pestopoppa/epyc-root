"""Real throwaway repositories prove detached worktree reuse and copy refusal."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('source_worktree_prepare', Path(__file__).with_name('prepare.py'))
mod = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(mod)

class TestPrepare(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.repo = self.root/'repo'; self.repo.mkdir()
        self.git('init', '-q')
        (self.repo/'unit.txt').write_text('source')
        self.git('add', 'unit.txt')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixture')
        self.commit = self.git('rev-parse', 'HEAD')
        self.dest = self.root/'source'
    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()
    def test_detached_creation_and_idempotent_reuse(self):
        first = mod.prepare(self.repo, self.commit, self.dest)
        self.assertTrue((self.dest/'.git').is_file())
        self.assertEqual(first, mod.prepare(self.repo, self.commit, self.dest))
        self.assertEqual(first['source_commit'], self.commit)
    def test_checkout_copy_and_dirty_worktree_refused(self):
        self.dest.mkdir(); (self.dest/'unit.txt').write_text('source')
        with self.assertRaisesRegex(ValueError, 'registered worktree'):
            mod.prepare(self.repo, self.commit, self.dest)
        (self.dest/'unit.txt').unlink(); self.dest.rmdir()
        mod.prepare(self.repo, self.commit, self.dest)
        (self.dest/'unit.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'dirty'):
            mod.prepare(self.repo, self.commit, self.dest)
    def test_wrong_commit_refused(self):
        mod.prepare(self.repo, self.commit, self.dest)
        (self.repo/'unit.txt').write_text('new'); self.git('add', 'unit.txt')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'next')
        with self.assertRaisesRegex(ValueError, 'commit changed'):
            mod.prepare(self.repo, 'HEAD', self.dest)

if __name__ == '__main__': unittest.main()
