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
             patch('analyze_timed_run.correlate_residency', return_value=[{'status':'UNKNOWN'}, {'status':'UNKNOWN'}]):
            self.assertEqual(analyze(**self.kw)['status'], 'UNKNOWN')

    def test_match_is_attributed_to_its_specific_dispatch(self):
        join = [{'invocation':1, 'status':'UNKNOWN', 'native_dispatch':1001.01},
                {'invocation':1, 'status':'BOUNDED_OBSERVATION', 'native_dispatch':1001.02}]
        with patch('analyze_timed_run.classify_invocation_trace_v5', return_value=self.parsed), \
             patch('analyze_timed_run.correlate_residency', return_value=join):
            result = analyze(**self.kw)
        self.assertEqual(result['status'], 'PARTIAL_SCOPED_DISPATCH_OBSERVED')
        self.assertFalse(result['vec_observed'])
        self.assertEqual(result['observed'][0]['kernel'], 200)
        self.assertFalse(result['coverage']['complete'])
        self.assertEqual(result['coverage']['bounded_dispatches'], 1)

    def test_bad_trace_is_unknown(self):
        with patch('analyze_timed_run.classify_invocation_trace_v5', side_effect=ValueError('bad')):
            self.assertEqual(analyze(**self.kw)['status'], 'UNKNOWN')


class NativeCoverageTest(unittest.TestCase):
    """Real V5 parser and residency join over model-free two-layer traces."""
    def setUp(self):
        from test_invocation_trace_v3 import B, D, E
        def stamped(line, seconds):
            return line + ' time_ns=' + str(round(seconds * 1e9))
        second = D.replace('layer=3', 'layer=7').replace('tensor=0x123', 'tensor=0x124')
        second = second.replace('kernel=100', 'kernel=200')
        trace = '\n'.join([stamped(B, 1001.), stamped(D, 1001.01),
                           stamped(second, 1001.02), stamped(E, 1001.03)])
        self.kw = dict(trace=trace, expected_layer_ids=[3, 7], baseline=sample(1000., 500.),
                       samples=[self.resident(1001.005, 1001.006),
                                self.resident(1001.009, 1001.011)],
                       card='card0', pid=10, backend='/tmp/backend', backend_sha256='a'*64,
                       complete=True, drained=True, device={'gpu_id': 42}, pid_birth=22,
                       topology_stable=True)

    def resident(self, start, end):
        return dict(observation_start=start, observation_end=end,
                    monotonic_start=start-500., monotonic_end=end-500.,
                    pid=10, birth=22, gpu_id=42, hip_mapped=True,
                    kfd_pid_present=True, own_vram_bytes=100, device_vram_bytes=200)

    def test_partial_real_join_retains_vec_without_complete_status(self):
        result = analyze(**self.kw)
        self.assertEqual(result['status'], 'PARTIAL_SCOPED_DISPATCH_OBSERVED')
        self.assertEqual(result['coverage'], dict(expected_dispatches=2,
                         bounded_dispatches=1, unknown_dispatches=1, complete=False))
        self.assertTrue(result['vec_observed'])
        self.assertEqual(len(result['observed']), 1)
        self.assertIn('1/2 native dispatches bounded', result['reasons'][-1])

    def test_full_real_join_is_scoped_observation_only(self):
        self.kw['samples'].append(self.resident(1001.019, 1001.021))
        result = analyze(**self.kw)
        self.assertEqual(result['status'], 'SCOPED_DISPATCH_OBSERVED')
        self.assertEqual(result['coverage'], dict(expected_dispatches=2,
                         bounded_dispatches=2, unknown_dispatches=0, complete=True))
        self.assertEqual(len(result['observed']), 2)
        self.assertNotIn('PASS', result['status'])

    def test_missing_foreign_zero_or_duplicate_samples_do_not_complete_coverage(self):
        for change in ({'pid': 99}, {'birth': 23}, {'gpu_id': 99},
                       {'own_vram_bytes': 0}, {'hip_mapped': False}):
            with self.subTest(change=change):
                kw = dict(self.kw, samples=[dict(s, **change) for s in self.kw['samples']])
                result = analyze(**kw)
                self.assertEqual(result['status'], 'UNKNOWN')
                self.assertEqual(result['coverage']['bounded_dispatches'], 0)
                self.assertFalse(result['coverage']['complete'])
        for samples in ([], [self.kw['samples'][1]] * 2):
            result = analyze(**dict(self.kw, samples=samples))
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertFalse(result['coverage']['complete'])

    def test_complete_capture_requires_coverage_across_every_invocation(self):
        # Second invocation has valid trace coverage but no overlapping residency.
        second = self.kw['trace'].replace('invocation=12', 'invocation=13')
        import re
        second = re.sub(r'time_ns=(\d+)',
                        lambda m: 'time_ns=' + str(int(m[1]) + 1000000000), second)
        self.kw['trace'] += '\n' + second
        self.kw['samples'].append(self.resident(1001.019, 1001.021))
        result = analyze(**self.kw)
        self.assertEqual(result['status'], 'PARTIAL_SCOPED_DISPATCH_OBSERVED')
        self.assertEqual(result['coverage'], dict(expected_dispatches=4,
                         bounded_dispatches=2, unknown_dispatches=2, complete=False))

    def test_missing_correlations_fail_closed(self):
        with patch('analyze_timed_run.correlate_residency', return_value=[]):
            result = analyze(**self.kw)
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertIsNone(result['coverage'])
        self.assertIn('correlation count differs', result['reasons'][-1])


if __name__ == '__main__': unittest.main()
