"""No-inference checks of the three identified live scratch guards."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path('/mnt/raid0/llm/tmp/x0-27b-quants')


class LiveScratchGuards(unittest.TestCase):
    def test_p3_v2_refuses_unsafe_cli_phases(self):
        for phase in ('all', 'a1'):
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'p3_kvu_probe_v2.py'),
                                     '--phase', phase, '--dry-run'], capture_output=True, text=True,
                                    check=False, timeout=5)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('KVU-16h', result.stderr)

    def test_p3_v2_refuses_direct_a1_and_measurement_calls(self):
        code = ("import sys;sys.path.insert(0,sys.argv[1]);import p3_kvu_probe_v2 as p;"
                "getattr(p,sys.argv[2])(*([None]*int(sys.argv[3])))")
        for name, count in [('phase_a1', 1), ('measure_level', 8)]:
            result = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT), name, str(count)],
                                    capture_output=True, text=True, check=False, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('KVU-16h', result.stderr)

    def test_p3_v1_and_slot_helpers_refuse_direct_calls(self):
        slot = Path('/mnt/raid0/llm/tmp/gpu-slot-ak-20261004')
        code = ("import sys;sys.path.insert(0,sys.argv[1]);"
                "m=__import__(sys.argv[2]);getattr(m,sys.argv[3])(*([None]*int(sys.argv[4])))")
        cases = [(ROOT, 'p3_kvu_probe', 'phase_a1', 1), (ROOT, 'p3_kvu_probe', 'measure_level', 7),
                 (slot, 'p3_kvu_probe_slot', 'measure_level', 8)]
        for folder, module, name, count in cases:
            result = subprocess.run([sys.executable, '-B', '-c', code, str(folder), module, name, str(count)],
                                    capture_output=True, text=True, check=False, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('KVU-16h', result.stderr)

    def test_x0_probe_refuses_before_output_or_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'must-not-exist'
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'probe_decode_x0.py'),
                                     '--url', 'http://127.0.0.1:1', '--label', 'test', '--out-dir', str(out)],
                                    capture_output=True, text=True, check=False, timeout=5)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('KVU-16h', result.stderr)
            self.assertFalse(out.exists())

    def test_x0_probe_direct_zero_override_refuses(self):
        code = ("import sys;sys.path.insert(0,sys.argv[1]);import probe_decode_x0 as p;"
                "p.stream_chat({'speculative.n_max':0})")
        result = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT)],
                                capture_output=True, text=True, check=False, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('KVU-16h', result.stderr)

    def test_shape_v2_refuses_probe_before_preflight(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'x0_shape_b_v2.py'),
                                 '--arm', 'q8', '--rep', '1', '--with-probe', '--dry-run'],
                                capture_output=True, text=True, check=False, timeout=5)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('KVU-16h', result.stderr)
        self.assertEqual(result.stdout, '')

    def test_shape_v2_refuses_direct_zero_override(self):
        code = ("import sys;sys.path.insert(0,sys.argv[1]);import x0_shape_b_v2 as s;"
                "s.stream_chat('http://127.0.0.1:1',{'speculative.n_max':0})")
        result = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT)],
                                capture_output=True, text=True, check=False, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('KVU-16h', result.stderr)


if __name__ == '__main__':
    unittest.main()
