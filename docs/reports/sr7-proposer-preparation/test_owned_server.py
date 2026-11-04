import os
from pathlib import Path
import sys
import tempfile
import unittest

from owned_server import launch_owned


class OwnedServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/speculative-decoding-mtp')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'trace'
        self.env = dict(os.environ, LD_LIBRARY_PATH='/tmp')

    def test_real_direct_child_is_reaped_and_trace_bounded(self):
        child = launch_owned([sys.executable, '-c', "print('trace', flush=True)"], self.env, self.path)
        child.process.wait(timeout=5)
        child.stop()
        self.assertEqual(child.read_trace(), b'trace\n')
        with self.assertRaises(ValueError): child.read_trace(2)
        with self.assertRaises(ValueError): child.stop()

    def test_stop_captured_live_child(self):
        child = launch_owned([sys.executable, '-c', 'import signal; signal.pause()'], self.env, self.path)
        self.addCleanup(lambda: child.process.poll() is None and child.process.kill())
        with self.assertRaises(ValueError): child.read_trace()
        child.stop()
        self.assertIsNotNone(child.process.poll())

    def test_refuses_unsafe_inputs_and_existing_trace(self):
        with self.assertRaises(ValueError): launch_owned(['relative'], self.env, self.path)
        with self.assertRaises(ValueError): launch_owned([sys.executable], {}, self.path)
        self.path.write_bytes(b'original')
        with self.assertRaises(FileExistsError): launch_owned([sys.executable], self.env, self.path)
        self.assertEqual(self.path.read_bytes(), b'original')

    def test_replaced_trace_is_rejected(self):
        child = launch_owned([sys.executable, '-c', 'pass'], self.env, self.path)
        child.process.wait(timeout=5)
        child.stop()
        self.path.rename(self.path.with_name('original'))
        self.path.write_bytes(b'fake')
        with self.assertRaisesRegex(ValueError, 'trace identity changed'): child.read_trace()


if __name__ == '__main__': unittest.main()
