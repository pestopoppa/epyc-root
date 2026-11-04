"""Model-free current-rowflow fixtures; never arm or run the copied engine."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import prepare
import rowflow_entry as entry

SCRATCH = '/mnt/raid0/llm/tmp/kvfork'


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='g3-rowflow-fixture-', dir=SCRATCH)
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.base = root/'candidate'; self.base.mkdir()
        self.flags = root/'flags'; (self.flags/'grants').mkdir(parents=True)
        self.grant = self.flags/'grants'/(entry.ROW+'.grant')
        self.raw = 'regions=mi210_0,8-11 start=2026-11-04T00:00Z end=2026-11-04T02:30Z'
        self.grant.write_text(self.raw)
        self.end = entry.epoch('2026-11-04T02:30Z')
        self.stack = [patch.object(entry, 'BASE', self.base), patch.object(entry, 'FLAGS', self.flags),
                      patch.object(entry.time, 'time', return_value=self.end-1000),
                      patch.object(entry.os, 'sched_getaffinity', return_value={8,9,10,11}),
                      patch.dict(os.environ, {'FILLER_ID': entry.ROW, 'FILLER_CPUS':'8-11',
                          'FILLER_THREADS':'4', 'FILLER_END':str(self.end),
                          'FILLER_DEADLINE':str(self.end-90), 'FILLER_STOPFILE':str(self.base/'STOP'),
                          'FILLER_NEEDGPU':'1'}, clear=True)]
        for context in self.stack:
            context.start(); self.addCleanup(context.stop)

    def test_current_schema_and_optional_claim_cpus(self):
        self.assertEqual(entry.boundary(), self.end)
        self.grant.write_text(self.raw+' cpus=0-3')
        self.assertEqual(entry.boundary(), self.end)

    def test_legacy_and_malformed_grants_refuse(self):
        for raw in (self.raw.replace('mi210_0', 'gpu'), self.raw+' end=2026-11-04T02:30Z',
                    self.raw+' unknown=1', self.raw+' cpus=193',
                    self.raw.replace('02:30Z', '01:30Z'), self.raw.replace('8-11', '11-8')):
            with self.subTest(raw=raw):
                self.grant.write_text(raw)
                with self.assertRaises(ValueError): entry.boundary()

    def test_stop_terminal_and_hold_refuse_without_writes(self):
        for path in (self.base/'STOP', self.grant.with_suffix('.ended'),
                     self.grant.with_suffix('.complete'), self.flags/'HOLD_test'):
            path.symlink_to(self.base/'absent')
            try:
                with self.assertRaises(ValueError): entry.boundary()
                self.assertEqual(self.grant.read_text(), self.raw)
            finally: path.unlink()

    def test_engine_drift_deadline_and_redirects_refuse(self):
        for values in ({'FILLER_ID':'historical'}, {'FILLER_STOPFILE':str(self.base/'STOP-smoke')},
                       {'FILLER_THREADS':'8'}, {'FILLER_END':str(self.end+1)},
                       {'FILLER_DEADLINE':str(self.end)}, {'FILLER_GRANTS_DIR':'/private'},
                       {'ROWFLOW_FLAGS':'/private'}, {'FILLER_FLAGS_DIR':'/private'},
                       {'FILLER_SMOKE':'1'}, {'FILLER_DRYRUN':'1'}):
            with self.subTest(values=values), patch.dict(os.environ,values):
                with self.assertRaises(ValueError): entry.boundary()
        with patch.object(entry.time, 'time', return_value=self.end-90):
            with self.assertRaises(ValueError): entry.boundary()
        with patch.object(entry.os, 'sched_getaffinity', return_value={12}):
            with self.assertRaises(ValueError): entry.boundary()
        self.grant.unlink(); self.grant.symlink_to(self.base/'absent')
        with self.assertRaises(OSError): entry.boundary()


class PreparedEntry(unittest.TestCase):
    def test_copy_command_barriers_and_custody(self):
        with tempfile.TemporaryDirectory(prefix='g3-rowflow-prepared-', dir=SCRATCH) as directory:
            output=Path(directory)/'prepared'; prepare.prepare(output)
            runtime=output/'candidate'
            argv=json.loads((runtime/'rowflow-command.json').read_text())
            self.assertEqual(argv,entry.command(runtime))
            self.assertIn('exclusive',argv)
            self.assertIn('--complete-cmd',argv)
            for name, digest in prepare.ROWFLOW_PINS.items():
                self.assertEqual(prepare.sha((runtime/name).read_bytes()),digest)
            guard=(runtime/'guard.py').read_text()
            self.assertIn('return rowflow_entry.boundary()',guard)
            self.assertNotIn("parts=GRANT.read_text()",guard)
            for name in ('rowflow-launch.sh','precondition.sh','complete.sh','launch.sh'):
                result=subprocess.run(['/bin/bash',str(runtime/name)],capture_output=True)
                self.assertEqual(result.returncode,78)
            result=subprocess.run([os.sys.executable,'-B',str(runtime/'rowflow_entry.py')],capture_output=True)
            self.assertEqual(result.returncode,78)
            for relative in ('rowflow_entry.py','rowflow-command.json','filler_run15.sh','complete.sh'):
                path=runtime/relative; raw=path.read_bytes()
                try:
                    path.write_bytes(raw+b'\n')
                    result=subprocess.run(['/bin/bash',str(output/'launch.sh'),'custody-check'],capture_output=True)
                    self.assertNotEqual(result.returncode,0)
                finally:path.write_bytes(raw)


if __name__ == '__main__': unittest.main()
