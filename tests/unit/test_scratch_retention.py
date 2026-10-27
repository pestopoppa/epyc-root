"""Focused checks for scratch retention declaration and path confinement."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('validate_fillers', ROOT / 'scripts/coordination/validate_fillers.py')
vf = importlib.util.module_from_spec(spec); spec.loader.exec_module(vf)
spec = importlib.util.spec_from_file_location('reclaim_filler_scratch', ROOT / 'scripts/safety/reclaim_filler_scratch.py')
reclaim = importlib.util.module_from_spec(spec); spec.loader.exec_module(reclaim)

class RetentionTests(unittest.TestCase):
    def test_safe_declaration(self):
        self.assertEqual(vf.scratch_retention_violations('scratch_root=/tmp/x; raw_globs=cache/**; keep_globs=proof.json'), [])
    def test_root_broad_patterns(self):
        for keep in ('*', '**', '**/*', '/tmp/x', '/tmp/x/**', 'results/**'):
            with self.subTest(keep=keep):
                self.assertTrue(vf.scratch_retention_violations('scratch_root=/tmp/x; raw_globs=cache/**; keep_globs=' + keep))
    def test_empty_raw_refused(self):
        self.assertTrue(vf.scratch_retention_violations('scratch_root=/tmp/x; raw_globs=; keep_globs=proof.json'))
    def test_duplicate_field_refused(self):
        self.assertTrue(vf.scratch_retention_violations('scratch_root=/tmp/x; scratch_root=/tmp/y; raw_globs=x'))
    def test_outside_pattern_refused(self):
        with self.assertRaises(ValueError): reclaim.patterns(Path('/tmp/x'), '../secret')
        with self.assertRaises(ValueError): reclaim.patterns(Path('/tmp/x'), '/tmp/elsewhere/*')
    def test_keep_marker_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); sub = root / 'sub'; sub.mkdir(); (root / 'KEEP').write_text('keep')
            with patch.object(reclaim, 'SCRATCH', root):
                with self.assertRaises(ValueError): reclaim.no_keep_marker(sub / 'file', root)
    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); (root / 'link').symlink_to('/tmp')
            with self.assertRaises(ValueError): reclaim.no_symlinks(root / 'link' / 'x', root)

    def test_filing_only_raw_minus_keep(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); scratch = root / 'scratch'; scratch.mkdir(); job = scratch / 'job'; job.mkdir()
            (job / 'cache').mkdir(); (job / 'cache' / 'delete.bin').write_text('cache')
            (job / 'cache' / 'keep.json').write_text('evidence')
            trash = root / 'trash'; trash.mkdir(); handoffs = root / 'handoffs'; handoffs.mkdir(); (root / 'grants').mkdir()
            notes = f'scratch_root={job}; raw_globs=cache/*; keep_globs=cache/keep.json'
            row = ['row1', 'owner', 'launcher', 'cpu', '1s', '1', '-', 'COMPLETE', 'block-correctness', '1s', '1s', 'n', 'n', '/tmp/prior', 'decision', 'exact', 'cpu', notes]
            header = '| ' + ' | '.join(vf.COLUMNS) + ' |\n'; queue = root / 'FILLERS.md'
            queue.write_text(header + '| ' + ' | '.join(row) + ' |\n')
            def fake_run(argv, env, check):
                src = Path(argv[-1]); src.rename(Path(env['TRASH_ROOT']) / src.name)
            with patch.object(reclaim, 'FLAGS', queue), patch.object(reclaim, 'SCRATCH', scratch), patch.object(reclaim, 'TRASH', trash), patch.object(reclaim, 'HANDOFFS', handoffs), patch.object(reclaim, 'GRANTS', root / 'grants'), patch.object(reclaim, 'no_holders'), patch.object(reclaim.subprocess, 'run', side_effect=fake_run), patch.object(sys, 'argv', ['reclaim', 'row1', '--apply']):
                reclaim.main()
            self.assertTrue((job / 'cache' / 'keep.json').exists())
            self.assertFalse((job / 'cache' / 'delete.bin').exists())
            self.assertEqual(len(list(trash.glob('*/item-*/*'))), 1)

if __name__ == '__main__': unittest.main()
