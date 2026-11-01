"""Region binding at the keeper's exclusive grant boundary."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/coordination'))
import loop49_keeper_gate as gate


class GrantRegionBinding(unittest.TestCase):
    def test_relocatable_quarter_accepts_full_quarter_with_smt(self):
        self.assertTrue(gate.validate_regions('any-cpu-quarter', 'q2'))

    def test_relocatable_quarter_rejects_wrong_cpu_slice(self):
        with self.assertRaisesRegex(gate.Refused, 'outside-relocatable'):
            gate.validate_regions('any-cpu-quarter', '0-23')

    def test_relocatable_quarter_rejects_unauthorized_gpu(self):
        with self.assertRaisesRegex(gate.Refused, 'outside-relocatable'):
            gate.validate_regions('any-cpu-quarter', 'q2,mi210_0')

    def test_any_of_is_limited_to_declared_quarters(self):
        self.assertTrue(gate.validate_regions('any-of q1,q3', 'q3'))
        with self.assertRaisesRegex(gate.Refused, 'outside-relocatable'):
            gate.validate_regions('any-of q1,q3', 'q2')

    def test_fixed_regions_require_subset_and_gpu_parity(self):
        self.assertTrue(gate.validate_regions('q1,mi210_0', '24-25,mi210_0'))
        with self.assertRaisesRegex(gate.Refused, 'outside-manifest'):
            gate.validate_regions('q1,mi210_0', '24-25')

    def test_duplicate_and_empty_tokens_refused(self):
        for value in ('q1,q1', 'q1,', ''):
            with self.subTest(value=value), self.assertRaises(gate.Refused):
                gate.validate_regions('any-cpu-quarter', value)

    def test_disk_capacity_uses_manifest_scratch_path(self):
        with tempfile.TemporaryDirectory() as scratch:
            stats = SimpleNamespace(f_bavail=10, f_frsize=1024**3)
            with patch.object(gate.os, 'statvfs', return_value=stats) as statvfs:
                self.assertEqual(gate.free_gib(scratch), 10)
            statvfs.assert_called_once_with(scratch)

    def test_state_uses_scratch_filesystem_for_disk_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); flags = base/'flags'; flags.mkdir(); (flags/'grants').mkdir()
            scratch = base/'job-output'; scratch.mkdir()
            manifest = {'id':'disk-1', 'scratch_root':str(scratch), 'ports':[]}
            options = SimpleNamespace(flags_dir=str(flags), fingerprint_now=False,
                                      allowlist='unused', policy='unused')
            with patch.object(gate, 'options', return_value=options), \
                 patch.object(gate, 'load', return_value=manifest), \
                 patch.object(gate, 'verify'), patch.object(gate, 'manifests', return_value=[]), \
                 patch.object(gate, 'free_gib', return_value=149) as free, \
                 patch.object(gate, 'scheduling_state', return_value='READY-WAIT-DISK') as schedule:
                self.assertEqual(gate.state(base/'manifest.json')[1], 'READY-WAIT-DISK')
            free.assert_called_once_with(scratch)
            self.assertEqual(schedule.call_args.args[2], 149)

    def test_grant_boundary_requires_external_row_id(self):
        with self.assertRaisesRegex(gate.Refused, 'grant-row-id-required'):
            gate.before_grant_unbound(Path('/does/not/matter'), None)
        with patch.object(gate, 'state', return_value=({'id':'row-a'}, 'READY-QUALIFIED')):
            with self.assertRaisesRegex(gate.Refused, 'grant-manifest-row-mismatch'):
                gate.before_grant_unbound(Path('/unused'), 'row-b')


if __name__ == '__main__':
    unittest.main()
