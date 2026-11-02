"""Offline contract tests against rowflow's real serializers; no keeper is started."""
import datetime as dt
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

guard = load('vkq3_guard', Path(__file__).with_name('guard.py'))
rowflow = load('rowflow_contract', ROOT / 'scripts/coordination/rowflow/rowflow.py')

class GuardContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.root = Path(self.tmp.name)
        (self.root / 'grants').mkdir()
        self.addCleanup(self.tmp.cleanup)
        self.rid = 'vkq3-test'
        self.now = 1793613600  # minute-aligned
        self.end = self.now + 3600
        self.env = {'FILLER_ID': self.rid, 'FILLER_NEEDGPU': '0',
                    'FILLER_CPUS': '0-95', 'FILLER_END': str(self.end),
                    'FILLER_DEADLINE': str(self.end - 90),
                    'FILLER_STOPFILE': str(self.root / 'engine-stop')}
        self.path = self.root / 'grants' / (self.rid + '.grant')

    def make(self):
        return guard.GrantGuard(self.env, self.root / 'grants', self.root / 'local-stop',
                                expected_id=self.rid, clock=lambda: self.now)

    def dry(self, regions='0-23', holds=frozenset()):
        start = dt.datetime.fromtimestamp(self.now - 60, dt.timezone.utc)
        end = dt.datetime.fromtimestamp(self.end, dt.timezone.utc)
        self.path.write_text(rowflow.dryrun_grant_text(self.rid, 'correctness', regions, holds, start, end))
        self.env.update(FILLER_DRYRUN='1', FILLER_CPUS=regions)

    def test_real_arm_serializer_and_missing_mode(self):
        # write_grant uses its real clock; pin it by deriving the expected end from its output.
        rowflow.write_grant(str(self.root), self.rid, '0-95', set(), 3600)
        regions, start, end = guard.parse_grant(self.path.read_bytes(), self.rid, False)
        self.now = start + 60
        self.env.update(FILLER_END=str(end), FILLER_DEADLINE=str(end - 90))
        self.assertEqual(regions, '0-95')
        self.assertIn(b'holds=\n', self.path.read_bytes())
        g = self.make()
        self.assertEqual(g.mode, 'full')
        self.assertFalse(g.check())
        self.env['FILLER_DRYRUN'] = '0'
        self.assertEqual(self.make().mode, 'full')
        self.path.unlink()
        self.assertTrue(g.check())
        self.assertEqual(g.reason, 'grant_lost')

    def test_real_arm_rejects_partial_and_dryrun_metadata(self):
        self.dry()
        self.env.pop('FILLER_DRYRUN')
        with self.assertRaises(ValueError): self.make()
        self.path.write_text(self.path.read_text().split(' holds=')[0] + '\n')
        with self.assertRaises(ValueError): self.make()

    def test_dryrun_keeper_serializer_and_revocation(self):
        self.dry(holds={'q0', 'gpu-quiet'})
        g = self.make()
        self.assertEqual(g.mode, 'qualification')
        self.assertFalse(g.check())
        self.path.write_bytes(self.path.read_bytes() + b' ')
        self.assertTrue(g.check())
        self.assertEqual(g.reason, 'grant_changed')

    def test_dryrun_q0_launcher_mapping_and_mode_binding(self):
        self.dry(regions='q0')
        self.env['FILLER_CPUS'] = '0-23,96-111'
        self.assertEqual(self.make().mode, 'qualification')
        self.env['FILLER_CPUS'] = '0-23'
        with self.assertRaises(ValueError): self.make()
        self.env['FILLER_CPUS'] = '0-23,96-111'
        self.env['FILLER_DRYRUN'] = '0'
        with self.assertRaises(ValueError): self.make()
        self.env['FILLER_DRYRUN'] = 'unexpected'
        with self.assertRaises(ValueError): self.make()

    def test_dryrun_identity_and_cpu_mismatch_refused(self):
        self.dry()
        self.path.write_text(self.path.read_text().replace('id=vkq3-test', 'id=other'))
        with self.assertRaises(ValueError): self.make()
        self.dry()
        self.path.write_text(self.path.read_text().split(' schema=')[0] + '\n')
        with self.assertRaises(ValueError): self.make()
        self.dry()
        self.env['FILLER_CPUS'] = '0-95'
        with self.assertRaises(ValueError): self.make()

    def test_stop_and_deadline(self):
        self.dry()
        g = self.make()
        (self.root / 'engine-stop').touch()
        self.assertTrue(g.check())
        self.assertEqual(g.reason, 'stop')
        (self.root / 'engine-stop').unlink()
        g = self.make()
        self.now = self.end - 120
        self.assertTrue(g.check())
        self.assertEqual(g.reason, 'deadline')

if __name__ == '__main__': unittest.main()
