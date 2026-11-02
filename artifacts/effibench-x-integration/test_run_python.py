"""Offline fail-closed checks; does not invoke inference or the sandbox."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('runner', Path(__file__).with_name('run_python.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class EvaluationChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.dataset = root / 'dataset'
        self.dataset.mkdir()
        self.output = root / 'output'
        (self.output / 'model').mkdir(parents=True)
        self.name = 'leetcode_1_example'
        (self.dataset / f'{self.name}.json').write_text(json.dumps({'generated_tests': [{}, {}]}))
        self.result = self.output / 'model' / f'{self.name}_python3.json'

    def check(self, attempted=None):
        runner.evaluation(self.dataset, self.output, 'model', {self.name}, {self.name} if attempted is None else attempted)

    def test_zero_attempts_fails(self):
        with self.assertRaisesRegex(ValueError, 'zero non-null'):
            self.check(set())

    def test_missing_or_partial_output_fails(self):
        with self.assertRaisesRegex(ValueError, 'denominator'):
            self.check()
        self.result.write_text(json.dumps([{'passed': True}]))
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.check()

    def test_malformed_and_extra_output_fail(self):
        self.result.write_text(json.dumps([{'passed': True}, {'passed': 'yes'}]))
        with self.assertRaisesRegex(ValueError, 'malformed'):
            self.check()
        self.result.write_text(json.dumps([{'passed': True}, {'passed': False}]))
        extra = self.result.parent / 'extra_python3.json'
        extra.write_text('[]')
        with self.assertRaisesRegex(ValueError, 'denominator'):
            self.check()

    def test_complete_output_accepts_failures_as_results(self):
        self.result.write_text(json.dumps([{'passed': True}, {'passed': False}]))
        self.check()


class CheckoutChecks(unittest.TestCase):
    def test_untracked_and_ignored_checkout_files_are_refused(self):
        for untracked, ignored in ((b"file.py\0", b""), (b"", b"cache.pyc\0")):
            with self.subTest(untracked=untracked, ignored=ignored):
                def git(command):
                    args = command[3:]
                    if args[:1] == ['rev-parse']:
                        return (runner.COMMIT + "\n").encode()
                    if args[:1] == ['diff']:
                        return b'patch'
                    return ignored if '--ignored' in args else untracked
                class Digest:
                    def hexdigest(self):
                        return runner.PATCH_DIGEST
                with patch.object(runner.subprocess, 'check_output', side_effect=git), patch.object(runner.hashlib, 'sha256', return_value=Digest()):
                    with self.assertRaisesRegex(ValueError, 'untracked or ignored'):
                        runner.check(Path('/tree'), Path('/dataset'), Path('/manifest'))


if __name__ == '__main__':
    unittest.main()
