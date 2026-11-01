import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('reducer', Path(__file__).with_name('reduce.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class TestReducer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for n in ('q', 'k', 'v', 'mask'):
            (self.root / n).write_bytes(n.encode())
        self.rows = []
        for i, arm in enumerate(r.ORDER):
            (self.root / f'o{i}').write_bytes(arm.encode())
            row = dict(case=78, arm=arm, inputs={n:n for n in ('q','k','v','mask')}, output=f'o{i}', output_bytes=1,
                       nonfinite_count=0, executable_sha256=arm.lower()*64, mapped_libraries_sha256='c'*64,
                       source_tree_sha256='d'*64)
            row.update({k:True for k in ('normal_exit','input_capture_complete','output_capture_complete',
                                         'live_vram_and_kfd','device_gfx90a','mapping_verified','cleanup_verified')})
            self.rows.append(row)

    def result(self):
        return r.reduce(self.root, {'runs':self.rows})['78']

    def test_cross_binary_difference_is_not_nondeterminism(self):
        result = self.result()
        self.assertEqual(result['arms']['A']['verdict'], 'NO-DIFFERENCE-OBSERVED')
        self.assertFalse(result['cross_binary_equal_all'])

    def test_within_binary_difference(self):
        (self.root/'o3').write_bytes(b'Z')
        self.assertEqual(self.result()['arms']['A']['verdict'], 'OBSERVED-NONDETERMINISM')

    def test_refuses_missing_residency_or_changed_inputs(self):
        self.rows[0]['live_vram_and_kfd'] = False
        self.assertEqual(self.result()['status'], 'incomplete')
        self.rows[0]['live_vram_and_kfd'] = True
        (self.root/'different').write_bytes(b'other')
        self.rows[1]['inputs']['q'] = 'different'
        self.assertEqual(self.result()['status'], 'incomplete')

    def test_refuses_changed_identity_and_path_escape(self):
        self.rows[3]['executable_sha256'] = 'e'*64
        self.assertEqual(self.result()['status'], 'incomplete')
        self.rows[3]['executable_sha256'] = 'a'*64
        self.rows[0]['output'] = '../outside'
        self.assertEqual(self.result()['status'], 'incomplete')

    def test_incomplete_schedule(self):
        self.rows.pop()
        self.assertEqual(self.result()['status'], 'incomplete')

if __name__ == '__main__':
    unittest.main()
