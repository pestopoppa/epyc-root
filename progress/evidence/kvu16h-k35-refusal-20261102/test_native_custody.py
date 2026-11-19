"""Real lightweight processes only; no model, GPU or grant activity."""
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

D = Path('/mnt/raid0/llm/tmp/kvu/k35-native-validation-20261102')
s = importlib.util.spec_from_file_location('native_custody_fixture', D / 'native_job.py')
j = importlib.util.module_from_spec(s)
s.loader.exec_module(j)


def alive(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().rsplit(') ',1)[1].split()[0] != 'Z'
    except FileNotFoundError:
        return False


def wait_for(predicate, timeout=8):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(.02)
    raise AssertionError('condition did not become true')


class CustodyTests(unittest.TestCase):
    def tearDown(self):
        j.ACTIVE = None
        j.STOPPED = False

    def test_parent_exec_retains_pid_and_group(self):
        p = subprocess.Popen([sys.executable, str(D/'parent_exec.py'), str(os.getpid()),
                              sys.executable, '-c', 'import os,time; print(os.getpid(),os.getpgrp(),flush=True); time.sleep(30)'],
                             stdout=subprocess.PIPE, text=True)
        try:
            self.assertTrue(select.select([p.stdout],[],[],5)[0])
            pid, pgid = map(int, p.stdout.readline().split())
            self.assertEqual(pid, p.pid)
            self.assertEqual(pgid, os.getpgrp())
        finally:
            p.terminate(); p.wait(timeout=5); p.stdout.close()
        self.assertFalse(alive(p.pid))

    def test_abrupt_worker_death_kills_execed_child(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
            ready = Path(tmp)/'ready'
            helper = '''import os,subprocess,sys,time
p=subprocess.Popen([sys.executable,sys.argv[1],str(os.getpid()),sys.executable,'-c',
'import pathlib,sys,time; pathlib.Path(sys.argv[1]).write_text("ready"); time.sleep(60)',sys.argv[2]])
print(p.pid,flush=True)
time.sleep(60)
'''
            parent = subprocess.Popen([sys.executable,'-c',helper,str(D/'parent_exec.py'),str(ready)],
                                      stdout=subprocess.PIPE,text=True)
            child = None
            try:
                self.assertTrue(select.select([parent.stdout],[],[],5)[0])
                child = int(parent.stdout.readline())
                wait_for(ready.exists)
                parent.kill(); parent.wait(timeout=5)
                wait_for(lambda: not alive(child))
                self.assertFalse(alive(child))
            finally:
                if parent.poll() is None:
                    parent.kill(); parent.wait(timeout=5)
                parent.stdout.close()
                if child is not None and alive(child):
                    os.kill(child,signal.SIGKILL)
                    wait_for(lambda:not alive(child))

    def test_parent_mismatch_refuses_exec(self):
        p = subprocess.run([sys.executable,str(D/'parent_exec.py'),str(os.getpid()+1000000),
                            sys.executable,'-c','raise SystemExit(99)'], timeout=5)
        self.assertEqual(p.returncode,125)

    def test_owned_spawn_removes_detached_session_and_registers_pid(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
            p = Mock(pid=12345)
            original = Mock(return_value=p)
            with patch.dict(os.environ,{'FILLER_PIDFILE':str(Path(tmp)/'pids')}):
                result = j.owned_spawn(original,[str(j.BINARY),'--fake'],start_new_session=True)
            argv = original.call_args.args[0]
            self.assertEqual(argv[:3],[sys.executable,str(D/'parent_exec.py'),str(os.getpid())])
            self.assertFalse(original.call_args.kwargs['start_new_session'])
            self.assertEqual((Path(tmp)/'pids').read_text(),'12345\n')
            self.assertIs(result,p)

    def test_stopfile_interrupts_blocking_live_child(self):
        self._watcher_case('stopfile')

    def test_deadline_interrupts_blocking_live_child(self):
        self._watcher_case('deadline')

    def _watcher_case(self, mode):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
            stop = Path(tmp)/'STOP'
            deadline = time.time() + (150.3 if mode=='deadline' else 1000)
            with patch.dict(os.environ,{'FILLER_STOPFILE':str(stop),'FILLER_DEADLINE':str(deadline)}):
                p = subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])
                j.ACTIVE = p
                done = threading.Event()
                thread = threading.Thread(target=j.watch_stop,args=(done,))
                thread.start()
                try:
                    if mode=='stopfile':
                        stop.touch()
                    p.wait(timeout=5)
                    self.assertTrue(j.STOPPED)
                    self.assertFalse(alive(p.pid))
                finally:
                    done.set(); thread.join(timeout=5)
                    if p.poll() is None:
                        p.kill(); p.wait(timeout=5)

    def test_smoke_affinity_is_four_actual_grant_cpus(self):
        affinity = sorted(os.sched_getaffinity(0))
        if len(affinity)<4:
            self.skipTest('test host needs four actual CPUs')
        granted = affinity[:min(8,len(affinity))]
        code = '''import importlib.util,json
s=importlib.util.spec_from_file_location('j',%r);j=importlib.util.module_from_spec(s);s.loader.exec_module(j)
print(json.dumps(j.grant_affinity()))
''' % str(D/'native_job.py')
        env = dict(os.environ,FILLER_SMOKE='1',FILLER_CPUS=','.join(map(str,granted)))
        actual = json.loads(subprocess.check_output([sys.executable,'-c',code],env=env,text=True,timeout=5))
        self.assertEqual(actual,granted[:4])

    def test_smoke_insufficient_granted_cpus_is_refused(self):
        with patch.dict(os.environ,{'FILLER_SMOKE':'1','FILLER_CPUS':'1,2,3'}), \
             patch.object(j.os,'sched_getaffinity',return_value={1,2,3,4,5}), \
             patch.object(j.os,'sched_setaffinity') as setaff:
            with self.assertRaisesRegex(RuntimeError,'four CPUs'):
                j.grant_affinity()
            setaff.assert_not_called()


if __name__ == '__main__':
    unittest.main()
