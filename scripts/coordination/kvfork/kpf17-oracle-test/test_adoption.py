"""Short actual-GDB regressions; each case owns an isolated supervisor process."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import cleanup
from gdb_job import finish_debugger, supervise_debugger


def fixture(case, root):
    cleanup.prepare_adoption()
    commands=['set confirm off','set startup-with-shell off',
              'set disable-randomization off','set debuginfod enabled off']
    hold=case in ('stop-before-receipt','callback-error')
    if hold:
        # Publish existence only, deliberately never the inferior PID or birth.
        hook=root/'hold.py'
        hook.write_text("import time\nfrom pathlib import Path\n"
                        f"Path({str(root/'held')!r}).touch()\n"
                        "while True: time.sleep(.01)\n")
        commands+=['starti','source '+str(hook)]
        program=['/usr/bin/sleep','30']
    else:
        program=['/usr/bin/true'] if case=='normal' else ['/usr/bin/false']
        commands+=['run','python print("POST_PID", gdb.selected_inferior().pid)', 'quit $_exitcode']
    argv=['/usr/bin/gdb','--batch','-nx']
    for command in commands: argv+=['-ex',command]
    argv+=['--args',*program]
    end=time.monotonic()+8
    stopped=False
    def requested():
        nonlocal stopped
        if (root/'held').exists() and not stopped:
            # Force bounded TERM-to-KILL on this captured debugger only.
            proc.send_signal(signal.SIGSTOP)
            stopped=True
            if case=='callback-error': raise RuntimeError('callback failed')
            (root/'STOP').touch()
        if time.monotonic()>=end: raise RuntimeError('GDB fixture startup timeout')
        return (root/'STOP').exists()
    with (root/'gdb.log').open('wb') as log:
        proc=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            interrupted,adopted=supervise_debugger(proc,requested,timeout_s=.2)
        except RuntimeError:
            if case!='callback-error': raise
            assert stopped and not cleanup.direct_children()
            assert cleanup.absent(proc.pid)
            return
        finally:
            if proc.poll() is None: finish_debugger(proc,timeout_s=.2)
    assert cleanup.absent(proc.pid) and not cleanup.direct_children()
    assert adopted['verified_dead']
    if hold:
        assert interrupted and stopped and adopted['children']
        assert all(x['verified_dead'] and x['pid']>0 and x['birth_ticks']>0 for x in adopted['children'])
        assert proc.returncode==-signal.SIGKILL
    else:
        assert not interrupted and not adopted['children']
        assert proc.returncode==(0 if case=='normal' else 1)
        assert 'POST_PID 0' in (root/'gdb.log').read_text()


class AdoptionTest(unittest.TestCase):
    def test_existing_child_refuses_adoption_scope(self):
        with patch.object(cleanup,'direct_children',return_value={123}):
            with self.assertRaisesRegex(RuntimeError,'pre-existing'):
                cleanup.prepare_adoption()

    def test_drain_failure_refuses_completion(self):
        with patch('gdb_job.stop_debugger') as stop, patch.object(cleanup,'drain_adopted',side_effect=RuntimeError('not dead')):
            with self.assertRaisesRegex(RuntimeError,'not dead'): finish_debugger(object())
            stop.assert_called_once()

    def test_actual_gdb_lifecycle(self):
        for case in ('normal','exit-1','stop-before-receipt','callback-error'):
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix='kpf17-',dir='/mnt/raid0/llm/tmp/kvu') as root:
                result=subprocess.run([sys.executable,'-B',__file__,'--fixture',case,root],
                                      capture_output=True,text=True,timeout=25)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--fixture': fixture(sys.argv[2],Path(sys.argv[3]))
    else: unittest.main()
