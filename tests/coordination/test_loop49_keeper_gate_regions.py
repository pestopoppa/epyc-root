"""Region binding at the keeper's exclusive grant boundary."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/coordination'))
import loop49_keeper_gate as gate


class GrantRegionBinding(unittest.TestCase):
    def test_relocatable_quarter_accepts_full_quarter_with_smt(self):
        self.assertTrue(gate.validate_regions('any-cpu-quarter', 'q2'))

    def test_relocatable_quarter_rejects_wrong_cpu_slice(self):
        with self.assertRaisesRegex(gate.Refused, 'outside-relocatable'):
            gate.validate_regions('any-cpu-quarter', '0-23')

    def test_relocatable_quarter_rejects_unauthorized_gpu(self):
        with self.assertRaisesRegex(gate.Refused, 'outside-relocatable'):
            gate.validate_regions('any-cpu-quarter', 'q2,mi210_0')

    def test_any_of_is_limited_to_declared_quarters(self):
        self.assertTrue(gate.validate_regions('any-of q1,q3', 'q3'))
        with self.assertRaisesRegex(gate.Refused, 'outside-relocatable'):
            gate.validate_regions('any-of q1,q3', 'q2')

    def test_fixed_regions_require_subset_and_gpu_parity(self):
        self.assertTrue(gate.validate_regions('q1,mi210_0', '24-25,mi210_0'))
        with self.assertRaisesRegex(gate.Refused, 'outside-manifest'):
            gate.validate_regions('q1,mi210_0', '24-25')

    def test_duplicate_and_empty_tokens_refused(self):
        for value in ('q1,q1', 'q1,', ''):
            with self.subTest(value=value), self.assertRaises(gate.Refused):
                gate.validate_regions('any-cpu-quarter', value)


if __name__ == '__main__':
    unittest.main()
