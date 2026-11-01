import unittest
from lifecycle import InvalidRun, run_pair


class Runtime:
    def __init__(self):
        self.started, self.stopped, self.calls = [], [], []
        self.bad_identity = False
        self.cache = 100
        self.bad_occupancy = False
    def start(self, variant):
        self.started.append(variant)
        return variant
    def identity(self, handle):
        return 'drafted' if self.bad_identity else handle
    def prepare_occupancy(self, handle, case):
        return {'verified': not self.bad_occupancy, 'arm': handle,
                'comparison': {'neighbors': 2, 'prefix_sha256': 'same'}}
    def request(self, handle, payload):
        self.calls.append((handle, payload))
        return {'timings': {'cache_n': self.cache}}
    def stop(self, handle):
        self.stopped.append(handle)
        return True


def case():
    return {'id':'L0', 'warm':{'messages':['same prompt'], 'max_tokens':1},
            'measure':{'messages':['same prompt'], 'max_tokens':32}, 'minimum_cache_tokens':90}


class Lifecycle(unittest.TestCase):
    def test_separate_servers_same_payloads_and_independent_warmups(self):
        rt = Runtime()
        rows = run_pair(rt, [case()])
        self.assertEqual(rt.started, ['drafted', 'nodraft'])
        self.assertEqual(rt.stopped, rt.started)
        self.assertEqual([x[0] for x in rt.calls], ['drafted','drafted','nodraft','nodraft'])
        self.assertEqual(rows[0]['measure_sha256'], rows[1]['measure_sha256'])
    def test_occupancy_mismatch_rejects_pair_after_cleanup(self):
        rt = Runtime()
        rt.prepare_occupancy = lambda handle, case: {
            'verified': True, 'comparison': {'neighbors': 1 if handle == 'drafted' else 2}}
        with self.assertRaisesRegex(InvalidRun, 'occupancy differs'):
            run_pair(rt, [case()])
        self.assertEqual(rt.stopped, ['drafted', 'nodraft'])

    def test_missing_occupancy_comparison_stops_first_arm(self):
        rt = Runtime()
        rt.prepare_occupancy = lambda handle, case: {'verified': True}
        with self.assertRaisesRegex(InvalidRun, 'occupancy comparison missing'):
            run_pair(rt, [case()])
        self.assertEqual(rt.stopped, ['drafted'])

    def test_unverified_cleanup_refuses_second_arm(self):
        for value in (False, None):
            rt = Runtime()
            def stop(handle):
                rt.stopped.append(handle)
                return value
            rt.stop = stop
            with self.assertRaisesRegex(InvalidRun, 'cleanup unverified'):
                run_pair(rt, [case()])
            self.assertEqual(rt.started, ['drafted'])
            self.assertEqual(rt.stopped, ['drafted'])

    def test_cleanup_exception_refuses_second_arm(self):
        rt = Runtime()
        def stop(handle):
            rt.stopped.append(handle)
            raise RuntimeError('no cleanup proof')
        rt.stop = stop
        with self.assertRaisesRegex(RuntimeError, 'no cleanup proof'):
            run_pair(rt, [case()])
        self.assertEqual(rt.started, ['drafted'])

    def test_no_request_override_before_start(self):
        c=case(); c['measure']['speculative.n_max']=0
        rt=Runtime()
        with self.assertRaises(InvalidRun): run_pair(rt, [c])
        self.assertEqual(rt.started, [])
    def test_mismatch_stops_second_server(self):
        rt=Runtime(); rt.bad_identity=True
        with self.assertRaises(InvalidRun): run_pair(rt, [case()])
        self.assertEqual(rt.stopped, ['drafted','nodraft'])
    def test_missing_cache_or_occupancy_stops_server(self):
        for mode in ('cache','occupancy'):
            rt=Runtime(); rt.cache = None if mode == 'cache' else 100
            rt.bad_occupancy = mode == 'occupancy'
            with self.assertRaises(InvalidRun): run_pair(rt, [case()])
            self.assertEqual(rt.stopped, ['drafted'])

if __name__ == '__main__': unittest.main()
