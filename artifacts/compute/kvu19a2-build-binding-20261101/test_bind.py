import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_unreadable_subdirectory_refuses_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            hidden = root / 'hidden'
            hidden.mkdir()
            (hidden / 'unit.c').write_text('int x;')
            real_scandir = os.scandir

            def refuse_hidden(path):
                if Path(path) == hidden:
                    raise PermissionError('simulated unreadable directory')
                return real_scandir(path)

            with patch.object(bind.os, 'scandir', side_effect=refuse_hidden):
                with self.assertRaises(PermissionError):
                    bind.source_manifest(root)

    def test_fifo_refused_without_a_writer(self):
        with tempfile.TemporaryDirectory() as d:
            fifo = Path(d) / 'source.fifo'
            os.mkfifo(fifo)
            with self.assertRaisesRegex(ValueError, 'not a regular file'):
                bind.source_manifest(Path(d))


if __name__ == '__main__':
    unittest.main()
