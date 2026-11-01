"""Exercise timeout/signal cleanup against owned nested sessions and a real flock."""
import ctypes
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

V2 = Path(__file__).resolve().parents[2] / 'qual_v2'

def birth(pid):
    return int((Path('/proc') / str(pid) / 'stat').read_text().rsplit(') ', 1)[1].split()[19])

def worker(folder, mode):
    sys.path.insert(0, str(V2))
    spec = importlib.util.spec_from_file_location('real_qualifier', V2 / 'qualify_launcher.py')
    q = importlib.util.module_from_spec(spec); spec.loader.exec_module(q)
    assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, q.request_interrupt)
    with (folder / 'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        code = ('import pathlib,subprocess,sys,time; '
                'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],start_new_session=True); '
                'm=pathlib.Path(sys.argv[1]);t=m.with_suffix(".tmp");t.write_text(str(p.pid));t.replace(m);time.sleep(60)')
        p = subprocess.Popen([sys.executable, '-c', code, str(folder / 'nested')], start_new_session=True)
        try:
            for _ in range(300):
                if (folder / 'nested').exists(): break
                time.sleep(.01)
            assert (folder / 'nested').exists()
            nested = int((folder / 'nested').read_text()); started = q.group_birth(p.pid)
            ready_tmp = folder / 'ready.tmp'
            ready_tmp.write_text(json.dumps({'child': p.pid, 'child_birth': birth(p.pid),
                                             'nested': nested, 'nested_birth': birth(nested)}))
            ready_tmp.replace(folder / 'ready')
            try:
                q.wait_qualification(p, started, .8 if mode == 'timeout' else 20)
                raise AssertionError('expected interrupted qualification')
            except q.Refused:
                pass
            assert p.poll() is not None
            (folder / 'drained').write_text('yes'); time.sleep(.5)
        finally:
            if p.poll() is None: p.kill(); p.wait()

class RealDrain(unittest.TestCase):
    def test_timeout_and_signals_drain_nested_sessions_before_unlock(self):
        for mode in ('timeout', 'TERM', 'INT', 'HUP'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp); p = subprocess.Popen([sys.executable, __file__, '--worker', temp, mode]); captured = {}
                try:
                    for _ in range(500):
                        if (folder / 'ready').exists(): break
                        if p.poll() is not None: self.fail('worker exited before ready')
                        time.sleep(.01)
                    self.assertTrue((folder / 'ready').exists())
                    captured = json.loads((folder / 'ready').read_text())
                    if mode != 'timeout': os.kill(p.pid, getattr(signal, 'SIG' + mode))
                    for _ in range(1000):
                        if (folder / 'drained').exists(): break
                        if p.poll() is not None: self.fail('worker exited before drain')
                        time.sleep(.01)
                    self.assertTrue((folder / 'drained').exists())
                    for key in ('child', 'nested'):
                        with self.assertRaises(ProcessLookupError): os.kill(captured[key], 0)
                    with (folder / 'lock').open('r') as lock:
                        with self.assertRaises(BlockingIOError): fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.assertEqual(p.wait(timeout=5), 0)
                finally:
                    if p.poll() is None: p.kill(); p.wait()
                    for key in ('child', 'nested'):
                        if key not in captured: continue
                        pid = captured[key]
                        try:
                            if birth(pid) == captured[key + '_birth']: os.kill(pid, signal.SIGKILL)
                        except (FileNotFoundError, ProcessLookupError): pass

if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--worker': worker(Path(sys.argv[2]), sys.argv[3])
    else: unittest.main()
