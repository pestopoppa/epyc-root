"""Installed R7 enrollment with real retained verifier; inert witness/gate."""
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


class InstalledRetainedR7(unittest.TestCase):
    def test_nondry_accepted_r7_and_pre_witness_refusals(self):
        for mode in ('pass', 'digest', 'stat', 'metadata', 'r7missing',
                     'r7wrong', 'unknown', 'projection'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, '-I', '-B', __file__, '--worker', mode],
                                        capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        from test_nondry_entry import worker
        worker(sys.argv[2], retained=True)
    else: unittest.main()
