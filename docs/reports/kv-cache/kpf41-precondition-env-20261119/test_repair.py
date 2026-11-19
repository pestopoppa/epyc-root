"""Execute the real custody precondition without engine-populated FILLER_ID."""
import os
from pathlib import Path
import shlex
import subprocess
import unittest

import repair


def precondition(raw):
    line = next(s for s in raw.decode().splitlines() if s.startswith('exec bash '))
    words = shlex.split(line)
    return words[words.index('--precond-cmd')+1].replace('$D', str(repair.BASE))


class Precondition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Recover the pinned predecessor from the repair once installed, so
        # the regression control remains reproducible after publication.
        raw = (repair.BASE/'launch.sh').read_bytes()
        new = b'&& env FILLER_ID='+repair.ROW.encode()+b" python3 '$D/job.py' --check\""
        old = b"&& python3 '$D/job.py' --check\""
        cls.old = raw.replace(new, old)
        cls.fixed = repair.repaired(cls.old)

    def run_check(self, raw):
        env = dict(os.environ)
        env.pop('FILLER_ID', None)
        return subprocess.run(['bash','-c',precondition(raw)], env=env,
                              capture_output=True, text=True, timeout=20)

    def test_predecessor_reproduces_missing_identity(self):
        result = self.run_check(self.old)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("KeyError: 'FILLER_ID'", result.stderr)

    def test_repaired_precondition_passes_before_engine_exports(self):
        result = self.run_check(self.fixed)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_source_drift_refused(self):
        with self.assertRaises(ValueError):repair.repaired(self.old+b'\n')


if __name__ == '__main__':unittest.main()
