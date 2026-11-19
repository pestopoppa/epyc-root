import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parent

class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flags = Path(self.tmp.name) / 'flags'
        (self.flags / 'grants').mkdir(parents=True)
        lock = types.ModuleType('lock_witness')
        lock.capture_gpu = lambda: ('owner', 'identity')
        lock.verify_gpu = lambda *args: True
        smoke = types.ModuleType('publisher_smoke')
        smoke.context = lambda base: (self.cpus, 2000)
        self.modules = patch.dict(sys.modules, {'lock_witness': lock, 'publisher_smoke': smoke})
        self.modules.start()
        self.cpus = {0, 1, 2, 3}
        self.mods = []
        for name in ('original', 'corrected'):
            spec = importlib.util.spec_from_file_location('fixture_' + name, BASE / (name + '.py'))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.FLAGS = self.flags
            self.mods.append(mod)
        self.clock = patch('time.time', return_value=1000)
        self.disk = patch('shutil.disk_usage', return_value=types.SimpleNamespace(free=300*1024**3))
        self.clock.start(); self.disk.start()

    def tearDown(self):
        self.disk.stop(); self.clock.stop(); self.modules.stop(); self.tmp.cleanup()

    def grant(self, region, start='1970-01-01T00:00:00+00:00', end='1970-01-01T00:25:00+00:00'):
        (self.flags/'grants'/'other.grant').write_text(f'regions={region} start={start} end={end}\n')
        cells = ['other'] + ['x'] * 17
        cells[5] = '1'; cells[8] = 'block-correctness'
        (self.flags/'FILLERS.md').write_text('| ' + ' | '.join(cells) + ' |\n')

    def test_quarter_overlap_original_bypass_corrected_refuses(self):
        for q in range(4):
            for cpu in (q*24, 96+q*24, 119+q*24):
                with self.subTest(q=q, cpu=cpu):
                    self.cpus = {cpu}; self.grant('q'+str(q))
                    self.assertTrue(self.mods[0].check())
                    with self.assertRaisesRegex(RuntimeError, 'overlaps'):
                        self.mods[1].check()

    def test_quarter_nonoverlap(self):
        self.cpus={0,1,2,3}; self.grant('q1')
        self.assertTrue(self.mods[1].check())

    def test_expired_overlap(self):
        self.grant('q0', end='1970-01-01T00:15:00+00:00')
        self.assertTrue(self.mods[1].check())

    def test_explicit_cpu_overlap(self):
        self.grant('2-5')
        with self.assertRaisesRegex(RuntimeError, 'overlaps'):
            self.mods[1].check()

    def test_gpu_conflict(self):
        self.grant('mi210_0')
        with self.assertRaisesRegex(RuntimeError, 'GPU grant overlap'):
            self.mods[1].check()

    def test_malformed_region_refused(self):
        self.grant('q4')
        with self.assertRaisesRegex(RuntimeError, 'unknown grant region'):
            self.mods[1].check()

    def test_hold_refused(self):
        (self.flags/'HOLD_TEST').touch()
        with self.assertRaisesRegex(RuntimeError, 'global HOLD'):
            self.mods[1].check()

if __name__ == '__main__':
    unittest.main()
