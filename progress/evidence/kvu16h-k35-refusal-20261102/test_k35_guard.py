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
            with self.assertRaises(ValueError):
                m.build_chat_request_body(scenario, 'prompt', max_tokens=8)

    def test_prebuilt_argv_refused_before_files_or_process(self):
        m = self.mod
        scenario = dataclasses.replace(m.SCENARIOS[0], request_spec_n_max=0,
                                       draft_model=None, spec_type='none')
        cell = {'scenario': scenario.name, 'nominal_context': 2048,
                'server_argv': ['/fake/server', '-md', 'draft.gguf']}
        output = Path(self.tmp.name) / 'untouched'
        with mock.patch.object(m, 'scenario_by_name', return_value=scenario), \
             mock.patch.object(m.subprocess, 'Popen') as popen:
            with self.assertRaises(ValueError):
                m.run_cell(cell, argparse.Namespace(), output)
        popen.assert_not_called()
        self.assertFalse(output.exists())

    def test_no_override_still_builds_normal_request(self):
        m = self.mod
        scenario = dataclasses.replace(m.SCENARIOS[0], request_spec_n_max=None)
        body = m.build_chat_request_body(scenario, 'prompt', max_tokens=8)
        self.assertNotIn('speculative.n_max', body)


if __name__ == '__main__':
    unittest.main()
