import os
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import slot_run as seq

HERE = Path(__file__).resolve().parent


class SupervisionTests(unittest.TestCase):
    def test_parent_death_kills_captured_native_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            pidfile = Path(tmp) / 'pid'
            worker_code = '''import os,subprocess,sys,time
p=subprocess.Popen([sys.executable,"-B",sys.argv[1],str(os.getpid()),sys.executable,"-c","import time;time.sleep(60)"])
open(sys.argv[2],"w").write(str(p.pid))
time.sleep(60)
'''
            worker = subprocess.Popen([sys.executable, '-B', '-c', worker_code,
                                       str(HERE / 'p3_pdeath_exec.py'), str(pidfile)])
            try:
                deadline = time.monotonic() + 5
                while not pidfile.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(pidfile.exists())
                child_pid = int(pidfile.read_text())
                # Allow the wrapper to install its handler and exec.
                time.sleep(.2)
                worker.kill()
                worker.wait(timeout=5)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    try:
                        state = Path(f'/proc/{child_pid}/stat').read_text().split(') ', 1)[1][0]
                    except FileNotFoundError:
                        break
                    if state == 'Z':
                        break
                    time.sleep(.02)
                else:
                    self.fail('parent-death child remained live')
            finally:
                if worker.poll() is None:
                    worker.kill()
                    worker.wait(timeout=5)

    def test_contained_timeout_checks_port_and_does_not_reap_pid_file(self):
        child = SimpleNamespace(pid=123, returncode=-signal.SIGKILL,
                                poll=lambda: None, send_signal=lambda sig: None,
                                wait=lambda timeout: (_ for _ in ()).throw(subprocess.TimeoutExpired('x', timeout))
                                if timeout == seq.TERM_GRACE_S else None)
        with patch.object(seq.subprocess, 'run') as run, patch.object(seq, 'reap_recorded_server') as reap:
            run.side_effect = [SimpleNamespace(returncode=1), SimpleNamespace(returncode=0, stdout='')]
            result = seq.stop_child(child, Path('/unused'), 18183, contained_p3=True)
        self.assertEqual(result['sent'], ['TERM', 'KILL'])
        self.assertTrue(result['verified_dead'])
        self.assertTrue(result['port_free_after'])
        reap.assert_not_called()

    def test_pair_runs_two_fake_arms_and_stops_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(results=Path(tmp), budget_min=100, p3_phase='a1')
            seq.STOP['flag'] = False
            def fake_driver(label, argv, log, hard_s, arm_dir, contained_p3):
                self.assertTrue(contained_p3)
                self.assertGreater(hard_s, 0)
                self.assertLessEqual(hard_s, 50 * 60)
                return {'rc': 0}
            run = {'items': []}
            with patch.object(seq, 'ARGS', args, create=True), patch.object(seq, 'elapsed_min', return_value=0), \
                 patch.object(seq, 'gpu_clear', return_value={'kfd_holders': {}}), \
                 patch.object(seq, 'p3_argv', return_value=['fake-driver']), \
                 patch.object(seq, 'run_child', side_effect=fake_driver) as child:
                self.assertEqual(seq.run_p3_pair(1, run, lambda: None), 0)
                self.assertEqual(child.call_count, 2)
                self.assertEqual([r['arm'] for r in run['items']], ['on', 'off'])
            run = {'items': []}
            seq.STOP['flag'] = False
            with patch.object(seq, 'ARGS', args, create=True), patch.object(seq, 'elapsed_min', return_value=0), \
                 patch.object(seq, 'gpu_clear', return_value={'kfd_holders': {}}), \
                 patch.object(seq, 'p3_argv', return_value=['fake-driver']), \
                 patch.object(seq, 'run_child', return_value={'rc': 1}) as child:
                self.assertEqual(seq.run_p3_pair(1, run, lambda: None), 1)
                self.assertEqual(child.call_count, 1)
                self.assertTrue(seq.STOP['flag'])
            seq.STOP['flag'] = False

    def test_sequencer_real_child_runs_p3_coordinator_against_fake_servers(self):
        # Exercise the sequencer's real child launch and the actual P3 coordinator.
        # The child substitutes the fake server/transport fixture, never a model.
        child_code = ("import json,sys; sys.path.insert(0,sys.argv[2]); "
                      "from test_p3_isolated import P3IsolatedTests; "
                      "rc,result=P3IsolatedTests().run_pair(); "
                      "open(sys.argv[1], 'w').write(json.dumps(result)); "
                      "raise SystemExit(rc)")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = SimpleNamespace(results=root, budget_min=100, p3_phase='a1', port=18183)
            run = {'items': []}
            seq.STOP['flag'] = False
            def fake_argv(arm, label, budget, dry):
                return [sys.executable, '-B', '-c', child_code, str(root / (arm + '.json')), str(HERE)]
            with patch.object(seq, 'ARGS', args, create=True), \
                 patch.object(seq, 'gpu_clear', return_value={'kfd_holders': {}}), \
                 patch.object(seq, 'p3_argv', side_effect=fake_argv):
                self.assertEqual(seq.run_p3_pair(1, run, lambda: None), 0)
            self.assertEqual([item['arm'] for item in run['items']], ['on', 'off'])
            for arm in ('on', 'off'):
                result = json.loads((root / (arm + '.json')).read_text())
                self.assertTrue(result['dedicated_server_per_variant'])
                self.assertEqual(len(result['rows']), 12)
                self.assertEqual(len(result['variant_runs']), 2)
                self.assertTrue(all(r['server']['teardown']['verified_dead'] for r in result['variant_runs']))
                report_dir = root / 'p3v2' / ('pair1_' + arm)
                report_dir.mkdir(parents=True)
                (report_dir / 'a1.json').write_text(json.dumps(result))
            report = subprocess.run([sys.executable, '-B', str(HERE / 'slot_report.py'), str(root)],
                                    text=True, capture_output=True)
            self.assertEqual(report.returncode, 0, report.stderr)
            self.assertIn('P3v2 A1', (root / 'report.md').read_text())

    def test_command_builder_passes_real_successor_arguments(self):
        import p3_kvu_probe_isolated as p3
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = SimpleNamespace(results=root, port=18183, p3_phase='a1', p3_npp_list='16384')
            with patch.object(seq, 'ARGS', args, create=True), patch.object(seq.C, 'BIN', root / 'bin'):
                command = seq._p3_isolated_argv('on', 'pair1_on', 42.5, True)
            self.assertEqual(Path(command[2]), HERE / 'p3_kvu_probe_isolated.py')
            with patch.object(sys, 'argv', command[2:]), patch.object(p3, 'dry', return_value=0) as dry, \
                 patch.object(p3.C, 'BIN', root / 'bin'), patch.object(p3, 'OUT'), \
                 patch.object(p3, 'LOGS'), patch.object(p3, 'SLOTDIR'), patch.object(p3, 'ARM'):
                self.assertEqual(p3.main(), 0)
            parsed = dry.call_args.args[0]
            self.assertEqual((parsed.arm, parsed.port, parsed.phase, parsed.park_mode), ('on', 18183, 'a1', 'prefill'))
            self.assertEqual(parsed.out_dir, root / 'p3v2' / 'pair1_on')
            self.assertEqual(parsed.budget_min, 42.5)
            self.assertEqual(parsed.b_npp_list, '16384')

    def test_double_lifecycle_estimate_and_timeout(self):
        self.assertEqual(seq.P3_EST, {'on': 30.0, 'off': 33.0})
        self.assertEqual(seq.P3_HARD_MIN['a1'], 50.0)

if __name__ == '__main__':
    unittest.main()
