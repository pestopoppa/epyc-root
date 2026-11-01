import importlib.util
import tempfile
import unittest
from pathlib import Path

p = Path(__file__).with_name('bind.py')
spec = importlib.util.spec_from_file_location('bind', p)
bind = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bind)


class BindingTest(unittest.TestCase):
    def test_mutation_and_extra_files_are_visible(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'src'
            root.mkdir()
            item = root / 'a'
            item.write_bytes(b'one')
            tool = Path(d) / 'compiler'
            tool.write_bytes(b'compiler')
            initial = bind.snapshot(root, {'compiler': tool})
            item.write_bytes(b'two')
            self.assertNotEqual(initial, bind.snapshot(root, {'compiler': tool}))
            item.write_bytes(b'one')
            (root / 'added').write_bytes(b'new')
            self.assertNotEqual(initial, bind.snapshot(root, {'compiler': tool}))
            (root / 'added').unlink()
            tool.write_bytes(b'different')
            self.assertNotEqual(initial, bind.snapshot(root, {'compiler': tool}))

    def test_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'src'
            root.mkdir()
            (root / 'outside').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                bind.source_manifest(root)

    def test_mode_changes_are_visible(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            item = root / 'a'
            item.write_bytes(b'a')
            before = bind.source_manifest(root)
            item.chmod(0o755)
            self.assertNotEqual(before, bind.source_manifest(root))


if __name__ == '__main__':
    unittest.main()
