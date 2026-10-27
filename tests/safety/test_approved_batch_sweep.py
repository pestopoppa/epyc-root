import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[2] / 'scripts/safety/approved_batch_sweep.py'
spec = importlib.util.spec_from_file_location('approved_batch_sweep', MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class BatchSweepTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.trash = self.root / 'trash'; self.trash.mkdir()
        self.batch = self.trash / 'kpf18-approved-fixture'; self.batch.mkdir()
        self.container = self.batch / 'unique'; self.container.mkdir()
        self.item = self.container / 'payload'; self.item.mkdir(); (self.item / 'data').write_text('x')
        st = self.item.stat()
        self.source = self.root / 'source.tsv'; self.source.write_text('1\t/example/source\n')
        self.expected_source_sha256 = mod.digest(self.source)
        self.mapping = self.root / 'mapping.json'
        self.mapping.write_text(json.dumps({'entries': [{'source': '/example/source', 'trash_name': 'unique', 'payload_name': 'payload', 'device': st.st_dev, 'inode': st.st_ino}]}))
        self.receipt = self.root / 'receipt.json'
        self.receipt.write_text(json.dumps({'operator_approved': True, 'early_hold_override': True, 'keep_override': True, 'action_checks_passed': True,
            'approval_reference': 'operator-test', 'batch': str(self.batch),
            'source_manifest_sha256': mod.digest(self.source), 'snapshot_sha256': 'a' * 64, 'mapping_sha256': mod.digest(self.mapping)}))
        self.audit = self.root / 'audit'

    def tearDown(self): self.tmp.cleanup()
    def run_sweep(self):
        mod.sweep(self.batch, self.source, self.mapping, self.receipt, self.trash, self.audit,
                  self.expected_source_sha256)
    def test_exact_batch(self):
        self.run_sweep(); self.assertFalse(self.item.exists())
        self.assertEqual(len(self.audit.read_text().splitlines()), 2)
    def test_wrong_manifest(self):
        self.source.write_text('1\t/example/changed\n')
        with self.assertRaises(ValueError): self.run_sweep()
        self.assertTrue(self.item.exists())
    def test_without_approval(self):
        d = json.loads(self.receipt.read_text()); d['early_hold_override'] = False; self.receipt.write_text(json.dumps(d))
        with self.assertRaises(ValueError): self.run_sweep()
        self.assertTrue(self.item.exists())
    def test_symlink_refused(self):
        (self.item / 'data').unlink(); self.item.rmdir(); self.item.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): self.run_sweep()
        self.assertTrue(self.item.is_symlink())
    def test_outside_batch_refused(self):
        self.batch = self.root / 'kpf18-approved-outside'; self.batch.mkdir()
        with self.assertRaises(ValueError): self.run_sweep()
    def test_extra_entry_refused(self):
        (self.batch / 'other').touch()
        with self.assertRaises(ValueError): self.run_sweep()
        self.assertTrue(self.item.exists())
    def test_duplicate_payload_names_in_distinct_containers(self):
        other = self.batch / 'second'; other.mkdir()
        payload = other / 'payload'; payload.mkdir(); (payload / 'data').write_text('y')
        st = payload.stat()
        self.source.write_text('1\t/example/source\n1\t/example/second\n')
        self.expected_source_sha256 = mod.digest(self.source)
        data = json.loads(self.mapping.read_text())
        data['entries'].append({'source': '/example/second', 'trash_name': 'second', 'payload_name': 'payload', 'device': st.st_dev, 'inode': st.st_ino})
        self.mapping.write_text(json.dumps(data))
        receipt = json.loads(self.receipt.read_text()); receipt['source_manifest_sha256'] = mod.digest(self.source); receipt['mapping_sha256'] = mod.digest(self.mapping)
        self.receipt.write_text(json.dumps(receipt))
        self.run_sweep(); self.assertFalse(self.item.exists()); self.assertFalse(payload.exists())
    def test_registered_worktree_is_removed_and_branch_preserved(self):
        repo = self.root / 'repo'; repo.mkdir()
        def git(*args): return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
        git('init', '-q'); git('config', 'user.email', 'fixture@example.invalid'); git('config', 'user.name', 'fixture')
        (repo / 'tracked').write_text('x'); git('add', 'tracked'); git('commit', '-qm', 'fixture')
        git('branch', 'candidate'); head = git('rev-parse', 'candidate')
        other = self.root / 'other-worktree'; git('worktree', 'add', '--detach', str(other))
        (self.item / 'data').unlink(); self.item.rmdir()
        original = self.root / 'original-worktree'
        git('worktree', 'add', str(original), 'candidate')
        git('worktree', 'move', str(original), str(self.item))
        self.assertFalse(original.exists())
        (repo / '.git/info/exclude').write_text('__pycache__/\n')
        (self.item / '__pycache__').mkdir(); (self.item / '__pycache__/test.pyc').write_text('cache')
        st = self.item.stat(); d = json.loads(self.mapping.read_text()); e = d['entries'][0]
        e.update(device=st.st_dev, inode=st.st_ino, branch={'repository': str(repo), 'ref': 'refs/heads/candidate', 'commit': head})
        self.mapping.write_text(json.dumps(d)); receipt = json.loads(self.receipt.read_text()); receipt['mapping_sha256'] = mod.digest(self.mapping); self.receipt.write_text(json.dumps(receipt))
        with patch.object(mod, 'WORKTREE_REFS', {'/example/source': ('candidate', head)}), patch.object(mod, 'WORKTREE_IGNORED', {'/example/source': {'!! __pycache__/'}}), patch.object(mod, 'RESEARCH', str(repo)):
            (self.item / 'unexpected').write_text('not disposable')
            with self.assertRaises(ValueError): self.run_sweep()
            (self.item / 'unexpected').unlink()
            checks = []
            original_check = mod.verify_worktree_clean
            def late_change(path, source):
                checks.append(1)
                if len(checks) == 2: (self.item / 'late-change').write_text('retain')
                return original_check(path, source)
            with patch.object(mod, 'verify_worktree_clean', side_effect=late_change):
                with self.assertRaises(ValueError): self.run_sweep()
            self.assertTrue(self.item.exists()); self.assertEqual(git('rev-parse', 'candidate'), head)
            (self.item / 'late-change').unlink()
            self.run_sweep()
        self.assertFalse(self.item.exists()); self.assertEqual(git('rev-parse', 'candidate'), head); self.assertTrue((other / 'tracked').is_file())
    def test_unexpected_branch_metadata_refused(self):
        d = json.loads(self.mapping.read_text()); d['entries'][0]['branch'] = {'repository': '/tmp', 'ref': 'refs/heads/x', 'commit': 'x'}
        self.mapping.write_text(json.dumps(d)); r = json.loads(self.receipt.read_text()); r['mapping_sha256'] = mod.digest(self.mapping); self.receipt.write_text(json.dumps(r))
        with self.assertRaises(ValueError): self.run_sweep()
        self.assertTrue(self.item.exists())
    def test_unknown_metadata_refused(self):
        d = json.loads(self.mapping.read_text()); d['entries'][0]['unexpected'] = True
        self.mapping.write_text(json.dumps(d)); r = json.loads(self.receipt.read_text()); r['mapping_sha256'] = mod.digest(self.mapping); self.receipt.write_text(json.dumps(r))
        with self.assertRaises(ValueError): self.run_sweep()
        self.assertTrue(self.item.exists())
    def test_missing_action_checks_refused(self):
        r = json.loads(self.receipt.read_text()); r['action_checks_passed'] = False; self.receipt.write_text(json.dumps(r))
        with self.assertRaises(ValueError): self.run_sweep()
        self.assertTrue(self.item.exists())

if __name__ == '__main__': unittest.main()
