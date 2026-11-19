"""Offline reservation and crash/retry tests; no target or model is run."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from exposure_ledger import PairedExposure

P = 'a' * 64
S = 'b' * 64
ARMS = ('hybrid', 'legacy')


class ExposureTests(unittest.TestCase):
    def test_paired_attempt_can_reserve_both_once_but_cannot_restart(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as root:
            attempt = PairedExposure(root, P, S, ARMS)
            with self.assertRaises(ValueError):
                attempt.reserve_arm('legacy')
            attempt.reserve_arm('hybrid')
            with self.assertRaises(ValueError):
                attempt.reserve_arm('hybrid')
            attempt.reserve_arm('legacy')
            attempt.close()
            self.assertEqual({p.name for p in (Path(root)/P).iterdir()},
                             {'attempt.json', 'hybrid.json', 'legacy.json'})
            with self.assertRaises(FileExistsError):
                PairedExposure(root, P, S, ARMS)

    def test_crashed_attempt_burns_prompt_across_process_restart(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as root:
            code = ('import os,sys; from exposure_ledger import PairedExposure; '
                    'x=PairedExposure(sys.argv[1],"a"*64,"b"*64,("hybrid","legacy")); '
                    'x.reserve_arm("hybrid"); os._exit(17)')
            child = subprocess.run([sys.executable, '-B', '-c', code, root], check=False)
            self.assertEqual(child.returncode, 17)
            with self.assertRaises(FileExistsError):
                PairedExposure(root, P, S, ARMS)
            self.assertTrue((Path(root)/P/'hybrid.json').exists())
            self.assertFalse((Path(root)/P/'legacy.json').exists())

    def test_wrong_order_and_untrusted_root_fail_before_reserving(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as root:
            with self.assertRaises(ValueError):
                PairedExposure(root, P, S, ('legacy', 'hybrid'))
            os.chmod(root, 0o755)
            with self.assertRaises(ValueError):
                PairedExposure(root, P, S, ARMS)
            self.assertFalse((Path(root)/P).exists())
            os.chmod(root, 0o700)

    def test_different_plans_cannot_reuse_a_prompt(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as root:
            attempt = PairedExposure(root, P, S, ARMS)
            attempt.close()
            with self.assertRaises(FileExistsError):
                PairedExposure(root, P, 'c'*64, ARMS)


if __name__ == '__main__':
    unittest.main()
