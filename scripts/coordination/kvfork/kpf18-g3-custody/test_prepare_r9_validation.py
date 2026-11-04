import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).absolute().parent))
from prepare_r9_validation import absolute_inventory, prepare_r9


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R9PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'q0').mkdir()
        (self.root / 'data').mkdir()
        self.native = self.root / 'native'
        self.native.write_text('native bytes')
        (self.root / 'q0/source.py').write_text('source only')
        (self.root / 'data/fixture.py').write_text('fixture only')
        (self.root / 'q0/NATIVE-SOURCES.sha256').write_text(f'{sha(self.native)}  {self.native}\n')
        (self.root / 'q0/SOURCES.sha256').write_text(f'{sha(self.root / "q0/source.py")}  source.py\n')
        (self.root / 'data/SHA256SUMS').write_text(f'{sha(self.root / "data/fixture.py")}  fixture.py\n')
        self.names = ('q0/SOURCES.sha256', 'q0/NATIVE-SOURCES.sha256', 'data/SHA256SUMS')
        self.pins = {name: sha(self.root / name) for name in self.names}
        self.mapping = self.root / 'mapping.json'
        self.mapping.write_text('{}')
        self.out = self.root / 'prepared'

    def prepare(self):
        return prepare_r9(self.out, self.mapping, self.root, self.pins)

    def test_complete_closure_preserves_originals(self):
        before = {name: (self.root / name).read_bytes() for name in self.names}
        receipt = self.prepare()
        self.assertFalse(receipt['runtime_dispatch'])
        self.assertFalse(receipt['model_files_read'])
        self.assertEqual([x['verified_entries'] for x in receipt['checks']], [1, 1, 1])
        self.assertFalse((self.out / 'INCOMPLETE').exists())
        self.assertEqual(before, {name: (self.root / name).read_bytes() for name in self.names})
        self.assertFalse((self.out / 'launch.sh').exists())

    def test_original_pin_drift_refuses_before_destination(self):
        (self.root / self.names[0]).write_text('drift')
        with self.assertRaisesRegex(ValueError, 'pin mismatch'):
            self.prepare()
        self.assertFalse(self.out.exists())

    def test_missing_native_retains_incomplete(self):
        self.native.unlink()
        with self.assertRaises(FileNotFoundError):
            self.prepare()
        self.assertTrue((self.out / 'INCOMPLETE').exists())
        self.assertFalse((self.out / 'RESULT.json').exists())

    def test_byte_equal_rebinding_and_non_equal_refusal(self):
        retained = self.root / 'retained'
        retained.write_bytes(self.native.read_bytes())
        self.mapping.write_text(json.dumps({str(self.native): str(retained)}))
        self.native.unlink()
        self.assertEqual(self.prepare()['checks'][2]['expected_paths'], [str(retained)])

    def test_changed_retained_native_refuses(self):
        self.native.write_text('changed bytes')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            self.prepare()

    def test_unknown_mapping_refuses_before_destination(self):
        self.mapping.write_text(json.dumps({'/wrong/path': '/other/path'}))
        with self.assertRaisesRegex(ValueError, 'unbound mapping'):
            self.prepare()
        self.assertFalse(self.out.exists())

    def test_model_inventory_or_mapping_refuses_before_member_read(self):
        for name in ('weights.gguf', 'FULL-MODEL.sha256'):
            with self.subTest(name=name):
                self.mapping.write_text(json.dumps({str(self.native): str(self.root / name)}))
                with self.assertRaisesRegex(ValueError, 'model input forbidden'):
                    self.prepare()
                self.assertFalse(self.out.exists())
        self.mapping.write_text('{}')
        manifest = self.root / 'q0/SOURCES.sha256'
        manifest.write_text(f'{"0" * 64}  nonexistent.gguf\n')
        self.pins['q0/SOURCES.sha256'] = sha(manifest)
        with self.assertRaisesRegex(ValueError, 'model input forbidden'):
            self.prepare()
        self.assertFalse(self.out.exists())

    def test_relative_escape_duplicate_empty_refuse(self):
        for names in ('../secret', '/absolute', 'a/./b', 'a//b', 'a\na', ''):
            raw = (f'{"a" * 64}  {names}\n').encode() if names else b''
            with self.subTest(names=names), self.assertRaises(ValueError):
                absolute_inventory(raw, self.root)
        raw = (f'{"a" * 64}  a\n' * 2).encode()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            absolute_inventory(raw, self.root)


if __name__ == '__main__':
    unittest.main()
