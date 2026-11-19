import json
import tempfile
import unittest
from pathlib import Path

from capture_client import publish_capture


class AtomicPublication(unittest.TestCase):
    def test_success_publishes_complete_json(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'capture.json'
            publish_capture(output, lambda: {'ready': True, 'unit': 1})
            self.assertEqual(json.loads(output.read_text()), {'ready': True, 'unit': 1})
            self.assertEqual(list(Path(d).glob('.capture.json.pending-*')), [])

    def test_producer_failure_publishes_nothing_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'capture.json'

            def fail():
                raise RuntimeError('transport failed')

            with self.assertRaisesRegex(RuntimeError, 'transport failed'):
                publish_capture(output, fail)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(d).glob('.capture.json.pending-*')), [])

    def test_existing_destination_refuses_before_producer(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'capture.json'
            output.write_text('retained')
            called = False

            def produce():
                nonlocal called
                called = True
                return {'new': True}

            with self.assertRaises(FileExistsError):
                publish_capture(output, produce)
            self.assertFalse(called)
            self.assertEqual(output.read_text(), 'retained')
            self.assertEqual(list(Path(d).glob('.capture.json.pending-*')), [])


if __name__ == '__main__':
    unittest.main()
