import copy
import importlib.util
from pathlib import Path
import unittest

_PATH = Path(__file__).resolve().parents[2] / 'scripts/harness/hs4_p6_catalog_gate.py'
_spec = importlib.util.spec_from_file_location('hs4_p6_catalog_gate', _PATH)
_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate)


class CatalogGateTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            'identity': {'model': 'model-sha', 'server': 'server-sha', 'plugin': 'plugin-sha', 'base_catalog': 'base-sha'},
            'catalogs': {'baseline': 'baseline-sha', 'candidate': 'candidate-sha'},
            'tasks': [{'id': 'task-a', 'fixture': 'fixture-sha', 'previously_passing': True}],
        }
        self.records = [
            {'task': 'task-a', 'arm': arm, 'trial': trial, 'fixture': 'fixture-sha',
             'identity': copy.deepcopy(self.manifest['identity']), 'catalog': self.manifest['catalogs'][arm],
             'outcome': 'pass', 'tokens': 100 if arm == 'baseline' else 150}
            for arm in ('baseline', 'candidate') for trial in (1, 2)
        ]

    def test_pass_and_paired_token_ratio(self):
        out = _gate.compare(self.manifest, self.records)
        self.assertEqual(out['verdict'], 'pass')
        self.assertEqual(out['tasks'][0]['candidate_to_baseline_token_ratio'], 1.5)

    def test_both_candidate_fail_blocks_and_one_failure_does_not(self):
        self.records[2]['outcome'] = 'fail'
        self.assertEqual(_gate.compare(self.manifest, self.records)['verdict'], 'pass')
        self.records[3]['outcome'] = 'fail'
        self.assertEqual(_gate.compare(self.manifest, self.records)['verdict'], 'fail')

    def test_infrastructure_and_unreproduced_baseline_are_unknown(self):
        self.records[2].update(outcome='infra_error', tokens=None)
        out = _gate.compare(self.manifest, self.records)
        self.assertEqual(out['verdict'], 'unknown')
        self.assertIsNone(out['tasks'][0]['candidate_to_baseline_token_ratio'])
        self.records[2].update(outcome='pass', tokens=150)
        self.records[0]['outcome'] = self.records[1]['outcome'] = 'fail'
        self.assertEqual(_gate.compare(self.manifest, self.records)['verdict'], 'unknown')

    def test_zero_baseline_unknown_and_missing_tokens_refused(self):
        self.records[0]['tokens'] = self.records[1]['tokens'] = 0
        self.assertEqual(_gate.compare(self.manifest, self.records)['verdict'], 'unknown')
        self.records[0]['tokens'] = None
        with self.assertRaises(ValueError):
            _gate.compare(self.manifest, self.records)

    def test_reject_missing_duplicate_or_unexpected_trial(self):
        for records in (self.records[:-1], self.records + [self.records[0]], self.records + [dict(self.records[0], trial=3)]):
            with self.subTest(length=len(records)), self.assertRaises(ValueError):
                _gate.compare(self.manifest, records)

    def test_reject_mismatched_or_unpinned_identity(self):
        for field in ('fixture', 'catalog'):
            records = copy.deepcopy(self.records)
            records[0][field] = 'other'
            with self.subTest(field=field), self.assertRaises(ValueError):
                _gate.compare(self.manifest, records)
        records = copy.deepcopy(self.records)
        records[0]['identity']['server'] = 'other'
        with self.assertRaises(ValueError):
            _gate.compare(self.manifest, records)
        self.manifest['tasks'][0]['previously_passing'] = False
        with self.assertRaises(ValueError):
            _gate.compare(self.manifest, self.records)

    def test_mixed_tasks_preserve_failure(self):
        self.manifest['tasks'].append({'id': 'task-b', 'fixture': 'fixture-b', 'previously_passing': True})
        self.records += [dict(copy.deepcopy(r), task='task-b', fixture='fixture-b') for r in self.records]
        self.records[-2]['outcome'] = self.records[-1]['outcome'] = 'fail'
        self.assertEqual(_gate.compare(self.manifest, self.records)['verdict'], 'fail')


if __name__ == '__main__':
    unittest.main()
