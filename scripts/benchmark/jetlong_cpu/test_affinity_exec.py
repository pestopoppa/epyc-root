import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

WRAPPER = Path(__file__).with_name('affinity_exec.py')

class TestAffinityExec(unittest.TestCase):
    def test_exact_mask_is_inherited_by_exec(self):
        cpu = min(os.sched_getaffinity(0))
        cmd = [sys.executable, str(WRAPPER), str(cpu), '--', sys.executable, '-c',
               'import os,json; print(json.dumps(sorted(os.sched_getaffinity(0))))']
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(out.stdout), [cpu])

    def test_outside_mask_refuses_to_exec(self):
        cpu = max(os.sched_getaffinity(0)) + 1
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / 'executed'
            cmd = [sys.executable, str(WRAPPER), str(cpu), '--', sys.executable, '-c',
                   f'from pathlib import Path; Path({str(marker)!r}).touch()']
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())

if __name__ == '__main__':
    unittest.main()
