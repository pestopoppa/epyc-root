"""Preparation and grant-time checks reject copied or altered sources."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from source_worktrees import inventory, prepare, verify

HERE = Path(__file__).resolve().parent


class SourceWorktrees(unittest.TestCase):
    def setUp(self):
        scratch = Path('/mnt/raid0/llm/tmp/kvfork')
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch, prefix='cpu-source-fixture-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        (self.repo / 'source.cpp').write_text('first\n')
        self.git('add', 'source.cpp')
        self.git('commit', '-qm', 'first')
        self.first = self.git('rev-parse', 'HEAD')
        self.first_files = {'source.cpp': hashlib.sha256(b'first\n').hexdigest()}
        (self.repo / 'source.cpp').write_text('second\n')
        self.git('commit', '-qam', 'second')
        self.second = self.git('rev-parse', 'HEAD')
        self.expected = {'commit': self.first, 'files': self.first_files}

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def test_prepare_is_detached_and_clean_and_rejects_reuse(self):
        source = self.root / 'source'
        prepare(self.repo, source, self.expected)
        verify(source, self.expected, self.repo)
        self.assertTrue((source / '.git').is_file())
        self.assertEqual(inventory(source), self.first_files)
        with self.assertRaises(FileExistsError):
            prepare(self.repo, source, self.expected)
        self.git('worktree', 'remove', str(source))

    def test_copy_missing_git_and_staged_tampering_refused(self):
        source = self.root / 'source'
        source.mkdir()
        (source / 'source.cpp').write_text('first\n')
        with self.assertRaisesRegex(ValueError, 'prepared git worktree'):
            verify(source, self.expected, self.repo)
        (source / 'source.cpp').unlink()
        source.rmdir()
        prepare(self.repo, source, self.expected)
        (source / 'source.cpp').write_text('tampered\n')
        subprocess.run(['git', '-C', str(source), 'add', 'source.cpp'], check=True)
        with self.assertRaisesRegex(ValueError, 'dirty'):
            verify(source, self.expected, self.repo)
        self.git('worktree', 'remove', '--force', str(source))

    def test_bad_manifest_removes_own_failed_worktree(self):
        source = self.root / 'source'
        with self.assertRaisesRegex(ValueError, 'inventory'):
            prepare(self.repo, source, {'commit': self.first, 'files': {}})
        self.assertFalse(source.exists())
        self.assertNotIn(str(source), self.git('worktree', 'list', '--porcelain'))

    def test_full_preparation_and_runner_precondition_without_archives(self):
        old = self.root / 'predecessor'
        for name in ('input', 'out'):
            (old / name).mkdir(parents=True)
        (old / 'input/original.cpp').write_text('harness\n')
        (old / 'input/shared.cpp').write_text('harness shared\n')
        for name in ('filler_run15.sh', 'filler_lib.sh'):
            (old / name).write_text('# fixture\n')
        second_files = {'source.cpp': hashlib.sha256(b'second\n').hexdigest()}
        (old / 'identity.json').write_text(json.dumps({'reviewed': True, 'sources': {
            'baseline': self.expected,
            'champion': {'commit': self.second, 'files': second_files}}}))
        dest = self.root / 'capsule'
        subprocess.run([sys.executable, str(HERE / 'prepare.py'), '--destination', str(dest),
                        '--predecessor', str(old), '--source-repository', str(self.repo)], check=True)
        self.assertFalse(list((dest / 'sources').glob('*.tar')))
        subprocess.run([sys.executable, str(dest / 'job.py'), '--check'], check=True)
        for arm in ('baseline', 'champion'):
            self.git('worktree', 'remove', str(dest / 'sources' / arm))
