import subprocess
import sys
import unittest
from pathlib import Path


class NestedCounterexample(unittest.TestCase):
    def test_grandchild_survives_direct_parent_death(self):
        script = Path(__file__).with_name('nested_counterexample.py')
        result = subprocess.run([sys.executable, '-B', str(script)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('nested grandchild survived parent-death kill', result.stdout)


if __name__ == '__main__':
    unittest.main()
