import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('inventory', Path(__file__).with_name('inventory.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class InventoryTests(unittest.TestCase):
    def test_elf_bytes_and_non_elf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'lib.so').write_bytes(b'\x7fELFexample')
            (root / 'text').write_text('not an ELF')
            row = m.inventory(root)
            self.assertEqual(list(row['files']), ['lib.so'])
            self.assertEqual(row['files']['lib.so']['bytes'], 11)
    def test_empty_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                m.inventory(tmp)
    def test_outside_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'link').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                m.inventory(root)
    def test_internal_symlink_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'lib.so.1').write_bytes(b'\x7fELFx')
            (root / 'lib.so').symlink_to('lib.so.1')
            self.assertEqual(list(m.inventory(root)['files']), ['lib.so.1'])


if __name__ == '__main__':
    unittest.main()
