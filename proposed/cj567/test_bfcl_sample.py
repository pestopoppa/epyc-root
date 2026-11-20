import copy
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from bfcl_sample import CATEGORIES, UPSTREAM, prepare, select


class SampleControls(unittest.TestCase):
    def setUp(self):
        self.frame = {c: [f'{c}_{i}' for i in range(40)] for c in CATEGORIES}

    def test_reproducible_order_independent_and_nonmutating(self):
        before = copy.deepcopy(self.frame)
        a = select(self.frame, 10, 42)
        b = select({k: list(reversed(v)) for k, v in reversed(list(self.frame.items()))}, 10, 42)
        self.assertEqual(a, b)
        self.assertEqual(self.frame, before)
        self.assertEqual(a['sample_n'], 60)
        self.assertEqual(a['population_n'], 240)
        for c, s in a['strata'].items():
            self.assertEqual(len(set(s['ids'])), 10)
            self.assertLessEqual(set(s['ids']), set(self.frame[c]))
            self.assertEqual(s['population_n'], 40)
        self.assertIsNone(a['score'])
        self.assertNotEqual(a, select(self.frame, 10, 43))

    def test_full_population_and_nested_sizes(self):
        a, b = select(self.frame, 10, 42), select(self.frame, 40, 42)
        for c in CATEGORIES:
            self.assertEqual(a['strata'][c]['ids'], b['strata'][c]['ids'][:10])
            self.assertEqual(set(b['strata'][c]['ids']), set(self.frame[c]))

    def test_rejects_wrong_scope_and_bad_ids(self):
        for change in ('missing', 'sql', 'duplicate', 'wrong', 'boolean'):
            frame = copy.deepcopy(self.frame)
            if change == 'missing':
                del frame['simple']
            elif change == 'sql':
                frame['sql'] = ['sql_0']
            elif change == 'duplicate':
                frame['simple'][1] = frame['simple'][0]
            elif change == 'wrong':
                frame['simple'][0] = 'multiple_0'
            else:
                frame['simple'][0] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                select(frame, 10, 42)

    def test_invalid_sizes_and_seeds(self):
        for n in (True, 0, -1, 41, 1.5):
            with self.subTest(n=n), self.assertRaises(ValueError):
                select(self.frame, n, 42)
        for seed in (True, -1, '42', 1.5):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                select(self.frame, 10, seed)

    def test_refuses_preparation_in_grant_before_reading(self):
        with patch.dict(os.environ, {'FILLER_ID': 'fixture'}), self.assertRaises(ValueError):
            prepare('/does-not-exist', 10, 42)

    def source(self, command, **kwargs):
        self.assertTrue(command[-1].startswith(UPSTREAM + ':'))
        if 'rev-parse' in command:
            return 'a' * 40 + '\n'
        path = command[-1]
        category = path.rsplit('BFCL_v3_', 1)[1].removesuffix('.json')
        gold = '/possible_answer/' in path
        rows = [{'id': f'{category}_{i}', **({'ground_truth': {}} if gold else
                 {'question': [[{'role': 'user', 'content': 'fixture'}]],
                  'function': [{'name': 'fixture'}]})} for i in range(40)]
        if self.damage == 'duplicate':
            rows[-1] = rows[0]
        elif self.damage == 'mismatch' and gold:
            rows[-1]['id'] = f'{category}_999'
        elif self.damage == 'missing_gold' and gold:
            del rows[-1]['ground_truth']
        elif self.damage == 'multiturn' and not gold:
            rows[-1]['question'].append([])
        return ('\n'.join(json.dumps(r) for r in rows) + '\n').encode()

    def test_immutable_source_bindings_without_gold_in_output(self):
        self.damage = None
        with tempfile.TemporaryDirectory() as d, patch('bfcl_sample.subprocess.check_output', self.source):
            result = prepare(d, 10, 42)
        self.assertEqual(len(result['sources']), 12)
        self.assertEqual(len(result['frame_sha256']), 64)
        self.assertNotIn('ground_truth', json.dumps(result))
        self.assertNotIn('question', json.dumps(result))
        self.assertTrue(all(v['rows'] == 40 for v in result['sources'].values()))

    def test_refuses_corrupted_source_populations(self):
        for damage in ('duplicate', 'mismatch', 'missing_gold', 'multiturn'):
            self.damage = damage
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as d, \
                    patch('bfcl_sample.subprocess.check_output', self.source), self.assertRaises(ValueError):
                prepare(d, 10, 42)


if __name__ == '__main__':
    unittest.main()
