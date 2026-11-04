import unittest
from unittest.mock import patch
from analyze_timed_run import analyze, clocks_stable


def sample(wall, mono):
    return {'observation_start': wall, 'observation_end': wall + 0.01,
            'monotonic_start': mono, 'monotonic_end': mono + 0.01}


class AnalysisTest(unittest.TestCase):
    def setUp(self):
        self.kw = {'trace': 'trace', 'expected_layer_ids': [3], 'baseline': sample(1000., 500.),
                   'samples': [sample(1001., 501.)], 'card': 'card0', 'pid': 10, 'backend': '/tmp/backend',
                   'backend_sha256': 'a'*64, 'complete': True, 'drained': True, 'device': {'gpu_id': 42}, 'pid_birth': 22, 'topology_stable': True}
        self.parsed = {'status': 'OBSERVED', 'candidates': [{'invocation': 1, 'draft_length': 2,
                     'dispatches': [{'kernel': 100, 'layer': 3}, {'kernel': 200, 'layer': 7}],
                     'native_timing': [{'native_dispatch': 1001.01}, {'native_dispatch': 1001.02}]}]}

    def test_clock_missing_and_step_fail_closed(self):
        self.assertFalse(clocks_stable([{'observation_start': 1}]))
        self.assertFalse(clocks_stable([sample(1000, 500), sample(1003, 501)]))
        self.assertTrue(clocks_stable([sample(1000, 500), sample(1001, 501)]))

    def test_nonfinite_clock_refused_in_any_position(self):
        for invalid in (float('nan'), float('inf'), float('-inf')):
            for key in ('observation_start', 'observation_end', 'monotonic_start', 'monotonic_end'):
                bad = sample(1001, 501); bad[key] = invalid
                with self.subTest(invalid=invalid, key=key):
                    self.assertFalse(clocks_stable([sample(1000, 500), bad]))

    def test_incomplete_or_unstable_is_unknown(self):
        self.kw['complete'] = False
        self.assertEqual(analyze(**self.kw)['status'], 'UNKNOWN')
        self.kw['complete'] = True
        self.kw['samples'] = [sample(2000, 501)]
        self.assertEqual(analyze(**self.kw)['status'], 'UNKNOWN')

    def test_no_matched_dispatch_is_unknown(self):
        with patch('analyze_timed_run.classify_invocation_trace_v5', return_value=self.parsed), \
             patch('analyze_timed_run.correlate_residency', return_value=[{'status':'UNKNOWN'}]):
            self.assertEqual(analyze(**self.kw)['status'], 'UNKNOWN')

    def test_match_is_attributed_to_its_specific_dispatch(self):
        join = [{'invocation':1, 'status':'BOUNDED_OBSERVATION', 'native_dispatch':1001.02}]
        with patch('analyze_timed_run.classify_invocation_trace_v5', return_value=self.parsed), \
             patch('analyze_timed_run.correlate_residency', return_value=join):
            result = analyze(**self.kw)
        self.assertEqual(result['status'], 'SCOPED_DISPATCH_OBSERVED')
        self.assertFalse(result['vec_observed'])
        self.assertEqual(result['observed'][0]['kernel'], 200)

    def test_bad_trace_is_unknown(self):
        with patch('analyze_timed_run.classify_invocation_trace_v5', side_effect=ValueError('bad')):
            self.assertEqual(analyze(**self.kw)['status'], 'UNKNOWN')


if __name__ == '__main__': unittest.main()
