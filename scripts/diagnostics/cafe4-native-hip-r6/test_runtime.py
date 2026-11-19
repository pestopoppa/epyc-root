import importlib.util
from pathlib import Path
import unittest
import tempfile

spec = importlib.util.spec_from_file_location('cafe4_native_runtime', Path(__file__).with_name('runtime.py'))
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

GOOD = '''CAFE4_MTP_LOAD_ENABLED
CAFE4_DRAFT_REWIND_V4 pos=12
CAFE4_TARGET_RS memory=0x1 seq=0 selected=1 used=1 mode=1
CAFE4_TARGET_RS memory=0x2 seq=0 selected=1 used=0 mode=2
CAFE4_MTP_ROLLBACK width=2 accepted=1 selected=1 faulted=1 off_error=0 observe_error=0 fault_error=100 off_observe=0 fault_observe=100 tolerance=0.743863867
'''


class Controls(unittest.TestCase):
    def test_normal_and_explicit_fault(self):
        self.assertIsNotNone(runtime.controls(GOOD + runtime.PASS, 0, 2, False))
        self.assertIsNotNone(runtime.controls(GOOD + runtime.FAULT, 1, 2, True))

    def test_arbitrary_failure_is_not_fault_witness(self):
        for text, rc in ((GOOD + runtime.PASS, 1), (GOOD, 1), (GOOD + runtime.FAULT, 2), (GOOD + runtime.FAULT, 0)):
            self.assertIsNone(runtime.controls(text, rc, 2, True))

    def test_nonfinite_and_failed_numeric_controls(self):
        for before, after in (('off_error=0', 'off_error=nan'), ('fault_error=100', 'fault_error=inf'),
                              ('observe_error=0', 'observe_error=1'), ('fault_observe=100', 'fault_observe=0.01'),
                              ('tolerance=0.743863867', 'tolerance=-1'), ('tolerance=0.743863867', 'tolerance=1')):
            self.assertIsNone(runtime.controls((GOOD + runtime.PASS).replace(before, after), 0, 2, False))

    def test_missing_native_controls_and_nonpartial_acceptance(self):
        for before, after in (('mode=2', 'mode=1'), ('accepted=1', 'accepted=0'),
                              ('accepted=1', 'accepted=2'), ('width=2', 'width=3'),
                              ('selected=1 faulted=1', 'selected=0 faulted=1'),
                              ('CAFE4_DRAFT_REWIND_V4', 'MISSING')):
            self.assertIsNone(runtime.controls((GOOD + runtime.PASS).replace(before, after), 0, 2, False))

    def test_duplicate_or_contradictory_results(self):
        self.assertIsNone(runtime.controls(GOOD + GOOD + runtime.PASS, 0, 2, False))
        self.assertIsNone(runtime.controls(GOOD + runtime.PASS + '\n' + runtime.FAULT, 0, 2, False))


class Residency(unittest.TestCase):
    def test_child_specific_membership_and_nonzero_vram(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(runtime.resident(runtime.residency(123, root)))
            child = root / '123'
            child.mkdir()
            (child / 'vram_7').write_text('0')
            self.assertFalse(runtime.resident(runtime.residency(123, root)))
            (child / 'vram_7').write_text('4096')
            sample = runtime.residency(123, root)
            self.assertTrue(runtime.resident(sample))
            self.assertEqual(sample['vram_bytes'], 4096)
            self.assertFalse(runtime.resident(runtime.residency(124, root)))


if __name__ == '__main__':
    unittest.main()
