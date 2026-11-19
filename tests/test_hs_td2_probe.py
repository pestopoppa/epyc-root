import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('probe', Path(__file__).parents[1] / 'scripts/harness/hs_td2_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class SelfCheckTests(unittest.TestCase):
    def response(self, content, finish='stop'):
        return {'choices': [{'finish_reason': finish, 'message': {'content': content}}]}

    def test_valid_negative_is_not_failure(self):
        value = probe.decision(self.response('{"satisfied":false,"confidence":0.8,"reason":"missing output"}'))
        self.assertFalse(value['satisfied'])

    def test_invalid_judgments_stay_unknown(self):
        for content in ('{}', '{"satisfied":"yes","confidence":1,"reason":"ok"}',
                        '{"satisfied":true,"confidence":NaN,"reason":"ok"}',
                        '{"satisfied":true,"confidence":true,"reason":"ok"}',
                        '{"satisfied":true,"confidence":1.1,"reason":"ok"}',
                        '{"satisfied":true,"confidence":1,"reason":""}'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                probe.decision(self.response(content))

    def test_truncation_is_unknown_even_with_valid_json(self):
        with self.assertRaises(ValueError):
            probe.decision(self.response('{"satisfied":true,"confidence":1,"reason":"ok"}', 'length'))

    def test_summary_keeps_missing_and_invalid_denominator_and_excludes_smoke(self):
        rows = [{'phase': 'full', 'status': 'ok', 'elapsed_s': 2,
                 'judgment': {'satisfied': True}, 'reference_satisfied': False, 'record_path': 'a'},
                {'phase': 'full', 'status': 'unknown', 'elapsed_s': 90},
                {'phase': 'smoke', 'status': 'ok', 'elapsed_s': 999}]
        result = probe.summarize(rows, 4)
        self.assertFalse(result['complete'])
        self.assertEqual((result['valid'], result['unknown'], result['observed']), (1, 3, 2))
        self.assertEqual(result['disagreements'], ['a'])
        self.assertEqual(result['mean_valid_call_s'], 2)
        self.assertEqual(result['all_attempt_call_s'], 92)
        self.assertFalse(result['gate'])

    def test_completion_is_distinct_from_agreement(self):
        rows = [{'phase': 'full', 'status': 'unknown', 'elapsed_s': 1}]
        result = probe.summarize(rows, 1)
        self.assertTrue(result['complete'])
        self.assertEqual(result['unknown'], 1)
        self.assertIsNone(result['mean_valid_call_s'])


if __name__ == '__main__':
    unittest.main()
