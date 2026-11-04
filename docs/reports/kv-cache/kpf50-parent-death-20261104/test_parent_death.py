import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class ParentDeathTest(unittest.TestCase):
    def test_outer_sigkill_cascades_to_direct_window_child(self):
        result = subprocess.run(
            [sys.executable, '-B', str(HERE / 'parent_death_fixture.py')],
            capture_output=True, text=True, timeout=12,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('captured children reaped', result.stdout)


if __name__ == '__main__':
    unittest.main()
