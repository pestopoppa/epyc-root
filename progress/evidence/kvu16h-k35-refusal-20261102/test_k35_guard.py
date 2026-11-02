"""Offline checks for an uninstalled, hash-bound K35 refusal patch."""
import argparse
import dataclasses
import hashlib
import importlib.util
from pathlib import Path
import shutil
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


if __name__ == '__main__':
    unittest.main()
