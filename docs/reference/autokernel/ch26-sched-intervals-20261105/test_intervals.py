import unittest
from intervals import project_intervals


def e(cpu, t, prev, nxt):
    return {'cpu': cpu, 'timestamp_ns': t, 'prev_tid': prev, 'next_tid': nxt}


class Projection(unittest.TestCase):
    def setUp(self):
        self.events = [e(0, 5, 9, 1), e(0, 12, 1, 2), e(0, 18, 2, 0),
                       e(0, 25, 0, 3), e(1, 4, 0, 4), e(1, 16, 4, 1),
                       e(1, 21, 1, 0), e(1, 26, 0, 5)]
        self.kw = {'cpus': {0, 1}, 'begin_ns': 10, 'end_ns': 23,
                   'allowed_by_tid': {1: {0}, 4: {1}}}

    def test_clip_and_classify(self):
        r = project_intervals(self.events, **self.kw)
        self.assertEqual(r['by_cpu_ns']['0'], {'owned_ns': 2, 'foreign_ns': 6,
                         'idle_ns': 5, 'owned_outside_allowed_ns': 0})
        self.assertEqual(r['by_cpu_ns']['1'], {'owned_ns': 11, 'foreign_ns': 0,
                         'idle_ns': 2, 'owned_outside_allowed_ns': 5})
        self.assertEqual(r['measurement_admission'], 'none')
        self.assertEqual(r['coverage'], 'unknown')

    def test_invalid_order_and_broken_chain(self):
        for rows in (self.events[:1] + [e(0, 12, 7, 2)] + self.events[2:],
                     [self.events[1], self.events[0]] + self.events[2:]):
            with self.assertRaises(ValueError): project_intervals(rows, **self.kw)

    def test_unbracketed_and_missing_cpu(self):
        for rows in (self.events[1:], self.events[:4]):
            with self.assertRaises(ValueError): project_intervals(rows, **self.kw)

    def test_tid_overlap_rejected(self):
        rows = [e(0, 5, 0, 1), e(0, 25, 1, 0),
                e(1, 5, 0, 1), e(1, 25, 1, 0)]
        with self.assertRaisesRegex(ValueError, 'overlapping'): project_intervals(rows, **self.kw)

    def test_idle_may_overlap(self):
        rows = [e(0, 5, 1, 0), e(0, 25, 0, 1), e(1, 5, 2, 0), e(1, 25, 0, 2)]
        r = project_intervals(rows, **self.kw)
        self.assertEqual(r['by_cpu_ns']['0']['idle_ns'], 13)
        self.assertEqual(r['by_cpu_ns']['1']['idle_ns'], 13)

    def test_bad_inputs_refused(self):
        for changes in ({'allowed_by_tid': {0: {0}}}, {'cpus': {True}},
                        {'begin_ns': 23}, {'allowed_by_tid': {1: set()}}):
            with self.assertRaises(ValueError): project_intervals(self.events, **(self.kw | changes))


if __name__ == '__main__': unittest.main()
