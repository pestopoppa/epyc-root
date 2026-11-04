import copy
import unittest
from bind_capture import bind_capture, Unknown


def fixture():
    ident = dict(run_id='r', pid=4, birth=5, request_id='req', task_id=7, slot=2)
    req, start, capture, end = [dict(ident, event_seq=i) for i in range(1, 5)]
    start['complete_stream'] = end['complete_stream'] = True
    end['outcome'] = 'completed'
    capture.update(kind='decode_boundary', rows=[{'index': 0, 'task_id': 7, 'slot': 2}, {'index': 1, 'task_id': 8, 'slot': 3}])
    return [req, start, capture, end]


class BindingTests(unittest.TestCase):
    def test_unique_ordered_capture(self):
        self.assertEqual(bind_capture(*fixture()), 0)

    def test_identity_mutations_refuse(self):
        for key, value in [('run_id', 'another'), ('pid', 9), ('birth', 9), ('request_id', 'other'), ('task_id', 8), ('slot', 3)]:
            for i in range(1, 4):
                events = fixture(); events[i][key] = value
                with self.subTest(key=key, event=i), self.assertRaises(Unknown): bind_capture(*events)

    def test_missing_and_boolean_id_refuse(self):
        events = fixture(); del events[2]['slot']
        with self.assertRaises(Unknown): bind_capture(*events)
        events = fixture(); events[0]['task_id'] = True
        with self.assertRaises(Unknown): bind_capture(*events)

    def test_order_and_completion(self):
        for key, val, i in [('event_seq', 2, 2), ('complete_stream', False, 1), ('complete_stream', False, 3), ('outcome', 'aborted', 3), ('kind', 'allocator', 2)]:
            events = fixture(); events[i][key] = val
            with self.subTest(key=key), self.assertRaises(Unknown): bind_capture(*events)

    def test_ambiguous_rows(self):
        for row in [{'index': 0, 'task_id': 99, 'slot': 99}, {'index': 2, 'task_id': 7, 'slot': 2}, {'index': 2, 'task_id': 7, 'slot': 99}, {'index': 2, 'task_id': 99, 'slot': 2}]:
            events = fixture(); events[2]['rows'].append(copy.copy(row))
            with self.subTest(row=row), self.assertRaises(Unknown): bind_capture(*events)

    def test_missing_or_invalid_rows(self):
        for rows in [[], [{'index': 0, 'task_id': 8, 'slot': 3}], [{'index': True, 'task_id': 7, 'slot': 2}], [None]]:
            events = fixture(); events[2]['rows'] = rows
            with self.subTest(rows=rows), self.assertRaises(Unknown): bind_capture(*events)

if __name__ == '__main__': unittest.main()
