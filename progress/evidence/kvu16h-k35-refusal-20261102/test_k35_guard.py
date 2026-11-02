"""Offline checks for an uninstalled, hash-bound K35 refusal patch."""
import argparse
import dataclasses
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

SOURCE = Path('/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/k35_stack_context_matrix_runner.py')
SOURCE_SHA256 = '2d50fcea9b790739eae97d6516d7b6d1d3c7494cb636aa6327deb42453d106ef'
PATCH = Path(__file__).with_name('k35-guard.patch')


class GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
            raise AssertionError('source changed; rebase and review patch')
        cls.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        root = Path(cls.tmp.name)
        target = root / 'scripts/benchmark/k35_stack_context_matrix_runner.py'
        target.parent.mkdir(parents=True)
        shutil.copyfile(SOURCE, target)
        subprocess.run(['patch', '-s', '-p1', '-i', str(PATCH.resolve())], cwd=root, check=True)
        spec = importlib.util.spec_from_file_location('k35_guard_fixture', target)
        cls.mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.mod
        spec.loader.exec_module(cls.mod)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()
        sys.modules.pop('k35_guard_fixture', None)

    def test_request_zero_refused_for_draft_in_extra_args(self):
        m = self.mod
        base = m.SCENARIOS[0]
        for args in (('-md', 'model.gguf'), ('--model-draft=model.gguf',),
                     ('--spec-type', 'draft-mtp')):
            scenario = dataclasses.replace(base, request_spec_n_max=0, spec_type='none',
                                           draft_model=None, extra_args=args)
            with self.subTest(args=args), self.assertRaises(ValueError):
                m.build_server_argv(scenario, binary=Path('/fake'), port=1234,
                                    nominal_context=2048, max_tokens=8)

    def test_prebuilt_argv_refused_before_files_or_process(self):
        m = self.mod
        scenario = dataclasses.replace(m.SCENARIOS[0], request_spec_n_max=0,
                                       draft_model=None, spec_type='none')
        cell = {'scenario': scenario.name, 'port': 1234, 'nominal_context': 2048,
                'server_argv': ['/fake/server', '-md', 'draft.gguf']}
        output = Path(self.tmp.name) / 'untouched'
        with mock.patch.object(m, 'scenario_by_name', return_value=scenario), \
             mock.patch.object(m.subprocess, 'Popen') as popen:
            with self.assertRaises(ValueError):
                m.run_cell(cell, argparse.Namespace(binary=Path('/fake/server'), max_tokens=8), output)
        popen.assert_not_called()
        self.assertFalse(output.exists())

    def test_no_override_still_builds_normal_request(self):
        m = self.mod
        scenario = dataclasses.replace(m.SCENARIOS[0], request_spec_n_max=None)
        body = m.build_chat_request_body(scenario, 'prompt', max_tokens=8)
        self.assertNotIn('speculative.n_max', body)

    def test_all_zero_override_scenarios_use_dedicated_no_draft(self):
        m = self.mod
        scenarios = [s for s in m.SCENARIOS if s.request_spec_n_max == 0]
        self.assertEqual(len(scenarios), 3)
        for scenario in scenarios:
            with self.subTest(scenario=scenario.name):
                argv = m.build_server_argv(scenario, binary=Path('/fake/server'), port=1234,
                                           nominal_context=2048, max_tokens=8)
                self.assertEqual(argv[argv.index('--spec-type') + 1], 'none')
                self.assertNotIn('-md', argv)
                self.assertFalse(any(a.startswith('--spec-draft-') for a in argv))
                self.assertNotIn('speculative.n_max', m.build_chat_request_body(scenario, 'p', max_tokens=8))

    def test_no_draft_and_drafted_cells_launch_separate_servers_and_drain(self):
        m = self.mod
        scenarios = [next(s for s in m.SCENARIOS if s.request_spec_n_max == n) for n in (0, 3)]
        args = SimpleNamespace(binary=Path('/fake/server'), max_tokens=8, startup_timeout=1,
                               request_timeout=1, min_completion_tokens=1)
        procs, requests = [], []
        def spawn(argv, **kwargs):
            p = mock.Mock(); p.pid = 100 + len(procs); p.poll.return_value = None
            procs.append((p, argv)); return p
        def query(port, body, **kwargs):
            requests.append(body); return {'usage': {'completion_tokens': 8}}
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp, \
             mock.patch.object(m.subprocess, 'Popen', side_effect=spawn), \
             mock.patch.object(m, 'collect_rocm_snapshot', return_value={}), \
             mock.patch.object(m, 'collect_process_blockers', return_value={}), \
             mock.patch.object(m, 'collect_resident_memory_sample', return_value={}), \
             mock.patch.object(m, 'collect_post_cleanup_sample', return_value={}), \
             mock.patch.object(m, 'process_birth', return_value=123), \
             mock.patch.object(m, 'owns_loopback_listener', return_value=True), \
             mock.patch.object(m, 'wait_for_health'), mock.patch.object(m, 'prompt_for_context', return_value='p'), \
             mock.patch.object(m, 'query_chat', side_effect=query), \
             mock.patch.object(m, 'terminate', side_effect=lambda p: {'completed': True, 'dead': True, 'pid': p.pid}) as drain:
            for i, scenario in enumerate(scenarios):
                port = 1234 + i
                argv = m.build_server_argv(scenario, binary=args.binary, port=port, nominal_context=2048, max_tokens=8)
                result = m.run_cell({'scenario': scenario.name, 'port': port, 'nominal_context': 2048,
                                     'server_argv': argv}, args, Path(tmp))
                self.assertTrue(result['cleanup']['completed'])
        self.assertEqual(len(procs), 2)
        self.assertNotEqual(procs[0][0].pid, procs[1][0].pid)
        self.assertEqual(drain.call_count, 2)
        self.assertNotIn('speculative.n_max', requests[0])
        self.assertEqual(requests[1]['speculative.n_max'], 3)
        self.assertEqual(procs[0][1][procs[0][1].index('--spec-type') + 1], 'none')
        self.assertIn('-md', procs[1][1])

    def test_unverified_cleanup_stops_before_next_cell(self):
        m = self.mod
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp, \
             mock.patch.object(m, 'collect_guard_state', return_value={}), \
             mock.patch.object(m, 'collect_process_blockers', return_value=[]), \
             mock.patch.object(m, 'run_cell', return_value={'status': 'cleanup_failed', 'cleanup': {'completed': False}}) as run:
            result = m.execute_plan({'cells': [{'scenario': 'first'}, {'scenario': 'second'}]},
                                    SimpleNamespace(binary=Path('/fake'), allow_dirty_host=False), Path(tmp))
        self.assertEqual(run.call_count, 1)
        self.assertEqual(result['unrun_cells'], 1)
        self.assertEqual(result['status'], 'failed')

    def test_failed_presample_still_terminates_and_failed_cleanup_stops_next_cell(self):
        m = self.mod
        scenario = next(s for s in m.SCENARIOS if s.request_spec_n_max is None)
        args = SimpleNamespace(binary=Path('/fake/server'), max_tokens=8, startup_timeout=1,
                               request_timeout=1, min_completion_tokens=1, allow_dirty_host=False)
        cell = {'scenario': scenario.name, 'port': 1234, 'nominal_context': 2048,
                'server_argv': ['/fake/server']}
        proc = mock.Mock(pid=123); proc.poll.return_value = None
        def sample(pid, phase):
            if phase == 'before_cleanup':
                raise OSError('injected sample failure')
            return {'phase': phase}
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp, \
             mock.patch.object(m, 'collect_guard_state', return_value={}), \
             mock.patch.object(m, 'collect_process_blockers', return_value=[]), \
             mock.patch.object(m, 'collect_rocm_snapshot', return_value={}), \
             mock.patch.object(m.subprocess, 'Popen', return_value=proc) as spawn, \
             mock.patch.object(m, 'process_birth', return_value=456), \
             mock.patch.object(m, 'owns_loopback_listener', return_value=True), \
             mock.patch.object(m, 'wait_for_health'), \
             mock.patch.object(m, 'prompt_for_context', return_value='p'), \
             mock.patch.object(m, 'query_chat', return_value={'usage': {'completion_tokens': 8}}), \
             mock.patch.object(m, 'collect_resident_memory_sample', side_effect=sample), \
             mock.patch.object(m, 'collect_post_cleanup_sample', return_value={}), \
             mock.patch.object(m, 'terminate', return_value={'completed': False, 'dead': False}) as terminate:
            result = m.execute_plan({'cells': [cell, dict(cell, port=1235)]}, args, Path(tmp))
            self.assertEqual(spawn.call_count, 1)
            terminate.assert_called_once_with(proc)
            spawn.reset_mock(); terminate.reset_mock()
            terminate.return_value = {'completed': True, 'dead': True}
            cleaned = m.run_cell(cell, args, Path(tmp) / 'cleaned')
        terminate.assert_called_once_with(proc)
        self.assertEqual(spawn.call_count, 1)
        self.assertEqual(result['unrun_cells'], 1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['results'][0]['status'], 'cleanup_failed')
        self.assertIn('injected sample failure', result['results'][0]['sampling_errors'][0]['sample_error'])
        self.assertEqual(cleaned['status'], 'sampling_failed')
        self.assertTrue(cleaned['cleanup']['completed'])

    def test_listener_owner_requires_correct_pid_birth(self):
        m = self.mod
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen()
            port = listener.getsockname()[1]
            birth = m.process_birth(os.getpid())
            self.assertTrue(m.owns_loopback_listener(os.getpid(), birth, port))
            self.assertFalse(m.owns_loopback_listener(os.getpid(), birth + 1, port))

    def test_health_never_contacts_a_listener_not_owned_by_captured_server(self):
        m = self.mod
        child = mock.Mock(pid=os.getpid()); child.poll.return_value = None
        with mock.patch.object(m.time, 'monotonic', side_effect=[0, 0, 2]), \
             mock.patch.object(m.time, 'sleep'), \
             mock.patch.object(m, 'owns_loopback_listener', return_value=False), \
             mock.patch.object(m.urllib.request, 'urlopen') as http:
            with self.assertRaises(TimeoutError):
                m.wait_for_health(1234, 1, child, 123)
        http.assert_not_called()

    def test_no_draft_parity_uses_explicit_server_evidence_and_native_count(self):
        m = self.mod
        base = {'nominal_context': 2048, 'rep': 1, 'token_ids': [1, 2]}
        disabled = dict(base, scenario='v9_dsv4_q8_dspark_request_nmax0',
                        server_no_draft=True, effective_speculative_n_max=None, draft_n=0)
        enabled = dict(base, scenario='v9_dsv4_q8_dspark_request_nmax3',
                       effective_speculative_n_max=3, draft_n=2)
        self.assertEqual(m.evaluate_dspark_parity([disabled, enabled])['status'], 'pass')
        disabled['draft_n'] = None
        self.assertEqual(m.evaluate_dspark_parity([disabled, enabled])['status'], 'fail')
        disabled['draft_n'] = 0; disabled['server_no_draft'] = False
        self.assertEqual(m.evaluate_dspark_parity([disabled, enabled])['status'], 'fail')


if __name__ == '__main__':
    unittest.main()
