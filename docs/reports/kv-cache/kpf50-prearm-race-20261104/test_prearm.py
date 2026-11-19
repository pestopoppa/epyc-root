import subprocess
import sys
import unittest
from pathlib import Path


class PreArmParentDeath(unittest.TestCase):
    def test_child_refuses_after_original_parent_dies_before_arm(self):
        p = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('prearm_fixture.py'))],
                           text=True, capture_output=True, timeout=8)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('PREARM_PARENT_LOSS_REFUSED_AND_REAPED', p.stdout)


if __name__ == '__main__':
    unittest.main()
