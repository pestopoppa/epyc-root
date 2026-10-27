import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
import fcntl
import signal
import json

PACKET = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ctc-qd-activation-prep/packet')
spec = importlib.util.spec_from_file_location('packettests', PACKET.parent / 'test_packet.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class Writers(mod.Packet):
    def exercise(self, gpu, pending=False, stale=False, registered=False):
        (self.base / 'grants').mkdir()
        (self.base / 'grant_ok.sh').write_text('#!/bin/sh\necho class=block-correctness\n'); (self.base / 'grant_ok.sh').chmod(0o755)
        rl = self.base / 'region-lock'; rl.write_text('#!/bin/sh\nexit 0\n'); rl.chmod(0o755)
        rid='codex-ni-old'; pid=str(os.getpid())
        if stale or registered:
            self.b[2] = '/fake/launcher.sh pid=' + pid
            self.regenerate()
            self.candidate.write_text(self.table([self.b]))
            self.meta.write_text(__import__('json').dumps(self.cat['rows']['new']))
            mod.gate.register(self.base, self.candidate, self.meta, pid, '900', '4', '0-23')
            if stale:
                catalog = __import__('json').loads((self.base / mod.gate.CAT).read_text())
                catalog['rows']['new']['session']['id'] = 'changed'
                (self.base / mod.gate.CAT).write_text(__import__('json').dumps(catalog))
            rid = 'new'
        if gpu:
            (self.base / 'ws58-gpu.queue').write_text(f'{rid}|{pid}|900|600|4|^ *gpu-quiet|mi210_0,184-191\n')
            script='grant-gpu-1026-v13.sh'
        else:
            (self.base / 'ws58-quarters-20261027.queue').write_text(f'{rid}|{pid}|900|4|0-23\n')
            script='grant-ws58-quarters-20261027.sh'
        if pending: (self.base / mod.gate.PENDING).write_text('{}')
        fd=os.open(self.base / '.publication.lock', os.O_RDWR); fcntl.flock(fd,fcntl.LOCK_EX)
        env=dict(os.environ, CTCQD_FLAGS=str(self.base), CTCQD_RL=str(rl), CTCQD_GATE=str(PACKET/'registration_gate.py'))
        proc=subprocess.Popen(['bash', str(PACKET/script)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            time.sleep(.5)
            grant=self.base / 'grants' / (rid+'.grant')
            self.assertFalse(grant.exists(), 'writer published while competing lease held')
            os.close(fd); fd=None
            if pending or stale:
                time.sleep(1)
                self.assertFalse(grant.exists(), 'writer published with unfinished transaction')
                log = self.base / ('grant-gpu-1026-v13.log' if gpu else 'grant-ws58-quarters-20261027.log')
                self.assertIn('unfinished-registration-recovery-required' if pending else 'stale receipt', log.read_text())
            else:
                deadline=time.monotonic()+5
                while not grant.exists() and time.monotonic()<deadline: time.sleep(.05)
                self.assertTrue(grant.exists(), 'writer did not grant verified legacy row')
        finally:
            if fd is not None: os.close(fd)
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)

    def test_quarter(self): self.exercise(False)
    def test_quarter_pending(self): self.exercise(False,True)
    def test_gpu(self): self.exercise(True)
    def test_gpu_pending(self): self.exercise(True,True)
    def test_quarter_stale(self): self.exercise(False,stale=True)
    def test_gpu_stale(self): self.exercise(True,stale=True)
    def test_quarter_registered(self): self.exercise(False,registered=True)
    def test_gpu_registered(self): self.exercise(True,registered=True)

    def stale_mark(self, gpu, queue_changed):
        (self.base / 'grants').mkdir()
        (self.base / 'grant_ok.sh').write_text('#!/bin/sh\nexit 0\n'); (self.base / 'grant_ok.sh').chmod(0o755)
        rl = self.base / 'region-lock'; rl.write_text('#!/bin/sh\nexit 0\n'); rl.chmod(0o755)
        rid='codex-ni-old'; pid=str(os.getpid())
        if gpu:
            queue=self.base / 'ws58-gpu.queue'; done=self.base / 'ws58-gpu.queue.held'
            line=f'{rid}|{pid}|900|600|4|^ *gpu-quiet|mi210_0,184-191\n'; script='grant-gpu-1026-v13.sh'; stamp=self.base / ('.wsg-granted-'+rid)
        else:
            queue=self.base / 'ws58-quarters-20261027.queue'; done=self.base / 'ws58-quarters-20261027.queue.done'
            line=f'{rid}|{pid}|900|4|0-23\n'; script='grant-ws58-quarters-20261027.sh'; stamp=self.base / ('.wsq-granted-'+rid)
        queue.write_text(line); done.write_text(''); stamp.write_text('')
        os.utime(stamp, (time.time()-10, time.time()-10))
        (self.base/'grants'/(rid+'.ended')).write_text('rc=1\n')
        fd=os.open(self.base / '.publication.lock', os.O_RDWR); fcntl.flock(fd,fcntl.LOCK_EX)
        env=dict(os.environ, CTCQD_FLAGS=str(self.base), CTCQD_RL=str(rl), CTCQD_GATE=str(PACKET/'registration_gate.py'))
        proc=subprocess.Popen(['bash', str(PACKET/script)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        log=self.base/('grant-gpu-1026-v13.log' if gpu else 'grant-ws58-quarters-20261027.log')
        try:
            time.sleep(.7); self.assertIsNone(proc.poll())
            if queue_changed: queue.write_text(line.replace('|900|', '|901|'))
            else:
                path=self.base/mod.gate.REGISTRY
                reg=json.loads(path.read_text()); reg['generation']='new-arm'; path.write_text(json.dumps(reg))
            os.close(fd); fd=None
            deadline=time.monotonic()+3
            while (not log.exists() or 'mark skipped: state changed' not in log.read_text()) and time.monotonic()<deadline: time.sleep(.05)
            self.assertIn('mark skipped: state changed', log.read_text())
            self.assertEqual(done.read_text(), '')
        finally:
            if fd is not None: os.close(fd)
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)

    def test_quarter_generation_race(self): self.stale_mark(False, False)
    def test_gpu_generation_race(self): self.stale_mark(True, False)
    def test_quarter_queue_race(self): self.stale_mark(False, True)
    def test_gpu_queue_race(self): self.stale_mark(True, True)

if __name__ == '__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Writers(n) for n in ('test_quarter','test_quarter_pending','test_gpu','test_gpu_pending','test_quarter_stale','test_gpu_stale','test_quarter_registered','test_gpu_registered','test_quarter_generation_race','test_gpu_generation_race','test_quarter_queue_race','test_gpu_queue_race')))
    sys.exit(not result.wasSuccessful())
