import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_unreadable_subtree_refuses_partial_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'visible').write_bytes(b'\x7fELFvisible')
            hidden = root / 'hidden'
            hidden.mkdir()
            (hidden / 'lib.so').write_bytes(b'\x7fELFhidden')
            actual_scandir = os.scandir

            def refuse_hidden(path):
                if Path(path) == hidden:
                    raise PermissionError('simulated unreadable subtree')
                return actual_scandir(path)

            with patch.object(m.os, 'scandir', side_effect=refuse_hidden):
                with self.assertRaises(PermissionError):
                    m.inventory(root)


if __name__ == '__main__':
    unittest.main()
