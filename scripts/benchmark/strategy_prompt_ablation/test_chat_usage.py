"""Model-free checks of actual /chat usage field semantics."""
import unittest
from chat_usage import request_usage


def valid():
    return {'real_mode': True, 'mock_mode': False, 'turns': 2,
            'prompt_tokens': 17, 'output_tokens_reported': 4,
            'output_tokens_status': 'reported', 'output_tokens_sources': ['timings.predicted_n']}


class UsageTest(unittest.TestCase):
    def test_request_total_is_not_per_turn_or_estimated(self):
        r = request_usage(valid())
        self.assertEqual((r['scope'], r['turns'], r['prompt_tokens'], r['output_tokens']),
                         ('request_total', 2, 17, 4))
        self.assertTrue(r['complete'])
        self.assertFalse(r['identity_verified'])
        self.assertFalse(r['grant_verified'])

    def test_missing_usage_never_becomes_zero_or_legacy_estimate(self):
        response = valid(); response.update(prompt_tokens=None, output_tokens_reported=None,
                                           output_tokens_status='unknown', output_tokens_sources=[],
                                           tokens_used=100, tokens_generated=33)
        r = request_usage(response)
        self.assertFalse(r['complete'])
        self.assertIsNone(r['prompt_tokens']); self.assertIsNone(r['output_tokens'])

    def test_mock_and_invalid_counters_fail_closed(self):
        for changes in ({'mock_mode': True}, {'turns': True}, {'prompt_tokens': -1},
                        {'output_tokens_status': 'unknown'}, {'output_tokens_sources': []},
                        {'error': 'failed'}):
            response = valid(); response.update(changes)
            self.assertFalse(request_usage(response)['complete'])


if __name__ == '__main__':
    unittest.main()
