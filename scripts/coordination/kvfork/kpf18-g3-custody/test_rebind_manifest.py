import hashlib
from pathlib import Path
import tempfile
import unittest
import importlib.util
spec = importlib.util.spec_from_file_location('rebind_manifest', Path(__file__).with_name('rebind_manifest.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
rebind = module.rebind

class RebindTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.d = Path(self.temp.name)
        self.original = self.d / 'original'
        self.original.write_bytes(b'original')
        self.copy = self.d / 'copy'
        self.copy.write_bytes(b'original')
        self.manifest = self.d / 'source.sha256'
        self.manifest.write_text(f'{hashlib.sha256(b"original").hexdigest()}  {self.original}\n')
        self.out = self.d / 'out.sha256'
    def test_matching_replacement(self):
        rebind(self.manifest, {str(self.original): str(self.copy)}, self.out)
        self.assertIn(str(self.copy), self.out.read_text())
        self.assertIn(str(self.original), self.manifest.read_text())
    def test_wrong_and_missing_refuse_without_output(self):
        self.copy.write_bytes(b'changed')
        with self.assertRaises((ValueError, OSError)): rebind(self.manifest, {str(self.original): str(self.copy)}, self.out)
        self.copy.unlink()
        with self.assertRaises((ValueError, OSError)): rebind(self.manifest, {str(self.original): str(self.copy)}, self.out)
        self.assertFalse(self.out.exists())
    def test_symlink_refused(self):
        self.copy.unlink(); self.copy.symlink_to(self.original)
        with self.assertRaises((ValueError, OSError)): rebind(self.manifest, {str(self.original): str(self.copy)}, self.out)
    def test_unbound_duplicate_and_source_overwrite_refused(self):
        with self.assertRaises((ValueError, OSError)): rebind(self.manifest, {'/unbound': str(self.copy)}, self.out)
        with self.assertRaises((ValueError, OSError)): rebind(self.manifest, {}, self.manifest)
        self.manifest.write_text(self.manifest.read_text() * 2)
        with self.assertRaises((ValueError, OSError)): rebind(self.manifest, {}, self.out)
    def test_existing_output_never_overwritten(self):
        self.out.write_text('preserve')
        with self.assertRaises((ValueError, OSError)): rebind(self.manifest, {}, self.out)
        self.assertEqual(self.out.read_text(), 'preserve')

    def test_symlink_ancestors_refused_for_input_and_output(self):
        alias = self.d / 'alias'
        alias.symlink_to(self.d, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            rebind(self.manifest, {str(self.original): str(alias / 'copy')}, self.out)
        with self.assertRaises((ValueError, OSError)):
            rebind(self.manifest, {}, alias / 'new-output')
        self.assertFalse((self.d / 'new-output').exists())

    def test_missing_unmapped_refused(self):
        self.original.unlink()
        with self.assertRaises((ValueError, OSError)): rebind(self.manifest, {}, self.out)
        self.assertFalse(self.out.exists())

if __name__ == '__main__': unittest.main()
