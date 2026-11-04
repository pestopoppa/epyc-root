import unittest
from unittest.mock import patch
from residency_correlation import correlate_residency


class CorrelationTest(unittest.TestCase):
    def setUp(self):
        self.call = {'invocation': 1, 'native_begin': 1, 'native_dispatch': 3, 'native_end': 5}
        self.sample = {'observation_start': 2, 'observation_end': 4}
        self.args = dict(calls=[self.call], samples=[self.sample], baseline={}, card='card0',
                         pid=42, backend='/unused', expected_sha256='unused')

    @patch('residency_correlation.analyze_residency', return_value={'status': 'PASS'})
    def test_enclosing_interval(self, check):
        self.assertEqual(correlate_residency(**self.args)[0]['status'], 'BOUNDED_OBSERVATION')
        check.assert_called_once()

    @patch('residency_correlation.analyze_residency', return_value={'status': 'PASS'})
    def test_v3_missing_native_time_unknown(self, check):
        del self.call['native_dispatch']
        self.assertEqual(correlate_residency(**self.args)[0]['status'], 'UNKNOWN')
        check.assert_not_called()

    @patch('residency_correlation.analyze_residency', return_value={'status': 'PASS'})
    def test_no_join_outside_invocation_or_dispatch(self, check):
        for bounds in [(0, 4), (2, 2.5), (2, 6)]:
            self.sample['observation_start'], self.sample['observation_end'] = bounds
            self.assertEqual(correlate_residency(**self.args)[0]['status'], 'UNKNOWN')
        check.assert_not_called()

    @patch('residency_correlation.analyze_residency', return_value={'status': 'UNKNOWN'})
    def test_residency_failure_cannot_qualify(self, check):
        self.assertEqual(correlate_residency(**self.args)[0]['status'], 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
