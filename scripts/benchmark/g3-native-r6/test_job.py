"""Model-free tests for the row wrapper's native terminal handling."""
import unittest
from job import result_exit_code


def record(*codes, drained=True):
    return {'cells': {str(i): {'rc': rc, 'result': {
        'process_group_drained': drained}} for i, rc in enumerate(codes)}}


class NativeExitTests(unittest.TestCase):
    def test_smoke_stop_after_control(self):
        self.assertEqual(result_exit_code(record(0, 75)), 75)

    def test_stop_before_first_control(self):
        self.assertEqual(result_exit_code(record(75)), 75)

    def test_undrained_stop_is_failure(self):
        self.assertEqual(result_exit_code(record(0, 75, drained=False)), 1)

    def test_failure_is_not_hidden_by_stop(self):
        self.assertEqual(result_exit_code(record(1, 75)), 1)

    def test_complete_six_cells(self):
        self.assertEqual(result_exit_code(record(*([0] * 6))), 0)

    def test_partial_success_is_not_complete(self):
        self.assertEqual(result_exit_code(record(0)), 1)
        self.assertEqual(result_exit_code(record()), 1)


if __name__ == '__main__':
    unittest.main()
