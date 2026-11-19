"""Actual GDB, own harmless inferior; exercises the packet's cleanup path."""
import os, subprocess, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
import gdb_job

HOOK = Path('/mnt/raid0/llm/worktrees/mains/h-heterogeneous-slot-fabric-residency/docs/reports/kv-cache/kpf17-gdb-adopt-unknown-20261104/gdb_hook.py')

class RunnerAdoption(unittest.TestCase):
    def test_pidfd_unavailable_before_identity_cleans_owned_child(self):
        gdb_job.enable_subreaper()
        self.assertEqual(gdb_job.direct_children(), [])
        proc=subprocess.Popen(['/usr/bin/sleep','30'])
        known={}
        try:
            with patch.object(gdb_job.os,'pidfd_open',side_effect=OSError(24,'injected fd exhaustion')):
                with self.assertRaisesRegex(OSError,'injected fd exhaustion'):
                    gdb_job.pin_debugger(proc,known)
            self.assertIsNotNone(proc.poll())
            self.assertIsNone(gdb_job.cleanup.identity(proc.pid))
            self.assertEqual(gdb_job.direct_children(),[])
        finally:
            if proc.poll() is None:
                gdb_job.signal_owned_child(proc.pid,gdb_job.proc_birth(proc.pid))
                proc.wait(timeout=5)

    def test_nested_adopted_descendants(self):
        gdb_job.enable_subreaper()
        self.assertEqual(gdb_job.direct_children(), [])
        code='''import os,signal
p=os.fork()
if not p:
 q=os.fork()
 if not q:
  print("READY",flush=True)
 signal.pause()
'''
        proc=subprocess.Popen(['/usr/bin/python3','-c',code],stdout=subprocess.PIPE)
        known={proc.pid:gdb_job.proc_birth(proc.pid)}
        self.assertEqual(proc.stdout.readline().strip(),b'READY')
        proc.wait(timeout=5)
        result=gdb_job.stop_and_drain(proc,known)
        self.assertEqual(sum(bool(x['signals']) for x in result),2)
        self.assertTrue(all(x['verified_dead'] for x in result))
        self.assertEqual(gdb_job.direct_children(),[])
        proc.stdout.close()

    def test_normal_exit_drains_surviving_child(self):
        gdb_job.enable_subreaper()
        self.assertEqual(gdb_job.direct_children(), [])
        code='import os,signal; p=os.fork(); print("READY",flush=True) if not p else None; signal.pause() if not p else None'
        proc=subprocess.Popen(['/usr/bin/python3','-c',code],stdout=subprocess.PIPE)
        known={proc.pid:gdb_job.proc_birth(proc.pid)}
        self.assertEqual(proc.stdout.readline().strip(),b'READY')
        proc.wait(timeout=5)
        result=gdb_job.stop_and_drain(proc,known)
        self.assertTrue(any(x['signals'] for x in result))
        self.assertTrue(all(x['verified_dead'] for x in result))
        self.assertEqual(gdb_job.direct_children(),[])
        proc.stdout.close()

    def test_reused_captured_pid_is_refused(self):
        gdb_job.enable_subreaper()
        class Exited:
            def poll(self):return 0
        with patch.object(gdb_job.cleanup,'identity',return_value=12345):
            with self.assertRaisesRegex(RuntimeError,'PID reused'):
                gdb_job.stop_and_drain(Exited(),{999999:11111})

    def test_stop_before_initial_receipt(self):
        gdb_job.enable_subreaper()
        self.assertEqual(gdb_job.direct_children(), [])
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            env=dict(os.environ,KPF17_TEST_ROOT=td,KPF17_TEST_PIDFILE=str(root/'pidfile'))
            argv=['/usr/bin/gdb','--batch','-nx','-ex','set startup-with-shell off',
                  '-ex',f'source {HOOK}','-ex','starti','-ex','python hold_before_receipt()',
                  '-ex','python capture_starti()','-ex','continue','--args','/usr/bin/sleep','30']
            with (root/'gdb.log').open('wb') as log:
                proc=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,env=env)
                known={proc.pid:gdb_job.proc_birth(proc.pid)}
                try:
                    end=time.monotonic()+10
                    while not (root/'held-before-receipt.json').exists():
                        if proc.poll() is not None or time.monotonic()>end:
                            self.fail('GDB did not reach initial-stop hold')
                        time.sleep(.01)
                    self.assertFalse((root/'receipt.json').exists())
                    # Deliberately do not discover inferior before GDB dies.
                    result=gdb_job.stop_and_drain(proc,known)
                    self.assertGreaterEqual(len(result),2)
                    self.assertTrue(all(x['verified_dead'] for x in result))
                    self.assertEqual(gdb_job.direct_children(),[])
                    self.assertFalse((root/'receipt.json').exists())
                    self.assertFalse((root/'COMPLETE').exists())
                finally:
                    if proc.poll() is None or gdb_job.direct_children():
                        gdb_job.stop_and_drain(proc,known)

if __name__=='__main__':unittest.main()
