"""Offline controls for the review-only selector lifecycle patch; no servers started."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
RESEARCH = '/mnt/raid0/llm/epyc-inference-research'
COMMIT = 'f0737320a54f6454a67f957bf1b6eb5ec204149d'
SOURCE = 'scripts/benchmark/qwable_verifier_selector_runner.py'
BASE_HASH = 'de05a45612bfa8270c6db89b9a017274dadd8f767ec19350c52959d3e517e1d8'

class FakeProcess:
    pid = 8242
    def __init__(self, timeout=False, stubborn=False):
        self.running = True
        self.timeout = timeout
        self.stubborn = stubborn
        self.actions = []
    def poll(self): return None if self.running else 0
    def terminate(self): self.actions.append('terminate')
    def kill(self): self.actions.append('kill')
    def wait(self, timeout):
        self.actions.append(('wait', timeout))
        if self.stubborn or (self.timeout and 'kill' not in self.actions):
            raise subprocess.TimeoutExpired('child', timeout)
        self.running = False
        return 0

class PatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        path = cls.base / SOURCE
        path.parent.mkdir(parents=True)
        raw = subprocess.check_output(['git', '-C', RESEARCH, 'show', f'{COMMIT}:{SOURCE}'], stderr=subprocess.DEVNULL)
        if hashlib.sha256(raw).hexdigest() != BASE_HASH:
            raise AssertionError('pinned source hash mismatch')
        path.write_bytes(raw)
        subprocess.run(['patch', '-s', '-p1', '-i', str(HERE / 'selector-safety.patch')], cwd=cls.base, check=True)
        cls.source = path.read_text()
        tree = ast.parse(cls.source)
        names = {'record_owned_process', 'terminate_server', 'cleanup_server'}
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
        ast.fix_missing_locations(module)
        cls.ns = {'Path': Path, 'subprocess': subprocess, 'time': time, 'datetime': datetime.datetime,
                  'timezone': datetime.timezone, 'json': json}
        exec(compile(module, '<extracted patched functions>', 'exec'), cls.ns)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def test_terminates_and_reaps_owned_child(self):
        proc = FakeProcess()
        self.ns['terminate_server'](proc)
        self.assertEqual(proc.actions, ['terminate', ('wait', 10)])
        self.assertIsNotNone(proc.poll())
    def test_escalates_and_confirms_kill(self):
        proc = FakeProcess(timeout=True)
        self.ns['terminate_server'](proc)
        self.assertEqual(proc.actions, ['terminate', ('wait', 10), 'kill', ('wait', 10)])
    def test_failed_kill_is_reported(self):
        with self.assertRaises(RuntimeError): self.ns['terminate_server'](FakeProcess(stubborn=True))
    def test_cleanup_closes_log_and_terminates_when_event_fails(self):
        proc = FakeProcess()
        proc._qwable_verifier_log_handle = mock.Mock()
        with mock.patch.dict(self.ns, {'record_owned_process': mock.Mock(side_effect=OSError('disk'))}):
            with self.assertRaises(OSError): self.ns['cleanup_server'](proc, self.base, 'verifier')
        self.assertIn('terminate', proc.actions)
        proc._qwable_verifier_log_handle.close.assert_called_once()
    def test_events_include_only_owned_pid(self):
        proc = FakeProcess()
        self.ns['record_owned_process'](self.base, 'verifier', proc, 'spawned')
        event = json.loads((self.base / 'owned_processes.jsonl').read_text().splitlines()[-1])
        self.assertEqual((event['pid'], event['role'], event['action']), (8242, 'verifier', 'spawned'))
    def test_failed_termination_is_not_logged_as_complete(self):
        proc = FakeProcess(stubborn=True)
        with self.assertRaises(RuntimeError):
            self.ns['cleanup_server'](proc, self.base, 'stubborn')
        events = [json.loads(line) for line in (self.base / 'owned_processes.jsonl').read_text().splitlines()]
        actions = [event['action'] for event in events if event['role'] == 'stubborn']
        self.assertEqual(actions, ['termination_requested', 'cleanup_attempt_finished'])
        self.assertIsNone(events[-1]['returncode'])
    def test_no_name_scan_or_group_signals_and_both_paths_use_cleanup(self):
        tree = ast.parse(self.source)
        self.assertNotIn('pgrep', self.source)
        self.assertNotIn('killpg', self.source)
        funcs = {n.name: ast.get_source_segment(self.source, n) for n in tree.body if isinstance(n, ast.FunctionDef)}
        for name in ('execute', 'execute_replay'):
            self.assertIn('record_owned_process(', funcs[name])
            self.assertIn('cleanup_server(', funcs[name])

if __name__ == '__main__': unittest.main()
