import json
import tempfile
import unittest
from pathlib import Path
import cohort_audit

class CoverageKeyTests(unittest.TestCase):
    def audit(self, records, expected):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'requests.jsonl'
            path.write_text(''.join(json.dumps(x) + '\n' for x in records))
            return cohort_audit.audit_coverage(expected, path)

    def test_boolean_true_cannot_masquerade_as_turn_one(self):
        result = self.audit([{'session': 'p', 'k': True}], [('p', 1)])
        self.assertFalse(result['complete'])
        self.assertEqual(result['malformed'], 1)
        self.assertEqual(result['missing'], [('p', 1)])

    def test_boolean_false_cannot_masquerade_as_turn_zero(self):
        result = self.audit([{'session': 'p', 'k': False}], [('p', 0)])
        self.assertFalse(result['complete'])
        self.assertEqual(result['malformed'], 1)
        self.assertEqual(result['missing'], [('p', 0)])

    def test_integer_turns_remain_eligible(self):
        result = self.audit([{'session': 'p', 'k': 0}, {'session': 'p', 'k': 1}], [('p', 0), ('p', 1)])
        self.assertTrue(result['complete'])

if __name__ == '__main__':
    unittest.main()
