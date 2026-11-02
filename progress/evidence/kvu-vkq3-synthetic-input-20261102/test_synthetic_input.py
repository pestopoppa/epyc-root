import hashlib
import io
from pathlib import Path
import subprocess
import sys
import unittest

import synthetic_input

EXPECTED_SIZE = 4_550_000
EXPECTED_SHA256 = 'e354df7f35d62a98716b1d0c37ddf1dbedc3ce69f9722286d8f8f19c865d5417'


class SyntheticInputTest(unittest.TestCase):
    def test_fixed_identity_through_cli(self):
        script = Path(synthetic_input.__file__)
        first = subprocess.run([sys.executable, '-B', str(script)], check=True, capture_output=True)
        second = subprocess.run([sys.executable, '-B', str(script)], check=True, capture_output=True)
        self.assertEqual(first.stderr, b'')
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(len(first.stdout), EXPECTED_SIZE)
        self.assertEqual(hashlib.sha256(first.stdout).hexdigest(), EXPECTED_SHA256)
        self.assertEqual(first.stdout.count(b'\n'), 70_000)

    def test_streaming_writes_are_bounded_and_binary(self):
        class CountingSink:
            count = 0
            total = 0
            def write(self, data):
                self.assert_bytes(data)
                self.count += 1
                self.total += len(data)
            @staticmethod
            def assert_bytes(data):
                if not isinstance(data, bytes) or len(data) != 65:
                    raise AssertionError('unexpected record')
        sink = CountingSink()
        synthetic_input.generate(sink)
        self.assertEqual((sink.count, sink.total), (70_000, EXPECTED_SIZE))

    def test_record_boundaries(self):
        out = io.BytesIO()
        synthetic_input.generate(out)
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], b'sample=00000 value=104729 category=00 synthetic diagnostic text.')
        self.assertEqual(lines[-1], b'sample=69999 value=425148 category=10 synthetic diagnostic text.')


if __name__ == '__main__':
    unittest.main()
