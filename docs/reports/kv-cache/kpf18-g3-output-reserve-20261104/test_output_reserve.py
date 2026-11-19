import importlib.util
import hashlib
import tempfile
import unittest
from pathlib import Path

p = Path(__file__).with_name('output_reserve.py')
if hashlib.sha256(p.read_bytes()).hexdigest() != 'a763c65fc953c1ec2957b0b0784e7ed94f52b63985a12a6c633422460dd5d4fe':
    raise RuntimeError('candidate output reservation source changed')
spec = importlib.util.spec_from_file_location('output_reserve', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class OutputReserveTests(unittest.TestCase):
    def test_exact_reservation_boundary_and_budget(self):
        self.assertTrue(m.check(m.FLOOR + m.CAP, 0))
        with self.assertRaises(RuntimeError): m.check(m.FLOOR + m.CAP - 1, 0)
        with self.assertRaises(RuntimeError): m.check(m.FLOOR, m.CAP)
        self.assertTrue(m.check(m.FLOOR + 1, m.CAP - 1))
    def test_invalid_values_fail_closed(self):
        for free, used in ((-1, 0), (0, -1), (True, 0), (0, 1.5)):
            with self.subTest(free=free, used=used):
                with self.assertRaises(ValueError): m.check(free, used)
    def test_symlink_output_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'root'; root.mkdir()
            (root/'external').symlink_to('/tmp')
            with self.assertRaisesRegex(RuntimeError, 'symlink'): m.owned_bytes(root)
    def test_sparse_bytes_counted_by_logical_size(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'sparse'
            with p.open('wb') as f: f.truncate(1024*1024)
            self.assertGreaterEqual(m.owned_bytes(d), 1024*1024)

if __name__ == '__main__': unittest.main()
