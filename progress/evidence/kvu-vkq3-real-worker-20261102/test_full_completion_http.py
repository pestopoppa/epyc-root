"""Native per-arm HTTP statuses must gate a completed paired result."""
import json
from pathlib import Path
import tempfile
import unittest

import completion
import worker


class FullCompletionTests(unittest.TestCase):
    def result(self, hybrid_status=200, legacy_status=200):
        arms = {
            'hybrid': {'http_status': hybrid_status, 'acceptance': 0.5, 'tokens': [1, 2, 3]},
            'legacy': {'http_status': legacy_status, 'acceptance': 0.25, 'tokens': [1, 7, 3]},
        }
        return worker.full_terminal(arms)

    def complete(self, record):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
            path = Path(tmp) / 'terminal.json'
            path.write_text(json.dumps(record))
            return completion.complete('full', path)

    def test_both_http_200_complete_and_preserve_statuses(self):
        terminal = self.result()
        self.assertEqual(terminal['hybrid_http_status'], 200)
        self.assertEqual(terminal['legacy_http_status'], 200)
        self.assertEqual(terminal['first_divergence_index'], 1)
        self.assertTrue(self.complete(terminal))

    def test_non_200_or_missing_status_is_incomplete(self):
        for left, right in ((201, 200), (200, 201), (None, 200), (200, None)):
            with self.subTest(hybrid=left, legacy=right):
                terminal = self.result(left, right)
                self.assertEqual(terminal['state'], 'incomplete_raw')
                self.assertFalse(terminal['divergence_known'])
                self.assertFalse(self.complete(terminal))

    def test_forged_complete_or_old_terminal_without_status_is_refused(self):
        terminal = self.result()
        terminal['legacy_http_status'] = 201
        self.assertFalse(self.complete(terminal))
        del terminal['legacy_http_status']
        self.assertFalse(self.complete(terminal))

    def test_missing_native_counts_never_completes(self):
        terminal = worker.full_terminal({'hybrid': {'http_status': 200, 'acceptance': None, 'tokens': [1]},
                                         'legacy': {'http_status': 200, 'acceptance': 0.5, 'tokens': [1]}})
        self.assertFalse(self.complete(terminal))


if __name__ == '__main__':
    unittest.main()
