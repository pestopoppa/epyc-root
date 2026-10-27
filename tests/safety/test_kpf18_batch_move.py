import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SAFETY = Path(__file__).resolve().parents[2] / 'scripts/safety'
sys.path.insert(0, str(SAFETY))
import kpf18_batch_move as mover
import approved_batch_sweep as sweeper


class BatchLifecycleTest(unittest.TestCase):
    def test_two_same_basename_and_worktree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); trash = root / 'trash'; trash.mkdir()
            repo = root / 'repo'; repo.mkdir()
            def git(*args): return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
            git('init', '-q'); git('config', 'user.email', 'fixture@example.invalid'); git('config', 'user.name', 'fixture')
            (repo / 'tracked').write_text('x'); git('add', 'tracked'); git('commit', '-qm', 'fixture')
            git('branch', 'candidate'); commit = git('rev-parse', 'candidate')
            wt = root / 'worktree'; git('worktree', 'add', str(wt), 'candidate')
            (repo / '.git/info/exclude').write_text('__pycache__/\n')
            (wt / '__pycache__').mkdir(); (wt / '__pycache__/test.pyc').write_text('cache')
            other = root / 'other'; git('worktree', 'add', '--detach', str(other))
            a = root / 'a' / 'same'; b = root / 'b' / 'same'; a.mkdir(parents=True); b.mkdir(parents=True)
            (a / 'x').write_text('a'); (b / 'x').write_text('b')
            sources = [a, b, wt]
            manifest = root / 'source.tsv'; manifest.write_text(''.join('1\t%s\n' % p for p in sources))
            manifest_sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
            snapshot = root / 'snapshot.json'
            snapshot.write_text(json.dumps({'source_manifest_sha256': manifest_sha,
                'entries': [{'source': str(p), 'device': p.stat().st_dev, 'inode': p.stat().st_ino} for p in sources]}))
            batch = trash / 'kpf18-approved-test'; receipt = root / 'approval.json'
            receipt.write_text(json.dumps({'operator_approved': True, 'early_hold_override': True, 'keep_override': True,
                'action_checks_passed': True, 'approval_reference': 'fixture', 'source_manifest_sha256': manifest_sha,
                'snapshot_sha256': mover.sha(snapshot), 'batch': str(batch)}))
            refs = {str(wt): ('candidate', commit)}
            args = ['kpf18_batch_move.py', str(manifest), str(snapshot), str(batch), '--apply', str(receipt)]
            audit = root / 'audit'
            with patch.object(mover, 'TRASH', trash), patch.object(mover, 'RESEARCH', str(repo)), \
                 patch.object(mover, 'APPROVED_SOURCE_SHA256', manifest_sha), patch.object(mover, 'WORKTREE_REFS', refs), \
                 patch.object(sweeper, 'WORKTREE_IGNORED', {str(wt): {'!! __pycache__/'}}), \
                 patch.object(sys, 'argv', args), patch.dict(os.environ, {'SAFETY_AUDIT_LOG': str(audit)}):
                with contextlib.redirect_stdout(io.StringIO()): mover.main()
            self.assertTrue(all(not p.exists() for p in sources))
            mapping = Path(str(batch) + '.mapping.json'); derived = Path(str(batch) + '.receipt.json')
            with patch.object(sweeper, 'WORKTREE_REFS', refs), patch.object(sweeper, 'RESEARCH', str(repo)), \
                 patch.object(sweeper, 'WORKTREE_IGNORED', {str(wt): {'!! __pycache__/'}}):
                sweeper.sweep(batch, manifest, mapping, derived, trash, audit, manifest_sha)
            self.assertEqual(git('rev-parse', 'candidate'), commit)
            self.assertTrue((other / 'tracked').is_file())
            self.assertEqual(list(batch.iterdir()), [])

if __name__ == '__main__': unittest.main()
