"""The KPF-20 grant precondition must reject hidden changes in a real worktree."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1] / 'kvfork'


class HiddenSourceTest(unittest.TestCase):
    def test_all_kpf20_versions_reject_hidden_tracked_changes(self):
        scratch = Path('/mnt/raid0/llm/tmp/kvfork')
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch, prefix='kpf20-index-flags-') as temp:
            root = Path(temp)
            repo = root / 'repo'
            repo.mkdir()
            def git(where, *args):
                return subprocess.check_output(['git', '-C', str(where), *args], text=True).strip()
            git(repo, 'init', '-q')
            git(repo, 'config', 'user.name', 'Fixture')
            git(repo, 'config', 'user.email', 'fixture@example.invalid')
            (repo / 'scripts').mkdir()
            wrapper = repo / 'scripts/gitnexus-analyze.sh'
            wrapper.write_text('# fixture\n')
            git(repo, 'add', 'scripts/gitnexus-analyze.sh')
            git(repo, '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixture')
            commit = git(repo, 'rev-parse', 'HEAD')
            source = root / 'source'
            git(repo, 'worktree', 'add', '--detach', str(source), commit)
            try:
                for name in ('kpf20', 'kpf20_v2', 'kpf20_v3'):
                    original = (ROOT / name / 'job.py').read_text()
                    source_line = next(x for x in original.splitlines() if x.startswith('TREE=Path('))
                    head_line = next(x for x in original.splitlines() if x.startswith('HEAD='))
                    script = root / (name + '.py')
                    script.write_text(original.replace(source_line, f'TREE=Path({str(source)!r})')
                                      .replace(head_line, f'HEAD={commit!r}'))
                    clean = subprocess.run([sys.executable, str(script), '--check'], capture_output=True, text=True)
                    self.assertEqual(clean.returncode, 0, clean.stderr)
                    for flag, undo in (('--assume-unchanged', '--no-assume-unchanged'),
                                       ('--skip-worktree', '--no-skip-worktree')):
                        with self.subTest(version=name, flag=flag):
                            git(source, 'update-index', flag, 'scripts/gitnexus-analyze.sh')
                            (source / 'scripts/gitnexus-analyze.sh').write_text('# tampered\n')
                            check = subprocess.run([sys.executable, str(script), '--check'], capture_output=True, text=True)
                            self.assertNotEqual(check.returncode, 0)
                            self.assertIn('hidden index flags', check.stderr)
                            (source / 'scripts/gitnexus-analyze.sh').write_text('# fixture\n')
                            git(source, 'update-index', undo, 'scripts/gitnexus-analyze.sh')
            finally:
                git(repo, 'worktree', 'remove', '--force', str(source))


if __name__ == '__main__':
    unittest.main()
