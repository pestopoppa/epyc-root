import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest

P=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ctc-qd-activation-prep')
spec=importlib.util.spec_from_file_location('test_packet', P/'test_packet.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class Adoption(mod.Packet):
    def exercise(self, change):
        g=self.base/'grants'; g.mkdir(); rid='codex-ni-old'; pid=str(os.getpid())
        queue=self.base/'ws58-gpu.queue'; queue.write_text(f'{rid}|{pid}|900|600|4|^ *gpu-quiet|mi210_0,184-191\n')
        grant=g/(rid+'.grant'); grant.write_text('regions=mi210_0,184-191 start=2026-10-27T16:00Z end=2026-10-27T18:00Z\n')
        stamp=self.base/('.wsg-granted-'+rid)
        rl=self.base/'region-lock'; rl.write_text('#!/bin/sh\nexit 0\n'); rl.chmod(0o755)
        fd=os.open(self.base/'.publication.lock', os.O_RDWR); fcntl.flock(fd,fcntl.LOCK_EX)
        env=dict(os.environ, CTCQD_FLAGS=str(self.base), CTCQD_RL=str(rl), CTCQD_GATE=str(P/'packet/registration_gate.py'))
        proc=subprocess.Popen(['bash', str(P/'packet/grant-gpu-1026-v13.sh')], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        log=self.base/'grant-gpu-1026-v13.log'
        try:
            time.sleep(.7); self.assertIsNone(proc.poll()); self.assertFalse(stamp.exists())
            if change=='row':
                row=self.a[:]; row[-1]='rearmed'; (self.base/'FILLERS.md').write_text(self.table([row]))
            elif change=='queue': queue.write_text(queue.read_text().replace('|900|', '|901|'))
            elif change=='grant': grant.write_text(grant.read_text().replace('18:00Z','19:00Z'))
            elif change=='pending': (self.base/mod.gate.PENDING).write_text('{}')
            os.close(fd); fd=None
            expected='adopted open grant' if change is None else 'adoption skipped: state changed or pending'
            deadline=time.monotonic()+3
            while (not log.exists() or expected not in log.read_text()) and time.monotonic()<deadline: time.sleep(.05)
            self.assertIn(expected, log.read_text())
            self.assertEqual(stamp.exists(), change is None)
            if change is None: self.assertEqual(stamp.stat().st_mtime_ns, grant.stat().st_mtime_ns)
        finally:
            if fd is not None: os.close(fd)
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)
    def test_adopt(self): self.exercise(None)
    def test_row_race(self): self.exercise('row')
    def test_queue_race(self): self.exercise('queue')
    def test_grant_race(self): self.exercise('grant')
    def test_pending(self): self.exercise('pending')

if __name__=='__main__':
    suite=unittest.TestSuite(Adoption(n) for n in ('test_adopt','test_row_race','test_queue_race','test_grant_race','test_pending'))
    sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
