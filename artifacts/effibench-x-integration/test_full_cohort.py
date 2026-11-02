"""Offline 306-item shape/denominator checks; no inference or sandbox."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('effibench_runner', HERE / 'run_python.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class FullCohortTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.dataset = root / 'dataset'
        self.solutions = root / 'solutions'
        self.evaluation = root / 'evaluation'
        self.dataset.mkdir()
        (self.solutions / 'test-model').mkdir(parents=True)
        (self.evaluation / 'test-model').mkdir(parents=True)
        self.expected = set(json.loads((HERE / 'dated-308.json').read_text())) - runner.EXCLUDED
        self.assertEqual(len(self.expected), 306)
        # Keep a few explicit null-code cases: their absence from evaluation is
        # expected and must not be mistaken for full correctness.
        self.attempted = set(sorted(self.expected)[3:])
        merged = {}
        for name in self.expected:
            attempted = name in self.attempted
            code = 'print(1)' if attempted else None
            (self.dataset / f'{name}.json').write_text(json.dumps({'generated_tests': json.dumps([{}, {}])}))
            (self.solutions / 'test-model' / f'{name}_python3.json').write_text(json.dumps({'raw': 'fixture', 'code': code}))
            merged[name] = {'python3': code}
            if attempted:
                (self.evaluation / 'test-model' / f'{name}_python3.json').write_text(json.dumps([{'passed': True}, {'passed': False}]))
        (self.solutions / 'test-model.json').write_text(json.dumps(merged))

    def test_full_fixture_and_null_denominators(self):
        runner.generated(self.solutions, 'test-model', self.expected)
        self.assertEqual(runner.merged(self.solutions, 'test-model', self.expected), self.attempted)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            runner.evaluation(self.dataset, self.evaluation, 'test-model', self.expected, self.attempted)
        self.assertIn('303 evaluated and 3 null-code cases of 306', out.getvalue())

    def test_missing_generated_or_extra_evaluation_is_refused(self):
        name = next(iter(self.expected))
        (self.solutions / 'test-model' / f'{name}_python3.json').unlink()
        with self.assertRaisesRegex(ValueError, 'generation incomplete'):
            runner.generated(self.solutions, 'test-model', self.expected)
        (self.evaluation / 'test-model' / 'unexpected_python3.json').write_text('[]')
        with self.assertRaisesRegex(ValueError, 'denominator'):
            runner.evaluation(self.dataset, self.evaluation, 'test-model', self.expected, self.attempted)

    def test_missing_merged_problem_and_short_test_result_are_refused(self):
        path = self.solutions / 'test-model.json'
        data = json.loads(path.read_text())
        del data[next(iter(self.expected))]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'denominator'):
            runner.merged(self.solutions, 'test-model', self.expected)
        name = next(iter(self.attempted))
        (self.evaluation / 'test-model' / f'{name}_python3.json').write_text('[{"passed": true}]')
        with self.assertRaisesRegex(ValueError, 'incomplete or malformed'):
            runner.evaluation(self.dataset, self.evaluation, 'test-model', self.expected, self.attempted)


if __name__ == '__main__':
    unittest.main()
