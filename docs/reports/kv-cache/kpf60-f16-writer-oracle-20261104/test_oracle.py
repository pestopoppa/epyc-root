import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from oracle import EXPECTED, compare


def independent_synthetic_fixture():
    # Separate construction from producer-style cell ranges, not oracle hex.
    data = bytearray(struct.pack('<II', 0, 2))
    for value in (False, True):
        for layer in (0, 1):
            data.extend(struct.pack('<iQ', 1, 8))
            tensor = bytes((i + layer * 31 + (79 if value else 0)) & 255
                           for i in range(64))
            for start, end in ((1, 3), (5, 6)):
                data.extend(tensor[start * 8:end * 8])
    return bytes(data)


class OracleTests(unittest.TestCase):
    def test_independently_built_fixture_matches_literal(self):
        self.assertEqual(len(EXPECTED), 152)
        self.assertEqual(compare(independent_synthetic_fixture()),
                         (True, 'all 152 bytes match the fixed fixture oracle'))

    def test_every_single_byte_mutation_is_refused(self):
        for offset in range(152):
            mutant = bytearray(EXPECTED)
            mutant[offset] ^= 1
            ok, message = compare(bytes(mutant))
            self.assertFalse(ok)
            self.assertTrue(message.startswith(f'byte {offset}:'))

    def test_equal_size_payload_reordering_and_duplicate_cell_refused(self):
        # K0 payload begins after 8-byte header and its 12-byte type/row header.
        for mutant in (EXPECTED[:20] + EXPECTED[28:36] + EXPECTED[20:28] + EXPECTED[36:],
                       EXPECTED[:36] + EXPECTED[20:28] + EXPECTED[44:]):
            self.assertEqual(len(mutant), len(EXPECTED))
            self.assertFalse(compare(mutant)[0])

    def test_length_and_type_refusals(self):
        for blob in (EXPECTED[:-1], EXPECTED + b'\0', b''):
            self.assertFalse(compare(blob)[0])
        with self.assertRaises(TypeError):
            compare(bytearray(EXPECTED))

    def test_cli_reports_actual_result_and_missing_input(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'blob'
            path.write_bytes(EXPECTED)
            cmd = [sys.executable, str(Path(__file__).with_name('oracle.py')), str(path)]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            path.write_bytes(EXPECTED[:-1])
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 1)
            path.unlink()
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)


if __name__ == '__main__':
    unittest.main()
